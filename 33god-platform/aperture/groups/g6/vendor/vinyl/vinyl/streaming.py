"""Lossless VAD framing and progressive decode requests.

PortAudio deliberately uses 100 ms blocks (1600 samples at 16 kHz), while
Silero requires exact 512-sample windows. 1600 is not divisible by 512. The
old callers processed three windows and discarded the remaining 64 samples
from *every* callback, corrupting four percent of the microphone stream.

``VadSegmenter`` owns that impedance mismatch. It carries incomplete windows
across callbacks, emits periodic snapshots of Silero's current speech segment
for progressive decoding, and emits one final request when Silero closes the
segment. The recognizer stays single-threaded; callers put these requests on
their existing decode queue in order.
"""
from collections import deque
from dataclasses import dataclass, field
import os
import queue
import time

import numpy as np

from .vad import SAMPLE_RATE, VAD_WINDOW, MAX_SEGMENT_SECONDS, MIN_SILENCE_SECONDS

# Speed of the provisional display. These are a measured trade, not a guess:
# over 131 real segments, simulating the whole provisional sequence gave
#
#   min_audio / interval / hold   first text   retractions   chars erased
#   1.5s / 1.0s / 0 (through 0.2.8)    1.58s           131           7710
#   0.8s / 0.8s / 0 (now)              0.86s           193           8785
#   0.8s / 0.8s / 1                    1.68s            58           7281
#
# Earlier text means more first guesses that turn out wrong and have to be
# taken back. VINYL_PARTIAL_HOLD_WORDS=1 buys the stability back at the cost
# of the latency — see inject.hold_tail.
PARTIAL_INTERVAL_SECONDS = float(os.environ.get("VINYL_PARTIAL_INTERVAL", "0.8"))
PARTIAL_MIN_AUDIO_SECONDS = float(os.environ.get("VINYL_PARTIAL_MIN_AUDIO", "0.8"))
MIN_SEGMENT_SECONDS = 0.25
# Leading context handed to the recognizer when a decode comes back empty.
# 0.3s measured best over the trace corpus; 0.5s is WORSE than no pre-roll at
# all (18.3% vs 15.3% empty finals), so this is a tuned value, not a margin to
# be widened. See Recognizer.decode.
PREROLL_SECONDS = float(os.environ.get("VINYL_PREROLL", "0.3"))


@dataclass(frozen=True)
class DecodeRequest:
    segment: int
    samples: np.ndarray
    final: bool
    start_sample: int | None = None
    created_ns: int = field(default_factory=time.monotonic_ns)
    # Audio immediately preceding `samples`. Only read when the first decode
    # returns nothing; see Recognizer.decode.
    preroll: np.ndarray | None = None

    @property
    def request_id(self) -> str:
        return f"{self.segment}-{self.created_ns:x}"

    def trace_fields(self) -> dict:
        return {"request_id": self.request_id, "segment": self.segment,
                "final": self.final, "start_sample": self.start_sample,
                "samples": len(self.samples), "created_ns": self.created_ns}


