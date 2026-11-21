/* Dolly: a scroll playhead for scroll-driven pages.

   The page's scroll position is where the reader wants to be. The playhead is where the
   film is. A critically damped spring pulls the playhead toward the scroll position every
   frame, so a mouse wheel's 100px notches, a keyboard's page jumps and a trackpad's flicks
   all come out as one continuous move that eases in and eases out. Nothing moves that the
   reader did not ask for: the playhead only ever chases the scroll position.

   Moves are the other way round. A page that gives the dolly a `move` function (a compiled
   score's `score.move`) makes the keyboard step through the film one section at a time:
   Space, Page Down and the down arrow play ONE continuous timed move to the next station,
   Shift+Space, Page Up and the up arrow one back. A move is a tween: it drives the playhead AND
   the scroll position every frame along the ease the plan carries, so the scrollbar travels with
   the film and a wheel notch mid-move hands control back at the playhead, not at the goal.
   A move never queues:
     - a held key plays one move; every auto-repeat is swallowed, release and press again;
     - the same key again mid-move fast-forwards that move once (4x), and no further;
     - the other direction mid-move turns around to the station behind;
     - any wheel, touch or scrollbar input mid-move drops the tween and the spring takes over.
   Home and End cut. Under reduced motion a move is a cut to the station.

   Seams are the in-between stretches of a film (a camera travel, a crossfade). When the
   reader stops inside one, the dolly finishes the move for them: it glides the scroll
   position to the rest point in the direction they were going (net, since they last came to
   rest), and never while a scrollbar thumb or a finger is still down. A page that never comes
   to rest half-dissolved. Stopping anywhere else (mid-body) leaves the film where it is.

   Glides use the same tween engine: over a duration (the seam's own `ms`, or one scaled to the
   distance) along the seam's `ease`.

   No dependencies. One instance per page:

     var dolly = Dolly.create({
       onFrame: function (y, info) { ... },  // y: playhead in px of scroll; info: { moving, velocity, playing, kind }
                                             //   playing: a timed move is in flight; kind: 'step' | 'settle' | 'spring'
       move: function (y, dir, o) { ... },    // optional: the move for a press at y (px into the film; dir 1 or -1):
                                             //   { from, to, ms, ease } or null (the browser scrolls as usual)
       onMove: function (plan) { ... },       // optional: a move has started
       seam: function (y) { ... },            // optional: null, or { from, to, ms?, ease? } px around y
       origin: function () { return 0; },     // optional: px from the document top to the film's start
     });
     dolly.step(dir)   // what a press of Down (1) or Up (-1) does; true if it moved. The caret button calls this
     dolly.playing     // a timed move is in flight
     dolly.cancel()    // drop a move where the playhead is
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
  var TOOK_OVER_PX = 3;    // the scroll position is this far from where the tween put it: the reader moved it
  var FF = 4, FF_MIN_MS = 300;       // a repeat press: the rest of the move at 4x, at least 300ms
  var STEP_KEYS = { ' ': 1, PageDown: 1, ArrowDown: 1, PageUp: -1, ArrowUp: -1 };
  function smooth(t) { return t * t * (3 - 2 * t); }
  function rush(t) { return 0.5 * (1 - (1 - t) * (1 - t)) + 0.5 * smooth(t); }

  function create(opts) {
    var onFrame = opts.onFrame, moveOf = opts.move || null, onMove = opts.onMove || null, seamOf = opts.seam || null, origin = opts.origin || function () { return 0; };
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
    var tw = null;                            // a timed move: { from, to, t0, ms, ease, last, kind, dir, ff }

    function target() { return window.scrollY; }

    function step(now) {
      raf = 0;
      if (!alive) return;
      var dt = then ? Math.min(0.05, (now - then) / 1000) : 1 / 60;
      then = now;
      var t = target();
      if (tw) {
        if (Math.abs(t - tw.last) > TOOK_OVER_PX) tw = null;   // the reader took over (a scrollbar drag, a key the browser handled): the spring picks up from the playhead
        else {
          if (!tw.t0) tw.t0 = now;
          var u = Math.min(1, (now - tw.t0) / tw.ms);
          var ny = u >= 1 ? tw.to : tw.from + (tw.to - tw.from) * tw.ease(u);
          window.scrollTo({ top: ny, behavior: 'auto' });     // the scroll position follows the film, frame by frame
          var rb = window.scrollY;                            // what the browser made of it (it rounds to device pixels)
          v = (ny - y) / dt; y = ny; tw.last = rb; prevT = lastTarget = rb;
          if (u >= 1) {
            var kind = tw.kind; tw = null; y = anchor = rb; v = 0; lastDir = 0; then = 0;
            onFrame(y, { moving: false, velocity: 0, playing: false, kind: kind });
            return;
          }
          onFrame(y, { moving: true, velocity: v, playing: true, kind: tw.kind }); schedule(); return;
        }
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
      onFrame(y, { moving: !resting, velocity: v, playing: false, kind: 'spring' });
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
      if (held || touching || burst || tw || !seamOf || reduced()) { anchor = t; return; }
      var o = origin(), s = seamOf(t - o);
      if (!s || s.to <= s.from) { anchor = t; lastDir = 0; return; }
      var net = t - anchor;
      var forward = lastDir ? lastDir > 0 : Math.abs(net) > 2 ? net > 0 : (t - o - s.from) > (s.to - s.from) / 2;
      var goal = (forward ? s.to : s.from) + o;
      anchor = goal; lastDir = 0;
      if (Math.abs(goal - t) >= 1) glide(goal, s.ms, s.ease);
    }
    // Play the playhead to px along ease over ms, the scroll position with it.
    function glide(px, ms, ease) {
      if (reduced()) { jump(px); return; }
      var dist = Math.abs(px - y), vh = window.innerHeight || 1;
      play({ from: y, to: px, ms: ms || Math.max(GLIDE_MS[0], Math.min(GLIDE_MS[1], 300 + 500 * dist / vh)), ease: ease || smooth }, 'settle', px > y ? 1 : -1);
    }
    // The one tween engine. plan: { from, to, ms, ease } in px of scroll.
    function play(plan, kind, dir) {
      var t = target();
      clearTimeout(idle);
      tw = { from: plan.from, to: plan.to, t0: 0, ms: Math.max(1, plan.ms), ease: plan.ease || smooth, last: t, kind: kind, dir: dir || (plan.to >= plan.from ? 1 : -1), ff: false };
      prevT = lastTarget = t; burst = false; v = 0;
      schedule();
    }
    function arm(ms) { clearTimeout(idle); idle = setTimeout(settle, ms); }

    var lastTarget = y;
    function onScroll() {
      var t = target();
      // Big leaps are not cut here: a fly-through arrives as several leaps, and cutting to each one
      // strobes the scenes in between. step() holds the frame and cuts once, where it lands.
      // A move writes the scroll position itself every frame; that is not the reader and not a stop.
      if (!tw && Math.abs(t - lastTarget) > 2 && Math.abs(t - lastTarget) <= window.innerHeight) lastDir = t > lastTarget ? 1 : -1;
      lastTarget = t;
      schedule();
      if (!held && !touching && !tw) arm(IDLE_MS);
    }
    function isTouch(e) { return e && e.pointerType === 'touch'; }
    function onDown(e) { if (isTouch(e)) return; held++; clearTimeout(idle); }
    function onUp(e) { if (isTouch(e)) return; held = Math.max(0, held - 1); if (!held) arm(POINTER_IDLE_MS); }
    function onCancel(e) { if (isTouch(e)) return; held = 0; arm(POINTER_IDLE_MS); }   // a touch drag cancels its pointer ~60ms in; the finger is still down
    function onTouchStart() { touching = true; clearTimeout(idle); if (tw) tw = null; schedule(); }
    function onTouchEnd(e) { if (!e.touches || e.touches.length === 0) { touching = false; arm(POINTER_IDLE_MS); } }
    // A wheel notch mid-move: the reader has the page. Drop the tween before the browser scrolls, so the
    // notch lands on the playhead's position and the spring carries on from there.
    function onWheel(e) { if (tw && e.deltaY !== 0 && !e.ctrlKey) { tw = null; schedule(); } }

    // What a press does. true = handled (the caller keeps the browser from also scrolling).
    function pressed(dir, repeat) {
      if (!moveOf) return false;
      var o = origin();
      // A held key plays one move and no more: every auto-repeat is swallowed.
      if (repeat) return !!tw || !!moveOf(y - o, dir);
      if (tw && tw.kind === 'step') {
        if (dir === tw.dir) {
          if (!tw.ff) {                                       // one fast-forward of what is left, never the next section
            var left = Math.max(0, tw.ms - (tw.t0 ? performance.now() - tw.t0 : 0));
            tw = { from: y, to: tw.to, t0: 0, ms: Math.max(FF_MIN_MS, left / FF), ease: rush, last: tw.last, kind: 'step', dir: tw.dir, ff: true };
            schedule();
          }
          return true;
        }
        var back = moveOf(y - o, dir, { turn: true });        // the other way: turn around at the playhead
        if (!back) return true;
        return start(back, dir, o);
      }
      var plan = moveOf(y - o, dir);
      if (!plan) return false;                                // past the last station: the browser scrolls as usual
      return start(plan, dir, o);
    }
    function start(plan, dir, o) {
      lastDir = 0; anchor = plan.to + o;
      var px = { from: y, to: plan.to + o, ms: plan.ms, ease: plan.ease };
      if (reduced()) { jump(px.to); return true; }
      if (onMove) onMove(plan);
      play(px, 'step', dir);
      return true;
    }
    function onKey(e) {
      var dir = STEP_KEYS[e.key];
      if (!dir || !moveOf || e.defaultPrevented || e.ctrlKey || e.metaKey || e.altKey || held || touching) return;
      var el = e.target, tag = el && el.tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || (el && el.isContentEditable)) return;
      if (e.key === ' ' && tag === 'BUTTON') return;          // Space on a focused button is its click (the caret); the arrows still step
      if (e.key === ' ' && e.shiftKey) dir = -1;
      if (pressed(dir, e.repeat)) e.preventDefault();
    }
    // Browsers do not always deliver the pointerup for a scrollbar drag; any sign of a free hand clears the hold.
    function onFree(e) { if (held && !isTouch(e) && (e.type !== 'pointermove' || e.buttons === 0)) { held = 0; arm(POINTER_IDLE_MS); } }

    function jump(px) {
      tw = null;
      window.scrollTo({ top: px, behavior: 'auto' });
      y = lastTarget = anchor = prevT = window.scrollY; v = 0; lastDir = 0; burst = false;
      clearTimeout(idle);
      onFrame(y, { moving: false, velocity: 0, playing: false, kind: 'spring' });
    }
    // Keep the reader's place when the film's geometry changes (a resize rescales every beat).
    function rescale(fraction, toPx) { jump(toPx(fraction)); }
    function refresh() { onFrame(y, { moving: raf !== 0, velocity: v, playing: !!tw, kind: tw ? tw.kind : 'spring' }); schedule(); }
    function cancel() { if (tw) { tw = null; anchor = target(); schedule(); } }
    function destroy() {
      alive = false; tw = null; cancelAnimationFrame(raf); clearTimeout(idle);
      window.removeEventListener('scroll', onScroll);
      window.removeEventListener('pointerdown', onDown); window.removeEventListener('pointerup', onUp); window.removeEventListener('pointercancel', onCancel);
      window.removeEventListener('pointermove', onFree); window.removeEventListener('wheel', onFree); window.removeEventListener('wheel', onWheel); window.removeEventListener('keydown', onFree); window.removeEventListener('keydown', onKey);
      window.removeEventListener('touchstart', onTouchStart); window.removeEventListener('touchend', onTouchEnd); window.removeEventListener('touchcancel', onTouchEnd);
    }

    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('pointerdown', onDown, { passive: true }); window.addEventListener('pointerup', onUp, { passive: true }); window.addEventListener('pointercancel', onCancel, { passive: true });
    window.addEventListener('pointermove', onFree, { passive: true }); window.addEventListener('wheel', onFree, { passive: true }); window.addEventListener('wheel', onWheel, { passive: true }); window.addEventListener('keydown', onFree); window.addEventListener('keydown', onKey);
    window.addEventListener('touchstart', onTouchStart, { passive: true }); window.addEventListener('touchend', onTouchEnd, { passive: true }); window.addEventListener('touchcancel', onTouchEnd, { passive: true });

    onFrame(y, { moving: false, velocity: 0, playing: false, kind: 'spring' });
    return {
      jump: jump, glide: glide, step: function (dir) { return pressed(dir < 0 ? -1 : 1, false); },
      cancel: cancel, refresh: refresh, rescale: rescale, destroy: destroy,
      get y() { return y; }, get playing() { return !!tw; }
    };
  }

  window.Dolly = { create: create };
})();
