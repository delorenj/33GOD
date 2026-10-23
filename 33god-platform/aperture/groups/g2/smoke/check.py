"""Destructive-data-free proof; only synthetic webhook posts on god-g2."""
import json
from pathlib import Path
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]


def dc(*args, data=None):
    p = subprocess.run(["docker", "compose", *args], cwd=ROOT, input=data,
                       capture_output=True, text=True, timeout=45)
    if p.returncode:
        raise RuntimeError(f"compose command failed ({p.returncode}): {p.stderr}")
    return p.stdout


def http(url, body=None, auth=True):
    # Header comes from the container env; no host .env parsing or printed token.
    command = 'curl --silent --show-error --max-time 15 -w "\\n%{http_code}" '
    if auth:
        command += '-H "X-Aperture-Demo: $GOD_DEMO_HEADER_TOKEN" '
    if body is not None:
        command += '-H "Content-Type: application/json" --data-binary @- '
    command += url
    raw = dc("run", "--rm", "--no-deps", "-T", "--entrypoint", "sh", "smoke-client",
             "-ec", command, data=json.dumps(body) if body is not None else None)
    payload, status = raw.rsplit("\n", 1)
    return int(status), json.loads(payload)


def main():
    config = json.loads(dc("config", "--format", "json"))
    assert config["name"] == "god-g2", "wrong Compose project"
    assert not any(s.get("ports") for s in config["services"].values()), "host port published"
    expected = {"n8n", "n8n-postgres", "nats-outbox", "nats-outbox-broker"}
    deadline = time.monotonic() + 180
    while True:
        rows = [json.loads(line) for line in dc("ps", "-a", "--format", "json").splitlines() if line]
        healthy = {r["Service"] for r in rows if r["State"] == "running" and r.get("Health") == "healthy"}
        imported = any(r["Service"] == "n8n-import" and r["State"] == "exited" and r["ExitCode"] == 0 for r in rows)
        if expected <= healthy and imported:
            break
        if time.monotonic() > deadline:
            raise RuntimeError("services not healthy/import not exit 0: " + json.dumps(rows))
        time.sleep(2)
    print("PASS: god-g2 only, zero published ports, 4 services healthy, import exit 0", flush=True)
    workflow_rows = dc("exec", "-T", "n8n-postgres", "sh", "-ec",
                       'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT id, active FROM workflow_entity ORDER BY id"')
    state = dict(line.split("|") for line in workflow_rows.splitlines() if line)
    assert state == {"apertureG2Smoke01": "t", "apertureG2Plane01": "f", "apertureG2Sched01": "f"}, state
    print("PASS: only smoke active; Plane TEMPLATE-NOT-LIVE and schedule inactive", flush=True)
    count = dc("exec", "-T", "n8n-postgres", "sh", "-ec",
               'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "SELECT count(*) FROM credentials_entity"').strip()
    assert count == "0", "fresh demo unexpectedly contains n8n credentials"
    print("PASS: fresh n8n database has zero credential records", flush=True)
    event_id = str(uuid.uuid4())
    status, result = http("http://n8n:5678/webhook/aperture-g2-smoke", {"id": event_id, "ping": True}, auth=False)
    assert status == 401 and result["error"] == "demo header required", (status, result)
    print("PASS: missing demo header rejected (401)", flush=True)
    status, result = http("http://n8n:5678/webhook/aperture-g2-smoke", {"id": "invalid", "ping": True})
    assert status == 400, (status, result)
    print("PASS: malformed synthetic input rejected (400)", flush=True)
    status, ack = http("http://n8n:5678/webhook/aperture-g2-smoke", {"id": event_id, "ping": True})
    assert status == 200 and ack["published"] is True and ack["id"] == event_id, (status, ack)
    assert ack["subject"] == "bloodbank.evt.aperture.smoke.g2" and ack["sequence"] > 0, ack
    print("PASS: in-network curl → n8n → JetStream persistence ack: " + json.dumps(ack), flush=True)
    status, stored = http("http://nats-outbox:8789/latest")
    assert status == 200, (status, stored)
    event = stored["event"]
    assert stored["subject"] == ack["subject"] and stored["sequence"] == ack["sequence"], stored
    assert event["id"] == event_id and event["correlationid"] == event_id, event
    assert (
        event["type"] == "bloodbank.aperture.smoke.g2"           # 4 tokens (canonical §2)
        and event["subject"] == ack["subject"] == "bloodbank.evt.aperture.smoke.g2"  # 5 tokens
        and event["specversion"] == "1.0"
        and event["kind"] == "event" and event["actor"]["type"] == "service"
        and event["service"] == "aperture-g2" and event["domain"] == "aperture"
    ), event
    assert event["source"] == "urn:33god:aperture:g2" and event["data"] == {"ping": True, "via": "n8n-webhook"}, event
    print("PASS: NATS stream GET (not HTTP cache) CloudEvent fidelity: " + json.dumps(event), flush=True)
    print("SMOKE RESULT: PASS — webhook → validate → CloudEvent → NATS JetStream → readback")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"SMOKE RESULT: FAIL — {exc}", file=sys.stderr)
        sys.exit(1)
