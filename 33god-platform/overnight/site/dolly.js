/* Dolly: a scroll playhead for scroll-driven pages.

   The page's scroll position is where the reader wants to be. The playhead is where the
   film is. A critically damped spring pulls the playhead toward the scroll position every
   frame, so a mouse wheel's 100px notches, a keyboard's page jumps and a trackpad's flicks
   all come out as one continuous move that eases in and eases out. Nothing moves that the
   reader did not ask for: the playhead only ever chases the scroll position.

   Seams are the in-between stretches of a film (a camera travel, a crossfade). When the
   reader stops inside one, the dolly finishes the move for them: it glides the scroll
   position to the rest point in the direction they were going (net, since they last came to
   rest), and never while a scrollbar thumb or a finger is still down. A page that never comes
   to rest half-dissolved.

   Glides are timed, not sprung: the playhead travels to the rest point over a duration (the seam's
   own `ms`, or one scaled to the distance) along the seam's `ease`, so a story beat plays as one
   shaped move. Any scroll input during a glide hands the playhead straight back to the spring.

   Stops (optional) make the keyboard step through the film: Space, Page Up/Down and the arrow keys
   glide to the next or previous stop instead of scrolling a fixed distance. Home and End still cut.

   No dependencies. One instance per page:

     var dolly = Dolly.create({
       onFrame: function (y, info) { ... },  // y: playhead in px of scroll; info: { moving, velocity }
       seam: function (y) { ... },            // optional: null, or { from, to, ms?, ease? } px around y
       stop: function (y, dir) { ... },       // optional: the next rest point past y (dir 1 or -1), or null
       origin: function () { return 0; },     // optional: px from the document top to the film's start
     });
     dolly.jump(px)    // cut straight to a scroll position (nav links): no glide through the middle
     dolly.refresh()   // re-render at the current playhead (after a re-measure)
     dolly.rescale(f, toPx)  // geometry changed: cut to toPx(f), f being the reader's place in the old geometry
     dolly.destroy()
*/
(function () {
  'use strict';

  var OMEGA = 11;          // spring stiffness, rad/s: lag ~2/OMEGA s, settle ~4/OMEGA s
  var CUT_VH = 2.5;        // a single jump further than this many screens is a cut, not a move
  var IDLE_MS = 160;       // no scroll input for this long and the reader has stopped
  var POINTER_IDLE_MS = 260; // a released scrollbar thumb or finger gets a little longer
  var REST_PX = 0.25, REST_V = 2;   // the playhead is at rest under these (px, px/s)
  var GLIDE_MS = [340, 1100];        // a glide with no ms of its own: 300ms + 500ms per screen, inside these
  var STEP_KEYS = { ' ': 1, PageDown: 1, ArrowDown: 1, PageUp: -1, ArrowUp: -1 };
  function smooth(t) { return t * t * (3 - 2 * t); }

  function create(opts) {
    var onFrame = opts.onFrame, seamOf = opts.seam || null, stopOf = opts.stop || null, origin = opts.origin || function () { return 0; };
    var omega = opts.omega || OMEGA;
    var mq = window.matchMedia ? window.matchMedia('(prefers-reduced-motion: reduce)') : null;
    function reduced() { return !!(mq && mq.matches); }

    var y = window.scrollY, v = 0;            // playhead and its velocity
    var raf = 0, then = 0, idle = 0, alive = true;
    var anchor = y;                           // where the reader last came to rest: intent is measured from here
    var held = 0;                             // mouse/pen pointers down (a scrollbar drag)
    var touching = false;                     // a finger on the glass (touch pointers cancel early, so tracked apart)
    var lastDir = 0;                          // sign of the reader's last real move (deltas over 2px)
    var burst = false;                        // a fly-through (End, Home, a long smooth scroll): hold the frame, cut at the end
    var burstT = NaN, prevT = y;
    var tw = null;                            // a timed glide: { from, to, t0, ms, ease }

    function target() { return window.scrollY; }

    function step(now) {
      raf = 0;
      if (!alive) return;
      var dt = then ? Math.min(0.05, (now - then) / 1000) : 1 / 60;
      then = now;
      var t = target();
      if (tw) {
        if (t === tw.to) {
          if (!tw.t0) tw.t0 = now;
          var u = Math.min(1, (now - tw.t0) / tw.ms);
          var ny = tw.from + (tw.to - tw.from) * tw.ease(u);
          v = (ny - y) / dt; y = ny; prevT = t;
          if (u >= 1) { tw = null; y = t; v = 0; onFrame(y, { moving: false, velocity: 0 }); then = 0; return; }
          onFrame(y, { moving: true, velocity: v }); schedule(); return;
        }
        tw = null;                            // the reader took over: the spring picks up from here
      }
      // Far behind the scroll position: the browser is flying through many scenes (End, Home, a long
      // smooth scroll). Rendering that strobes beats; hold the current frame and cut when it lands.
      var vh = window.innerHeight;
      if (!burst && (Math.abs(t - y) > CUT_VH * vh || Math.abs(t - prevT) > vh)) { burst = true; burstT = NaN; }
      prevT = t;
      if (burst) {
        if (t !== burstT) { burstT = t; schedule(); return; }
        burst = false; y = anchor = t; v = 0; lastDir = 0;   // landed: cut, and the reader starts fresh here
      }
      if (reduced()) { y = t; v = 0; }
      else {
        // Semi-implicit Euler on x'' = ω²(t − x) − 2ωx', sub-stepped so a long frame cannot overshoot.
        var n = Math.ceil(dt / (1 / 120)), h = dt / n;
        for (var k = 0; k < n; k++) { v += (omega * omega * (t - y) - 2 * omega * v) * h; y += v * h; }
      }
      var resting = Math.abs(t - y) < REST_PX && Math.abs(v) < REST_V;
      if (resting) { y = t; v = 0; }
      onFrame(y, { moving: !resting, velocity: v });
      if (!resting) schedule();
      else then = 0;
    }
    function schedule() { if (!raf && alive) raf = requestAnimationFrame(step); }

    // The reader has let go. If they stopped inside a seam, finish the move the way they were going:
    // their last real move decides (so one wheel notch out of a rest point commits to the next scene,
    // and a reader who reverses mid-seam goes back), then the net move since they last came to rest,
    // then the nearer end.
    function settle() {
      idle = 0;
      var t = target();
      if (held || touching || burst || !seamOf || reduced()) { anchor = t; return; }
      var o = origin(), s = seamOf(t - o);
      if (!s || s.to <= s.from) { anchor = t; lastDir = 0; return; }
      var net = t - anchor;
      var forward = lastDir ? lastDir > 0 : Math.abs(net) > 2 ? net > 0 : (t - o - s.from) > (s.to - s.from) / 2;
      var goal = (forward ? s.to : s.from) + o;
      anchor = goal; lastDir = 0;
      if (Math.abs(goal - t) >= 1) glide(goal, s.ms, s.ease);
    }
    // Play the playhead to px along ease over ms: the scroll position cuts there at once, the film follows.
    function glide(px, ms, ease) {
      if (reduced()) { jump(px); return; }
      var dist = Math.abs(px - y), vh = window.innerHeight || 1;
      tw = { from: y, to: 0, t0: 0, ms: ms || Math.max(GLIDE_MS[0], Math.min(GLIDE_MS[1], 300 + 500 * dist / vh)), ease: ease || smooth };
      window.scrollTo({ top: px, behavior: 'instant' });
      tw.to = window.scrollY; prevT = tw.to; v = 0;
      schedule();
    }
    function arm(ms) { clearTimeout(idle); idle = setTimeout(settle, ms); }

    var lastTarget = y;
    function onScroll() {
      var t = target();
      // Big leaps are not cut here: a fly-through arrives as several leaps, and cutting to each one
      // strobes the scenes in between. step() holds the frame and cuts once, where it lands.
      if (Math.abs(t - lastTarget) > 2 && Math.abs(t - lastTarget) <= window.innerHeight) lastDir = t > lastTarget ? 1 : -1;
      lastTarget = t;
      schedule();
      if (!held && !touching) arm(IDLE_MS);
    }
    function isTouch(e) { return e && e.pointerType === 'touch'; }
    function onDown(e) { if (isTouch(e)) return; held++; clearTimeout(idle); }
    function onUp(e) { if (isTouch(e)) return; held = Math.max(0, held - 1); if (!held) arm(POINTER_IDLE_MS); }
    function onCancel(e) { if (isTouch(e)) return; held = 0; arm(POINTER_IDLE_MS); }   // a touch drag cancels its pointer ~60ms in; the finger is still down
    function onTouchStart() { touching = true; clearTimeout(idle); }
    function onTouchEnd(e) { if (!e.touches || e.touches.length === 0) { touching = false; arm(POINTER_IDLE_MS); } }
    // Browsers do not always deliver the pointerup for a scrollbar drag; any sign of a free hand clears the hold.
    function onKey(e) {
      var dir = STEP_KEYS[e.key];
      if (!dir || !stopOf || e.defaultPrevented || e.ctrlKey || e.metaKey || e.altKey || held || touching) return;
      var el = e.target, tag = el && el.tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || tag === 'BUTTON' || (el && el.isContentEditable)) return;
      if (e.key === ' ' && e.shiftKey) dir = -1;
      var o = origin(), from = (tw ? tw.to : target()) - o;   // a second press chains from where the glide is going
      var goal = stopOf(from, dir);
      if (goal == null) return;                               // past the last stop: the browser scrolls as usual
      e.preventDefault();
      clearTimeout(idle); lastDir = 0;
      anchor = goal + o;
      glide(goal + o);
    }
    function onFree(e) { if (held && !isTouch(e) && (e.type !== 'pointermove' || e.buttons === 0)) { held = 0; arm(POINTER_IDLE_MS); } }

    function jump(px) {
      tw = null;
      window.scrollTo({ top: px, behavior: 'instant' });
      y = lastTarget = anchor = prevT = window.scrollY; v = 0; lastDir = 0; burst = false;
      clearTimeout(idle);
      onFrame(y, { moving: false, velocity: 0 });
    }
    // Keep the reader's place when the film's geometry changes (a resize rescales every beat).
    function rescale(fraction, toPx) { jump(toPx(fraction)); }
    function refresh() { onFrame(y, { moving: raf !== 0, velocity: v }); schedule(); }
    function destroy() {
      alive = false; cancelAnimationFrame(raf); clearTimeout(idle);
      window.removeEventListener('scroll', onScroll);
      window.removeEventListener('pointerdown', onDown); window.removeEventListener('pointerup', onUp); window.removeEventListener('pointercancel', onCancel);
      window.removeEventListener('pointermove', onFree); window.removeEventListener('wheel', onFree); window.removeEventListener('keydown', onFree); window.removeEventListener('keydown', onKey);
      window.removeEventListener('touchstart', onTouchStart); window.removeEventListener('touchend', onTouchEnd); window.removeEventListener('touchcancel', onTouchEnd);
    }

    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('pointerdown', onDown, { passive: true }); window.addEventListener('pointerup', onUp, { passive: true }); window.addEventListener('pointercancel', onCancel, { passive: true });
    window.addEventListener('pointermove', onFree, { passive: true }); window.addEventListener('wheel', onFree, { passive: true }); window.addEventListener('keydown', onFree); window.addEventListener('keydown', onKey);
    window.addEventListener('touchstart', onTouchStart, { passive: true }); window.addEventListener('touchend', onTouchEnd, { passive: true }); window.addEventListener('touchcancel', onTouchEnd, { passive: true });

    onFrame(y, { moving: false, velocity: 0 });
    return { jump: jump, glide: glide, refresh: refresh, rescale: rescale, destroy: destroy, get y() { return y; } };
  }

  window.Dolly = { create: create };
})();
