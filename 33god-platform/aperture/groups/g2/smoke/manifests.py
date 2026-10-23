#!/usr/bin/env python3
"""Check all resolved external images (including the outbox base) for both targets."""
import json
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[1]
config = json.loads(subprocess.check_output(
    ["docker", "compose", "--profile", "tools", "config", "--format", "json"], cwd=root, text=True))
images = {s["image"] for s in config["services"].values() if "build" not in s}
images.add(config["services"]["nats-outbox"]["build"]["args"]["GOD_PYTHON_IMAGE"])
for image in sorted(images):
    raw = subprocess.check_output(["docker", "manifest", "inspect", image], text=True, timeout=180)
    manifest = json.loads(raw)
    # schemaVersion 2 index/list: architecture is on each descriptor's platform.
    platforms = {f"{m['platform'].get('os')}/{m['platform'].get('architecture')}": m["digest"]
                 for m in manifest.get("manifests", [])}
    missing = {"linux/arm64", "linux/amd64"} - platforms.keys()
    if missing:
        raise SystemExit(f"FAIL {image}: missing index platforms {sorted(missing)}. "
                         "Single manifests need explicit per-platform config/pull verification; not inferred.")
    print(f"$ docker manifest inspect {image}\nexit=0 schemaVersion={manifest['schemaVersion']}")
    for target in ["linux/arm64", "linux/amd64"]:
        print(target, platforms[target])
print("MANIFEST RESULT: PASS — every external image has linux/arm64 and linux/amd64")
