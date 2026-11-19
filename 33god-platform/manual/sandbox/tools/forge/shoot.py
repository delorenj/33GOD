#!/usr/bin/env python3
"""Photograph a Factory asset: the forge's eyes (and the verifier's).

    shoot.py <id> --out DIR [--dist DIR | --base-url URL] [--fixture] [--no-situ]

Serves a temp build with `vite preview` (base /sandbox/) on a free port, or uses --base-url, and drives it
with Playwright. For the asset alone (`?at=<id>&forge&spin=0&angle=N`, ambient sim paused) it writes:

    turn-000..270.png            four angles, idle pose
    idle-1..3 accept-1..3 work-1..3 emit-1..3.png   three frames across each clip, via window.__factoryForge.pose()
    visit-0..5.png               a real parcel visit (window.__factoryForge.visit) across Accept, Work and Emit, live, at half size
    situ.png                     the in-situ wide shot (?at=<id>, no forge)
    contact-sheet.png            all of the above on one labelled sheet (read this first)
    console.json                 console errors and warnings, page errors, failed requests, the asset's info()

Exit 0 only when every shot was taken and the console had no errors. --fixture shoots the runtime's test
asset (`?at=fixture&forge&fixture`), which proves the pipeline before any real asset exists.
"""
from __future__ import annotations

import argparse
import contextlib
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
SANDBOX = HERE.parents[1]
ANGLES = (0, 90, 180, 270)
FRACS = (0.1, 0.5, 0.9)
DEFAULT_LEN = {"idle": 4.0, "accept": 1.0, "work": 2.0, "emit": 0.8}
FIXTURE_ID = "fixture"
THUMB = (360, 270)


def node_env() -> dict:
    env = {k: v for k, v in os.environ.items() if not k.startswith("__MISE_") and k != "MISE_SHELL"}
    home = env.get("HOME") or str(Path.home())
    mise = shutil.which("mise") or f"{home}/.local/bin/mise"
    r = subprocess.run([mise, "which", "node"], cwd=SANDBOX, capture_output=True, text=True)
    extra = [str(Path(r.stdout.strip()).parent)] if r.returncode == 0 and r.stdout.strip() else []
    env["PATH"] = ":".join(dict.fromkeys(extra + [f"{home}/.local/bin"] + env.get("PATH", "/usr/local/bin:/usr/bin:/bin").split(":")))
    return env


def free_port() -> int:
    with contextlib.closing(socket.socket()) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def find_glb(dist: Path | None, cid: str, fixture: bool) -> Path | None:
    cands = ([SANDBOX / "forge" / "fixture" / "model.glb"] if fixture else []) + \
            ([dist / "assets" / cid / "model.glb"] if dist else []) + [SANDBOX / "public" / "assets" / cid / "model.glb"]
    return next((c for c in cands if c.exists()), None)


def clip_lengths(glb: Path | None, asset: dict | None) -> dict:
    out = dict(DEFAULT_LEN)
    if not glb:
        return out
    try:
        sys.path.insert(0, str(HERE))
        import glbcheck
        cl = glbcheck.clips(glbcheck.Glb(glb))
        names = (asset or {}).get("clips") or {"idle": "Idle", "accept": "Accept", "work": "Work", "emit": "Emit"}
        for k, nm in names.items():
            if nm in cl and cl[nm]["duration"] > 0:
                out[k] = cl[nm]["duration"]
    except Exception as e:  # noqa: BLE001
        print(f"shoot: could not read clip lengths from {glb}: {e}", file=sys.stderr)
    return out


# Hide every overlay (position fixed or absolute, not the canvas or one of its ancestors): the in-situ shot is the floor alone.
HIDE_HUD = """() => {
  const cv = document.querySelector('canvas'); if (!cv) return 0
  const keep = new Set(); for (let n = cv; n; n = n.parentElement) keep.add(n)
  let hidden = 0
  document.querySelectorAll('body *').forEach((el) => {
    if (keep.has(el) || el.tagName === 'CANVAS' || el.closest('canvas')) return
    const p = getComputedStyle(el).position
    if (p === 'fixed' || p === 'absolute') { el.style.display = 'none'; hidden++ }
  })
  return hidden
}"""


