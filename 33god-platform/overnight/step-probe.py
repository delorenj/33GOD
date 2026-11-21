"""Step probe for the Overnight page: one press of Down is one section.

Presses ArrowDown from the top until the end of the film and records, for every press, where the film
comes to rest (it must be the major's body end), how long the move took, whether the film position
only ever moves forward, the longest stall inside the move (apart from an act statement's hold),
whether the caret showed while moving, and the elevator's reading. Then the arbitration: a held key,
a double press, ArrowUp, a wheel notch mid-move, the caret, a nav link, Home and End.

  cd site && python3 -m http.server 47391 --bind 127.0.0.1 &
  python3 step-probe.py http://127.0.0.1:47391/            # real pace: about 3 minutes
  python3 step-probe.py http://127.0.0.1:47391/ --pace 0.2  # five times faster, about 40 seconds
  python3 step-probe.py http://127.0.0.1:47391/ --pace 0.2 --json

Exits 1 if any check fails. The rests must equal the number of majors (one per section) and land at each
major's body end; no stall may last longer than 250ms outside an act statement's hold (`in.hold` x pace).
"""
import json, math, sys, argparse, pathlib
from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
SITE = HERE / "site"

SAMPLER = """
window.__s = []; (function loop() {
  const st = document.querySelector('.stage'), c = document.querySelector('.next'), g = document.querySelector('.gauge');
  if (st) window.__s.push({ t: performance.now(), y: scrollY, motion: st.dataset.motion, station: +st.dataset.station, beat: st.dataset.beat,
    ready: c ? c.dataset.ready : null, vis: c ? getComputedStyle(c).opacity : null, gauge: g ? +g.getAttribute('aria-valuenow') : null });
  requestAnimationFrame(loop);
})();
"""


def geometry(vh):
    """Station px and the major each one closes, from score.json (the same arithmetic score.js does)."""
    S = json.loads((SITE / "score.json").read_text())
    k = S.get("scale", 1) * vh / 100
    d_out = (S.get("defaults", {}).get("out") or {})
    st, ids, holds = [0], [], []
    for i, m in enumerate(S["majors"]):
        span = (m["end"] - m["start"]) * k
        out = None if i == len(S["majors"]) - 1 else {**d_out, **(m.get("out") or {})}
        ln = 0
        if out and out.get("len") is not None:
            ln = float(out["len"][:-1]) / 100 * span if isinstance(out["len"], str) else out["len"] * k
        st.append(math.ceil(m["end"] * k - ln))
        ids.append(m["id"])
        i_ = m.get("in")
        holds.append((S.get("defaults", {}).get("in", {}).get("hold", 1800) if not i_ else {**S.get("defaults", {}).get("in", {}), **i_}.get("hold", 1800)) if i_ and i_.get("len") else 0)
    return st, ids, holds


def runs_of_stall(samples, thresh=0.3):
    """Longest run (ms) of frames that did not move, between the first and the last frame that did."""
    mv = [i for i in range(1, len(samples)) if abs(samples[i]["y"] - samples[i - 1]["y"]) >= thresh]
    if len(mv) < 2:
        return 0, 0
    a, b = mv[0], mv[-1]
    best, start = 0, None
    for i in range(a, b + 1):
        still = abs(samples[i]["y"] - samples[i - 1]["y"]) < thresh
        if still and start is None:
            start = i - 1
        if not still and start is not None:
            best = max(best, samples[i - 1]["t"] - samples[start]["t"]); start = None
    return best, mv[-1] - mv[0] + 1


