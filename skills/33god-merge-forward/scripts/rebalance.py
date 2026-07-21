#!/usr/bin/env python3
"""Tune the merge-forward skill from the latest completed 33GOD session."""
from __future__ import annotations

import argparse
import contextlib
import fcntl
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

SCRIPT = Path(__file__).resolve()
SKILL_DIR = SCRIPT.parent.parent
REPO_ROOT = SKILL_DIR.parent.parent
STATE_DIR = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")) / "33god-merge-forward"
PENDING_DIR = STATE_DIR / "pending"
LOG_FILE = STATE_DIR / "rebalance.log"
RESULT_FILE = STATE_DIR / "last-result.json"
ALLOWED_RELATIVE = {
    Path("SKILL.md"),
    Path("references/gates.md"),
    Path("agents/openai.yaml"),
}
REQUIRED_INVARIANTS = (
    "one user and one decision-maker",
    "pre-production",
    "Lifecycle",
    "Momo",
    "Holocene",
    "Bloodbank",
    "component `main`",
    "root `main`",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(message: str) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as handle:
        handle.write(f"{utc_now()} {message}\n")


def emit_result(status: str, **details: object) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    payload = {"at": utc_now(), "status": status, **details}
    RESULT_FILE.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    log(f"result={status} {json.dumps(details, sort_keys=True)}")


def safe_session_id(value: str, client: str, payload: str) -> str:
    if value:
        cleaned = re.sub(r"[^A-Za-z0-9._-]", "-", value)[:120]
        if cleaned:
            return cleaned
    digest = hashlib.sha256(payload.encode("utf-8", errors="replace")).hexdigest()[:16]
    return f"{client}-{os.getppid()}-{digest}"


def payload_value(data: dict, *paths: str) -> str:
    for path in paths:
        current: object = data
        for part in path.split("."):
            if not isinstance(current, dict):
                current = None
                break
            current = current.get(part)
        if isinstance(current, str) and current:
            return current
    return ""


def parse_payload(raw: str, client: str) -> dict:
    try:
        data = json.loads(raw or "{}")
    except json.JSONDecodeError:
        data = {}
    if not isinstance(data, dict):
        data = {}
    session_id = payload_value(data, "session_id", "sessionId", "session.id")
    event = payload_value(data, "hook_event_name", "event", "event_name")
    cwd = payload_value(data, "cwd") or os.getcwd()
    return {
        "client": client,
        "session_id": safe_session_id(session_id, client, raw),
        "event": event,
        "cwd": cwd,
        "transcript_path": payload_value(data, "transcript_path", "transcriptPath"),
        "payload": data,
        "received_at": utc_now(),
        "quiet_seconds": 90 if client == "codex" or event == "Stop" else 2,
    }


def within_repo(path: str) -> bool:
    try:
        resolved = Path(path).expanduser().resolve()
        resolved.relative_to(REPO_ROOT.resolve())
        return True
    except (OSError, ValueError):
        return False


def enqueue(record: dict) -> Path:
    PENDING_DIR.mkdir(parents=True, exist_ok=True)
    target = PENDING_DIR / f"{record['session_id']}.json"
    temp = target.with_suffix(".tmp")
    temp.write_text(json.dumps(record, sort_keys=True) + "\n")
    temp.replace(target)
    return target


def newest_pending() -> Path | None:
    files = list(PENDING_DIR.glob("*.json")) if PENDING_DIR.exists() else []
    return max(files, key=lambda path: path.stat().st_mtime_ns) if files else None


def wait_until_quiet() -> Path | None:
    deadline = time.monotonic() + int(os.environ.get("GOD_MERGE_FORWARD_REBALANCE_MAX_WAIT", "600"))
    while time.monotonic() < deadline:
        pending = newest_pending()
        if pending is None:
            return None
        try:
            record = json.loads(pending.read_text())
            configured = int(os.environ.get("GOD_MERGE_FORWARD_REBALANCE_QUIET_SECONDS", str(record.get("quiet_seconds", 2))))
            age = time.time() - pending.stat().st_mtime
        except (OSError, ValueError, json.JSONDecodeError):
            time.sleep(2)
            continue
        if age >= max(0, configured):
            return pending
        time.sleep(min(5, max(1, configured - int(age))))
    return None


def find_transcript(record: dict) -> Path | None:
    explicit = record.get("transcript_path")
    if explicit:
        path = Path(explicit).expanduser()
        if path.is_file():
            return path
    session_id = record["session_id"]
    roots = (Path.home() / ".codex/sessions", Path.home() / ".claude/projects")
    for root in roots:
        if not root.is_dir():
            continue
        with contextlib.suppress(OSError):
            matches = list(root.rglob(f"*{session_id}*.jsonl"))
            if matches:
                return max(matches, key=lambda path: path.stat().st_mtime_ns)
    return None


def flatten_content(content: object) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        texts = []
        for block in content:
            if isinstance(block, str):
                texts.append(block)
            elif isinstance(block, dict) and block.get("type") in {"text", "input_text", "output_text"}:
                texts.append(str(block.get("text", "")))
        return " ".join(texts)
    return ""


def transcript_digest(path: Path | None, record: dict) -> tuple[str, int]:
    messages: list[str] = []
    if path is not None:
        with path.open(errors="replace") as handle:
            for line in handle:
                try:
                    item = json.loads(line)
                except json.JSONDecodeError:
                    continue
                payload = item.get("payload", item) if isinstance(item, dict) else {}
                if isinstance(payload, dict) and payload.get("type") == "message":
                    message = payload
                elif isinstance(payload, dict) and isinstance(payload.get("message"), dict):
                    message = payload["message"]
                else:
                    message = payload if isinstance(payload, dict) else {}
                role = message.get("role")
                if role not in {"user", "assistant"}:
                    continue
                text = flatten_content(message.get("content"))
                text = re.sub(r"\s+", " ", text).strip()
                if text:
                    messages.append(f"{role.upper()}: {text[:1800]}")
    if not messages:
        payload = record.get("payload") or {}
        for role, key in (("USER", "prompt"), ("ASSISTANT", "last_assistant_message")):
            value = payload.get(key) if isinstance(payload, dict) else None
            if isinstance(value, str) and value.strip():
                messages.append(f"{role}: {re.sub(r'\s+', ' ', value).strip()[:4000]}")
    selected = messages[-120:]
    digest = "\n".join(selected)
    return digest[-60000:], sum(1 for message in selected if message.startswith("USER:"))


def git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(REPO_ROOT), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def skill_is_clean_on_main() -> tuple[bool, str]:
    branch = git("branch", "--show-current").stdout.strip()
    if branch != "main" and os.environ.get("GOD_MERGE_FORWARD_REBALANCE_ALLOW_NON_MAIN") != "1":
        return False, f"canonical checkout branch is {branch or 'detached'}, not main"
    status = git("status", "--porcelain", "--", str(SKILL_DIR.relative_to(REPO_ROOT))).stdout.strip()
    if status:
        return False, "merge-forward skill already has uncommitted changes"
    return True, ""


def file_hashes(root: Path) -> dict[Path, str]:
    result = {}
    for path in root.rglob("*"):
        if path.is_file() and "__pycache__" not in path.parts:
            result[path.relative_to(root)] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def validator_path() -> Path | None:
    configured = os.environ.get("SKILL_VALIDATOR")
    candidates = [
        Path(configured).expanduser() if configured else None,
        Path.home() / "code/skillex/skill-sets/global/.system/skill-creator/scripts/quick_validate.py",
        Path.home() / ".agents/skills/skill-creator/scripts/quick_validate.py",
    ]
    return next((path for path in candidates if path and path.is_file()), None)


def validate_candidate(candidate: Path, original_lines: int) -> tuple[bool, str]:
    skill = candidate / "SKILL.md"
    text = skill.read_text()
    if len(text.splitlines()) > 500:
        return False, "SKILL.md exceeds 500 lines"
    if len(text.splitlines()) - original_lines > int(os.environ.get("GOD_MERGE_FORWARD_REBALANCE_MAX_GROWTH", "50")):
        return False, "candidate grows SKILL.md beyond the per-session budget"
    missing = [value for value in REQUIRED_INVARIANTS if value not in text]
    if missing:
        return False, f"candidate removed invariants: {', '.join(missing)}"
    validator = validator_path()
    if validator:
        result = subprocess.run([sys.executable, str(validator), str(candidate)], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
        if result.returncode:
            return False, f"skill validator failed: {result.stdout[-1000:]}"
    return True, ""


def build_prompt(candidate: Path, digest: str, record: dict, snapshot: str) -> str:
    return f"""You maintain the 33GOD repo-scoped skill at {candidate}.

Use the latest session evidence below to optimize and rebalance the skill. Edit only:
- {candidate / 'SKILL.md'}
- {candidate / 'references/gates.md'}
- {candidate / 'agents/openai.yaml'} (only if trigger metadata truly changed)

Rules:
- Make no change when the session provides no durable workflow lesson.
- Prefer replacing, tightening, or deleting guidance over adding more ceremony.
- Preserve the single-user, pre-production, smallest-slice, immediate-main-merge model.
- Preserve all product authority boundaries.
- Add verification only for a reproduced failure mode; remove or narrow gates shown to be wasteful.
- Do not add reports, changelogs, evidence files, scripts, hooks, or new references.
- Keep SKILL.md concise and under 500 lines.
- Do not touch anything outside the candidate skill directory.

Session metadata:
client={record.get('client')}
event={record.get('event')}
session_id={record.get('session_id')}
cwd={record.get('cwd')}

Current repository snapshot:
{snapshot[-6000:]}

Latest session transcript digest:
{digest}
"""


def run_codex(candidate: Path, prompt: str, workspace: Path) -> tuple[bool, str]:
    binary = os.environ.get("GOD_MERGE_FORWARD_REBALANCE_CODEX") or shutil.which("codex")
    if not binary:
        return False, "codex binary not found"
    result_file = workspace / "result.md"
    env = dict(os.environ)
    env["GOD_MERGE_FORWARD_REBALANCE"] = "1"
    try:
        result = subprocess.run(
            [
                binary,
                "exec",
                "--cd",
                str(workspace),
                "--skip-git-repo-check",
                "--sandbox",
                "workspace-write",
                "--ephemeral",
                "--color",
                "never",
                "--output-last-message",
                str(result_file),
                "-",
            ],
            input=prompt,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=int(os.environ.get("GOD_MERGE_FORWARD_REBALANCE_CODEX_TIMEOUT", "240")),
            env=env,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return False, "codex tuning timed out"
    summary = result_file.read_text(errors="replace")[-4000:] if result_file.exists() else result.stdout[-4000:]
    return result.returncode == 0, summary


def apply_candidate(candidate: Path, changed: list[Path], baseline: dict[Path, bytes]) -> tuple[bool, str]:
    current_hashes = file_hashes(SKILL_DIR)
    baseline_hashes = {path: hashlib.sha256(data).hexdigest() for path, data in baseline.items()}
    if any(current_hashes.get(path) != digest for path, digest in baseline_hashes.items()):
        return False, "real skill changed while candidate was being evaluated"
    try:
        for relative in changed:
            destination = SKILL_DIR / relative
            temp = destination.with_suffix(destination.suffix + ".rebalance-tmp")
            temp.write_bytes((candidate / relative).read_bytes())
            os.chmod(temp, destination.stat().st_mode)
            temp.replace(destination)
        valid, reason = validate_candidate(SKILL_DIR, len(baseline[Path("SKILL.md")].decode().splitlines()))
        if not valid:
            raise RuntimeError(reason)
        diff_check = git("diff", "--check", "--", str(SKILL_DIR.relative_to(REPO_ROOT)))
        if diff_check.returncode:
            raise RuntimeError(diff_check.stdout + diff_check.stderr)
    except Exception as exc:  # noqa: BLE001
        for relative, data in baseline.items():
            (SKILL_DIR / relative).write_bytes(data)
        return False, f"apply validation failed: {exc}"
    return True, ""


def process_pending(path: Path, dry_run: bool = False) -> int:
    record = json.loads(path.read_text())
    transcript = find_transcript(record)
    digest, user_turns = transcript_digest(transcript, record)
    fingerprint = hashlib.sha256((digest + json.dumps({key: record.get(key) for key in ("client", "session_id", "event")}, sort_keys=True)).encode()).hexdigest()
    processed = STATE_DIR / "processed" / f"{record['session_id']}.sha256"
    if processed.exists() and processed.read_text().strip() == fingerprint:
        path.unlink(missing_ok=True)
        return 0

    if dry_run:
        print(json.dumps({"eligible": bool(digest and user_turns), "session_id": record["session_id"], "client": record["client"], "event": record["event"], "transcript": str(transcript) if transcript else None, "user_turns": user_turns, "digest_bytes": len(digest)}, indent=2))
        return 0

    if not digest or user_turns < int(os.environ.get("GOD_MERGE_FORWARD_REBALANCE_MIN_TURNS", "2")):
        emit_result("skipped", reason="insufficient session evidence", user_turns=user_turns)
        path.unlink(missing_ok=True)
        return 0

    clean, reason = skill_is_clean_on_main()
    if not clean:
        emit_result("deferred", reason=reason, session_id=record["session_id"])
        return 0

    baseline = {relative: (SKILL_DIR / relative).read_bytes() for relative in ALLOWED_RELATIVE}
    original_hashes = file_hashes(SKILL_DIR)
    snapshot = git("status", "--short").stdout + "\n" + git("log", "-5", "--oneline", "--decorate").stdout

    with tempfile.TemporaryDirectory(prefix="33god-merge-forward-rebalance-") as temp_dir:
        workspace = Path(temp_dir)
        candidate = workspace / "33god-merge-forward"
        shutil.copytree(SKILL_DIR, candidate, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        ok, summary = run_codex(candidate, build_prompt(candidate, digest, record, snapshot), workspace)
        if not ok:
            emit_result("failed", reason=summary[-1000:], session_id=record["session_id"])
            return 0
        candidate_hashes = file_hashes(candidate)
        outside = sorted(str(path) for path in set(original_hashes) | set(candidate_hashes) if original_hashes.get(path) != candidate_hashes.get(path) and path not in ALLOWED_RELATIVE)
        if outside:
            emit_result("rejected", reason="candidate changed disallowed files", files=outside)
            return 0
        changed = sorted(path for path in ALLOWED_RELATIVE if original_hashes.get(path) != candidate_hashes.get(path))
        if not changed:
            processed.parent.mkdir(parents=True, exist_ok=True)
            processed.write_text(fingerprint + "\n")
            emit_result("no-change", session_id=record["session_id"], summary=summary[-1000:])
            path.unlink(missing_ok=True)
            return 0
        valid, reason = validate_candidate(candidate, len(baseline[Path("SKILL.md")].decode().splitlines()))
        if not valid:
            emit_result("rejected", reason=reason, files=[str(item) for item in changed])
            return 0
        applied, reason = apply_candidate(candidate, changed, baseline)
        if not applied:
            emit_result("failed", reason=reason, files=[str(item) for item in changed])
            return 0

    processed.parent.mkdir(parents=True, exist_ok=True)
    processed.write_text(fingerprint + "\n")
    for stale in PENDING_DIR.glob("*.json"):
        stale.unlink(missing_ok=True)
    emit_result("applied", session_id=record["session_id"], files=[str(item) for item in changed], summary=summary[-1500:])
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--client", default="unknown")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true", help="skip debounce for a manual dry run")
    args = parser.parse_args()

    raw = args.input.read_text(errors="replace") if args.input.exists() else "{}"
    if not args.dry_run:
        args.input.unlink(missing_ok=True)
    record = parse_payload(raw, args.client)
    if not within_repo(record["cwd"]):
        return 0
    pending = enqueue(record)
    if args.dry_run:
        try:
            return process_pending(pending, dry_run=True)
        finally:
            pending.unlink(missing_ok=True)

    STATE_DIR.mkdir(parents=True, exist_ok=True)
    lock_path = STATE_DIR / "rebalance.lock"
    with lock_path.open("a+") as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 0
        target = newest_pending() if args.force else wait_until_quiet()
        return process_pending(target) if target else 0


if __name__ == "__main__":
    raise SystemExit(main())
