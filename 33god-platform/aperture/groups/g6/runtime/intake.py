"""Portable intake transport, not Wax. Blank credentials mean remote intake is INERT.
Pattern: HeyMa telnyx-s3-intake (stage -> verify -> atomic publish -> receipt).
Fresh implementation: no personal scope, credential resolver or Wax ledger copied.
"""
import hashlib
import io
import json
import os
from pathlib import Path
import threading
import time
import urllib.request
import uuid
import wave
from fastapi import FastAPI

ROOT = Path(os.environ.get("GOD_PIPELINE_DIR", "/pipeline"))
INTERVAL = float(os.environ.get("GOD_INTAKE_POLL_SECONDS", "2"))
MAX_BYTES = 16 * 1024 * 1024
last_scan = 0.0
last_error = None
app = FastAPI()


def configured():
    return all(os.environ.get(name) for name in
               ("GOD_INTAKE_ENDPOINT", "GOD_INTAKE_BUCKET", "GOD_INTAKE_ACCESS_KEY", "GOD_INTAKE_SECRET_KEY"))


def post(url, payload, headers=None):
    request = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                     headers={"Content-Type": "application/json", **(headers or {})})
    with urllib.request.urlopen(request, timeout=5) as response:
        if not 200 <= response.status < 300:
            raise RuntimeError("notification_rejected")


def alert(code):
    url = os.environ.get("GOD_NTFY_URL", "")
    if url:
        try:
            post(url.rstrip("/") + "/" + os.environ.get("GOD_NTFY_TOPIC", "aperture-g6-alerts"),
                 {"service": "audio-intake", "error": code})
        except Exception:
            print("intake alert delivery failed", flush=True)


def publish(path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise ValueError("invalid_local_file")
    raw = path.read_bytes()
    with wave.open(io.BytesIO(raw)) as wav:
        if wav.getnframes() <= 0:
            raise ValueError("empty_wav")
    digest = hashlib.sha256(raw).hexdigest()
    target = ROOT / "input" / (digest + ".wav")
    receipt = ROOT / "receipts" / (digest + ".json")
    if not target.exists():
        temp = target.with_suffix(".partial")
        temp.write_bytes(raw)
        temp.replace(target)
    if not receipt.exists():
        event = {"version": 1, "id": str(uuid.uuid4()), "sha256": digest,
                 "file": target.name, "bytes": len(raw), "state": "landed", "notified": False}
        temp = receipt.with_suffix(".partial")
        temp.write_text(json.dumps(event))
        temp.replace(receipt)
        print(json.dumps(event), flush=True)
    path.unlink()  # only local inbox copy; remote source is NEVER deleted


def remote_poll():
    import boto3
    from botocore.config import Config
    client = boto3.client("s3", endpoint_url=os.environ["GOD_INTAKE_ENDPOINT"],
                           aws_access_key_id=os.environ["GOD_INTAKE_ACCESS_KEY"],
                           aws_secret_access_key=os.environ["GOD_INTAKE_SECRET_KEY"],
                           region_name=os.environ.get("GOD_INTAKE_REGION", "us-east-1"),
                           config=Config(connect_timeout=5, read_timeout=10, retries={"max_attempts": 1}))
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=os.environ["GOD_INTAKE_BUCKET"],
                                   Prefix=os.environ.get("GOD_INTAKE_PREFIX", "")):
        for obj in page.get("Contents", []):
            if not obj["Key"].lower().endswith(".wav") or not 0 < obj["Size"] <= MAX_BYTES:
                continue
            identity = hashlib.sha256((obj["Key"] + obj.get("ETag", "")).encode()).hexdigest()
            marker = ROOT / "receipts" / (identity + ".remote")
            if marker.exists():
                continue
            response = client.get_object(Bucket=os.environ["GOD_INTAKE_BUCKET"], Key=obj["Key"],
                                         IfMatch=obj["ETag"])
            with response["Body"] as body:
                raw = body.read(MAX_BYTES + 1)
            if len(raw) != obj["Size"]:
                raise ValueError("remote_size_mismatch")
            dest = ROOT / "inbox" / (identity + ".wav")
            temp = dest.with_suffix(".partial")
            temp.write_bytes(raw)
            temp.replace(dest)
            publish(dest)
            marker.write_text("landed\n")


def notify_pending():
    url = os.environ.get("GOD_N8N_INTAKE_URL", "")
    if not url:
        return
    for receipt in (ROOT / "receipts").glob("*.json"):
        event = json.loads(receipt.read_text())
        if event.get("notified"):
            continue
        headers = {}
        key = os.environ.get("GOD_N8N_INTAKE_KEY", "")
        if key:
            headers["X-API-Key"] = key
        post(url, event, headers)
        event["notified"] = True
        temp = receipt.with_suffix(".partial")
        temp.write_text(json.dumps(event))
        temp.replace(receipt)


def scan():
    global last_scan, last_error
    while True:
        try:
            # Remote credentials are optional; LOCAL inbox pickup is always real.
            for path in (ROOT / "inbox").glob("*.wav"):
                before = path.stat()
                time.sleep(min(INTERVAL, 0.2))
                if (before.st_size, before.st_mtime_ns) != (path.stat().st_size, path.stat().st_mtime_ns):
                    continue
                try:
                    publish(path)
                except (ValueError, wave.Error, EOFError):
                    path.rename(path.with_suffix(".rejected"))
                    print("invalid WAV quarantined", flush=True)
            if configured():
                remote_poll()
            notify_pending()
            last_error = None
        except Exception as exc:
            # Never print exception messages or URLs: transport SDK errors can carry credentials.
            last_error = type(exc).__name__
            print("intake scan failed:", last_error, flush=True)
            alert(last_error)
        last_scan = time.time()
        time.sleep(INTERVAL)


@app.on_event("startup")
def start():
    for name in ("inbox", "input", "receipts"):
        (ROOT / name).mkdir(parents=True, exist_ok=True)
    print("remote intake " + ("configured" if configured() else "INERT: credentials unset"), flush=True)
    threading.Thread(target=scan, daemon=True).start()


@app.get("/healthz")
def healthz():
    age = time.time() - last_scan
    return {"ready": 0 < last_scan and age < max(60, INTERVAL * 3),
            "remote": "configured" if configured() else "inert", "error": last_error,
            "local_pickup": "enabled", "scan_age_s": round(age, 2)}