class DecodeQueue(queue.Queue):
    """FIFO for decode requests where a stale partial is dead weight.

    Every partial carries the WHOLE segment from its start, so decoding and
    injecting a partial that a newer request has already superseded is pure
    cost — at 12ms/char of erase+type, a backlog of them churned for tens of
    seconds after speech stopped. A newer request for the same segment
    (partial or final) replaces a pending partial in place; finals are never
    dropped, and nothing touches requests for other segments or the None
    sentinel.
    """

    def __init__(self, maxsize=0, *, trace=None):
        super().__init__(maxsize=maxsize)
        self.trace = trace

    def _replaced(self, previous, replacement):
        if self.trace:
            self.trace.event("decode.superseded", **previous.trace_fields(),
                             replacement_id=replacement.request_id)

    def put(self, item, block: bool = True, timeout: float | None = None) -> None:
        with self.mutex:
            if isinstance(item, DecodeRequest):
                if item.final:
                    for previous in self.queue:
                        if (isinstance(previous, DecodeRequest) and not previous.final
                                and previous.segment == item.segment):
                            self._replaced(previous, item)
                    kept = deque(
                        r for r in self.queue
                        if not (isinstance(r, DecodeRequest)
                                and not r.final and r.segment == item.segment)
                    )
                    self.unfinished_tasks -= len(self.queue) - len(kept)
                    self.queue = kept
                    self.queue.append(item)
                else:
                    for i, r in enumerate(self.queue):
                        if (isinstance(r, DecodeRequest)
                                and not r.final and r.segment == item.segment):
                            self.queue[i] = item
                            self._replaced(r, item)
                            if self.trace:
                                self.trace.event("decode.queued", **item.trace_fields(), depth=len(self.queue))
                            self.not_empty.notify()
                            return
                    self.queue.append(item)
            else:
                self.queue.append(item)
            self.unfinished_tasks += 1
            if self.trace and isinstance(item, DecodeRequest):
                self.trace.event("decode.queued", **item.trace_fields(), depth=len(self.queue))
            self.not_empty.notify()


