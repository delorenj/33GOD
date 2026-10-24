#!/usr/bin/env python3
"""Re-query every pinned upstream OCI index; ignore unknown/unknown attestations."""
import json
from pathlib import Path
import subprocess
lock = json.loads((Path(__file__).resolve().parents[1] / "images.lock.json").read_text())
for image, expected in lock.items():
    data = json.loads(subprocess.check_output(["docker", "buildx", "imagetools", "inspect", image, "--raw"]))
    actual = {m["platform"]["os"] + "/" + m["platform"]["architecture"]: m["digest"]
              for m in data.get("manifests", []) if m.get("platform", {}).get("architecture") in ("amd64", "arm64")}
    assert set(expected) == {"linux/arm64", "linux/amd64"}, image
    assert actual == expected, (image, actual, expected)
    print("PASS manifest", image, "linux/amd64 + linux/arm64")
