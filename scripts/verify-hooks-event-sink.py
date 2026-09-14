#!/usr/bin/env python3
"""Exercise a native hook through Bloodbank, Holocene, and Candystore.

This creates one identifiable acceptance invocation and retries its delivery.
It never executes a CLI tool or reads the hub's HTTP API/receipt database.
Run against a deployed collector, after its initial catch-up has completed.
"""
from __future__ import annotations

import argparse
import json
import os
import queue
import socket
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid


def read_json(url: str):
    with urllib.request.urlopen(url, timeout=5) as response:
        return json.load(response)


class Stream:
    def __init__(self, url: str, cursor: int):
        request = urllib.request.Request(url, headers={
            "Accept": "text/event-stream", "Last-Event-ID": str(cursor),
        })
        self.response = urllib.request.urlopen(request, timeout=25)
        self.events: queue.Queue = queue.Queue()
        self.thread = threading.Thread(target=self._read, daemon=True)
        self.thread.start()

    def _read(self):
        fields: dict[str, str] = {}
        data: list[str] = []
        try:
            for raw in self.response:
                line = raw.decode("utf-8").rstrip("\r\n")
                if not line:
                    if data:
                        self.events.put((fields.get("event", "message"), fields.get("id"), json.loads("\n".join(data))))
                    fields, data = {}, []
                elif line.startswith("data:"):
                    data.append(line[5:].lstrip(" "))
                elif not line.startswith(":") and ":" in line:
                    key, value = line.split(":", 1)
                    fields[key] = value.lstrip(" ")
        except Exception as error:
            self.events.put(error)

    def receipt(self, invocation_id: str, predicate, timeout: float = 20):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            item = self.events.get(timeout=max(.01, deadline - time.monotonic()))
            if isinstance(item, Exception):
                raise item
            name, cursor, body = item
            if name == "reset":
                raise AssertionError(f"Unexpected stream reset: {body.get('reason')}")
            if name != "bloodbank-event":
                continue
            envelope = body["envelope"]
            invocation = envelope.get("data", {}).get("invocation", {})
            if invocation.get("invocation_id") == invocation_id and predicate(invocation):
                return int(cursor), envelope
        raise TimeoutError("Receipt did not reach the event stream")

    def close(self):
        self.response.close()


def send_native(path: str, invocation_id: str, cli: str, native: str):
    frame = {
        "v": 1, "cli": cli, "native": native, "invocation_id": invocation_id,
        "cwd": "/tmp", "env": {"DISABLE_HINDSIGHT_HOOKS": "1"},
        "payload": {"session_id": f"hooks-sink-acceptance-{invocation_id}",
                    "tool_name": "Read", "tool_input": {"file_path": "/dev/null"},
                    "tool_use_id": invocation_id},
    }
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.settimeout(15)
        client.connect(path)
        client.sendall(json.dumps(frame).encode() + b"\n")
        with client.makefile("rb") as response:
            reply = json.loads(response.readline(1 << 20))
    accepted = reply.get("invocation_id")
    assert isinstance(accepted, str) and accepted, "Hub did not return an invocation identity"
    return accepted


def wait_json(url: str, predicate, timeout: float = 20):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            value = read_json(url)
            if predicate(value):
                return value
        except urllib.error.HTTPError as error:
            if error.code != 404:
                raise
        time.sleep(.1)
    raise TimeoutError(f"Acceptance condition not reached: {urllib.parse.urlparse(url).path}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api", default="http://localhost:4000")
    parser.add_argument("--candystore", default="http://localhost:8683")
    parser.add_argument("--socket", default=f"/run/user/{os.getuid()}/33god/hook-hub.sock")
    parser.add_argument("--cli", default="codex")
    parser.add_argument("--native", default="PreToolUse")
    args = parser.parse_args()
    api, candystore = args.api.rstrip("/"), args.candystore.rstrip("/")
    before = read_json(f"{api}/api/events/status")
    assert before["state"] == "live" and not before.get("catching_up"), \
        f"Collector must finish catch-up first: {before['state']}"
    native_identity = str(uuid.uuid4())
    stream_url = f"{api}/api/events/stream?type=bloodbank.agent.hook.updated"
    first = Stream(stream_url, before["cursor"])
    try:
        started = time.monotonic()
        invocation_id = send_native(args.socket, native_identity, args.cli, args.native)
        _, arrival = first.receipt(invocation_id, lambda _: True)
        latency = round((time.monotonic() - started) * 1000)
        terminal = wait_json(f"{api}/api/modules/hooks/invocations/{invocation_id}",
                             lambda v: v["invocation"]["status"] != "received")
        cursor_before_retry = read_json(f"{api}/api/events/status")["cursor"]
    finally:
        first.close()

    # The browser is disconnected while a duplicate native delivery is recorded.
    # Reconnection must replay its fact and still produce one invocation row.
    assert send_native(args.socket, native_identity, args.cli, args.native) == invocation_id
    latest = wait_json(f"{api}/api/modules/hooks/invocations/{invocation_id}",
                       lambda v: v["invocation"].get("deduplicated", 0) == 1)
    replay = Stream(stream_url, cursor_before_retry)
    try:
        replay_cursor, repeated = replay.receipt(invocation_id, lambda v: v.get("deduplicated") == 1)
    finally:
        replay.close()
    assert replay_cursor > cursor_before_retry
    query = urllib.parse.urlencode({"cli": args.cli, "native": args.native, "limit": 200})
    page = read_json(f"{api}/api/modules/hooks/invocations?{query}")
    assert sum(row["invocation_id"] == invocation_id for row in page["items"]) == 1
    for envelope in (arrival, repeated):
        saved = wait_json(f"{candystore}/events/{envelope['id']}/raw", lambda value: value.get("id") == envelope["id"])
        assert saved["data"]["invocation"]["invocation_id"] == invocation_id
    generic = read_json(f"{api}/api/events?limit=100")
    other_types = sorted({item["envelope"]["type"] for item in generic["items"]
                          if item["envelope"]["type"] not in {"bloodbank.agent.hook.updated", "bloodbank.system.hook.updated"}})
    assert other_types, "Common collection must contain non-hook events too"
    print(json.dumps({
        "passed": True, "invocation_id": invocation_id, "cli": args.cli, "native": args.native,
        "first_event_latency_ms": latency, "terminal_status": terminal["invocation"]["status"],
        "deduplicated": latest["invocation"]["deduplicated"], "invocation_rows": 1,
        "candystore_event_ids": [arrival["id"], repeated["id"]],
        "replay_from": cursor_before_retry, "replayed_cursor": replay_cursor,
        "other_collected_types": other_types[:5],
    }, indent=2))


if __name__ == "__main__":
    main()
