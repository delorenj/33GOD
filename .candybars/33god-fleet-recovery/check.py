#!/usr/bin/env python3
"""One Candybar fire; no dispatcher, daemon, publisher, or private clock."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import time
import urllib.request
import uuid

DESK = Path(__file__).resolve().parent
ROOT = DESK.parent.parent
RUNTIME = DESK / "runtime"
NAME = "33god-fleet-recovery"
TRACKED = ("33GOD-97", "33GOD-59", "BB-60", "BB-62", "FLUME-111", "FLUME-112", "PJAN-229", "SSBNK-1")
FIXES = ("BB-62", "FLUME-111", "PJAN-229")
AFFECTED = {"33GOD", "BB", "FLUME", "PJAN", "SSBNK"}
REWAKE = 1800
OFFICER_TIMEOUT = 240


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def stamp(now):
    return datetime.fromtimestamp(now, timezone.utc).isoformat()


def atomic(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".new")
    with tmp.open("w") as f:
        f.write(json.dumps(value, sort_keys=True, indent=2) + "\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def read_json(path, missing=None) -> dict:
    if not path.exists():
        if missing is None:
            raise ValueError(f"missing JSON receipt: {path}")
        return missing
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"not an object: {path}")
    return value


def binary(name):
    local = Path.home() / ".local/bin" / name
    return str(local) if local.exists() else (shutil.which(name) or name)


def command_json(argv):
    p = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, timeout=60)
    if p.returncode:
        raise RuntimeError(f"{Path(argv[0]).name} failed (exit {p.returncode})")
    value = json.loads(p.stdout)
    if not isinstance(value, dict):
        raise ValueError("source is not a JSON object")
    return value


def compact_ticket(t):
    if not isinstance(t, dict) or t.get("ref") not in TRACKED:
        raise ValueError("missing or wrong tracked ticket")
    for field in ("label_names", "comments"):
        if not isinstance(t.get(field), list):
            raise ValueError(f"ticket missing {field}")
    comments = sorted(t["comments"], key=lambda c: (c.get("created_at", ""), c.get("id", "")))
    evidence = [{k: c.get(k) for k in ("id", "actor_name", "created_at", "text", "comment_html")} for c in comments]
    flat = lambda s: re.sub(r"\s+", " ", str(s or "")).strip()
    return {"ref": t["ref"], "lane": t.get("lane"), "labels": sorted(t["label_names"]),
            "title": t.get("name"), "evidence_hash": digest([t.get("description_text"), evidence]),
            "description": flat(t.get("description_text"))[:2600],
            "comments": [{"actor": c.get("actor_name"), "text": flat(c.get("text") or c.get("comment_html"))[:1500]}
                         for c in comments[-3:]]}


def compact_status(raw):
    if raw.get("version") != 1 or not isinstance(raw.get("scopes"), list) or not raw["scopes"]:
        raise ValueError("unsupported or empty Krebs status")
    if not raw.get("candystore", {}).get("ok"):
        raise ValueError("Candystore unavailable")
    watch = raw.get("tick", {}).get("watch", {})
    scopes = []
    for s in raw["scopes"]:
        for field in ("board", "agentId", "tickets", "inFlight", "counts", "errors", "warnings"):
            if field not in s:
                raise ValueError(f"scope missing {field}")
        tickets = [{k: t.get(k) for k in ("key", "state", "stage", "blockedBy", "queuePosition")}
                   | {"labels": sorted(t.get("labels", []))} for t in s["tickets"]]
        # Versioned facts change the gate; generatedAt, ETA, runningMinutes and tick times do not.
        scopes.append({"board": s["board"], "owner": s["agentId"], "scopeLabels": sorted(s.get("scopeLabels", [])),
                       "free": s.get("free"), "occupied": sorted(s.get("occupied", [])), "counts": s["counts"],
                       "tickets": sorted(tickets, key=lambda t: t["key"]),
                       "inFlight": sorted([{k: t.get(k) for k in ("key", "kind", "state", "invocationId")}
                                           for t in s["inFlight"]], key=canonical),
                       "recent": [{k: r.get(k) for k in ("ts", "key", "action", "ok")} for r in s.get("recent", [])],
                       "errors": s["errors"],
                       "warnings": [re.sub(r"\d+(?:\.\d+)?", "N", str(w)) for w in s["warnings"]]})
    return {"watch_alive": watch.get("alive") is True, "tick_overdue": raw.get("tick", {}).get("overdue") is True,
            "scopes": sorted(scopes, key=lambda s: (s["board"], s["owner"], s["scopeLabels"]))}


def collect():
    faults, tickets = [], []
    with ThreadPoolExecutor(max_workers=9) as pool:
        jobs = {"krebs": pool.submit(command_json, [binary("krebs"), "status", "--json"])}
        jobs.update({ref: pool.submit(command_json, [binary("px"), "show", ref, "--json"]) for ref in TRACKED})
        status = None
        for key, job in jobs.items():
            try:
                raw = job.result()
                if key == "krebs":
                    status = compact_status(raw)
                else:
                    if raw.get("ok") is not True:
                        raise ValueError("Pilot not ok")
                    tickets.append(compact_ticket(raw.get("ticket")))
            except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
                # Stable fault identity, not clock text / changing transport diagnostics.
                faults.append(f"{key}:UNAVAILABLE:{type(exc).__name__}")
    if status:
        if not status["watch_alive"] or status["tick_overdue"]:
            faults.append("krebs:WATCH_OR_TICK_UNHEALTHY")
        faults.extend(f'{s["board"]}:{s["owner"]}:SCOPE_ERRORS' for s in status["scopes"] if s["errors"])
    return {"status": status, "tracked": sorted(tickets, key=lambda t: t["ref"]), "faults": sorted(faults)}


def gate(snapshot, state, now):
    if state.get("pending_at") and now - state["pending_at"] < REWAKE:
        return False, "backoff: pending/interrupted officer"
    if state.get("failed_at") and now - state["failed_at"] < REWAKE:
        return False, "backoff: failed officer"
    if state.get("last_hash") != digest(snapshot):
        return True, "changed evidence" if state.get("last_hash") else "first observation"
    if now - state.get("last_officer_at", 0) >= REWAKE:
        return True, "30-minute aging/fault escalation"
    return False, "quiet: unchanged evidence"


def officer_command():
    return [binary("hermes"), "-p", "33god-pm", "chat", "-Q", "--query-file", "-",
            "-t", "terminal,file,no_mcp", "--max-turns", "6",
            "--reasoning", "medium", "--ignore-rules", "--format", "stream-json", "--source", "tool"]


def parse_turn(stdout, code, marker):
    events = []
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
            if isinstance(event, dict):
                events.append(event)
        except ValueError:
            pass
    results = [e for e in events if e.get("type") == "result"]
    result = results[0] if len(results) == 1 else {}
    terminal_use = any(e.get("type") == "tool_use" and e.get("name") == "terminal" for e in events)
    terminal_result = any(e.get("type") == "tool_result" and e.get("name") == "terminal"
                          and not e.get("is_error") and marker in e.get("output", "") for e in events)
    tokens = result.get("tokens", {}).get("total")
    token_known = isinstance(tokens, int) and not isinstance(tokens, bool) and tokens >= 0
    ok = (code == 0 and result.get("exit_code") == 0 and bool(result.get("session_id"))
          and terminal_use and terminal_result and token_known)
    verdict = None
    try:
        verdict = json.loads(result.get("text", ""))
        ok = ok and isinstance(verdict, dict) and verdict.get("verdict") in {"continue", "unknown", "complete"}
    except ValueError:
        ok = False
    return {"ok": bool(ok), "tokens": tokens if token_known else None, "session_id": result.get("session_id"),
            "terminal_evidenced": terminal_use and terminal_result, "verdict": verdict, "exit": code}


def session_from_files(directory):
    ids = []
    for line in (directory / "turn.jsonl").read_text().splitlines():
        try:
            event = json.loads(line)
            if isinstance(event, dict) and event.get("session_id"):
                ids.append(event["session_id"])
        except ValueError:
            pass
    if ids:
        return ids[-1]
    stderr = (directory / "stderr.log").read_text()
    match = re.search(r"(?:Session:|session_id:)\s*(local-[0-9a-f]+)", stderr)
    return match.group(1) if match else None


def gateway_control(directory, mode="status"):
    sid = session_from_files(directory)
    if not sid:
        return {"settled": False, "error": "no session identity; manual inspection required"}
    python = Path.home() / ".hermes/hermes-agent/.venv/bin/python"
    env = dict(os.environ, HERMES_HOME=str(Path.home() / ".hermes/profiles/33god-pm"))
    try:
        p = subprocess.run([str(python), str(DESK / "gateway_control.py"), mode, sid], cwd=ROOT,
                           env=env, text=True, capture_output=True, timeout=35)
        data = json.loads(p.stdout) if p.returncode == 0 else {"settled": False, "error": "gateway control failed"}
    except (OSError, ValueError, subprocess.TimeoutExpired):
        data = {"settled": False, "error": "gateway control unavailable"}
    atomic(directory / ("gateway-" + mode + ".json"), data)
    return data


def run_officer(brief, directory, marker):
    env = {k: v for k, v in os.environ.items() if not k.startswith("CANDYBAR_")}
    # The child may read evidence and act as PM; it cannot inherit a result file and impersonate the driver.
    with (directory / "turn.jsonl").open("w") as out, (directory / "stderr.log").open("w") as err:
        child = subprocess.Popen(officer_command(), cwd=ROOT, stdin=subprocess.PIPE, stdout=out, stderr=err,
                                 text=True, start_new_session=True, env=env)
        try:
            child.communicate(brief, timeout=OFFICER_TIMEOUT)
            code = child.returncode
        except subprocess.TimeoutExpired:
            os.killpg(child.pid, signal.SIGKILL)
            child.communicate()
            code = 124
        turn = parse_turn((directory / "turn.jsonl").read_text(), code, marker)
        if not turn["ok"]:
            # A killed thin CLI does NOT stop its gateway-owned turn. Interrupt only this
            # exact accepted session, and retain uncertainty until a later read proves idle.
            control = gateway_control(directory, "interrupt")
        else:
            control = {"settled": True}
    turn["unsettled"] = not control.get("settled", False)
    return turn


def evidence_file(path, runtime):
    if not isinstance(path, str):
        raise ValueError("proof receipt must be a path")
    p = (runtime / path).resolve()
    if not p.is_relative_to(runtime.resolve()) or not p.is_file() or p.stat().st_size == 0:
        raise ValueError("missing/empty/outside-runtime proof receipt")
    return {"path": str(p), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}


def completion_proof(verdict, samples, runtime, now):
    if verdict.get("verdict") != "complete":
        return None
    path = evidence_file(verdict.get("proof_file"), runtime)
    proof = read_json(Path(path["path"]))
    receipts = [path]
    for key in FIXES:
        f = proof.get("fixes", {}).get(key, {})
        if (f.get("installed") is not True or f.get("independent_review") is not True
                or not f.get("reviewer") or not f.get("implementer") or f["reviewer"] == f["implementer"]):
            raise ValueError(f"{key}: installed independent review not proven")
        receipts.extend(evidence_file(f.get(k), runtime) for k in ("installed_probe_receipt", "review_receipt"))
    chosen = samples[-3:]
    if (len(chosen) != 3 or any(not s["data_ok"] or s["warnings"] or s["trigger"] != "scheduled" for s in chosen)
            or len({s["invocation_id"] for s in chosen}) != 3
            or any(b["at"] - a["at"] < 240 for a, b in zip(chosen, chosen[1:]))
            or chosen[-1]["at"] - chosen[0]["at"] < 600 or now - chosen[-1]["at"] > 360):
        raise ValueError("need three clean spaced scheduled samples spanning >=10 minutes")
    if proof.get("sample_ids") != [s["id"] for s in chosen]:
        raise ValueError("proof must cite the latest three scheduled samples")
    required_scopes = set().union(*(set(s["ready_scopes"]) for s in chosen)) & AFFECTED
    flow = proof.get("flow", {})
    if not required_scopes or not required_scopes.issubset(flow):
        raise ValueError("missing useful starts/handbacks for affected ready scopes")
    for scope in required_scopes:
        receipts.append(evidence_file(flow[scope], runtime))
    held_scopes = set(chosen[-1]["held_scopes"])
    holds = proof.get("held_scopes", {})
    for scope in held_scopes:
        h = holds.get(scope, {})
        if not h.get("classification"):
            raise ValueError(f"unclassified held scope: {scope}")
        receipts.append(evidence_file(h.get("receipt"), runtime))
    if proof.get("no_unexplained_stale_ready") is not True or proof.get("no_fail_loops") is not True:
        raise ValueError("stale ready work or failure loops unresolved")
    return {"verdict": verdict, "proof": proof, "receipts": receipts, "samples": chosen, "at": stamp(now)}


def api(method, route, data=None):
    base = os.environ.get("CANDYBAR_API_URL", "http://127.0.0.1:8700").rstrip("/")
    req = urllib.request.Request(base + route, data=None if data is None else canonical(data).encode(),
                                 headers={"Content-Type": "application/json"}, method=method)
    with urllib.request.urlopen(req, timeout=15) as response:
        return json.load(response)


def pause_self():
    matches = [r for r in api("GET", "/candybars") if r["name"] == NAME]
    if len(matches) != 1:
        raise ValueError("self registration absent/ambiguous")
    row = matches[0]
    if "project:33GOD" not in row["tags"]:
        raise ValueError("foreign project registration")
    identity = os.environ.get("CANDYBAR_ID")
    if not identity or identity != row["id"]:
        raise ValueError("not this Candybar invocation")
    route = f'/candybars/{row["id"]}'
    api("POST", route + "/enabled", {"enabled": False})
    readback = api("GET", route)
    if readback.get("enabled") is not False:
        raise ValueError("pause not confirmed")
    return readback


def sample_record(snapshot, now, run_id):
    scopes = (snapshot.get("status") or {}).get("scopes", [])
    return {"id": run_id, "at": now, "hash": digest(snapshot), "data_ok": not snapshot["faults"],
            "trigger": os.environ.get("CANDYBAR_TRIGGER", "local"),
            "invocation_id": os.environ.get("CANDYBAR_INVOCATION_ID", ""),
            "warnings": [w for s in scopes for w in s["warnings"]],
            "ready_scopes": sorted({s["board"] for s in scopes if any(
                t["stage"] not in {"held", "blocked-by", "epic"} for t in s["tickets"])}),
            "held_scopes": sorted({s["board"] for s in scopes if any(
                t["stage"] in {"held", "blocked-by"} for t in s["tickets"])})}


def result(ok, message, tokens: int | None = 0):
    value = {"status": "success" if ok else "fail", "message": message[:500]}
    if tokens is not None:
        value["metrics"] = {"token_spend": tokens}
    if os.environ.get("CANDYBAR_RESULT_FILE"):
        atomic(Path(os.environ["CANDYBAR_RESULT_FILE"]), value)
    print(canonical(value))
    return 0 if ok else 1


def execute(runtime=RUNTIME, probe=False):
    runtime.mkdir(parents=True, exist_ok=True)
    with (runtime / "run.lock").open("a+") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return result(True, "quiet: overlap (no officer)")
        state_path = runtime / "state.json"
        state = read_json(state_path, {})
        uncertain = state.get("unsettled_sample") or state.get("pending_sample")
        if uncertain and not probe:
            directory = runtime / "runs" / uncertain
            control = gateway_control(directory, "status")
            if not control.get("settled"):
                return result(False, "UNKNOWN: previous gateway turn not confirmed settled; no new officer", 0)
            state.pop("unsettled_sample", None)
            state.pop("pending_sample", None)
            state.pop("pending_at", None)
            atomic(state_path, state)
        if state.get("completed") and not probe:
            return result(True, "retired: completion receipt already persisted")
        snapshot, now = collect(), time.time()
        run_id = datetime.fromtimestamp(now, timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
        directory = runtime / "runs" / run_id
        directory.mkdir(parents=True)
        sample = sample_record(snapshot, now, run_id)
        atomic(directory / "sample.json", {"sample": sample, "snapshot": snapshot})
        wake, why = gate(snapshot, state, now)
        samples = (state.get("samples", []) + [sample])[-288:]
        state["samples"] = samples
        if not wake and not probe:
            atomic(state_path, state)
            atomic(directory / "receipt.json", {"decision": why, "tokens": 0})
            return result(not snapshot["faults"], why + ("; UNKNOWN sources" if snapshot["faults"] else ""))
        marker = f'FLEET_SAMPLE_VERIFIED {run_id} {sample["hash"]}'
        state.update(pending_at=now, pending_sample=run_id)
        atomic(state_path, state)  # crash before terminal result = uncertain; wait 30m, never blind retry
        previous = state.get("roadmap", "No roadmap yet. Use the live snapshot, not the historical baseline.")
        brief = ((DESK / "contract.md").read_text() + "\n\n# Driver facts\n" + canonical({
            "mode": "READ_ONLY_PROBE" if probe else "RECOVERY", "data_ok": not snapshot["faults"],
            "reason": why, "repo": str(ROOT), "runtime": str(runtime), "sample": sample,
            "verify_command": [sys.executable, "-I", str(DESK / "check.py"), "evidence", str(directory / "sample.json")],
            "snapshot": snapshot, "previous_roadmap": previous, "scheduled_samples": samples[-3:]}))
        (directory / "brief.md").write_text(brief)
        try:
            turn = run_officer(brief, directory, marker)
        except OSError as exc:
            turn = {"ok": False, "tokens": None, "error": type(exc).__name__}
        atomic(directory / "receipt.json", {"decision": why, **turn})
        state.pop("pending_at", None)
        state.pop("pending_sample", None)
        state.update(last_hash=sample["hash"], last_officer_at=now)
        if not turn["ok"]:
            state["failed_at"] = now
            if turn.get("unsettled", True):
                state["unsettled_sample"] = run_id
            atomic(state_path, state)
            return result(False, "officer failed or no actual terminal/result evidence; see local receipt", turn.get("tokens"))
        state.pop("failed_at", None)
        verdict = turn["verdict"]
        state["roadmap"] = str(verdict.get("roadmap", previous))[:6000]
        atomic(state_path, state)
        if verdict["verdict"] == "complete" and not probe:
            # Re-read current sources: completion cannot rely on a snapshot from before this turn's writes.
            fresh = collect()
            if digest(fresh) != sample["hash"] or fresh["faults"]:
                return result(False, "completion deferred: evidence changed during officer turn", turn["tokens"])
            try:
                proof = completion_proof(verdict, samples, runtime, time.time())
                atomic(runtime / "completion.pending.json", proof)
                proof["registration_readback"] = pause_self()
                atomic(runtime / "completion.json", proof)
                state["completed"] = True
                atomic(state_path, state)
            except (OSError, ValueError) as exc:
                return result(False, "completion refused: " + str(exc), turn["tokens"])
            return result(True, "fleet recovery independently verified; own Candybar paused; completion.json persisted", turn["tokens"])
        return result(not snapshot["faults"], ("probe" if probe else "PM pass") + ": actual terminal turn evidenced; "
                      + str(verdict.get("note", ""))[:220], turn["tokens"])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=("run", "probe", "snapshot", "evidence"))
    p.add_argument("path", nargs="?", type=Path)
    args = p.parse_args()
    try:
        if args.mode == "evidence":
            path = args.path.resolve()
            if not path.is_relative_to(RUNTIME.resolve()):
                raise ValueError("sample outside desk runtime")
            data = read_json(path)
            s = data["sample"]
            if s["hash"] != digest(data["snapshot"]):
                raise ValueError("sample hash mismatch")
            print(f'FLEET_SAMPLE_VERIFIED {s["id"]} {s["hash"]}')
            print(canonical({"data_ok": s["data_ok"], "faults": data["snapshot"]["faults"]}))
            return 0
        if args.mode == "snapshot":
            data = collect()
            print(json.dumps(data, indent=2))
            return 1 if data["faults"] else 0
        runtime = RUNTIME / "probes" / uuid.uuid4().hex if args.mode == "probe" else RUNTIME
        return execute(runtime, probe=args.mode == "probe")
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        return result(False, f"UNKNOWN: {type(exc).__name__}: {exc}", None)


if __name__ == "__main__":
    raise SystemExit(main())
