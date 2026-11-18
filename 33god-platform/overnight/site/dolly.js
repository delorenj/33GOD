/* Dolly: a scroll playhead for scroll-driven pages.

   The page's scroll position is where the reader wants to be. The playhead is where the
   film is. A critically damped spring pulls the playhead toward the scroll position every
   frame, so a mouse wheel's 100px notches, a keyboard's page jumps and a trackpad's flicks
   all come out as one continuous move that eases in and eases out. Nothing moves that the
   reader did not ask for: the playhead only ever chases the scroll position.

   Seams are the in-between stretches of a film (a camera travel, a crossfade). When the
   reader stops inside one, the dolly finishes the move for them: it glides the scroll
   position to the nearer rest point, leaning the way they were going. A page that never
   comes to rest half-dissolved.

   No dependencies. One instance per page:

     var dolly = Dolly.create({
       onFrame: function (y, info) { ... },  // y: playhead in px of scroll; info: { moving, velocity }
       seam: function (y) { ... },            // optional: null, or { from, to } px around y
       origin: function () { return 0; },     // optional: px from the document top to the film's start
     });
     dolly.jump(px)    // cut straight to a scroll position (nav links): no glide through the middle
     dolly.refresh()   // re-render at the current playhead (after a resize or a re-measure)
     dolly.destroy()
*/
(function () {
  'use strict';

  var OMEGA = 11;          // spring stiffness, rad/s: lag ~2/OMEGA s, settle ~4/OMEGA s
  var CUT_VH = 2.5;        // a single jump further than this many screens is a cut, not a move
  var IDLE_MS = 160;       // no scroll input for this long and the reader has stopped
  var LEAN = 0.3;          // in a seam, going this far in the reader's direction commits to it
  var REST_PX = 0.25, REST_V = 2;   // the playhead is at rest under these (px, px/s)

  function create(opts) {
    var onFrame = opts.onFrame, seamOf = opts.seam || null, origin = opts.origin || function () { return 0; };
    var omega = opts.omega || OMEGA;
    var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    var y = window.scrollY, v = 0;            // playhead and its velocity
    var raf = 0, then = 0, idle = 0, dir = 1, lastTarget = y, settling = false, alive = true;

    function target() { return window.scrollY; }

    function step(now) {
      raf = 0;
      if (!alive) return;
      var dt = then ? Math.min(0.05, (now - then) / 1000) : 1 / 60;
      then = now;
      var t = target();
      if (reduce) { y = t; v = 0; }
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

    function settle() {
      idle = 0;
      if (!seamOf || reduce) return;
      var t = target() - origin(), s = seamOf(t);
      if (!s) return;
      var span = s.to - s.from; if (span <= 0) return;
      var at = (t - s.from) / span;           // 0 at the seam's start, 1 at its end
      var forward = dir > 0 ? at >= LEAN : at > 1 - LEAN;
      var goal = (forward ? s.to : s.from) + origin();
      if (Math.abs(goal - window.scrollY) < 1) return;
      settling = true;
      window.scrollTo({ top: goal, behavior: 'auto' });   // the spring turns this into a glide
    }

    function onScroll() {
      var t = target();
      if (t !== lastTarget) {
        if (Math.abs(t - lastTarget) > CUT_VH * window.innerHeight) { y = t; v = 0; }
        if (!settling) dir = t > lastTarget ? 1 : -1;
        lastTarget = t;
      }
      settling = false;
      schedule();
      clearTimeout(idle);
      idle = setTimeout(settle, IDLE_MS);
    }

    function jump(px) {
      window.scrollTo({ top: px, behavior: 'auto' });
      y = lastTarget = window.scrollY; v = 0;
      clearTimeout(idle);
      onFrame(y, { moving: false, velocity: 0 });
    }
    function refresh() { onFrame(y, { moving: raf !== 0, velocity: v }); schedule(); }
    function destroy() { alive = false; cancelAnimationFrame(raf); clearTimeout(idle); window.removeEventListener('scroll', onScroll); }

    window.addEventListener('scroll', onScroll, { passive: true });
    onFrame(y, { moving: false, velocity: 0 });
    return { jump: jump, refresh: refresh, destroy: destroy, get y() { return y; } };
  }

  window.Dolly = { create: create };
})();
