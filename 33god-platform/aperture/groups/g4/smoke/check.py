"""G4 smoke — proves the observability data path end-to-end on god-g4.

(a) prometheus scrapes itself + node-exporter + cadvisor + the canary
    (up==1 for every job, via /api/v1/query).
(b) pausing the canary (a real god-g4 container) makes InstanceDown AND
    ContainerGone reach FIRING via Alertmanager /api/v2/alerts.
    (We pause rather than stop: this host runs a production auto-restart
    monitor that restarts any *exited* container, so a `docker compose stop`
    gets undone mid-test. A paused container is left alone, and pausing
    still kills the scrape path.)
(c) unpausing the canary makes them RESOLVE (bridge receives the resolved
    webhook).
(d) the alert-bridge received every webhook — its log shows the formatted
    human line (delivery evidence even when GOD_NTFY_URL is unset).
(e) Grafana's HTTP API answers: /api/health plus the provisioned Prometheus
    datasource proxied through Grafana (no anonymous-write deps).
(f) zero published host ports across the resolved config.

Nothing is touched outside the god-g4 project. Exit non-zero on any failure.
"""
import json
from pathlib import Path
from urllib.parse import quote
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]

CORE_HEALTHY = {"prometheus", "grafana", "alertmanager", "node-exporter",
                "cadvisor", "alert-bridge", "canary"}
CANARY_INSTANCE = "canary:8791"
CANARY_CONTAINER = "god-g4-canary-1"


def dc(*args, data=None):
    p = subprocess.run(["docker", "compose", *args], cwd=ROOT, input=data,
                       capture_output=True, text=True, timeout=90)
    if p.returncode:
        raise RuntimeError(f"compose command failed ({p.returncode}): {p.stderr}")
    return p.stdout


def curl(url, user=None, password=None, max_time=25):
    cmd = 'curl --silent --show-error --max-time %d -w "\\n%%{http_code}" ' % max_time
    if user:
        cmd += '-u "%s:%s" ' % (user, password)
    cmd += '"%s"' % url
    raw = dc("run", "--rm", "--no-deps", "-T", "--entrypoint", "sh",
             "smoke-client", "-ec", cmd)
    payload, status = raw.rsplit("\n", 1)
    return int(status.strip()), payload


def query_prom(expr):
    status, body = curl("http://prometheus:9090/api/v1/query?query=" + quote(expr, safe=""))
    assert status == 200, (expr, status, body)
    return json.loads(body)


def up_value(job):
    result = query_prom(f'up{{job="{job}"}}')
    vals = [float(x["value"][1]) for x in result["data"]["result"]]
    return vals


def alertmanager_alerts():
    status, body = curl("http://alertmanager:9093/api/v2/alerts")
    assert status == 200, (status, body)
    return json.loads(body)


def find_active_alerts(alertname):
    return [a for a in alertmanager_alerts()
            if a["labels"].get("alertname") == alertname
            and a["status"]["state"] == "active"]


def wait_for(predicate, desc, timeout):
    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
        try:
            if predicate():
                return True
        except Exception as exc:  # noqa: BLE001 — transient during bring-up
            last = exc
        time.sleep(3)
    raise RuntimeError(f"timed out after {timeout}s waiting for {desc}: {last}")


