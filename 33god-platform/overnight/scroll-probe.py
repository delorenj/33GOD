"""Scroll-feel probe for the Overnight page.

Plays 60 real mouse-wheel notches (100px, 90ms apart, browser smooth scrolling off) and reads the
film position every animation frame, then stops dead inside four camera travels (numbers, bus, jev, pms-talk) and reports where
the film comes to rest.

  cd site && python3 -m http.server 47391 --bind 127.0.0.1 &
  python3 scroll-probe.py http://127.0.0.1:47391/ after

Good: moving_frames close to active_frames (no slideshow), small max_film_step_per_frame,
and every settle result resting with its caption up (cap 1) or on an act statement (interlude beats).
Baseline before the dolly's spring: 60 moving frames out of 636. Now: 405 of 407.
This probe is free scrolling. The ArrowDown stepping (one press, one section) is step-probe.py.
"""
import json, sys
from playwright.sync_api import sync_playwright
URL = sys.argv[1] if len(sys.argv) > 1 else 'https://33god.delo.sh/'
label = sys.argv[2] if len(sys.argv) > 2 else 'run'
SAMPLER = """
window.__s = []; (function loop(){ const st=document.querySelector('.stage'), c=document.querySelector('.captions'), w=document.querySelector('.world');
 if (st) window.__s.push({t:performance.now(), y:scrollY, p:+st.style.getPropertyValue('--p'), beat: st.dataset.beat, cap: c? +c.style.opacity:1, tf: w? w.style.transform:''});
 requestAnimationFrame(loop); })();
"""
with sync_playwright() as pw:
    b = pw.chromium.launch(args=["--disable-smooth-scrolling"])
    pg = b.new_page(viewport={"width": 1440, "height": 860})
    pg.goto(URL); pg.wait_for_selector('.stage', state='attached'); pg.wait_for_timeout(800)
    beats = pg.evaluate("fetch('manifest.json').then(r=>r.json()).then(m=>m.beats.map(b=>b.id))")
    pg.mouse.move(900, 400); pg.evaluate(SAMPLER)
    for n in range(60):
        pg.mouse.wheel(0, 100); pg.wait_for_timeout(90)
    pg.wait_for_timeout(1200)
    s = pg.evaluate("window.__s")
    film = [beats.index(r["beat"]) + r["p"] for r in s]
    d = [film[k+1]-film[k] for k in range(len(film)-1)]
    active = d[:int(len(d)*0.85)]
    moving = sum(1 for x in active if abs(x) > 1e-6)
    biggest = max(abs(x) for x in d)
    # settle test: stop dead in the middle of each of 4 travels, check where the film comes to rest
    results = []
    for bi in [beats.index(i) for i in ('numbers', 'bus', 'jev', 'pms-talk')]:   # by id, so adding a beat does not change what is probed
        # Use the page's own layout: scroll to 85% through beat bi (inside the travel), no wheel
        y = pg.evaluate("""(bi) => { const vh=innerHeight; return fetch('score.json').then(r=>r.json()).then(s=>{ const m=s.majors[bi], k=(s.scale||1)*vh/100; return (m.start + (m.end-m.start)*0.85)*k; }); }""", bi)
        pg.evaluate(f"window.scrollTo(0, {y})"); pg.wait_for_timeout(60)
        pg.mouse.wheel(0, 40); pg.wait_for_timeout(1500)
        st = pg.evaluate("({beat: document.querySelector('.stage').dataset.beat, p: +document.querySelector('.stage').style.getPropertyValue('--p'), cap: +document.querySelector('.captions').style.opacity, y: scrollY})")
        results.append({"stopped_in": beats[bi] + " p=0.85", "rested": st})
    b.close()
print(json.dumps({"label": label, "active_frames": len(active), "moving_frames": moving, "max_film_step_per_frame": round(biggest, 4), "settle": results}, indent=1))
