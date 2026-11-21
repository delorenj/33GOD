"""waybill publish: public profile, MinIO via the artifacts skill, the Factory deep link."""
from __future__ import annotations

import gzip
import json
import os
import subprocess
import sys
import tempfile
import urllib.parse
from pathlib import Path
from typing import Any

from . import model as M
from .assemble import apply_profile

PUBLISH_SCRIPT = Path(os.environ.get("WAYBILL_PUBLISH_SCRIPT",
                                     str(Path.home() / ".agents/skills/artifacts/scripts/publish.py")))
FACTORY = os.environ.get("WAYBILL_FACTORY_URL", "https://manual.delo.sh/sandbox/")
ROOT = Path(__file__).resolve().parents[1]


def factory_url(json_url: str) -> str:
    return f"{FACTORY}?waybill={urllib.parse.quote(json_url, safe='')}"


def parse_receipt(stdout: str) -> dict:
    """publish.py prints an indented JSON receipt, then the entry URL on the last line."""
    start = stdout.find("{")
    if start < 0:
        raise ValueError("publish.py printed no JSON receipt")
    obj, _ = json.JSONDecoder().raw_decode(stdout[start:])
    if not isinstance(obj, dict):
        raise ValueError("publish.py receipt is not an object")
    return obj


def to_public(wb: dict) -> dict:
    if (wb.get("recorder") or {}).get("profile") == "public":
        return M.scrub_obj(wb)
    return apply_profile(json.loads(json.dumps(wb)), "public")


def publish(path: str, full: bool = False, name: str | None = None, project: str | None = None,
            dry_run: bool = False, runner: Any = None) -> dict:
    """Publish one waybill file. Returns {json_url, factory_url, receipt, profile}.

    runner is the subprocess.run stand-in (tests mock it); the real call is
    python3 publish.py <dir> --name <name> --entry <id>.waybill.json [--project P] [--dry-run].
    """
    raw = Path(path).read_bytes()
    gz = raw[:2] == b"\x1f\x8b"
    wb = json.loads((gzip.decompress(raw) if gz else raw).decode("utf-8"))
    if wb.get("format") != "33god.waybill":
        raise ValueError(f"{path} is not a 33god.waybill document")
    rec = wb.get("recorder") or {}
    if rec.get("mode") == "query" and rec.get("profile") != "public" and not full:
        # a public query waybill is built public (aliased desks and filters, allow-listed envelopes, private types
        # counted never named); cutting a full one afterwards cannot alias anything, so it would leak what the
        # public profile exists to hide
        raise ValueError("this is a full-profile query waybill; rebuild it with --profile public (the default) "
                         "or pass --full to publish it as is")
    wb = M.scrub_obj(wb) if full else to_public(wb)
    wid = wb.get("id") or Path(path).name.split(".")[0]
    name = name or ("waybill-" + wid.lower().replace("_", "-"))
    fname = f"{wid}.waybill.json" + (".gz" if gz else "")
    run = runner or subprocess.run
    with tempfile.TemporaryDirectory(prefix="waybill-publish-") as tmp:
        d = Path(tmp) / name
        d.mkdir(parents=True)
        if gz:    # a query waybill ships compact and gzipped; the Factory sniffs the magic bytes
            body = (json.dumps(wb, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
            (d / fname).write_bytes(gzip.compress(body, compresslevel=9, mtime=0))
        else:
            (d / fname).write_text(json.dumps(wb, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        cmd = [sys.executable, str(PUBLISH_SCRIPT), str(d), "--name", name, "--entry", fname]
        if project:
            cmd += ["--project", project]
        if dry_run:
            cmd.append("--dry-run")
        proc = run(cmd, capture_output=True, text=True, timeout=300, cwd=str(ROOT))
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip().splitlines()
        raise RuntimeError(f"publish.py exited {proc.returncode}: {detail[-1] if detail else 'no output'}")
    receipt = parse_receipt(proc.stdout or "")
    if not dry_run and receipt.get("ok") is not True:
        raise RuntimeError(f"publish.py receipt is not ok: {receipt}")
    url = receipt.get("entry_url") or ""
    if not url.startswith("https://"):
        raise RuntimeError(f"publish.py receipt has no https entry_url: {receipt}")
    if not url.endswith(fname):
        url = url.rsplit("/", 1)[0] + "/" + fname
    return {"json_url": url, "factory_url": factory_url(url), "receipt": receipt,
            "profile": (wb.get("recorder") or {}).get("profile"), "dry_run": dry_run}
