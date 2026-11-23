"""perf-probe: frame-rate measurement for the overnight site (front page + tour).

Usage:
  cd site && python3 -m http.server 47391 --bind 127.0.0.1 &
  python3 perf-probe.py [base_url] [--throttle 4] [--pace 0.5] [--json out.json] [--only tour|front] [--width 1280 --height 720]

Measures, per page, with Chrome's own counters:
  frames   rAF interval stats while the page animates: p50/p95/p99 ms, % frames over 16.7/33 ms, effective fps
  longtasks count and total ms of main-thread tasks >50 ms (PerformanceObserver 'longtask')
  metrics  deltas of Performance.getMetrics: ScriptDuration, LayoutDuration, RecalcStyleDuration, LayoutCount, RecalcStyleCount, TaskDuration
  profile  top 15 JS functions by self time (CDP Profiler), so you can see where the main thread goes

Tour: plays every section with ArrowDown and waits for each rest (stage[data-motion=rest]).
Front / flow (tour.html?view=flow, the phone view): scroll the whole page with wheel steps, then back up.
--throttle N applies CDP CPU throttling (4 ~ a mid phone). Headless has no GPU: compare runs, not absolutes.
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from collections import defaultdict

from playwright.sync_api import sync_playwright

SAMPLER = """() => {
  window.__f = []; window.__lt = []; let last = performance.now();
  (function tick(t) { window.__f.push(t - last); last = t; requestAnimationFrame(tick); })(performance.now());
  try { new PerformanceObserver(l => l.getEntries().forEach(e => window.__lt.push(e.duration))).observe({ type: 'longtask', buffered: false }); } catch (e) {}
}"""

KEYS = ["ScriptDuration", "LayoutDuration", "RecalcStyleDuration", "TaskDuration", "LayoutCount", "RecalcStyleCount", "JSHeapUsedSize", "Nodes"]


def metrics(cdp):
    m = {x["name"]: x["value"] for x in cdp.send("Performance.getMetrics")["metrics"]}
    return {k: m.get(k, 0) for k in KEYS}


def frame_stats(fr):
    fr = [x for x in fr[2:] if 0 < x < 1000]
    if not fr:
        return {}
    s = sorted(fr)
    q = lambda p: round(s[min(len(s) - 1, int(p * len(s)))], 1)
    return {"frames": len(fr), "p50": q(.5), "p95": q(.95), "p99": q(.99), "max": round(s[-1], 1),
            "over16_pct": round(100 * sum(x > 17.5 for x in fr) / len(fr), 1),
            "over33_pct": round(100 * sum(x > 34 for x in fr) / len(fr), 1),
            "fps": round(1000 / statistics.mean(fr), 1)}


def top_functions(profile, n=15):
    nodes = {nd["id"]: nd for nd in profile["nodes"]}
    self_t = defaultdict(float)
    samples, deltas = profile.get("samples", []), profile.get("timeDeltas", [])
    for sid, dt in zip(samples, deltas):
        cf = nodes[sid]["callFrame"]
        url = cf["url"].rsplit("/", 1)[-1]
        key = f'{cf["functionName"] or "(anon)"} {url}:{cf["lineNumber"] + 1}' if url else (cf["functionName"] or "(program)")
        self_t[key] += dt / 1000.0
    tot = sum(self_t.values()) or 1
    return [{"fn": k, "ms": round(v, 1), "pct": round(100 * v / tot, 1)} for k, v in sorted(self_t.items(), key=lambda kv: -kv[1])[:n]]


def measure(pg, cdp, drive):
    pg.evaluate(SAMPLER)
    m0 = metrics(cdp)
    cdp.send("Profiler.enable"); cdp.send("Profiler.setSamplingInterval", {"interval": 200}); cdp.send("Profiler.start")
    drive()
    prof = cdp.send("Profiler.stop")["profile"]
    m1 = metrics(cdp)
    fr = pg.evaluate("window.__f"); lt = pg.evaluate("window.__lt")
    d = {k: round(m1[k] - m0[k], 3) if "Duration" in k else m1[k] - m0[k] for k in KEYS}
    return {"frames": frame_stats(fr), "longtasks": {"n": len(lt), "ms": round(sum(lt))}, "metrics": d, "profile": top_functions(prof)}


def run(base, throttle, pace, width, height, only):
    base = re.sub(r"(tour|index)\.html.*$", "", base)
    if not base.endswith("/"):
        base += "/"
    out = {"base": base, "throttle": throttle, "pace": pace, "viewport": [width, height]}
    with sync_playwright() as pw:
        b = pw.chromium.launch(args=["--disable-smooth-scrolling"])
        for page in (["tour", "front", "flow"] if not only else [only]):
            ctx = b.new_context(viewport={"width": width, "height": height}, device_scale_factor=1)
            pg = ctx.new_page(); errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            cdp = ctx.new_cdp_session(pg); cdp.send("Performance.enable")
            if page == "tour":
                pg.goto(base + f"tour.html?view=film&pace={pace}"); pg.wait_for_selector(".stage", state="attached"); pg.wait_for_timeout(1200)
                if throttle > 1: cdp.send("Emulation.setCPUThrottlingRate", {"rate": throttle})
                n = pg.evaluate("document.querySelectorAll('[data-major], .stage [data-beat]').length")

                def drive():
                    for _ in range(40):
                        st = pg.evaluate("() => { const s = document.querySelector('.stage'); return [s.dataset.station, document.querySelector('.next')?.dataset.ready]; }")
                        pg.keyboard.press("ArrowDown")
                        try:
                            pg.wait_for_function("document.querySelector('.stage').dataset.motion === 'moving'", timeout=1500)
                        except Exception:
                            break
                        pg.wait_for_function("document.querySelector('.stage').dataset.motion === 'rest'", timeout=120000)
                        pg.wait_for_timeout(50)
                res = measure(pg, cdp, drive)
            else:
                pg.goto(base if page == "front" else base + "tour.html?view=flow"); pg.wait_for_load_state("load"); pg.wait_for_timeout(1200)
                if throttle > 1: cdp.send("Emulation.setCPUThrottlingRate", {"rate": throttle})

                def drive():
                    pg.mouse.move(width / 2, height / 2)
                    h = pg.evaluate("document.documentElement.scrollHeight")
                    steps = int(h / 120) + 5
                    for _ in range(steps):
                        pg.mouse.wheel(0, 120); pg.wait_for_timeout(40)
                    pg.wait_for_timeout(800)
                    for _ in range(steps // 2):
                        pg.mouse.wheel(0, -240); pg.wait_for_timeout(40)
                    pg.wait_for_timeout(500)
                res = measure(pg, cdp, drive)
            res["errors"] = errs
            out[page] = res
            ctx.close()
        b.close()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("base", nargs="?", default="http://127.0.0.1:47391/")
    ap.add_argument("--throttle", type=float, default=1)
    ap.add_argument("--pace", type=float, default=0.5)
    ap.add_argument("--width", type=int, default=1280); ap.add_argument("--height", type=int, default=720)
    ap.add_argument("--only", choices=["tour", "front", "flow"])
    ap.add_argument("--json")
    a = ap.parse_args()
    r = run(a.base, a.throttle, a.pace, a.width, a.height, a.only)
    if a.json:
        open(a.json, "w").write(json.dumps(r, indent=2))
    for page in ("tour", "front", "flow"):
        if page in r:
            x = r[page]
            print(f"{page:5s} {json.dumps(x['frames'])}\n      longtasks {x['longtasks']}  metrics {json.dumps(x['metrics'])}")
            for f in x["profile"][:8]:
                print(f"        {f['ms']:8.1f}ms {f['pct']:5.1f}%  {f['fn']}")
            if x["errors"]: print("      errors:", x["errors"][:3])


if __name__ == "__main__":
    sys.exit(main())