def run(url, pace=1.0, width=1280, height=720, only_steps=False):
    stations, ids, holds = geometry(height)
    report = {"url": url, "pace": pace, "viewport": [width, height], "moves": [], "checks": [], "failed": []}

    def check(name, ok, detail=""):
        report["checks"].append({"name": name, "ok": bool(ok), "detail": detail})
        if not ok:
            report["failed"].append(f"{name}: {detail}")

    with sync_playwright() as pw:
        b = pw.chromium.launch(args=["--disable-smooth-scrolling"])
        pg = b.new_page(viewport={"width": width, "height": height})
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
        q = f"?view=film&night=staged&pace={pace}"
        pg.goto(url + q); pg.wait_for_selector(".stage", state="attached"); pg.wait_for_timeout(900)
        pg.evaluate(SAMPLER)

        def state():
            return pg.evaluate("""() => { const st = document.querySelector('.stage'), c = document.querySelector('.next'), g = document.querySelector('.gauge');
              return { y: scrollY, motion: st.dataset.motion, station: +st.dataset.station, beat: st.dataset.beat, ready: c.dataset.ready, vis: getComputedStyle(c).opacity, gauge: +g.getAttribute('aria-valuenow'), text: g.getAttribute('aria-valuetext') }; }""")

        def wait_move(timeout=60000):
            try:
                pg.wait_for_function("document.querySelector('.stage').dataset.motion === 'moving'", timeout=1500)
            except Exception:
                pass
            pg.wait_for_function("document.querySelector('.stage').dataset.motion === 'rest'", timeout=timeout)
            pg.wait_for_timeout(60)

        def press(key="ArrowDown"):
            i0 = len(pg.evaluate("window.__s"))
            pg.keyboard.press(key); wait_move()
            return pg.evaluate("window.__s")[i0:]

        s0 = state()
        check("starts at the top, caret ready", s0["station"] == 0 and s0["ready"] == "true" and s0["gauge"] == 0, str(s0))
        gauges = [s0["gauge"]]
        for n in range(1, len(stations)):
            smp = press()
            st = state()
            moving = [r for r in smp if r["motion"] == "moving"]
            ys = [r["y"] for r in moving]
            t0 = moving[0]["t"] if moving else 0
            t1 = next((r["t"] for r in smp if r["motion"] == "rest" and r["t"] > t0), smp[-1]["t"])
            back = sum(1 for k in range(1, len(ys)) if ys[k] < ys[k - 1] - 1)
            stall, nfr = runs_of_stall(moving)
            allowed = 250 + (holds[n - 1] * pace if n - 1 < len(holds) else 0)
            caret_moving = sum(1 for r in moving if r["ready"] == "true")
            gap = max((moving[k]["t"] - moving[k - 1]["t"] for k in range(1, len(moving))), default=0)
            mv = {"n": n, "major": ids[n - 1], "rest_y": st["y"], "want_y": stations[n], "beat": st["beat"], "station": st["station"],
                  "ms": round(t1 - t0), "max_frame_gap_ms": round(gap), "frames": nfr, "backward_frames": back, "longest_stall_ms": round(stall), "allowed_stall_ms": round(allowed),
                  "caret_while_moving": caret_moving, "caret_at_rest": st["ready"], "gauge": st["gauge"]}
            report["moves"].append(mv)
            gauges.append(st["gauge"])
            check(f"press {n} rests on {ids[n-1]}'s body end", st["station"] == n and abs(st["y"] - stations[n]) <= 2 and st["beat"] == ids[n - 1], str(mv))
            check(f"press {n} never runs backwards", back == 0, str(mv))
            check(f"press {n} has no stall over {round(allowed)}ms", stall <= allowed, str(mv))
            check(f"press {n}: caret hidden while moving", caret_moving == 0 and all(float(r["vis"]) < 0.5 or r["ready"] == "false" for r in moving), str(mv))
            check(f"press {n}: caret " + ("ready at rest" if n < len(stations) - 1 else "hidden at the end"), (st["ready"] == "true") == (n < len(stations) - 1), str(mv))
        check("the film has one rest per major", len(report["moves"]) == len(ids) and len({m["station"] for m in report["moves"]}) == len(ids), f"{len(report['moves'])} rests, {len(ids)} majors")
        check("gauge is monotonic and ends at 100", gauges == sorted(gauges) and gauges[-1] == 100, str(gauges))
        check("gauge valuetext names the section", state()["text"] == f"Section {len(ids)} of {len(ids)}", str(state()["text"]))
        # past the last station the browser scrolls natively: no move
        y_end = state()["y"]
        pg.keyboard.press("ArrowDown"); pg.wait_for_timeout(500)
        check("Down at the end leaves the browser to scroll", state()["y"] >= y_end, str(state()))

        if not only_steps:
            # --- ArrowUp: one station back
            pg.evaluate("window.scrollTo(0, 0)"); pg.wait_for_timeout(500)
            for _ in range(4):
                press()
            at = state()["station"]
            press("ArrowUp")
            check("ArrowUp goes back exactly one station", state()["station"] == at - 1 and abs(state()["y"] - stations[at - 1]) <= 2, f"{at} -> {state()}")

            # --- a held key: one section, not a queue
            at = state()["station"]
            pg.keyboard.down("ArrowDown")
            for _ in range(14):
                pg.wait_for_timeout(70); pg.keyboard.down("ArrowDown")
            pg.keyboard.up("ArrowDown"); wait_move(); pg.wait_for_timeout(300)
            st = state()
            check("a held ArrowDown advances exactly one section", st["station"] == at + 1 and st["motion"] == "rest", f"{at} -> {st}")

            # --- a double press mid-move: fast-forward, never the next section
            at = state()["station"]
            pg.keyboard.press("ArrowDown"); pg.wait_for_timeout(120); pg.keyboard.press("ArrowDown"); pg.wait_for_timeout(60); pg.keyboard.press("ArrowDown")
            wait_move(); pg.wait_for_timeout(400)
            st = state()
            check("a double press ends on the same station", st["station"] == at + 1 and st["motion"] == "rest", f"{at} -> {st}")

            # --- the other way mid-move turns around
            at = state()["station"]
            pg.keyboard.press("ArrowDown"); pg.wait_for_timeout(140); pg.keyboard.press("ArrowUp")
            wait_move(); pg.wait_for_timeout(300)
            st = state()
            check("Up mid-move turns around to the station behind", st["station"] == at, f"{at} -> {st}")

            # --- a wheel notch mid-move hands control back at the playhead, not the goal
            at = state()["station"]
            pg.mouse.move(640, 360)
            pg.keyboard.press("ArrowDown"); pg.wait_for_timeout(260)
            y_before = state()["y"]
            pg.mouse.wheel(0, 40); pg.wait_for_timeout(1200)
            st = state(); y_a = st["y"]; pg.wait_for_timeout(500); y_b = state()["y"]
            check("a wheel notch mid-move stops the move short of its goal", st["motion"] == "rest" and y_a < stations[at + 1] - 100 and y_a >= y_before, f"before {y_before}, after {y_a}, goal {stations[at + 1]}, {st}")
            check("and the film does not carry on afterwards", abs(y_b - y_a) <= 2, f"{y_a} -> {y_b}")

            # --- the caret is a button
            pg.evaluate("window.scrollTo(0, 0)"); pg.wait_for_timeout(500)
            pg.keyboard.press("Home"); pg.wait_for_timeout(500)
            pg.click(".next"); wait_move()
            check("clicking the caret advances one section", state()["station"] == 1, str(state()))
            pg.keyboard.press("ArrowDown"); wait_move()
            check("the arrow keys still step after a caret click", state()["station"] == 2, str(state()))

            # --- a nav link cuts to the beat, no travelling through the night
            link = pg.locator(".hud__nav a", has_text="The staff")
            if link.count():
                link.first.click(); pg.wait_for_timeout(700)
                st = state()
                check("a nav link cuts to the beat and rests there (not on a station)", st["beat"] == "staff" and st["motion"] == "rest" and st["ready"] == "false", str(st))
                pg.keyboard.press("ArrowDown"); wait_move()
                check("Down from a nav landing plays out that section", state()["beat"] == "staff" and state()["station"] == ids.index("staff") + 1, str(state()))

            # --- the URL keeps your place: the hash names the beat you rest on, and a reload comes back to it
            si = ids.index("staff") + 1
            check("the hash names the beat the film rests on", pg.evaluate("location.hash") == "#staff", pg.evaluate("location.hash"))
            pg.reload(); pg.wait_for_selector(".stage", state="attached"); pg.wait_for_timeout(1200)
            st = state()
            check("a reload comes back to the same station", st["station"] == si and abs(st["y"] - stations[si]) <= 2 and st["ready"] == "true", str(st))
            ctx2 = b.new_context(viewport={"width": width, "height": height})
            p2 = ctx2.new_page(); p2.goto(url + "?view=film&night=staged&pace=0.2#gateway"); p2.wait_for_selector(".stage", state="attached"); p2.wait_for_timeout(1200)
            r2 = p2.evaluate("({b: document.querySelector('.stage').dataset.beat, y: scrollY})")
            check("a deep link (#gateway) lands on that beat", r2["b"] == "gateway" and r2["y"] > 0, str(r2))
            ctx2.close()

            # --- keyboard users keep the caret: focus survives the move, a second Enter plays the next section
            pg.keyboard.press("Home"); pg.wait_for_timeout(700)
            pg.focus(".next"); n0 = state()["station"]
            pg.keyboard.press("Enter"); wait_move()
            check("the caret keeps focus through its own move", pg.evaluate("document.activeElement.className") == "next" and state()["station"] == n0 + 1, pg.evaluate("document.activeElement.tagName") + " " + str(state()))
            pg.keyboard.press("Enter"); wait_move()
            check("and a second Enter plays the next section", state()["station"] == n0 + 2, str(state()))

            # --- Home and End cut
            pg.keyboard.press("Home"); pg.wait_for_timeout(900)
            st = state()
            check("Home cuts to the top", st["y"] <= 2 and st["station"] == 0, str(st))
            pg.keyboard.press("End"); pg.wait_for_timeout(1500)
            st = state()
            check("End cuts to the bottom", st["y"] > stations[-1] - 2 and st["motion"] == "rest", str(st))
            pg.keyboard.press("ArrowUp"); wait_move()
            check("Up from the footer comes back to the last station", state()["station"] == len(ids), str(state()))
        check("no console errors", not errs, str(errs[:3]))
        b.close()
    return report


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("url", nargs="?", default="http://127.0.0.1:47391/")
    ap.add_argument("--pace", type=float, default=1.0, help="multiplies every ms (0.2 = five times faster)")
    ap.add_argument("--size", default="1280x720")
    ap.add_argument("--steps", action="store_true", help="only the 23 presses")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    w, h = (int(v) for v in a.size.split("x"))
    r = run(a.url, a.pace, w, h, a.steps)
    if a.json:
        print(json.dumps(r, indent=1))
    else:
        print(f"{'#':>2} {'major':<15} {'rest y':>7} {'want':>6} {'ms':>6} {'frames':>6} {'stall':>6} {'caret':>5} {'gauge':>5}")
        for m in r["moves"]:
            print(f"{m['n']:>2} {m['major']:<15} {m['rest_y']:>7} {m['want_y']:>6} {m['ms']:>6} {m['frames']:>6} {m['longest_stall_ms']:>6} {m['caret_at_rest']:>5} {m['gauge']:>5}")
        print(f"\n{len(r['moves'])} rests for {len(r['moves'])} majors; total {sum(m['ms'] for m in r['moves']) / 1000:.1f}s at pace {a.pace}")
        print(f"{sum(1 for c in r['checks'] if c['ok'])}/{len(r['checks'])} checks passed")
        for f in r["failed"]:
            print("FAIL", f)
    sys.exit(1 if r["failed"] else 0)
