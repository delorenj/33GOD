#!/usr/bin/env python3
"""Momo's self-contained Trello board adapter (stdlib only — no uv/httpx).

This is the Trello twin of the pjangler `tp` adapter's providers/trello.sh, but
bundled INSIDE the momo skill so Momo carries its own board capability into ANY
repo — the repo needs only a `.project.json` (ticket_provider.type = "trello")
and, when its kanban columns are non-standard, a `.momo/config.json` lane map.
Nothing is installed per-repo; local parameters override shared behavior.

Implements the same normalized-op contract as `tp` so Momo's board-awareness
doctrine is provider-uniform:
    resolve                          -> {provider, board_id, board_url, me, list_map, board_lists}
    active_milestone                 -> {id, name, state}   (Trello has no cycles; board-as-milestone)
    list_issues                      -> [{id, key, title, state, state_type, list, url, ...}]
    get_issue <id|idShort>           -> {id, key, title, description, acceptance, state, list, comments}
    comment <id> <body>              -> prints comment id
    transition <id> <state|lane>     -> move to the lane for a normalized state, OR a literal lane name

Credentials (env): TRELLO_API_KEY (or TRELLO_KEY) + TRELLO_TOKEN.
Board id: --board-id, else $TRELLO_BOARD_ID, else .project.json ticket_provider.board_id.
Lane map: <root>/.momo/config.json  "lanes" table (multi-lane per state). Falls back to
the STANDARD flow if absent. Fails loud (never guesses) on an unmapped/unknown target.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.parse
import urllib.request

API = "https://api.trello.com/1"

# Normalized state -> Trello lane(s). Used when a repo has no .momo/config.json.
# Matches the pjangler trello.sh standard defaults. Non-standard boards supply a
# config; the FIRST lane per state is the canonical write target.
_STANDARD_LANES = {
    "backlog": ["Backlog"],
    "unstarted": ["To Do"],
    "started": ["In Progress"],
    "in_review": ["Review"],
    "completed": ["Done"],
}
_NORMALIZED_STATES = list(_STANDARD_LANES)


def die(msg: str, code: int = 2):
    sys.stderr.write(f"trello: {msg}\n")
    raise SystemExit(code)


def find_root(start: str) -> str:
    d = os.path.abspath(start)
    while True:
        if os.path.isfile(os.path.join(d, ".project.json")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            return os.path.abspath(start)
        d = parent


def load_project(root: str) -> dict:
    path = os.path.join(root, ".project.json")
    try:
        return json.loads(open(path, encoding="utf-8").read())
    except Exception:
        return {}


def load_config(root: str) -> dict:
    path = os.path.join(root, ".momo", "config.json")
    if not os.path.isfile(path):
        return {}
    try:
        return json.loads(open(path, encoding="utf-8").read())
    except Exception as e:
        die(f"invalid .momo/config.json: {e}")


def lane_map(config: dict) -> dict:
    lanes = (config.get("lanes") or {}) if isinstance(config, dict) else {}
    m = {k: list(v) for k, v in _STANDARD_LANES.items()}
    for state in m:
        if isinstance(lanes.get(state), list) and lanes[state]:
            m[state] = list(lanes[state])
    return m


def write_target(config: dict, lm: dict, state: str) -> str:
    wt = (config.get("write_targets") or {}) if isinstance(config, dict) else {}
    return wt.get(state) or lm[state][0]


def state_for_lane(lane: str, lm: dict) -> str:
    for state in ("completed", "in_review", "started", "unstarted", "backlog"):
        if lane in lm[state]:
            return state
    return "other"


class Trello:
    def __init__(self, key: str, token: str):
        self.key, self.token = key, token

    def _url(self, path: str, extra: dict | None = None) -> str:
        q = {"key": self.key, "token": self.token, **(extra or {})}
        return f"{API}/{path}?{urllib.parse.urlencode(q)}"

    def _req(self, method: str, path: str, extra: dict | None = None):
        req = urllib.request.Request(self._url(path, extra), method=method)
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                body = r.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            die(f"{method} {path} -> HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:200]}", 4)
        except Exception as e:
            die(f"{method} {path} -> {e}", 4)
        return json.loads(body) if body.strip() else {}

    def get(self, path, extra=None):
        return self._req("GET", path, extra)

    def put(self, path, extra=None):
        return self._req("PUT", path, extra)

    def post(self, path, extra=None):
        return self._req("POST", path, extra)


def creds() -> tuple[str, str]:
    key = os.environ.get("TRELLO_API_KEY") or os.environ.get("TRELLO_KEY")
    token = os.environ.get("TRELLO_TOKEN")
    if not key or not token:
        die("TRELLO_API_KEY (or TRELLO_KEY) and TRELLO_TOKEN must be set", 2)
    return key, token


def emit(obj):
    print(json.dumps(obj, indent=2))


def main() -> int:
    argv = sys.argv[1:]
    root = os.getcwd()
    board_override = None
    # Pull out --root / --board-id anywhere in argv.
    rest = []
    i = 0
    while i < len(argv):
        if argv[i] == "--root" and i + 1 < len(argv):
            root = argv[i + 1]; i += 2; continue
        if argv[i] == "--board-id" and i + 1 < len(argv):
            board_override = argv[i + 1]; i += 2; continue
        rest.append(argv[i]); i += 1
    if not rest:
        sys.stderr.write(__doc__ or "")
        return 2

    root = find_root(root)
    project = load_project(root)
    config = load_config(root)
    lm = lane_map(config)
    tp = (project.get("ticket_provider") or {}) if isinstance(project, dict) else {}
    board = board_override or os.environ.get("TRELLO_BOARD_ID") or tp.get("board_id")
    if not board:
        die("no board id (--board-id, $TRELLO_BOARD_ID, or .project.json ticket_provider.board_id)", 2)

    key, token = creds()
    t = Trello(key, token)
    op, args = rest[0], rest[1:]

    if op == "resolve":
        b = t.get(f"boards/{board}", {"fields": "name,url"})
        me = t.get("members/me", {"fields": "username,fullName"})
        lists = t.get(f"boards/{board}/lists", {"fields": "name"})
        emit({
            "provider": "trello",
            "board_id": b.get("id", board),
            "board_url": b.get("url", ""),
            "board_name": b.get("name", ""),
            "me": {"id": me.get("id", ""), "username": me.get("username", ""), "full_name": me.get("fullName", "")},
            "list_map": lm,
            "config_present": bool(config),
            "board_lists": [l.get("name", "") for l in lists],
        })
    elif op == "active_milestone":
        b = t.get(f"boards/{board}", {"fields": "name"})
        emit({"id": b.get("id", board), "name": b.get("name", ""), "state": "active"})
    elif op == "list_issues":
        lists = {l["id"]: l.get("name", "") for l in t.get(f"boards/{board}/lists", {"fields": "name"})}
        cards = t.get(f"boards/{board}/cards", {"fields": "name,idList,dateLastActivity,url,shortLink,idMembers"})
        rows = []
        for c in cards:
            lane = lists.get(c.get("idList", ""), "?")
            state = state_for_lane(lane, lm)
            rows.append({
                "id": c.get("id", ""), "key": c.get("shortLink", ""), "title": c.get("name", ""),
                "state": state, "state_type": state, "list": lane,
                "updated_at": c.get("dateLastActivity", ""), "assignee": c.get("idMembers", []),
                "url": c.get("url", ""),
            })
        order = {"started": 0, "in_review": 1, "unstarted": 2, "backlog": 3, "completed": 4, "other": 5}
        rows.sort(key=lambda r: (order.get(r["state"], 9), r["list"], r["title"]))
        emit(rows)
    elif op == "get_issue":
        if not args:
            die("get_issue needs <id|idShort>")
        c = t.get(f"cards/{args[0]}", {"fields": "name,desc,idList,shortLink,url,idShort"})
        lists = {l["id"]: l.get("name", "") for l in t.get(f"boards/{board}/lists", {"fields": "name"})}
        lane = lists.get(c.get("idList", ""), "?")
        acts = t.get(f"cards/{args[0]}/actions", {"filter": "commentCard", "limit": "50"})
        emit({
            "id": c.get("id", ""), "key": c.get("shortLink", ""), "title": c.get("name", ""),
            "description": c.get("desc", ""), "acceptance": c.get("desc", ""),
            "state": state_for_lane(lane, lm), "state_type": state_for_lane(lane, lm), "list": lane,
            "url": c.get("url", ""),
            "comments": [
                {"id": a.get("id", ""), "author": (a.get("memberCreator") or {}).get("username", ""),
                 "date": a.get("date", ""), "body": (a.get("data") or {}).get("text", "")}
                for a in acts
            ],
        })
    elif op == "comment":
        if len(args) < 2:
            die("comment needs <id|idShort> <body>")
        res = t.post(f"cards/{args[0]}/actions/comments", {"text": " ".join(args[1:])})
        print(res.get("id", ""))
    elif op == "transition":
        if len(args) < 2:
            die("transition needs <id|idShort> <state|lane>")
        card_ref, target = args[0], args[1]
        lists = {l.get("name", ""): l["id"] for l in t.get(f"boards/{board}/lists")}
        if target in _NORMALIZED_STATES:
            lane = write_target(config, lm, target)
        elif target in lists:
            lane = target
        else:
            die(f"{target!r} is neither a normalized state ({', '.join(_NORMALIZED_STATES)}) "
                f"nor a live lane ({sorted(lists)}). Not guessing.", 3)
        if lane not in lists:
            die(f"{target!r} maps to lane {lane!r}, which is not on the board. "
                f"Lanes: {sorted(lists)}. Fix .momo/config.json — not guessing.", 3)
        t.put(f"cards/{card_ref}", {"idList": lists[lane]})
        emit({"ok": True, "card": card_ref, "target": target, "moved_to": lane,
              "state": state_for_lane(lane, lm)})
    else:
        die(f"unknown op {op!r}. Ops: resolve|active_milestone|list_issues|get_issue|comment|transition")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
