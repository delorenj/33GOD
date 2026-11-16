"""Shared contract for Waybill collectors (see ../SPEC.md sections 2-3).

Every collector returns a Fragment. The assembler merges fragments by deterministic id,
so collectors never need to import each other: they only need to compute the same ids.
Times inside a Fragment are ABSOLUTE epoch milliseconds (float); the assembler rebases
them to clock.t0. Use `ms()` to convert ISO strings.
"""
from __future__ import annotations

import dataclasses
import datetime as _dt
import hashlib
import json
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

HOME = str(Path.home())


# ---------- time ----------

def ms(value: Any) -> float | None:
    """ISO-8601 (Z or offset, any precision), epoch seconds, or epoch ms -> epoch ms (float). None on failure."""
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        v = float(value)
        return v if v > 1e11 else v * 1000.0
    s = str(value).strip()
    if re.fullmatch(r"\d+(\.\d+)?", s):
        return ms(float(s))
    s = s.replace(" ", "T", 1) if re.match(r"\d{4}-\d\d-\d\d \d", s) else s
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    # Python accepts at most 6 fractional digits
    m = re.match(r"^(.*T\d\d:\d\d:\d\d)(\.\d+)?(.*)$", s)
    if m:
        frac = (m.group(2) or "")[:7]
        s = m.group(1) + frac + m.group(3)
    try:
        d = _dt.datetime.fromisoformat(s)
    except ValueError:
        return None
    if d.tzinfo is None:
        d = d.astimezone()  # naive = local time (transitions.log uses local time)
    return d.timestamp() * 1000.0


def iso(epoch_ms: float | None) -> str | None:
    if epoch_ms is None:
        return None
    return _dt.datetime.fromtimestamp(epoch_ms / 1000.0, _dt.timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def now_ms() -> float:
    return time.time() * 1000.0


# ---------- ids ----------

def sha256(text: str | bytes) -> str:
    b = text.encode() if isinstance(text, str) else text
    return hashlib.sha256(b).hexdigest()


def short_hash(text: str, n: int = 12) -> str:
    return hashlib.sha1(text.encode()).hexdigest()[:n]


class Ids:
    """Deterministic span/node ids (SPEC section 3). Collectors MUST use these."""
    PROMPT = "prompt"
    TURN = "turn"

    @staticmethod
    def hook(invocation_id: str) -> str: return f"hook:{invocation_id}"
    @staticmethod
    def handler(invocation_id: str, handler_id: str) -> str: return f"handler:{invocation_id}:{handler_id}"
    @staticmethod
    def context(invocation_id: str, handler_id: str | None = None) -> str:
        return f"context:{invocation_id}" + (f":{handler_id}" if handler_id else "")
    @staticmethod
    def evt(event_id: str) -> str: return f"evt:{event_id}"
    @staticmethod
    def publish(event_id: str) -> str: return f"publish:{event_id}"
    @staticmethod
    def consume(consumer: str, event_id: str) -> str: return f"consume:{consumer}:{event_id}"
    @staticmethod
    def llm(n: int) -> str: return f"llm:{n}"
    @staticmethod
    def tool(tool_use_id: str) -> str: return f"tool:{tool_use_id}"
    @staticmethod
    def recall(invocation_id: str, bank: str) -> str: return f"memory:recall:{invocation_id}:{bank}"
    @staticmethod
    def buffer(invocation_id: str) -> str: return f"memory:buffer:{invocation_id}"
    @staticmethod
    def flush(operation_id: str) -> str: return f"memory:flush:{operation_id}"
    @staticmethod
    def asm(key: str) -> str: return f"state:asm:{key}"
    @staticmethod
    def notify(channel: str, key: str) -> str: return f"notify:{channel}:{key}"
    @staticmethod
    def file(path: str, at_ms: float) -> str: return f"file:{short_hash(path)}:{int(at_ms)}"


# ---------- scrubbing ----------

_SECRET_PATTERNS = [
    re.compile(r"ops_[A-Za-z0-9_\-]{40,}"),                       # 1Password service tokens
    re.compile(r"\bsk-(?:ant-|or-|proj-)?[A-Za-z0-9_\-]{20,}"),     # OpenAI / Anthropic / OpenRouter
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}"),                    # GitHub
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),                            # AWS access key
    re.compile(r"\beyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}"),  # JWT
    re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._\-]{16,}"),
    re.compile(r"(?i)\b(xox[abpr]-[A-Za-z0-9\-]{10,})"),            # Slack
    re.compile(r"(?i)((?:password|passwd|secret|api[_-]?key|token)\s*[=:]\s*)['\"]?[^\s'\"&]{8,}"),
    re.compile(r"(://[^/\s:@]+:)[^@\s/]+@"),                        # URL user:pass@
]
REDACTED = "«redacted»"


def scrub(text: str) -> str:
    """Replace credential-shaped substrings. Always applied, in every profile."""
    if not text:
        return text
    out = text
    for pat in _SECRET_PATTERNS:
        if pat.groups:
            out = pat.sub(lambda m: m.group(1) + REDACTED, out)
        else:
            out = pat.sub(REDACTED, out)
    return out


def scrub_obj(obj: Any) -> Any:
    if isinstance(obj, str):
        return scrub(obj)
    if isinstance(obj, list):
        return [scrub_obj(x) for x in obj]
    if isinstance(obj, dict):
        return {k: scrub_obj(v) for k, v in obj.items()}
    return obj


def tilde(path: str | None) -> str | None:
    if not path:
        return path
    return path.replace(HOME, "~")


# ---------- the contract ----------

