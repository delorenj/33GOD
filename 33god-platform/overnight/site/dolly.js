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

   No dependencies. One instance per page:

     var dolly = Dolly.create({
       onFrame: function (y, info) { ... },  // y: playhead in px of scroll; info: { moving, velocity }
       seam: function (y) { ... },            // optional: null, or { from, to } px around y
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

  function create(opts) {
    var onFrame = opts.onFrame, seamOf = opts.seam || null, origin = opts.origin || function () { return 0; };
    var omega = opts.omega || OMEGA;
    var mq = window.matchMedia ? window.matchMedia('(prefers-reduced-motion: reduce)') : null;
    function reduced() { return !!(mq && mq.matches); }

    var y = window.scrollY, v = 0;            // playhead and its velocity
    var raf = 0, then = 0, idle = 0, alive = true;
    var anchor = y;                           // where the reader last came to rest: intent is measured from here
    var held = 0;                             // pointers and touches currently down (scrollbar drag, finger on glass)

    function target() { return window.scrollY; }

    function step(now) {
      raf = 0;
      if (!alive) return;
      var dt = then ? Math.min(0.05, (now - then) / 1000) : 1 / 60;
      then = now;
      var t = target();
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
    // intent is the net direction since they last came to rest, so one wheel notch out of a rest point
    // commits to the next scene instead of snapping back. With no net direction, take the nearer end.
    function settle() {
      idle = 0;
      var t = target();
      if (held || !seamOf || reduced()) { anchor = t; return; }
      var o = origin(), s = seamOf(t - o);
      if (!s || s.to <= s.from) { anchor = t; return; }
      var net = t - anchor;
      var forward = Math.abs(net) > 2 ? net > 0 : (t - o - s.from) > (s.to - s.from) / 2;
      var goal = (forward ? s.to : s.from) + o;
      anchor = goal;
      if (Math.abs(goal - t) >= 1) window.scrollTo({ top: goal, behavior: 'auto' });   // the spring turns this into a glide
    }
    function arm(ms) { clearTimeout(idle); idle = setTimeout(settle, ms); }

    var lastTarget = y;
    function onScroll() {
      var t = target();
      if (Math.abs(t - lastTarget) > CUT_VH * window.innerHeight) { y = anchor = t; v = 0; }   // a cut: the reader starts fresh here
      lastTarget = t;
      schedule();
      if (!held) arm(IDLE_MS);
    }
    function onDown() { held++; clearTimeout(idle); }
    function onUp() { held = Math.max(0, held - 1); if (!held) arm(POINTER_IDLE_MS); }
    function onCancel() { held = 0; arm(POINTER_IDLE_MS); }
    // Browsers do not always deliver the pointerup for a scrollbar drag; any sign of a free hand clears the hold.
    function onFree(e) { if (held && (e.type !== 'pointermove' || e.buttons === 0)) { held = 0; arm(POINTER_IDLE_MS); } }

    function jump(px) {
      window.scrollTo({ top: px, behavior: 'auto' });
      y = lastTarget = anchor = window.scrollY; v = 0;
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
      window.removeEventListener('pointermove', onFree); window.removeEventListener('wheel', onFree); window.removeEventListener('keydown', onFree);
    }

    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('pointerdown', onDown, { passive: true }); window.addEventListener('pointerup', onUp, { passive: true }); window.addEventListener('pointercancel', onCancel, { passive: true });
    window.addEventListener('pointermove', onFree, { passive: true }); window.addEventListener('wheel', onFree, { passive: true }); window.addEventListener('keydown', onFree);

    onFrame(y, { moving: false, velocity: 0 });
    return { jump: jump, refresh: refresh, rescale: rescale, destroy: destroy, get y() { return y; } };
  }

  window.Dolly = { create: create };
})();
