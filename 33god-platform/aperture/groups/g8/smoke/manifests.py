#!/usr/bin/env python3
"""Check every external image in the resolved G8 compose config for
linux/arm64 + linux/amd64 manifest entries. Crib: g7/smoke/manifests.py."""
import json
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
config = json.loads(subprocess.check_output(
    ["docker", "compose", "config", "--format", "json"],
    cwd=root, text=True))
images = set()
for name, svc in config["services"].items():
    if "build" not in svc and svc.get("image"):
        images.add(svc["image"])
    build = svc.get("build") or {}
    for arg in (build.get("args") or {}).values():
        if isinstance(arg, str) and "/" in arg and ":" in arg:
            images.add(arg)
# the vendored candystore build uses the plain python base (Dockerfile FROM)
images.add("python:3.11-slim")

for image in sorted(images):
    raw = subprocess.check_output(["docker", "manifest", "inspect", image],
                                  text=True, timeout=180)
    manifest = json.loads(raw)
    platforms = {f"{m['platform'].get('os')}/{m['platform'].get('architecture')}": m["digest"]
                 for m in manifest.get("manifests", [])
                 if m["platform"].get("os") != "unknown"}
    missing = {"linux/arm64", "linux/amd64"} - platforms.keys()
    if missing:
        print(f"FAIL {image}: missing {sorted(missing)}", file=sys.stderr)
        raise SystemExit(1)
    print(f"$ docker manifest inspect {image}")
    for target in ("linux/arm64", "linux/amd64"):
        print(f"  {target} {platforms[target][:19]}...")
print("MANIFEST RESULT: PASS — every external image has linux/arm64 and linux/amd64")
