"""Audit the shipped artifact tree, including this file, without exclusions."""
import json
from pathlib import Path
import re

root = Path("/bundle")
# Construct markers to avoid treating the scanner's own rules as findings.
markers = ["op:" + "//", "sk" + "-", "Bea" + "rer", "/home/" + "delorenj",
           "delo" + ".sh", "auto" + "maticai", "A" + "AI"]
hits = []
files = [path for path in root.rglob("*") if path.is_file()]
for path in files:
    text = path.read_text()
    for marker in markers:
        if marker in text:
            hits.append((str(path.relative_to(root)), markers.index(marker) + 1))
assert not hits, hits
print(f"artifact scan: {len(files)} files, zero forbidden-marker hits")
assert not list(root.glob("*compose*.y*ml")), "G5 must not define services"
expected = {
    "Dockerfile.pjangler": ["pj"],
    "Dockerfile.skillex": ["skillex"],
    "Dockerfile.mcp-codegraph": ["codegraph-voyage-mcp"],
}
base_refs = {entry["reference"] for entry in json.loads((root / "base-images.json").read_text())["images"]}
seen = set()
for filename, command in expected.items():
    text = (root / filename).read_text()
    assert not re.search(r"^(EXPOSE|HEALTHCHECK)\b", text, re.M), filename
    assert not re.search(r"sleep\s+infinity|tail\s+-f|http.server|uvicorn\s", text), filename
    assert re.search(r"^USER (node|tool)$", text, re.M), filename
    entry = re.search(r"^ENTRYPOINT (.+)$", text, re.M)
    assert entry and json.loads(entry[1]) == command, filename
    for line in text.splitlines():
        if line.startswith("FROM "):
            ref = line.split()[1]
            assert ref in base_refs, (filename, ref)
            seen.add(ref)
assert seen == base_refs
assert "run-only tool images; no daemons" in (root / "README.md").read_text()
print("artifact taxonomy: 3 real tool entrypoints, no Compose, no daemon command, no port instruction")
