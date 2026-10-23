"""Destructive-data-free proof; only synthetic events on the isolated god-g3 bus."""
import json
from pathlib import Path
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]

SUBJ_HEARTBEAT = "bloodbank.evt.system.heartbeat.received"
SUBJ_LIFECYCLE = "bloodbank.evt.lifecycle.status.updated"
SUBJ_AGENT = "bloodbank.evt.agent.invocation.started"
SUBJ_SMOKE = "bloodbank.evt.aperture.smoke.g3"   # NATS subject (5 tokens)
CE_TYPE_SMOKE = "bloodbank.aperture.smoke.g3"      # CloudEvents type (4 tokens)

CORE = {"nats", "outbox", "heartbeat-tick", "lifecycle-controller", "hermes-agent", "ntfy"}


def dc(*args, data=None):
    p = subprocess.run(["docker", "compose", *args], cwd=ROOT, input=data,
                       capture_output=True, text=True, timeout=60)
    if p.returncode:
        raise RuntimeError(f"compose command failed ({p.returncode}): {p.stderr}")
    return p.stdout


def http(url, body=None, auth=True):
    command = 'curl --silent --show-error --max-time 20 -w "\\n%{http_code}" '
    if auth:
        command += '-H "X-Aperture-Demo: $GOD_DEMO_HEADER_TOKEN" '
    if body is not None:
        command += '-H "Content-Type: application/json" --data-binary @- '
    command += url
    raw = dc("run", "--rm", "--no-deps", "-T", "--entrypoint", "sh", "smoke-client",
             "-ec", command, data=json.dumps(body) if body is not None else None)
    payload, status = raw.rsplit("\n", 1)
    return int(status), json.loads(payload)


def latest(subject):
    status, result = http(f"http://outbox:8789/latest?subject={subject}")
    assert status == 200, (subject, status, result)
    return result


