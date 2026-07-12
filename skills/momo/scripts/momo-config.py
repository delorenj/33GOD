#!/usr/bin/env python3
"""momo-config — per-repo Momo board config (.momo/config.json) + lane detection.

Momo's normalized stages are `backlog | unstarted | started | in_review | completed`,
but a repo's kanban columns rarely match 1:1. This tool lets Momo learn a repo's real
lanes ONCE and codify the mapping locally, so the shared board adapter stays generic
and the per-repo lanes are just data.

Ops:
    detect  --root R    Fetch the live board lanes (via the bundled provider) and report
                        which are unmapped and which mapped targets are missing. Momo runs
                        this on first use; if the board is non-standard it asks the operator
                        to map the odd lanes, then calls `set`.
    show    --root R     Print the current .momo/config.json (or the standard defaults).
    set     --root R --lanes '<json>' [--write-targets '<json>'] [--notes '<json>']
                        Write .momo/config.json (validated shape).

`detect` shells out to ../providers/trello.py `resolve`, so it uses the same creds/board
resolution as the adapter (no duplicated transport).
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STATES = ["backlog", "unstarted", "started", "in_review", "completed"]


def provider_resolve(root: str) -> dict:
    out = subprocess.run(
        [sys.executable, os.path.join(HERE, "providers", "trello.py"), "resolve", "--root", root],
        capture_output=True, text=True,
    )
    if out.returncode != 0:
        sys.stderr.write(out.stderr)
        raise SystemExit(out.returncode or 2)
    return json.loads(out.stdout)


def state_for_lane(lane: str, lm: dict) -> str:
    for state in ("completed", "in_review", "started", "unstarted", "backlog"):
        if lane in lm.get(state, []):
            return state
    return "other"


def config_path(root: str) -> str:
    return os.path.join(root, ".momo", "config.json")


def cmd_detect(root: str) -> int:
    info = provider_resolve(root)
    lm = info["list_map"]
    board_lists = info["board_lists"]
    unmapped = [l for l in board_lists if state_for_lane(l, lm) == "other"]
    missing = {s: lm[s] for s in STATES if not any(t in board_lists for t in lm.get(s, []))}
    report = {
        "board_name": info.get("board_name", ""),
        "board_id": info.get("board_id", ""),
        "config_present": info.get("config_present", False),
        "board_lists": board_lists,
        "current_lane_map": lm,
        "unmapped_lanes": unmapped,          # board columns no stage claims -> classified "other"
        "states_with_missing_lane": missing,  # stages whose mapped lane(s) aren't on the board
        "is_standard": not unmapped and not missing,
    }
    print(json.dumps(report, indent=2))
    return 0


def cmd_show(root: str) -> int:
    path = config_path(root)
    if os.path.isfile(path):
        print(open(path, encoding="utf-8").read())
    else:
        print(json.dumps({"note": "no .momo/config.json — adapter uses standard defaults"}, indent=2))
    return 0


def cmd_set(root: str, lanes: str, write_targets: str | None, notes: str | None) -> int:
    try:
        lanes_obj = json.loads(lanes)
    except Exception as e:
        sys.stderr.write(f"momo-config: --lanes is not valid JSON: {e}\n")
        return 2
    if not isinstance(lanes_obj, dict):
        sys.stderr.write("momo-config: --lanes must be a JSON object of state -> [lane, ...]\n")
        return 2
    for state, v in lanes_obj.items():
        if state not in STATES:
            sys.stderr.write(f"momo-config: unknown state {state!r} (allowed: {', '.join(STATES)})\n")
            return 2
        if not isinstance(v, list) or not all(isinstance(x, str) for x in v):
            sys.stderr.write(f"momo-config: lanes[{state!r}] must be a list of lane-name strings\n")
            return 2
    cfg = {
        "provider": "trello",
        "lanes": lanes_obj,
    }
    if write_targets:
        cfg["write_targets"] = json.loads(write_targets)
    if notes:
        cfg["lane_notes"] = json.loads(notes)
    path = config_path(root)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(cfg, indent=2) + "\n")
    print(f"wrote {path}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="op", required=True)
    for name in ("detect", "show"):
        p = sub.add_parser(name)
        p.add_argument("--root", default=os.getcwd())
    ps = sub.add_parser("set")
    ps.add_argument("--root", default=os.getcwd())
    ps.add_argument("--lanes", required=True, help="JSON: {state: [lane, ...]}")
    ps.add_argument("--write-targets", default=None, help="JSON: {state: lane} canonical write lane")
    ps.add_argument("--notes", default=None, help="JSON: {lane: 'meaning'} human semantics")
    args = ap.parse_args()

    root = os.path.abspath(args.root)
    if args.op == "detect":
        return cmd_detect(root)
    if args.op == "show":
        return cmd_show(root)
    if args.op == "set":
        return cmd_set(root, args.lanes, args.write_targets, args.notes)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