@dataclass
class Span:
    id: str
    kind: str
    component: str
    name: str
    summary: str
    phase: str
    t0: float                      # absolute epoch ms inside a Fragment
    t1: float | None = None
    status: str = "ok"
    reason: str | None = None
    sync: bool | None = None
    parent: str | None = None
    refs: dict[str, Any] = field(default_factory=dict)
    attrs: dict[str, Any] = field(default_factory=dict)
    payload: str | None = None
    evidence: list[str] = field(default_factory=list)


@dataclass
class Consumer:
    name: str
    component: str
    kind: str                      # durable | ephemeral | core
    outcome: str = "unknown"
    filter: str | None = None
    t: float | None = None         # absolute epoch ms
    evidence: str = "inferred"     # observed | inferred
    span: str | None = None


@dataclass
class BusEvent:
    id: str
    type: str
    t: float                       # absolute epoch ms (envelope time)
    subject: str | None = None
    stream: str | None = None
    seq: int | None = None
    stored: float | None = None
    archived: float | None = None
    correlationid: str | None = None
    causationid: str | None = None
    producer: str | None = None
    publisher_span: str | None = None
    consumers: list[Consumer] = field(default_factory=list)
    payload: str | None = None
    schema: dict[str, Any] | None = None


@dataclass
class Link:
    from_: str
    to: str
    kind: str
    label: str | None = None


@dataclass
class Gap:
    component: str
    what: str
    why: str
    severity: str = "info"
    span: str | None = None


@dataclass
class Finding:
    severity: str
    title: str
    detail: str
    component: str
    evidence: list[str] = field(default_factory=list)


@dataclass
class Component:
    id: str
    name: str
    kind: str
    registry: bool = False


@dataclass
class Source:
    id: str
    kind: str
    locator: str
    status: str = "ok"
    items: int = 0
    ms: float = 0.0
    error: str | None = None


@dataclass
class Fragment:
    """What one collector contributes. Merge is by id; later sources enrich (never blank out) earlier ones."""
    source: Source
    spans: list[Span] = field(default_factory=list)
    events: list[BusEvent] = field(default_factory=list)
    links: list[Link] = field(default_factory=list)
    artifacts: dict[str, dict[str, Any]] = field(default_factory=dict)
    gaps: list[Gap] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    components: dict[str, Component] = field(default_factory=dict)
    # facts a collector learned that the window/assembler may use (e.g. {'turn_id': ..., 'model_served': ...})
    facts: dict[str, Any] = field(default_factory=dict)

    def component(self, cid: str, name: str | None = None, kind: str = "service") -> str:
        if cid not in self.components:
            self.components[cid] = Component(id=cid, name=name or cid, kind=kind, registry=registry_has(cid))
        return cid

    def artifact(self, content: Any, mime: str | None = None, limit: int = 65536, note: str | None = None) -> str:
        """Store a payload, return its artifact id ('a:<sha12>'). Text is scrubbed and truncated."""
        if isinstance(content, (dict, list)):
            text = json.dumps(content, ensure_ascii=False, default=str)
            mime = mime or "application/json"
        else:
            text = str(content)
            mime = mime or "text/plain"
        text = scrub(text)
        digest = sha256(text)
        aid = f"a:{digest[:12]}"
        truncated = len(text) > limit
        body = text[:limit]
        art: dict[str, Any] = {"mime": mime, "bytes": len(text.encode()), "sha256": digest, "truncated": truncated}
        if mime == "application/json" and not truncated:
            try:
                art["json"] = json.loads(body)
            except ValueError:
                art["text"] = body
        else:
            art["text"] = body
        if note:
            art["note"] = note
        self.artifacts[aid] = art
        return aid


# ---------- context handed to every collector ----------

@dataclass
class TurnWindow:
    cli: str                       # claude | codex
    surface: str                   # claude-code | claude-code-headless | codex-cli | codex-exec | codex-desktop
    session_id: str
    t0: float                      # submit instant, epoch ms
    t_end: float                   # end of the turn (Stop) + settle, epoch ms
    turn_end: float | None = None  # Stop instant (before settle), epoch ms
    turn_id: str | None = None
    turn_index: int | None = None
    prompt_text: str | None = None
    cwd: str | None = None
    transcript_path: str | None = None
    prompt_invocation_id: str | None = None   # hook-hub UserPromptSubmit invocation
    stop_invocation_id: str | None = None
    settle_ms: float = 15000.0


@dataclass
class Ctx:
    window: TurnWindow
    profile: str = "full"          # full | public
    deep: bool = False             # allow credentialed lookups (gateway traces)
    live: dict[str, Any] = field(default_factory=dict)   # live-mode captures handed to collectors
    timeout_s: float = 20.0

    def margin(self, before_ms: float = 2000.0, after_ms: float = 0.0) -> tuple[float, float]:
        return self.window.t0 - before_ms, self.window.t_end + after_ms


# ---------- registry ----------

_REGISTRY_DIR = Path(__file__).resolve().parents[2] / "components"
_REGISTRY: set[str] | None = None


def registry_has(cid: str) -> bool:
    global _REGISTRY
    if _REGISTRY is None:
        try:
            _REGISTRY = {p.stem for p in _REGISTRY_DIR.glob("*.yaml")}
        except OSError:
            _REGISTRY = set()
    return cid in _REGISTRY


def to_jsonable(obj: Any) -> Any:
    if dataclasses.is_dataclass(obj):
        d = {}
        for f in dataclasses.fields(obj):
            v = getattr(obj, f.name)
            key = "from" if f.name == "from_" else f.name
            d[key] = to_jsonable(v)
        return d
    if isinstance(obj, dict):
        return {k: to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_jsonable(v) for v in obj]
    return obj


def env_flag(name: str, default: bool = False) -> bool:
    v = os.environ.get(name)
    return default if v is None else v.lower() in ("1", "true", "yes", "on")