def main():
    config = json.loads(dc("config", "--format", "json"))
    assert config["name"] == "god-g3", "wrong Compose project"
    assert not any(s.get("ports") for s in config["services"].values()), "host port published"

    deadline = time.monotonic() + 240
    while True:
        rows = [json.loads(line) for line in dc("ps", "-a", "--format", "json").splitlines() if line]
        healthy = {r["Service"] for r in rows if r["State"] == "running" and r.get("Health") == "healthy"}
        if CORE <= healthy:
            break
        if time.monotonic() > deadline:
            raise RuntimeError("services not healthy: " + json.dumps(rows))
        time.sleep(3)
    print("PASS: god-g3 only, zero published ports, 6 services healthy", flush=True)

    # D2 proof: the containerized agent really carries hermes-agent + the
    # vendored bloodbank plugin (verified from its own startup logs, not a
    # host-side import).
    logs = dc("logs", "--no-color", "hermes-agent")
    assert "stack: hermes-agent =" in logs, "hermes-agent version evidence missing"
    assert "stack: bloodbank_hermes_gateway = imports (adapter + contract)" in logs, \
        "vendored plugin import evidence missing"
    assert "bloodbank-platform" in logs, "plugin entry-point evidence missing"
    print("PASS: hermes-agent stack verified (hermes-agent + vendored bloodbank-platform plugin)", flush=True)

    # (a) heartbeat/tick path fires.
    hb = latest(SUBJ_HEARTBEAT)
    assert hb["subject"] == SUBJ_HEARTBEAT and hb["sequence"] > 0, hb
    ev = hb["event"]
    assert ev["type"] == "bloodbank.system.heartbeat.received", ev
    assert ev["source"] == "urn:33god:service:heartbeat-tick", ev
    assert ev["data"]["tick_seq"] >= 0 and ev["data"]["producer_id"].startswith("heartbeat-tick:"), ev
    print("PASS: heartbeat path fires (seq=%d, tick_seq=%d)" % (hb["sequence"], ev["data"]["tick_seq"]), flush=True)

    # (b) lifecycle-controller transitions a synthetic task envelope.
    lc = latest(SUBJ_LIFECYCLE)
    assert lc["subject"] == SUBJ_LIFECYCLE and lc["sequence"] > 0, lc
    ev = lc["event"]
    assert ev["type"] == "bloodbank.lifecycle.status.updated", ev
    data = ev["data"]
    assert data["current"]["status"] == "active", data
    assert data["previous"] is None or data["previous"]["status"] == "planned", data
    assert data["transition"]["reason"] == "PROGRESSING", data
    assert data["transition"]["detector"] == "lifecycle-controller@0.1.0", data
    print("PASS: synthetic task envelope transitioned (%s -> active, reason=%s)"
          % (data["previous"]["status"] if data["previous"] else "none", data["transition"]["reason"]), flush=True)

    # (c) containerized agent publishes invocation.started to NATS.
    ag = latest(SUBJ_AGENT)
    assert ag["subject"] == SUBJ_AGENT and ag["sequence"] > 0, ag
    ev = ag["event"]
    assert ev["type"] == "bloodbank.agent.invocation.started", ev
    assert ev["producer"] == "hermes-agent:g3-demo", ev
    assert ev["source"] == "urn:33god:service:bloodbank-hermes-gateway", ev
    assert ev["data"]["invocation_id"] and ev["data"]["target_agent_id"] == "g3-demo-agent", ev
    assert ev["correlationid"] and ev["id"], ev
    print("PASS: agent heartbeat task published invocation.started (seq=%d, producer=%s)"
          % (ag["sequence"], ev["producer"]), flush=True)

    # Direct outbox path: negative + positive + retained readback correlation.
    event_id = str(uuid.uuid4())
    status, result = http("http://outbox:8789/publish", {"id": event_id, "ping": True}, auth=False)
    assert status == 401 and result["error"] == "demo header required", (status, result)
    print("PASS: missing demo header rejected (401)", flush=True)
    status, result = http("http://outbox:8789/publish", {"id": "invalid", "ping": True})
    assert status == 400, (status, result)
    print("PASS: malformed synthetic input rejected (400)", flush=True)

    smoke_event = {
        "specversion": "1.0",
        "id": event_id,
        "source": "urn:33god:aperture:g3",
        "type": CE_TYPE_SMOKE,
        "subject": SUBJ_SMOKE,
        "time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "datacontenttype": "application/json",
        "correlationid": event_id,
        "causationid": event_id,
        "producer": "aperture-g3-smoke", "service": "aperture-g3",
        "domain": "aperture", "kind": "event",
        "ordering_key": "aperture:g3:smoke",
        "actor": {"type": "service", "agent_id": "aperture-g3-smoke"},
        "data": {"ping": True, "via": "g3-outbox"},
    }
    status, ack = http("http://outbox:8789/publish", smoke_event)
    assert status == 200 and ack["published"] is True and ack["id"] == event_id, (status, ack)
    assert ack["subject"] == SUBJ_SMOKE and ack["sequence"] > 0 and ack["stream"] == "G3_EVENTS", ack
    print("PASS: in-network curl -> outbox -> JetStream persistence ack: " + json.dumps(ack), flush=True)

    stored = latest(SUBJ_SMOKE)
    assert stored["subject"] == ack["subject"] and stored["sequence"] == ack["sequence"], stored
    ev = stored["event"]
    assert ev["id"] == event_id and ev["correlationid"] == event_id, ev
    assert ev["type"] == CE_TYPE_SMOKE and ev["subject"] == SUBJ_SMOKE and ev["kind"] == "event", ev
    assert ev["source"] == "urn:33god:aperture:g3" and ev["data"] == {"ping": True, "via": "g3-outbox"}, ev
    print("PASS: NATS stream GET (not HTTP cache) CloudEvent fidelity: " + json.dumps(ev), flush=True)

    print("SMOKE RESULT: PASS — heartbeat fires + lifecycle transition + agent publish + CloudEvent persistence ack + retained readback")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"SMOKE RESULT: FAIL — {exc}", file=sys.stderr)
        sys.exit(1)