class Server:
    """vite preview of a built dist, base /sandbox/."""
    def __init__(self, dist: Path, env: dict):
        self.port = free_port()
        self.dist, self.env = dist, env
        self.url = f"http://127.0.0.1:{self.port}/sandbox/"
        self.start()

    def ensure(self):
        """Another job on this box may kill a stray vite: bring the preview back on the same port."""
        if self.proc.poll() is not None:
            self.start()

    def start(self):
        self.proc = subprocess.Popen(
            ["npx", "--no-install", "vite", "preview", "--outDir", str(self.dist), "--host", "127.0.0.1", "--port", str(self.port), "--strictPort"],
            cwd=SANDBOX, env=self.env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for _ in range(100):
            if self.proc.poll() is not None:
                raise RuntimeError("vite preview exited: " + (self.proc.stdout.read() or "")[-600:])
            try:
                urllib.request.urlopen(self.url, timeout=1).read(64)
                return
            except Exception:  # noqa: BLE001
                time.sleep(0.2)
        raise RuntimeError("vite preview never answered on " + self.url)

    def stop(self):
        self.proc.terminate()
        try:
            self.proc.wait(5)
        except subprocess.TimeoutExpired:
            self.proc.kill()


def contact_sheet(out: Path, files: list[Path]) -> Path:
    from PIL import Image, ImageDraw
    cols = 4
    rows = (len(files) + cols - 1) // cols
    pad, lab = 8, 22
    W, H = cols * (THUMB[0] + pad) + pad, rows * (THUMB[1] + lab + pad) + pad
    sheet = Image.new("RGB", (W, H), (36, 32, 28))
    d = ImageDraw.Draw(sheet)
    for i, f in enumerate(files):
        im = Image.open(f).convert("RGB")
        im.thumbnail(THUMB)
        x, y = pad + (i % cols) * (THUMB[0] + pad), pad + (i // cols) * (THUMB[1] + lab + pad)
        sheet.paste(im, (x, y + lab))
        d.text((x + 2, y + 4), f.stem, fill=(239, 230, 212))
    dest = out / "contact-sheet.png"
    sheet.save(dest)
    return dest


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("id", nargs="?", default=FIXTURE_ID)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--dist", type=Path, help="an already built dist (vite build --outDir ...); built into a temp dir when absent")
    ap.add_argument("--base-url", help="shoot a running site instead, e.g. https://manual.delo.sh/sandbox/")
    ap.add_argument("--fixture", action="store_true", help="shoot the runtime's ?fixture test asset")
    ap.add_argument("--no-situ", action="store_true")
    ap.add_argument("--width", type=int, default=960)
    ap.add_argument("--height", type=int, default=720)
    ap.add_argument("--ready-timeout", type=int, default=90)
    a = ap.parse_args()
    cid = FIXTURE_ID if a.fixture else a.id
    a.out.mkdir(parents=True, exist_ok=True)
    for old in list(a.out.glob("*.png")) + list(a.out.glob("console.json")):
        old.unlink()
    extra = "&fixture" if a.fixture else ""

    env = node_env()
    tmp_dist, server = None, None
    dist = a.dist
    if a.base_url:
        base = a.base_url.rstrip("/") + "/"
    else:
        if dist is None:
            tmp_dist = dist = Path(tempfile.mkdtemp(prefix="factory-check-shoot-"))
            b = subprocess.run(["npx", "--no-install", "vite", "build", "--outDir", str(dist), "--emptyOutDir"], cwd=SANDBOX, env=env, capture_output=True, text=True)
            if b.returncode != 0:
                print("shoot: temp build failed\n" + (b.stdout + b.stderr)[-1500:], file=sys.stderr)
                return 2
        server = Server(dist, env)
        base = server.url

    asset = None
    for cand in ([SANDBOX / "forge" / "fixture" / "asset.json"] if a.fixture else []) + [SANDBOX / "src" / "assets" / cid / "asset.json"]:
        if cand.exists():
            asset = json.loads(cand.read_text())
            break
    lengths = clip_lengths(find_glb(dist, cid, a.fixture), asset)

    from playwright.sync_api import sync_playwright
    errors, warnings, files, visit_t = [], [], [], []
    info = {}
    status = 0

    def note_console(m):
        (errors if m.type == "error" else warnings if m.type == "warning" else []).append({"type": m.type, "text": m.text[:400], "at": str(m.location.get("url", ""))[-80:]})

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True, args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist", "--enable-webgl"])
            ctx = browser.new_context(viewport={"width": a.width, "height": a.height}, device_scale_factor=1)
            page = ctx.new_page()
            page.on("console", note_console)
            page.on("pageerror", lambda e: errors.append({"type": "pageerror", "text": str(e)[:400]}))
            # ERR_ABORTED is the browser cancelling an in-flight fetch when the next shot navigates away: not a fault
            page.on("requestfailed", lambda r: errors.append({"type": "requestfailed", "text": f"{r.url[-120:]} {r.failure}"}) if "favicon" not in r.url and "ERR_ABORTED" not in str(r.failure) else None)
            page.on("response", lambda r: errors.append({"type": "http", "text": f"{r.status} {r.url[-120:]}"}) if r.status >= 400 and "favicon" not in r.url else None)

            def settle(n=2, ms=120):
                page.evaluate("n => new Promise(r => { const f = k => k ? requestAnimationFrame(() => f(k - 1)) : r(); f(n) })", n)
                page.wait_for_timeout(ms)

            def shot(name: str):
                p = a.out / f"{name}.png"
                page.screenshot(path=str(p))
                files.append(p)

            def load_forge(angle: int):
                if server:
                    server.ensure()
                page.goto(f"{base}?at={cid}&forge&spin=0&angle={angle}{extra}", wait_until="load")
                page.wait_for_function("() => !!window.__factoryForge", timeout=a.ready_timeout * 1000)
                page.evaluate("() => window.__factoryForge.ready", )
                settle(3, 300)

            for ang in ANGLES:
                load_forge(ang)
                shot(f"turn-{ang:03d}")
            info = page.evaluate("id => window.__factoryForge.info(id)", cid) or {}

            load_forge(35)
            for clip in ("idle", "accept", "work", "emit"):
                for k, f in enumerate(FRACS, 1):
                    page.evaluate("([id, c, t]) => window.__factoryForge.pose(id, c, t)", [cid, clip, round(lengths[clip] * f, 3)])
                    settle()
                    shot(f"{clip}-{k}")
            page.evaluate("() => window.__factoryForge.release()")
            settle(3, 600)

            # A live visit: the real Accept -> Work -> Emit, in real time. Bloom and vignette (and a big canvas) make
            # software GL crawl at ~5 fps, which would skip the whole cycle between two frames; with ?nofx at a quarter
            # of the pixels it runs at ~60 fps, so the six frames land across the cycle. (The pose frames above are the
            # deterministic, full-quality view of the same clips.)
            if server:
                server.ensure()
            page.set_viewport_size({"width": a.width // 2, "height": a.height // 2})
            page.goto(f"{base}?at={cid}&forge&spin=0&angle=35&nofx{extra}", wait_until="load")
            page.wait_for_function("() => !!window.__factoryForge", timeout=a.ready_timeout * 1000)
            page.evaluate("() => window.__factoryForge.ready")
            settle(3, 600)
            total = lengths["accept"] + lengths["work"] + lengths["emit"] + 0.4
            page.evaluate("id => window.__factoryForge.visit(id, 'parcel')", cid)
            t0 = time.time()
            for k in range(6):
                page.wait_for_timeout(max(0, int((t0 + total * k / 5 - time.time()) * 1000)))
                shot(f"visit-{k}")
                visit_t.append(round(time.time() - t0, 2))
            page.set_viewport_size({"width": a.width, "height": a.height})

            if not a.no_situ and not a.fixture:
                if server:
                    server.ensure()
                page.goto(f"{base}?at={cid}", wait_until="load")
                page.wait_for_selector("canvas", timeout=a.ready_timeout * 1000)
                page.wait_for_timeout(7000)
                page.evaluate(HIDE_HUD)     # the card, checklist, controls and labels: just the floor
                settle(3, 400)
                shot("situ")
            browser.close()
    except Exception as e:  # noqa: BLE001
        errors.append({"type": "shoot-failed", "text": f"{type(e).__name__}: {str(e)[:400]}"})
        status = 1
    finally:
        if server:
            server.stop()
        if tmp_dist:
            shutil.rmtree(tmp_dist, ignore_errors=True)

    clips = info.get("clips") or []
    if not info:
        errors.append({"type": "asset-not-loaded", "text": "window.__factoryForge.info() returned nothing"})
    elif not info.get("tris") or len(clips) < 4:
        errors.append({"type": "asset-not-loaded", "text": f"info(): {json.dumps(info)[:200]} (floor fell back to the primitive?)"})
    sheet = contact_sheet(a.out, files) if files else None
    (a.out / "console.json").write_text(json.dumps({
        "id": cid, "base": base, "errors": errors, "warnings": warnings[:60], "frames": len(files),
        "files": [f.name for f in files], "visit_offsets_s": visit_t, "info": info, "clip_lengths": lengths, "contact_sheet": sheet.name if sheet else None}, indent=1))
    print(f"shoot: {len(files)} frames, {len(errors)} error(s), {len(warnings)} warning(s) -> {a.out}")
    for e in errors[:8]:
        print(f"  [{e['type']}] {e['text']}", file=sys.stderr)
    return 1 if errors or status or not files else 0


if __name__ == "__main__":
    sys.exit(main())