class VadSegmenter:
    """Turn arbitrary PCM blocks into ordered partial/final decode requests."""

    def __init__(self, vad, *, partial_interval: float = PARTIAL_INTERVAL_SECONDS,
                 partial_min_audio: float = PARTIAL_MIN_AUDIO_SECONDS,
                 preroll: float = PREROLL_SECONDS, trace=None):
        self.vad = vad
        self.trace = trace
        self._speech_detected = False
        self.partial_interval_samples = max(1, int(partial_interval * SAMPLE_RATE))
        self.partial_min_samples = max(1, int(partial_min_audio * SAMPLE_RATE))
        self.preroll_samples = max(0, int(preroll * SAMPLE_RATE))
        # Recent audio, so a request can carry the context that precedes it.
        # A segment is only popped MIN_SILENCE after it ends and may run to
        # MAX_SEGMENT, so the window has to reach back past both to still hold
        # the samples before that segment's start. ~31s of float32 is ~2MB,
        # next to an 800MB recognizer.
        self._history_samples = (
            self.preroll_samples
            + int((MAX_SEGMENT_SECONDS + MIN_SILENCE_SECONDS + 1) * SAMPLE_RATE)
        ) if self.preroll_samples else 0
        self._history = np.empty(0, dtype=np.float32)
        self._fed = 0
        self._remainder = np.empty(0, dtype=np.float32)
        self._segment = 0
        self._last_partial_samples = 0

    def feed(self, samples: np.ndarray) -> list[DecodeRequest]:
        samples = np.asarray(samples, dtype=np.float32).reshape(-1)
        if self._remainder.size:
            samples = np.concatenate((self._remainder, samples))

        complete = samples.size - (samples.size % VAD_WINDOW)
        self._remainder = samples[complete:].copy()
        self._remember(samples[:complete])
        requests: list[DecodeRequest] = []
        for offset in range(0, complete, VAD_WINDOW):
            self.vad.accept_waveform(samples[offset:offset + VAD_WINDOW])
            requests.extend(self._drain_finals())
            partial = self._maybe_partial()
            if partial is not None:
                requests.append(partial)
        return requests

    def flush(self) -> list[DecodeRequest]:
        if self.trace:
            self.trace.event("vad.flush", remainder_samples=self.remainder_samples)
        requests: list[DecodeRequest] = []
        if self._remainder.size:
            # Silero only accepts full windows. At most 31.9 ms of real audio is
            # padded here, once at session end; unlike the old loop, none of it
            # is discarded.
            padded = np.pad(self._remainder, (0, VAD_WINDOW - self._remainder.size))
            self._remainder = np.empty(0, dtype=np.float32)
            requests.extend(self.feed(padded))
        self.vad.flush()
        requests.extend(self._drain_finals())
        # _drain_finals has already taken the pre-roll it needs; reset() zeroes
        # the VAD's sample counter, so the history must go with it.
        self.vad.reset()
        self._forget()
        self._last_partial_samples = 0
        self._speech_detected = False
        return requests

    def reset(self) -> None:
        self.vad.reset()
        self._forget()
        self._remainder = np.empty(0, dtype=np.float32)
        self._segment = 0
        self._last_partial_samples = 0
        self._speech_detected = False

    @property
    def remainder_samples(self) -> int:
        """Exposed for diagnostics/tests; always less than one VAD window."""
        return int(self._remainder.size)

    # -- pre-roll history -------------------------------------------------

    def _remember(self, samples: np.ndarray) -> None:
        """Track recent audio alongside the VAD's own sample counter.

        ``_fed`` must advance by exactly what the VAD is fed and reset exactly
        when the VAD resets: sherpa's ``VoiceActivityDetector.reset()`` zeroes
        its absolute sample counter, so a history indexed off a counter that
        kept running would hand back the wrong audio for every later segment.
        """
        if not self._history_samples or not samples.size:
            self._fed += int(samples.size)
            return
        self._fed += int(samples.size)
        self._history = np.concatenate((self._history, samples))
        if self._history.size > self._history_samples:
            self._history = self._history[-self._history_samples:].copy()

    def _forget(self) -> None:
        self._history = np.empty(0, dtype=np.float32)
        self._fed = 0

    def _preroll_for(self, start_sample: int | None) -> np.ndarray | None:
        """The ``preroll_samples`` of audio immediately before ``start_sample``."""
        if not self._history_samples or start_sample is None:
            return None
        history_start = self._fed - self._history.size
        lo = max(history_start, start_sample - self.preroll_samples)
        i, j = lo - history_start, start_sample - history_start
        if j <= i or i < 0 or j > self._history.size:
            return None
        return self._history[i:j].copy()

    def _maybe_partial(self) -> DecodeRequest | None:
        # sherpa exposes is_speech_detected as a METHOD; older fakes used a
        # property. A bound method is always truthy, which would emit
        # partials for trailing silence — resolve either form to a bool.
        detected = self.vad.is_speech_detected
        if callable(detected):
            detected = detected()
        if self.trace and bool(detected) != self._speech_detected:
            self.trace.event("vad.speech", detected=bool(detected), segment=self._segment)
        self._speech_detected = bool(detected)
        if not detected:
            return None
        current = self.vad.current_segment
        samples = np.asarray(current.samples, dtype=np.float32)
        n = samples.size
        if n < self.partial_min_samples:
            return None
        if self._last_partial_samples and n - self._last_partial_samples < self.partial_interval_samples:
            return None
        self._last_partial_samples = n
        start = getattr(current, "start", None)
        request = DecodeRequest(self._segment, samples.copy(), False, start,
                                preroll=self._preroll_for(start))
        if self.trace:
            self.trace.event("vad.partial", **request.trace_fields())
        return request

    def _drain_finals(self) -> list[DecodeRequest]:
        requests: list[DecodeRequest] = []
        while not self.vad.empty():
            front = self.vad.front
            samples = np.asarray(front.samples, dtype=np.float32).copy()
            start_sample = getattr(front, "start", None)
            self.vad.pop()
            if samples.size > MIN_SEGMENT_SECONDS * SAMPLE_RATE:
                request = DecodeRequest(self._segment, samples, True, start_sample,
                                        preroll=self._preroll_for(start_sample))
                requests.append(request)
                if self.trace:
                    self.trace.event("vad.final", **request.trace_fields())
            elif self.trace:
                self.trace.event("vad.discarded", segment=self._segment, start_sample=start_sample,
                                 samples=len(samples), reason="segment_too_short")
            self._segment += 1
            self._last_partial_samples = 0
        return requests
