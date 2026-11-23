#!/usr/bin/env python3
"""Use the installed Hermes gateway's own client for this officer's cancellation/readback.

Not an alternative runner: no session create, submit, fallback, service control or clock.
Discovery is read-only and connect_gateway gets that exact existing endpoint.
"""
import asyncio
import json
from pathlib import Path
import sys

HOME = Path.home() / ".hermes/profiles/33god-pm"
HERMES = Path.home() / ".hermes/hermes-agent"
sys.path.insert(0, str(HERMES))
from hermes_cli.gateway_client import connect_gateway
from hermes_cli.gateway_runtime import attachable, discover_gateway_endpoint


async def inspect(session_id, interrupt=False):
    endpoint = discover_gateway_endpoint(HOME)
    if not attachable(endpoint):
        raise RuntimeError("shared gateway unavailable; no spawn/fallback")
    async with connect_gateway(endpoint=endpoint.endpoint) as client:
        snapshot = await client.rpc("session.resume", session_id=session_id, _timeout=8)
        if snapshot.get("stored_session_id") != session_id:
            raise RuntimeError("session identity changed; manual review")
        if interrupt and (snapshot.get("running") is True or snapshot.get("pending") or snapshot.get("prompts")):
            await client.rpc("session.interrupt", session_id=session_id,
                             execution_generation=snapshot["execution_generation"], _timeout=8)
            snapshot = await client.rpc("session.resume", session_id=session_id, _timeout=8)
        settled = (snapshot.get("running") is False
                   and not snapshot.get("pending") and not snapshot.get("prompts"))
        return {"session_id": session_id, "settled": settled,
                "running": snapshot.get("running"),
                "pending": len(snapshot.get("pending", [])), "prompts": len(snapshot.get("prompts", []))}


if __name__ == "__main__":
    try:
        if len(sys.argv) != 3 or sys.argv[1] not in {"status", "interrupt"}:
            raise ValueError("usage: gateway_control.py status|interrupt SESSION_ID")
        print(json.dumps(asyncio.run(inspect(sys.argv[2], sys.argv[1] == "interrupt"))))
    except Exception as exc:
        print(json.dumps({"settled": False, "error": type(exc).__name__}), file=sys.stderr)
        raise SystemExit(1)
