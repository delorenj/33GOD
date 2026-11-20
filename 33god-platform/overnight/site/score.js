/* Score: scroll offset markers for scroll-driven pages.

   A score is the page's scroll length cut into markers. Two kinds, each with a start and an end:

   MAJOR  a section (an act, a flagship). Inside it the content does not travel: the stage is pinned
          and every px of scroll between start and end advances that section's exhibit. A major has
          three phases: `in` (arriving, optional), the body (the exhibit's own timeline) and `out`
          (leaving for the next major). `in` and `out` each carry a curve.
   MINOR  an animation timeline inside a major's body. It may hold story beats (`beats`, or `steps`
          for N evenly spaced ones). Its curve shapes each stretch between two stops, so an elevator
          can speed up and slow down between floors. A beat may carry a `value` (where the animation
          is at that beat); by default it is the beat's position.

   The markers also drive the scroll itself (see dolly.js). Every stop is a rest point. A reader who
   stops between two stops of a glide (a major's arrival or departure, an act statement handing over,
   a minor's beats) is carried on to the next stop the way they were going, along a timed curve; and
   Space, Page Up/Down and the arrow keys step from stop to stop. Stretches outside any glide scrub
   freely.

   Units. Majors: vh from the top of the film (`start`, `end`), times `scale`. Inside a major, a
   number is vh and "N%" is a share: of the major's span for `in.len`, `out.len`, `land` and
   `in.seam`; of the body for a minor's `start`/`end`; of the minor for a beat's `at`.
   "@name" in `steps` reads opts.vars.name (counts that live in content, not in the score).

     {
       "scale": 0.8,
       "defaults": { "land": "6%", "out": { "len": "28%", "curve": "smoothstep" } },
       "majors": [
         { "id": "lobby", "start": 0, "end": 250 },
         { "id": "elevator", "start": 250, "end": 450,
           "in": { "len": 40, "curve": "ease-out", "seam": [-12, 6] },   // a title card, then a crossfade
           "land": 8,                                                    // the title card is up
           "minors": [
             { "id": "ride", "start": "10%", "end": "90%", "curve": { "in": 0.6, "out": 0.4 },
               "beats": [ { "id": "f3", "at": "40%", "value": 0.3 }, { "id": "f9", "at": "100%", "value": 0.9 } ] },
             { "id": "doors", "start": "92%", "end": "100%", "glide": false } ] } ]
     }

   Curves: "linear", "smoothstep", "ease", "ease-in", "ease-out", "ease-in-out", "elevator",
   "cubic-bezier(x1,y1,x2,y2)", [x1,y1,x2,y2], or { "in": a, "out": b } (handle lengths 0..1: how hard
   the move speeds up and how gently it lands; { in: 0, out: 0 } is linear).

   No dependencies:
     var score = Score.compile(spec, { vars: {...} });
     score.layout(innerHeight)          // px geometry; returns the film's length in px
     score.at(y)                        // y px into the film -> { i, id, major, p, stay, enter, enterT, body, exit, exitT, stop, phase }
     score.minor(majorId, minorId, q)   // q = the major's body progress -> { p, t, step, steps, beat, beatId, active }
     score.beatQ(majorId, minorId, beatId)   // body progress where a beat lands (thresholds read the score, never copy it)
     score.stopQ(majorId, minorId, k)   // body progress at a minor's k-th stop (0 = start)
     score.range(majorId, minorId)      // { from, to } in body progress
     score.seam(y)                      // the glide around y, or null: { from, to, ms, ease }
     score.next(y, dir)                 // the next stop past y (dir 1 or -1), or null
     score.landing(i), score.qPx(i, q), score.total, score.majors
     Score.curve(spec)                  // a curve as a function [0,1] -> [0,1]
*/
(function () {
  'use strict';

  var KEY_MERGE = 0.06;   // share of a screen under which two stops are one keypress

  function clamp(v, a, b) { return Math.max(a, Math.min(b, v)); }
  function seg(v, a, b) { return b > a ? clamp((v - a) / (b - a), 0, 1) : (v >= b ? 1 : 0); }
  function lerp(a, b, t) { return a + (b - a) * t; }

  /* ---------- curves ---------- */
  function linear(t) { return t; }
  linear.linear = true;
  function smoothstep(t) { return t * t * (3 - 2 * t); }
  // A CSS cubic-bezier: solve x(s) = u for s (Newton, then bisection), return y(s).
  function bezier(x1, y1, x2, y2) {
    if (x1 === y1 && x2 === y2) return linear;
    x1 = clamp(x1, 0, 1); x2 = clamp(x2, 0, 1);
    var cx = 3 * x1, bx = 3 * (x2 - x1) - cx, ax = 1 - cx - bx;
    var cy = 3 * y1, by = 3 * (y2 - y1) - cy, ay = 1 - cy - by;
    function sx(s) { return ((ax * s + bx) * s + cx) * s; }
    function sy(s) { return ((ay * s + by) * s + cy) * s; }
    function dx(s) { return (3 * ax * s + 2 * bx) * s + cx; }
    return function (u) {
      if (u <= 0) return 0; if (u >= 1) return 1;
      var s = u, k, x, d;
      for (k = 0; k < 8; k++) { x = sx(s) - u; if (Math.abs(x) < 1e-6) return sy(s); d = dx(s); if (Math.abs(d) < 1e-6) break; s -= x / d; }
      var lo = 0, hi = 1; s = u;
      for (k = 0; k < 40; k++) { x = sx(s); if (Math.abs(x - u) < 1e-6) break; if (x < u) lo = s; else hi = s; s = (lo + hi) / 2; }
      return sy(s);
    };
  }
  var PRESETS = {
    linear: linear,
    smoothstep: smoothstep,
    ease: bezier(0.25, 0.1, 0.25, 1),
    'ease-in': bezier(0.42, 0, 1, 1),
    'ease-out': bezier(0, 0, 0.58, 1),
    'ease-in-out': bezier(0.42, 0, 0.58, 1),
    elevator: bezier(0.55, 0, 0.25, 1)      // a slow pull away, a long coast, a soft stop
  };
  function curve(spec) {
    if (spec == null || spec === 'linear') return linear;
    if (typeof spec === 'function') return spec;
    if (Array.isArray(spec) && spec.length === 4) return bezier(+spec[0], +spec[1], +spec[2], +spec[3]);
    if (typeof spec === 'object') {
      var a = clamp(+spec['in'] || 0, 0, 1), b = clamp(+spec.out || 0, 0, 1);
      return bezier(a, 0, 1 - b, 1);
    }
    if (typeof spec === 'string') {
      if (PRESETS[spec]) return PRESETS[spec];
      var m = /^cubic-bezier\(([^)]+)\)$/.exec(spec.replace(/\s+/g, ''));
      if (m) { var v = m[1].split(',').map(Number); if (v.length === 4 && v.every(isFinite)) return bezier(v[0], v[1], v[2], v[3]); }
    }
    throw new Error('Score: unknown curve ' + JSON.stringify(spec));
  }

  /* ---------- compile ---------- */
  function compile(spec, opts) {
    opts = opts || {};
    var vars = opts.vars || {};
    var defs = spec.defaults || {};
    var scale = spec.scale != null ? +spec.scale : 1;
    if (!spec.majors || !spec.majors.length) throw new Error('Score: no majors');

    function where(m, mn) { return 'Score: ' + m.id + (mn ? '/' + mn.id : ''); }
    function num(v, what) { if (typeof v !== 'number' || !isFinite(v)) throw new Error(what + ' must be a number, got ' + JSON.stringify(v)); return v; }
    function count(v, what) {
      if (typeof v === 'string' && v.charAt(0) === '@') { var n = vars[v.slice(1)]; if (n == null) throw new Error(what + ': no var ' + v); v = n; }
      v = Math.floor(num(v, what)); if (v < 1) throw new Error(what + ' must be at least 1'); return v;
    }

    var prevEnd = -Infinity;
    var majors = spec.majors.map(function (m, i) {
      if (!m.id) throw new Error('Score: major ' + i + ' has no id');
      num(m.start, where(m) + '.start'); num(m.end, where(m) + '.end');
      if (!(m.end > m.start)) throw new Error(where(m) + ': end must be after start');
      if (m.start < prevEnd) throw new Error(where(m) + ': starts before the previous major ends');
      prevEnd = m.end;
      var inn = m['in'] || null, out = m.out !== undefined ? m.out : (i < spec.majors.length - 1 ? defs.out || null : null);
      var minors = (m.minors || []).map(function (mn) {
        if (!mn.id) throw new Error(where(m) + ': a minor has no id');
        var beats = (mn.beats || []).map(function (b, k) { return { id: b.id || String(k), at: b.at, value: b.value }; });
        var steps = mn.steps != null ? count(mn.steps, where(m, mn) + '.steps') : 0;
        if (steps && beats.length) throw new Error(where(m, mn) + ': use beats or steps, not both');
        var c = curve(mn.curve);
        return {
          id: mn.id, start: mn.start != null ? mn.start : 0, end: mn.end != null ? mn.end : '100%',
          beats: beats, steps: steps, curve: c,
          glide: mn.glide !== false, ms: mn.glideMs, timing: curve(mn.timing || (c.linear ? 'smoothstep' : 'linear'))
        };
      });
      return {
        id: m.id, i: i, spec: m, minors: minors,
        inSpec: inn, outSpec: out,
        inCurve: curve(inn && inn.curve), outCurve: curve(out && out.curve),
        outTiming: curve((out && out.timing) || 'smoothstep'), outMs: out && out.ms,
        land: m.land !== undefined ? m.land : defs.land
      };
    });
    var byId = {}; majors.forEach(function (M) { if (byId[M.id]) throw new Error('Score: duplicate major ' + M.id); byId[M.id] = M; });

    var api = { majors: majors, total: 0, glides: [], stops: [] };

    function L(v, basis, k, what) {
      if (v == null) return 0;
      if (typeof v === 'string' && /%$/.test(v)) { var f = parseFloat(v); if (!isFinite(f)) throw new Error(what + ': bad share ' + v); return f / 100 * basis; }
      return num(v, what) * k;
    }

    api.layout = function (vh) {
      vh = Math.max(1, vh || 0);                 // a hidden or not-yet-laid-out viewport still compiles
      var k = scale * vh / 100;
      var glides = [], stops = [];
      majors.forEach(function (M) {
        var s = M.spec.start * k, e = M.spec.end * k, span = e - s;
        var inLen = L(M.inSpec && M.inSpec.len, span, k, where(M) + '.in.len');
        var outLen = L(M.outSpec && M.outSpec.len, span, k, where(M) + '.out.len');
        var b0 = s + inLen, b1 = e - outLen;
        if (b1 < b0) throw new Error(where(M) + ': in + out are longer than the major');
        M.start = s; M.end = e; M.span = span; M.inLen = inLen; M.outLen = outLen; M.bodyStart = b0; M.bodyEnd = b1; M.body = b1 - b0;
        M.minors.forEach(function (mn) {
          var a = b0 + L(mn.start, M.body, k, where(M, mn) + '.start'), z = b0 + L(mn.end, M.body, k, where(M, mn) + '.end');
          if (!(z > a)) throw new Error(where(M, mn) + ': end must be after start');
          if (a < b0 - 0.5 || z > b1 + 0.5) throw new Error(where(M, mn) + ': runs outside its major\'s body (start and end are shares or vh of the body)');
          var fr = [0], val = [0];
          if (mn.steps) { for (var n = 1; n <= mn.steps; n++) { fr.push(n / mn.steps); val.push(n / mn.steps); } }
          else {
            mn.beats.forEach(function (b) {
              var f = L(b.at, z - a, k, where(M, mn) + '.beats.' + b.id) / (z - a);
              if (f > 1 && f < 1 + 1e-9) f = 1;
              if (!(f > fr[fr.length - 1]) || f > 1) throw new Error(where(M, mn) + ': beat ' + b.id + ' must come after the one before it, inside the minor');
              fr.push(f); val.push(b.value != null ? num(b.value, where(M, mn) + '.beats.' + b.id + '.value') : f);
            });
            if (fr[fr.length - 1] < 1) { fr.push(1); val.push(1); }
          }
          mn.a = a; mn.z = z; mn.fr = fr; mn.val = val; mn.tol = 1 / (z - a);   // one px, as a share of the minor
        });
        // Where an arriving reader lands: a share or vh from the start, or the end of a named minor.
        var land = M.land;
        var named = typeof land === 'string' && !/%$/.test(land) ? M.minors.filter(function (mn) { return mn.id === land; })[0] : null;
        if (typeof land === 'string' && !/%$/.test(land) && !named) throw new Error(where(M) + ': land names no minor ' + land);
        M.landing = clamp(named ? named.z : land == null ? b0 : s + L(land, span, k, where(M) + '.land'), s, b1);
        M.seamIn = null;
        if (M.inSpec && M.inSpec.seam) {
          var sa = b0 + L(M.inSpec.seam[0], span, k, where(M) + '.in.seam'), sz = b0 + L(M.inSpec.seam[1], span, k, where(M) + '.in.seam');
          if (sz > sa) M.seamIn = { from: sa, to: sz };
        }
      });
      majors.forEach(function (M, i) {
        var N = majors[i + 1];
        // The film's first section is where the reader already is: its stop is the top, not its landing.
        stops.push(i === 0 ? M.start : M.landing);
        if (N && M.outLen > 0) glides.push({ from: M.bodyEnd, to: N.landing, ms: M.outMs, ease: M.outTiming, kind: 'out', major: M.id });
        if (M.seamIn) glides.push({ from: M.seamIn.from, to: M.seamIn.to, ease: PRESETS.smoothstep, kind: 'in', major: M.id });
        var arrival = Math.max(M.landing, M.seamIn ? M.seamIn.to : -Infinity);
        M.minors.forEach(function (mn) {
          if (!mn.glide) return;
          for (var n = 0; n < mn.fr.length - 1; n++) {
            var a = Math.max(lerp(mn.a, mn.z, mn.fr[n]), arrival), z = Math.min(lerp(mn.a, mn.z, mn.fr[n + 1]), M.bodyEnd);
            // A minor's own start is no stop of its own: nothing has happened there yet.
            if (z - a > 2) glides.push({ from: a, to: z, ms: mn.ms, ease: mn.timing, kind: 'minor', major: M.id, minor: mn.id, head: n === 0 && a > arrival });
          }
        });
      });
      // An act statement's handover starts on the same held card the reader landed on: not a stop of its own.
      glides.forEach(function (g) { if (g.kind !== 'in' && !g.head) stops.push(g.from); stops.push(g.to); });
      // A stop strictly inside another glide would settle, then glide straight on: say so once.
      if (!api.warned) glides.forEach(function (g) {
        stops.forEach(function (y) { if (y > g.from + 2 && y < g.to - 2 && !api.warned) { api.warned = true; console.warn('Score: a stop at ' + Math.round(y) + 'px sits inside the ' + g.kind + ' glide of ' + g.major + (g.minor ? '/' + g.minor : '') + '; give one of the overlapping minors glide: false'); } });
      });
      stops.sort(function (a, b) { return a - b; });
      api.stops = stops.filter(function (v, n) { return n === 0 || v - stops[n - 1] > 2; });
      // The keyboard skips a stop that sits within a sliver of screen of the one before: nothing to see.
      var near = vh * KEY_MERGE;
      api.keyStops = [];
      api.stops.forEach(function (v) { var k = api.keyStops; if (!k.length || v - k[k.length - 1] > near) k.push(v); });
      api.glides = glides;
      api.total = majors[majors.length - 1].end;
      return api.total;
    };

    function majorAt(y) { var i = 0; while (i < majors.length - 1 && y >= majors[i + 1].start) i++; return majors[i]; }
    function idx(m) { return typeof m === 'number' ? majors[m] : byId[m]; }

    function stopsPassed(y) { var s = api.stops, lo = 0, hi = s.length; while (lo < hi) { var mid = (lo + hi) >> 1; if (s[mid] <= y + 1) lo = mid + 1; else hi = mid; } return lo; }
    api.index = function (id) { return byId[id] ? byId[id].i : -1; };
    api.at = function (y) {
      var M = majorAt(y);
      var enter = M.inLen > 0 ? seg(y, M.start, M.bodyStart) : 1;
      // Rests sit up to a px past their stop (rounding, device pixels): a px of slack keeps the body whole there.
      var exit = M.outLen > 0 ? seg(y, M.bodyEnd + 1, M.end) : 0;
      return {
        i: M.i, id: M.id, major: M,
        p: seg(y, M.start, M.end),                 // through the whole major
        stay: seg(y, M.start, M.bodyEnd),          // through everything before it starts to leave
        enter: enter, enterT: M.inCurve(enter),
        body: seg(y, M.bodyStart, M.bodyEnd),      // the exhibit's timeline (linear)
        exit: exit, exitT: M.outCurve(exit),
        stop: stopsPassed(y),                      // how many stops lie at or behind y: changes exactly on a story beat
        phase: y < M.bodyStart ? 'in' : y < M.bodyEnd ? 'body' : 'out'
      };
    };
    function minorOf(majorId, minorId) {
      var M = idx(majorId); if (!M) throw new Error('Score: no major ' + majorId);
      var mn = M.minors.filter(function (x) { return x.id === minorId; })[0];
      if (!mn) throw new Error('Score: no minor ' + majorId + '/' + minorId);
      return { M: M, mn: mn };
    }
    // A minor read off its major's body progress q, so staging code stays a pure function of (beat, q).
    api.minor = function (majorId, minorId, q) {
      var o = minorOf(majorId, minorId), M = o.M, mn = o.mn;
      var y = M.bodyStart + clamp(q, 0, 1) * M.body;
      var p = seg(y, mn.a, mn.z), fr = mn.fr, n = 0;
      while (n < fr.length - 2 && p >= fr[n + 1]) n++;
      var t = lerp(mn.val[n], mn.val[n + 1], mn.curve(seg(p, fr[n], fr[n + 1])));
      var step = 0; for (var k = 1; k < fr.length; k++) if (p >= fr[k] - mn.tol) step = k;
      var beats = mn.beats.length, beat = beats ? Math.min(step, beats) - 1 : -1;
      return { p: p, t: t, step: step, steps: fr.length - 1, beat: beat, beatId: beat >= 0 ? mn.beats[beat].id : null, active: p > 0 && p < 1 };
    };
    // Body progress at a minor's k-th stop (0 is its start, steps is its end).
    api.stopQ = function (majorId, minorId, k) {
      var o = minorOf(majorId, minorId), M = o.M, mn = o.mn;
      if (!(k >= 0 && k < mn.fr.length)) throw new Error('Score: ' + majorId + '/' + minorId + ' has no stop ' + k);
      return M.body ? (lerp(mn.a, mn.z, mn.fr[k]) - M.bodyStart) / M.body : 0;
    };
    api.beatQ = function (majorId, minorId, beatId) {
      var mn = minorOf(majorId, minorId).mn;
      var k = -1; mn.beats.forEach(function (b, n) { if (b.id === beatId) k = n + 1; });
      if (k < 0) throw new Error('Score: no beat ' + majorId + '/' + minorId + '/' + beatId);
      return api.stopQ(majorId, minorId, k);
    };
    api.range = function (majorId, minorId) {
      var o = minorOf(majorId, minorId), M = o.M, mn = o.mn;
      return M.body ? { from: (mn.a - M.bodyStart) / M.body, to: (mn.z - M.bodyStart) / M.body } : { from: 0, to: 0 };
    };
    // The innermost glide strictly around y: stop there and the dolly finishes it.
    api.seam = function (y) {
      var best = null;
      for (var n = 0; n < api.glides.length; n++) {
        var g = api.glides[n];
        if (y > g.from + 1 && y < g.to - 1 && (!best || g.to - g.from < best.to - best.from)) best = g;
      }
      // Rest on or just past a stop, never short of it, so whatever happens at the stop has happened.
      return best ? { from: Math.ceil(best.from), to: Math.ceil(best.to), ms: best.ms, ease: best.ease } : null;
    };
    api.next = function (y, dir) {
      var s = api.keyStops, n;
      if (dir > 0) { for (n = 0; n < s.length; n++) if (s[n] > y + 2) return Math.ceil(s[n]); }
      else { for (n = s.length - 1; n >= 0; n--) if (s[n] < y - 2) return Math.ceil(s[n]); }
      return null;
    };
    api.landing = function (m) { return idx(m).landing; };
    api.qPx = function (m, q) { var M = idx(m); return M.bodyStart + clamp(q, 0, 1) * M.body; };
    return api;
  }

  window.Score = { compile: compile, curve: curve, presets: PRESETS };
})();
