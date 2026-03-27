#!/usr/bin/env python3
"""Compute SHA256 content hash of an audio file. Outputs JSON to stdout."""
import hashlib
import json
import os
import sys


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: compute_hash.py <file_path>"}))
        return 1
    path = sys.argv[1]
    if not os.path.exists(path):
        print(json.dumps({"error": f"File not found: {path}"}))
        return 1
    sha256 = hashlib.sha256()
    size = 0
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
            size += len(chunk)
    print(json.dumps({"sha256": sha256.hexdigest(), "size_bytes": size}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