def main():
    config = json.loads(dc("config", "--format", "json"))
    assert config["name"] == "god-g4", "wrong Compose project"
    assert not any(s.get("ports") for s in config["services"].values()), \
        "host port published in core config"
    print("PASS: god-g4 only, zero published host ports", flush=True)

    # Core services healthy. cadvisor ships its own HEALTHCHECK (v0.49.1
    # image has a wget /healthz probe), so it is included in the healthy set
    # and additionally proven scrapable below via up{job="cadvisor"}==1.
    deadline = time.monotonic() + 240
    while True:
        rows = [json.loads(line) for line in dc("ps", "-a", "--format", "json").splitlines() if line]
        healthy = {r["Service"] for r in rows
                   if r["State"] == "running" and r.get("Health") == "healthy"}
        if CORE_HEALTHY <= healthy:
            break
        if time.monotonic() > deadline:
            raise RuntimeError("services not healthy: " + json.dumps(rows))
        time.sleep(3)
    print("PASS: 7 core services healthy", flush=True)

    # (a) prometheus self + exporter + canary targets all up.
    wait_for(lambda: all(up_value(j) == [1.0] for j in ("prometheus", "node-exporter", "cadvisor", "canary")),
             "all scrape targets up==1", 120)
    for job in ("prometheus", "node-exporter", "cadvisor", "canary"):
        print(f"PASS: up{{job=\"{job}\"}} == 1", flush=True)

    # (b) kill the canary -> alerts reach FIRING via Alertmanager.
    dc("pause", "canary")
    wait_for(lambda: bool(find_active_alerts("InstanceDown")), "InstanceDown FIRING", 120)
    print("PASS: InstanceDown FIRING after canary paused", flush=True)
    wait_for(lambda: bool(find_active_alerts("ContainerGone")), "ContainerGone FIRING", 180)
    print("PASS: ContainerGone FIRING after canary paused", flush=True)

    # (d) alert-bridge received the webhook: its log carries the formatted
    # line. group_wait (10s) delays the first notification, so poll rather
    # than assert once.
    def bridge_log():
        return dc("logs", "--no-color", "alert-bridge")
    wait_for(lambda: ("[firing]" in bridge_log() and "InstanceDown" in bridge_log()),
             "alert-bridge InstanceDown firing line", 60)
    wait_for(lambda: ("[firing]" in bridge_log() and "ContainerGone" in bridge_log()
                      and "god-g4-canary-1" in bridge_log()),
             "alert-bridge ContainerGone firing line", 60)
    print("PASS: alert-bridge logged the formatted firing lines (webhook received)", flush=True)

    # (c) bring the canary back -> alerts RESOLVE.
    dc("unpause", "canary")
    wait_for(lambda: up_value("canary") == [1.0], "canary up==1 again", 60)
    # The resolve signal: InstanceDown leaves Alertmanager's active set.
    wait_for(lambda: not find_active_alerts("InstanceDown"), "InstanceDown resolved", 180)
    wait_for(lambda: not find_active_alerts("ContainerGone"), "ContainerGone resolved", 180)
    print("PASS: alerts left FIRING state after canary returned", flush=True)
    # Bridge must have received the resolved webhook too (send_resolved: true).
    wait_for(lambda: "[resolved]" in bridge_log(), "alert-bridge resolved line", 120)
    print("PASS: alert-bridge logged the resolved lines (webhook received)", flush=True)

    # (e) Grafana HTTP API answers + provisioned Prometheus datasource proxies.
    status, body = curl("http://grafana:3000/api/health")
    assert status == 200 and json.loads(body)["database"] == "ok", (status, body)
    print("PASS: grafana /api/health ok", flush=True)
    guser = config["services"]["grafana"]["environment"].get("GF_SECURITY_ADMIN_USER", "admin")
    gpass = config["services"]["grafana"]["environment"].get("GF_SECURITY_ADMIN_PASSWORD", "aperture-g4-demo-only")
    status, body = curl(
        "http://grafana:3000/api/datasources/proxy/uid/g4-prometheus/api/v1/query?query=" + quote("up", safe=""),
        user=guser, password=gpass)
    assert status == 200, (status, body)
    proxied = json.loads(body)
    assert proxied["status"] == "success" and proxied["data"]["resultType"] == "vector", proxied
    print("PASS: grafana datasource proxy -> prometheus query succeeded", flush=True)

    print("SMOKE RESULT: PASS — self+exporter scrape up, canary kill->firing->resolve, "
          "alert-bridge webhook received, grafana datasource healthy, zero published ports")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"SMOKE RESULT: FAIL — {exc}", file=sys.stderr)
        sys.exit(1)
