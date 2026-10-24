"""Local, replayable session traces. This module has no audio dependencies.

Producer threads only put ordered records into a bounded queue. One background
writer owns the event log and the optional, exact little-endian float32 audio.
Trace loss is counted and a manifest is only complete after the writer drains.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
import uuid

from .rpc import STATE_DIR


TRACE_DIR = STATE_DIR / "traces"
SCHEMA_VERSION = 1
QUEUE_SIZE = 2048
FINISH_TIMEOUT = 5.0
# Retention. Traces are debugging evidence for a session you are still looking at, not an
# archive: 151 of them took 14.7 GiB in five weeks (one session left listening ran 7.7 GiB).
RETAIN_DAYS = 7.0
RETAIN_MAX_BYTES = 2 * 1024 ** 3
RETAIN_MIN_KEEP = 3          # newest traces kept whatever the age/size limits say
RETAIN_IDLE_SECONDS = 3600   # a trace touched this recently may still be recording
# Raw float32 mic audio is 64 KB/s; a session left listening for two days wrote 7.2 GiB.
AUDIO_MAX_BYTES = 512 * 1024 ** 2
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}\Z")
_PRIVATE_FIELDS = frozenset({
    "token", "auth_token", "server_token", "authorization", "password",
    "secret", "api_key", "env", "environ", "environment",
})


def _enabled(name: str, default: str = "1") -> bool:
    return os.environ.get(name, default).strip().lower() not in {"0", "false", "off", "no"}


def _env_number(name: str, default: float) -> float:
    try:
        value = float(os.environ.get(name, ""))
    except ValueError:
        return default
    return value if value > 0 else default


def _tree_bytes(path: Path) -> int:
    total = 0
    for root, _dirs, files in os.walk(path):
        for name in files:
            try:
                total += os.lstat(os.path.join(root, name)).st_size
            except OSError:
                pass
    return total


def _last_touched(path: Path) -> float:
    newest = 0.0
    try:
        newest = path.stat().st_mtime
        for child in path.iterdir():
            newest = max(newest, child.lstat().st_mtime)
    except OSError:
        pass
    return newest


def prune_traces(directory: Path | None = None, *, max_age_days: float | None = None,
                 max_bytes: int | None = None, keep: int = RETAIN_MIN_KEEP,
                 protect: frozenset[str] | set[str] = frozenset(),
                 now: float | None = None, dry_run: bool = False) -> dict:
    """Delete trace directories older than `max_age_days`, then oldest-first until the rest
    fit in `max_bytes`. The newest `keep`, anything in `protect` and anything touched within
    RETAIN_IDLE_SECONDS (possibly still recording) are never removed. Only directories whose
    name is a trace id are considered; symlinks and foreign entries are left alone."""
    root = directory if directory is not None else TRACE_DIR
    max_age_days = max_age_days if max_age_days is not None else _env_number("VINYL_TRACE_RETAIN_DAYS", RETAIN_DAYS)
    max_bytes = max_bytes if max_bytes is not None else int(
        _env_number("VINYL_TRACE_RETAIN_MAX_MB", RETAIN_MAX_BYTES / 1024 ** 2) * 1024 ** 2)
    now = time.time() if now is None else now
    result = {"removed": [], "freed_bytes": 0, "kept": 0, "kept_bytes": 0, "dry_run": dry_run}
    if not root.is_dir():
        return result
    entries = []
    for path in root.iterdir():
        if not (_ID.fullmatch(path.name) and path.is_dir() and not path.is_symlink()):
            continue
        entries.append({"path": path, "touched": _last_touched(path), "bytes": _tree_bytes(path)})
    entries.sort(key=lambda entry: (entry["touched"], entry["path"].name))  # oldest first
    newest = {entry["path"].name for entry in entries[max(0, len(entries) - max(0, keep)):]}
    total = sum(entry["bytes"] for entry in entries)
    doomed = []
    for entry in entries:
        name = entry["path"].name
        if name in newest or name in protect or now - entry["touched"] < RETAIN_IDLE_SECONDS:
            continue
        if now - entry["touched"] > max_age_days * 86400 or total > max_bytes:
            doomed.append(entry)
            total -= entry["bytes"]
    for entry in doomed:
        if not dry_run:
            shutil.rmtree(entry["path"], ignore_errors=True)
        result["removed"].append(entry["path"].name)
        result["freed_bytes"] += entry["bytes"]
    result["kept"] = len(entries) - len(doomed)
    result["kept_bytes"] = total
    return result


def _safe_fields(value):
    """Avoid accidental structured credentials; dictated text remains exact."""
    if isinstance(value, dict):
        return {key: "[redacted]" if str(key).lower() in _PRIVATE_FIELDS
                else _safe_fields(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_safe_fields(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value


def _private_open(path: Path, *, binary: bool = False):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    return os.fdopen(fd, "wb" if binary else "w", **({} if binary else {"encoding": "utf-8"}))


def _write_manifest(path: Path, manifest: dict) -> None:
    temporary = path / ".manifest.tmp"
    try:
        with _private_open(temporary) as stream:
            json.dump(manifest, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path / "manifest.json")
    finally:
        temporary.unlink(missing_ok=True)


class TraceSession:
    def __init__(self, mode: str, *, metadata: dict | None = None,
                 parent_ref: str | None = None, directory: Path | None = None):
        self.enabled = _enabled("VINYL_TRACE")
        # Off unless asked for: raw audio is the bulk of the disk cost and the most private part.
        self.audio_enabled = self.enabled and _enabled("VINYL_TRACE_AUDIO", "0")
        self._audio_cap = int(_env_number("VINYL_TRACE_AUDIO_MAX_MB", AUDIO_MAX_BYTES / 1024 ** 2) * 1024 ** 2)
        self._audio_queued_bytes = 0
        self._audio_truncated = False
        self.id = ""
        self.ref = ""
        self.path: Path | None = None
        self.error = ""
        self.dropped_events = 0
        self._dropped_audio_frames = 0
        self._late_events = 0
        self._lock = threading.Lock()
        self._finish_lock = threading.Lock()
        self._closing = threading.Event()
        self._finished = threading.Event()
        self._queue: queue.Queue = queue.Queue(maxsize=QUEUE_SIZE)
        self._thread: threading.Thread | None = None
        self._seq = 0
        self._events_written = 0
        self._audio_frames = 0
        self._audio_bytes_written = 0
        self._errors: list[str] = []
        self._start_ns = time.monotonic_ns()
        self._wall_start_ns = time.time_ns()
        self._end_ns: int | None = None
        self._reason: str | None = None
        self._summary: dict = {}
        self._mode = mode
        self._metadata = _safe_fields(metadata or {})
        self._parent_ref = parent_ref
        if not self.enabled:
            return
        self.id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ-") + uuid.uuid4().hex[:8]
        self.ref = "vinyl-trace:" + self.id
        self.path = (directory if directory is not None else TRACE_DIR) / self.id
        try:
            self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            self.path.parent.chmod(0o700)
            self.path.mkdir(mode=0o700)
            try:
                prune_traces(self.path.parent, protect={self.id})
            except Exception as exc:  # retention must never stop a session from being traced
                self._record_error("retention", exc)
            _write_manifest(self.path, self._manifest())
            self._thread = threading.Thread(target=self._write, name="vinyl-trace", daemon=True)
            self._thread.start()
            self.event("session.start", mode=mode, parent_ref=parent_ref,
                       metadata=self._metadata, audio_enabled=self.audio_enabled)
        except Exception as exc:
            self._record_error("initialize", exc)
            self._closing.set()
            self._finished.set()

    def info(self) -> dict:
        """Fields shared by the RPC state, desktop wrapper and network client."""
        error = self.error
        if self.dropped_events:
            error = "; ".join(part for part in (error, f"{self.dropped_events} trace events dropped") if part)
        if self._summary.get("incomplete"):
            error = "; ".join(part for part in (error, f"session trace incomplete: {self._reason}") if part)
        return {"trace_id": self.id, "trace_ref": self.ref,
                "trace_path": str(self.path) if self.path is not None else "",
                "trace_error": error}

    def __bool__(self) -> bool:
        return self.enabled and self._thread is not None and not self._closing.is_set()

    def _record_error(self, stage: str, exc: Exception) -> None:
        message = f"{stage}: {type(exc).__name__}: {exc}"
        with self._lock:
            if len(self._errors) < 20:
                self._errors.append(message)
            self.error = "; ".join(self._errors)

    def _enqueue(self, kind: str, fields: dict, pcm: bytes | None = None,
                 frames: int = 0) -> None:
        if not self.enabled:
            return
        # Snapshot nested lists/dicts before returning to the caller; later
        # mutation of a command or metadata must not rewrite past evidence.
        try:
            fields = _safe_fields(fields)
        except Exception as exc:
            with self._lock:
                self._seq += 1
                self.dropped_events += 1
                self._dropped_audio_frames += frames
            self._record_error("snapshot", exc)
            return
        with self._lock:
            if self._closing.is_set():
                self._late_events += 1
                return
            now = time.monotonic_ns()
            self._seq += 1
            record = dict(fields)
            record.update(kind=kind, seq=self._seq, monotonic_ns=now,
                          elapsed_ms=(now - self._start_ns) / 1_000_000,
                          wall_time_ns=self._wall_start_ns + now - self._start_ns)
            if kind == "audio.block":
                record["sample_offset"] = self._audio_frames
                self._audio_frames += frames
            try:
                self._queue.put_nowait((record, pcm))
            except queue.Full:
                self.dropped_events += 1
                self._dropped_audio_frames += frames

    def event(self, kind: str, **fields) -> None:
        self._enqueue(kind, fields)

    def audio(self, pcm: bytes, *, frames: int, sample_rate: int = 16000,
              **fields) -> None:
        if not self.enabled:
            return
        try:
            data = bytes(pcm)
            if frames < 0 or sample_rate <= 0 or len(data) != frames * 4:
                raise ValueError("audio must contain frames * 4 bytes of mono float32 PCM")
            save = self.audio_enabled and self._audio_queued_bytes + len(data) <= self._audio_cap
            if self.audio_enabled and not save and not self._audio_truncated:
                self._audio_truncated = True
                self.event("trace.audio.truncated", limit_bytes=self._audio_cap)
            if save:
                self._audio_queued_bytes += len(data)
            self._enqueue("audio.block", dict(fields, frames=frames,
                          sample_rate=sample_rate, format="f32le", channels=1,
                          audio_saved=save),
                          data if save else None, frames=frames)
        except Exception as exc:
            self._record_error("audio", exc)
            self.event("trace.error", stage="audio", message=str(exc))

    def _manifest(self, *, drained: bool = False) -> dict:
        with self._lock:
            errors = list(self._errors)
            dropped = self.dropped_events
            late = self._late_events
        elapsed = ((self._end_ns or time.monotonic_ns()) - self._start_ns) / 1_000_000
        return {
            "schema_version": SCHEMA_VERSION, "trace_id": self.id,
            "trace_ref": self.ref, "mode": self._mode,
            "parent_ref": self._parent_ref, "metadata": self._metadata,
            "started_at": datetime.fromtimestamp(self._wall_start_ns / 1e9, timezone.utc).isoformat(),
            "started_at_ns": self._wall_start_ns, "start_monotonic_ns": self._start_ns,
            "duration_ms": elapsed, "status": "finished" if drained else "recording",
            "reason": self._reason,
            "complete": drained and not errors and dropped == 0 and not self._summary.get("incomplete", False),
            "completeness_scope": "trace_recording_only",
            "incomplete_reason": self._reason if self._summary.get("incomplete") else None,
            "events_written": self._events_written, "events_submitted": self._seq,
            "dropped_events": dropped, "late_events": late, "errors": errors,
            "audio": {"enabled": self.audio_enabled, "format": "f32le", "channels": 1,
                      "path": "audio.f32le" if self.audio_enabled else None,
                      "frames_received": self._audio_frames,
                      "bytes_written": self._audio_bytes_written,
                      "truncated": self._audio_truncated,
                      "dropped_frames": self._dropped_audio_frames},
            "summary": _safe_fields(self._summary),
            "visibility": "Injection events describe requested edits and subprocess results; "
                          "they do not independently verify the application's field contents.",
        }

    def _write(self) -> None:
        assert self.path is not None
        audio_stream = None
        pending = None
        try:
            with _private_open(self.path / "events.jsonl") as events:
                if self.audio_enabled:
                    audio_stream = _private_open(self.path / "audio.f32le", binary=True)
                while not self._closing.is_set() or not self._queue.empty():
                    try:
                        record, pcm = self._queue.get(timeout=0.05)
                    except queue.Empty:
                        continue
                    pending = record
                    try:
                        if pcm is not None:
                            record["audio_offset_bytes"] = self._audio_bytes_written
                            record["audio_bytes"] = len(pcm)
                        line = json.dumps(record, ensure_ascii=False,
                                          allow_nan=False) + "\n"
                        if pcm is not None:
                            audio_stream.write(pcm)
                            self._audio_bytes_written += len(pcm)
                        events.write(line)
                        events.flush()
                        self._events_written += 1
                        pending = None
                    except (TypeError, ValueError) as exc:
                        with self._lock:
                            self.dropped_events += 1
                            self._dropped_audio_frames += record.get("frames", 0) if pcm else 0
                        self._record_error("serialize", exc)
                        pending = None
                    finally:
                        self._queue.task_done()
                events.flush()
                os.fsync(events.fileno())
                if audio_stream is not None:
                    audio_stream.flush()
                    os.fsync(audio_stream.fileno())
        except Exception as exc:
            self._record_error("write", exc)
            self._closing.set()
            if pending is not None:
                with self._lock:
                    self.dropped_events += 1
                    self._dropped_audio_frames += pending.get("frames", 0)
            while True:
                try:
                    record, _ = self._queue.get_nowait()
                except queue.Empty:
                    break
                with self._lock:
                    self.dropped_events += 1
                    self._dropped_audio_frames += record.get("frames", 0) if record["kind"] == "audio.block" else 0
                self._queue.task_done()
            with self._lock:
                if self._reason is None:
                    self._reason = "trace_error"
                    self._end_ns = time.monotonic_ns()
        finally:
            if audio_stream is not None:
                try:
                    audio_stream.close()
                except Exception as exc:
                    self._record_error("close audio", exc)
            try:
                _write_manifest(self.path, self._manifest(drained=True))
            except Exception as exc:
                self._record_error("manifest", exc)
            self._finished.set()

    def finish(self, reason: str, **summary) -> dict:
        if not self.enabled:
            return self.info()
        with self._finish_lock:
            if self._reason is None:
                self.event("session.finish", reason=reason, **summary)
                with self._lock:
                    self._reason = reason
                    self._summary = summary
                    self._end_ns = time.monotonic_ns()
                    self._closing.set()
            if self._thread is not None and self._thread is not threading.current_thread():
                self._thread.join(timeout=FINISH_TIMEOUT)
                if self._thread.is_alive():
                    self._record_error("finish", TimeoutError("trace writer did not drain before timeout"))
            return self.info()


def resolve_trace(reference: str = "latest", *, directory: Path | None = None) -> Path:
    root = directory if directory is not None else TRACE_DIR
    name = reference.strip()
    if name.startswith("vinyl-trace:"):
        name = name[len("vinyl-trace:"):]
    if name == "latest":
        if not root.is_dir():
            raise ValueError("No Vinyl traces yet. Toggle dictation on, speak, then toggle off.")
        candidates = [path for path in root.iterdir()
                      if _ID.fullmatch(path.name) and path.is_dir() and not path.is_symlink()]
        if not candidates:
            raise ValueError("No Vinyl traces yet. Toggle dictation on, speak, then toggle off.")
        candidates.sort(key=lambda path: path.name, reverse=True)
        for candidate in candidates:
            try:
                mode = json.loads((candidate / "manifest.json").read_text(encoding="utf-8")).get("mode")
            except (OSError, ValueError):
                continue
            if mode in {"daemon", "client"}:
                return candidate
        return candidates[0]
    if not _ID.fullmatch(name):
        raise ValueError("Expected a vinyl-trace:<id> reference or bare trace id.")
    path = root / name
    if path.is_symlink() or path.resolve().parent != root.resolve():
        raise ValueError("Trace references cannot point outside the trace directory.")
    if not path.is_dir():
        raise ValueError(f"Trace not found: vinyl-trace:{name}")
    return path


def load_trace(reference: str = "latest", *, directory: Path | None = None) -> tuple[dict, list[dict]]:
    path = resolve_trace(reference, directory=directory)
    manifest = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
    events = []
    event_path = path / "events.jsonl"
    if event_path.exists():
        for number, line in enumerate(event_path.read_text(encoding="utf-8").splitlines(), 1):
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Trace event {number} is incomplete or invalid: {path}") from exc
    return manifest, events


def copy_reference(reference: str = "latest", *, directory: Path | None = None) -> str:
    ref = "vinyl-trace:" + resolve_trace(reference, directory=directory).name
    candidates = [["pbcopy"]] if sys.platform == "darwin" else [
        ["wl-copy"], ["xclip", "-selection", "clipboard"], ["xsel", "--clipboard", "--input"]]
    failures = []
    for command in candidates:
        if not shutil.which(command[0]):
            continue
        try:
            # wl-copy/xclip fork a clipboard owner. A captured stderr pipe can
            # stay open in that child and make communicate() wait until the
            # clipboard changes, even though the parent already succeeded.
            subprocess.run(command, input=ref.encode("utf-8"), check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
            return ref
        except (OSError, subprocess.SubprocessError) as exc:
            failures.append(f"{command[0]}: {type(exc).__name__}")
    detail = "; ".join(failures) or "no clipboard utility is installed"
    raise ValueError(f"Could not copy ({detail}). Copy this reference manually: {ref}")


def summarize_events(events: list[dict]) -> dict:
    """Count only recorded commands and field events, without inferring receipt."""
    issued = {"inserted_characters": 0, "deleted_characters": 0,
              "insertion_commands": 0, "deletion_commands": 0, "failed_commands": 0}
    observed = {"inserted_characters": 0, "deleted_characters": 0, "text_events": 0,
                "events_without_text": 0, "provider_count_mismatches": 0}
    coverage = "not_recorded"
    gaps = []
    backend = None
    for event in events:
        kind = event.get("kind")
        action = event.get("action")
        count = event.get("count")
        if not isinstance(count, int) or isinstance(count, bool) or count < 0:
            count = len(event["text"]) if isinstance(event.get("text"), str) else 0
        if kind == "inject.command.completed":
            if action in {"type", "paste"}:
                issued["inserted_characters"] += count
                issued["insertion_commands"] += 1
            elif action == "erase":
                issued["deleted_characters"] += count
                issued["deletion_commands"] += 1
        elif kind == "inject.command.failed":
            issued["failed_commands"] += 1
        elif kind == "observer.text_changed":
            observed["text_events"] += 1
            if action == "insert":
                observed["inserted_characters"] += count
            elif action == "delete":
                observed["deleted_characters"] += count
            if not event.get("text_available", isinstance(event.get("text"), str)):
                observed["events_without_text"] += 1
            if event.get("text_length_matches") is False:
                observed["provider_count_mismatches"] += 1
            coverage = "focused_text_events_observed"
        elif kind == "observer.started":
            backend = event.get("backend")
            coverage = event.get("coverage", "awaiting_focused_text_events")
        elif kind == "observer.focus":
            focus_coverage = event.get("coverage")
            if focus_coverage == "focused_target_has_no_text_interface":
                coverage = focus_coverage
                if focus_coverage not in gaps:
                    gaps.append(focus_coverage)
        elif kind in {"observer.coverage", "observer.unavailable"}:
            coverage = event.get("coverage", event.get("state", "unknown"))
            if event.get("reason") and event["reason"] not in gaps:
                gaps.append(event["reason"])
        elif kind == "observer.stopped":
            coverage = event.get("coverage", coverage)
            if event.get("helper_stopped") is False:
                gaps.append("observer_helper_still_running")
    if (issued["insertion_commands"] or issued["deletion_commands"]) and not observed["text_events"]:
        gaps.append("issued_edits_have_no_observed_field_events")
    return {"issued": issued, "observed": observed, "coverage": coverage,
            "coverage_gaps": gaps, "backend": backend}


def _print_summary(manifest: dict, path: Path, events: list[dict]) -> None:
    print(manifest["trace_ref"])
    status = manifest.get("status", "unknown")
    if status == "finished":
        status += ", trace recording complete" if manifest.get("complete") else ", trace recording INCOMPLETE"
    print(f"{manifest.get('mode', 'unknown')} | {status} | "
          f"{manifest.get('duration_ms', 0) / 1000:.3f}s | "
          f"{manifest.get('events_written', 0)} events")
    print(f"Files: {path}")
    if manifest.get("incomplete_reason"):
        print(f"Incomplete session: {manifest['incomplete_reason']}")
    if manifest.get("dropped_events"):
        print(f"Dropped events: {manifest['dropped_events']}")
    for error in manifest.get("errors", []):
        print(f"Trace error: {error}")
    evidence = summarize_events(events)
    issued = evidence["issued"]
    observed = evidence["observed"]
    print(f"Issued commands: insert {issued['inserted_characters']} characters "
          f"({issued['insertion_commands']} commands), delete {issued['deleted_characters']} "
          f"({issued['deletion_commands']} commands); failed commands: {issued['failed_commands']}")
    print(f"Observed field changes: insert {observed['inserted_characters']} characters, "
          f"delete {observed['deleted_characters']} ({observed['text_events']} events)")
    coverage = evidence["coverage"].replace("_", " ")
    if evidence["backend"]:
        coverage += f" via {evidence['backend']}"
    print(f"Observer coverage: {coverage}; events missing text: {observed['events_without_text']}; "
          f"provider count mismatches: {observed['provider_count_mismatches']}")
    if evidence["coverage_gaps"]:
        print("Observation gaps: " + "; ".join(reason.replace("_", " ") for reason in evidence["coverage_gaps"]))
    if manifest.get("summary"):
        print("Result: " + json.dumps(manifest["summary"], ensure_ascii=False))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="vinyl trace", description="Inspect or copy a local dictation trace.")
    commands = parser.add_subparsers(dest="command")
    latest = commands.add_parser("latest", help="summarize the most recent session")
    show = commands.add_parser("show", help="show the complete event timeline")
    show.add_argument("reference", nargs="?", default="latest")
    copy = commands.add_parser("copy", help="copy only the session reference to the clipboard")
    copy.add_argument("reference", nargs="?", default="latest")
    prune = commands.add_parser("prune", help="delete old traces (default: older than 7 days, then oldest until under 2 GiB)")
    prune.add_argument("--days", type=float, help="maximum age in days")
    prune.add_argument("--max-mb", type=float, help="maximum total size in MiB")
    prune.add_argument("--dry-run", action="store_true", help="report what would be removed")
    for command in (latest, show):
        output = command.add_mutually_exclusive_group()
        output.add_argument("--json", action="store_true", help="output manifest and events as JSON")
        output.add_argument("--events", action="store_true", help="output event records as JSONL")
    args = parser.parse_args(argv)
    try:
        reference = getattr(args, "reference", "latest")
        if args.command == "copy":
            print(copy_reference(reference))
            return 0
        if args.command == "prune":
            report = prune_traces(max_age_days=args.days,
                                  max_bytes=None if args.max_mb is None else int(args.max_mb * 1024 ** 2),
                                  dry_run=args.dry_run)
            verb = "Would remove" if args.dry_run else "Removed"
            print(f"{verb} {len(report['removed'])} traces, {report['freed_bytes'] / 1024 ** 3:.2f} GiB; "
                  f"kept {report['kept']} ({report['kept_bytes'] / 1024 ** 3:.2f} GiB)")
            return 0
        path = resolve_trace(reference)
        manifest, events = load_trace(reference)
        if getattr(args, "json", False):
            print(json.dumps({"manifest": manifest, "events": events}, ensure_ascii=False, indent=2))
        elif getattr(args, "events", False):
            for event in events:
                print(json.dumps(event, ensure_ascii=False))
        else:
            _print_summary(manifest, path, events)
            if args.command == "show":
                print(manifest.get("visibility", ""))
                for event in events:
                    fields = {key: value for key, value in event.items()
                              if key not in {"kind", "seq", "monotonic_ns", "elapsed_ms", "wall_time_ns"}}
                    print(f"{event['elapsed_ms']:10.3f} ms  #{event['seq']:05d}  "
                          f"{event['kind']}  {json.dumps(fields, ensure_ascii=False)}")
        return 0
    except (OSError, ValueError, KeyError) as exc:
        print(f"vinyl trace: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
