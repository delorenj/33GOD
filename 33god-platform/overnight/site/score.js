/* Score: scroll offset markers for scroll-driven pages.

   A score is the page's scroll length cut into markers. Two kinds, each with a start and an end:

   MAJOR  a section (an act, a flagship). Inside it the content does not travel: the stage is pinned
          and every px of scroll between start and end advances that section's exhibit. A major has
          three phases: `in` (arriving, optional), the body (the exhibit's own timeline) and `out`
          (leaving for the next major). `in` and `out` each carry a curve.
   MINOR  an animation timeline inside a major's body. It may hold story beats (`beats`, or `steps`
          for N evenly spaced ones). A beat may carry a `value` (where the animation is at that beat);
          by default it is the beat's position. A minor is not a stop: it is the SPEED PROFILE of the
          body. The tween eases into and holds near each beat (`dwell`) without ever resting on it.

   STATIONS. The markers also drive the scroll itself (see dolly.js). A score has exactly one resting
   place per major, at the point where that major's content is done (the end of its body, before its
   `out`), plus the very top. 23 majors give 24 stations and 23 moves. One press of Down plays one
   continuous timed move from the station you are on to the next: the previous major's `out`, the
   next major's `in` (the act statement, with a hold to read it) and the whole body, along the curves
   and paces the score gives it. Up goes back one station, a little faster. Nothing is a stop in
   between. A reader who scrubs with the wheel and stops inside a camera travel or an act handover
   (a half-dissolved state) is carried on the way they were going (a "seam"); a reader who stops
   mid-body stays where they are, like a video scrubber.

   Units. Majors: vh from the top of the film (`start`, `end`), times `scale`. Inside a major, a
   number is vh and "N%" is a share: of the major's span for `in.len`, `out.len`, `land` and
   `in.seam`; of the body for a minor's `start`/`end` and for `body.play`; of the minor for a beat's
   `at`. "@name" in `steps` reads opts.vars.name (counts that live in content, not in the score).
   Times (`ms`, `hold`, `settleMs`, everything under `pace`) are milliseconds.

     {
       "scale": 0.8,
       "pace": { "back": 0.55, "launch": 280, "settle": 420, "smooth": 200, "rush": 5, "reach": 0.03, "min": 450, "dwell": 0.5 },
       "defaults": { "land": "6%",
                     "out":  { "len": "28%", "curve": "smoothstep", "ms": 1400 },
                     "in":   { "ms": 900, "hold": 1800 },
                     "body": { "ms": 5000, "perStep": 650 } },
       "majors": [
         { "id": "lobby", "start": 0, "end": 250 },
         { "id": "elevator", "start": 250, "end": 450,
           "in": { "len": 40, "curve": "ease-out", "seam": [-12, 6], "hold": 2400 },   // a title card, then a crossfade
           "land": 8,                                                    // the title card is up
           "body": { "ms": 9000, "play": ["10%", "90%"] },               // nothing moves before 10% or after 90%
           "minors": [
             { "id": "ride", "start": "10%", "end": "90%", "curve": { "in": 0.6, "out": 0.4 }, "dwell": 0.7,
               "beats": [ { "id": "f3", "at": "40%", "value": 0.3 }, { "id": "f9", "at": "100%", "value": 0.9 } ] },
             { "id": "doors", "start": "92%", "end": "100%", "pace": false } ] } ]
     }

   PACE (every field optional).
     top level  pace.back    ratio of a forward move's time for a move backwards (0.55)
                pace.launch  ms: every move starts at rest and reaches speed over this long (280)
                pace.settle  ms: and comes to rest over this long (420)
                pace.smooth  ms: width of the window that smooths the speed profile (200)
                pace.rush    x speed through stretches where nothing happens, see body.play (5)
                pace.reach   share of the viewport height within which you count as ON a station (0.03)
                pace.min     ms: no move is shorter than this (450)
                pace.dwell   0..1 default for a minor's dwell (0.5)
     defaults   body {ms, perStep}, out {ms}, in {ms, hold}; a major's own `body`, `out`, `in` override them
     major      body.ms       ms for the whole body (5000). Raised if a stepped minor would get less than
                             steps x perStep ms (650), so adding a step never turns the roll into a blur.
                body.play    ["30%","95%"]: the share of the body in which the exhibit actually changes.
                             Before and after it the tween rushes (pace.rush x), so dead air is not played.
                out.ms       ms the camera travel takes when stepping (1400). Its ease is the travel's own
                             `timing` if given, else linear when `curve` already shapes the picture (so it
                             is not eased twice), else smoothstep. out.settleMs is the ms of a wheel-settle
                             glide there (300 + 500 per screen otherwise).
                in.ms        ms from the landing to the start of the body (900); in.hold ms the act
                             statement stands still at its landing (1800): time inside a move, not a stop.
     minor      dwell 0..1   how hard the tween eases into and out of each story beat: speed at a beat is
                             (1 - dwell) x the average. 0 is linear. Default pace.dwell, or 0 when the
                             minor's own `curve` already shapes the value (a pull-back, a push-in).
                `timing`     an explicit curve for the stretch between two beats; overrides dwell.
                pace: false  the minor adds no beats to the speed profile (glass, a window opening). The
                             old `glide: false` still works.
   The page may pass opts.paceScale (a number, 0.25 = four times faster) to scale every ms: the demo, the
   tests and ?pace= use it.

   Curves: "linear", "smoothstep", "ease", "ease-in", "ease-out", "ease-in-out", "elevator",
   "cubic-bezier(x1,y1,x2,y2)", [x1,y1,x2,y2], or { "in": a, "out": b } (handle lengths 0..1: how hard
   the move speeds up and how gently it lands; { in: 0, out: 0 } is linear).

   No dependencies:
     var score = Score.compile(spec, { vars: {...}, paceScale: 1 });
     score.layout(innerHeight)          // px geometry; returns the film's length in px
     score.at(y)                        // y px into the film -> { i, id, major, p, stay, enter, enterT, body, exit, exitT, stop, phase, station, progress }
     score.minor(majorId, minorId, q)   // q = the major's body progress -> { p, t, step, steps, beat, beatId, active }
     score.beatQ(majorId, minorId, beatId)   // body progress where a beat lands (thresholds read the score, never copy it)
     score.stopQ(majorId, minorId, k)   // body progress at a minor's k-th stop (0 = start)
     score.range(majorId, minorId)      // { from, to } in body progress
     score.stations                     // px of every station: 0, then the end of each major's body
     score.reach                        // px within which y counts as being ON a station
     score.move(y, dir, opts)           // the move one press makes: { from, to, ms, ease, station, kind: 'forward'|'back' } or null
                                        //   ease is a function [0,1] -> [0,1]; opts.turn: a reversal mid-move (no reach slack)
     score.where(y)                     // { progress 0..1 (one floor per section), station (index or -1), last, count, at, hasNext, hasPrev, id, section, sections }
     score.seam(y)                      // the travel or act handover around y, or null: { from, to, ms, ease }
     score.marks                        // every px at which the page must draw exactly (stations, landings, beats); at().stop counts them
     score.timeline                     // the nominal pace segments { y0, y1, ms, kind } (tests and tools)
     score.landing(i), score.qPx(i, q), score.total, score.majors
     Score.curve(spec)                  // a curve as a function [0,1] -> [0,1]
     var tell = Score.watch(score, cb)  // call tell(y, { moving }) every frame; cb fires only on change with
                                        //   { progress, station, stations, section, sections, at, moving, ready, hasNext, hasPrev, id }.
                                        //   ready = resting on a station that has a next one: the "section done" signal.
                                        //   tell.force() re-emits after a relayout.
*/
(function () {
  'use strict';

  var PACE = { back: 0.55, launch: 280, settle: 420, smooth: 200, rush: 5, reach: 0.03, min: 450, dwell: 0.5 };
  var BODY_MS = 5000, PER_STEP = 650, OUT_MS = 1400, IN_MS = 900, HOLD_MS = 1800;
  var SAMPLES = 240;      // points the speed profile of a move is read at

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
  // A curve's inverse by bisection (curves are monotone), so a move can start or stop part-way through a stretch.
  function inverse(ease, f) {
    if (ease.linear) return f;
    var lo = 0, hi = 1, k;
    for (k = 0; k < 30; k++) { var mid = (lo + hi) / 2; if (ease(mid) < f) lo = mid; else hi = mid; }
    return (lo + hi) / 2;
  }
  // How hard a stretch between two story beats eases into and out of them: 0 linear .. 1 smoothstep.
  function dwellCurve(d) {
    if (!d) return linear;
    return function (u) { return u + (smoothstep(u) - u) * d; };
  }

  /* ---------- compile ---------- */
  function compile(spec, opts) {
    opts = opts || {};
    var vars = opts.vars || {};
    var defs = spec.defaults || {};
    var scale = spec.scale != null ? +spec.scale : 1;
    var paceScale = opts.paceScale > 0 ? +opts.paceScale : 1;
    if (!spec.majors || !spec.majors.length) throw new Error('Score: no majors');

    function where(m, mn) { return 'Score: ' + m.id + (mn ? '/' + mn.id : ''); }
    function num(v, what) { if (typeof v !== 'number' || !isFinite(v)) throw new Error(what + ' must be a number, got ' + JSON.stringify(v)); return v; }
    function count(v, what) {
      if (typeof v === 'string' && v.charAt(0) === '@') { var n = vars[v.slice(1)]; if (n == null) throw new Error(what + ': no var ' + v); v = n; }
      v = Math.floor(num(v, what)); if (v < 1) throw new Error(what + ' must be at least 1'); return v;
    }
    function ms(v, what, zeroOk) { num(v, what); if (zeroOk ? v < 0 : !(v > 0)) throw new Error(what + ' must be ' + (zeroOk ? 'zero or more' : 'above 0') + ' ms, got ' + v); return v; }
    // A share of a body: "30%" or a number 0..1.
    function share(v, what) {
      var f = typeof v === 'string' && /%$/.test(v) ? parseFloat(v) / 100 : v;
      if (typeof f !== 'number' || !isFinite(f) || f < 0 || f > 1) throw new Error(what + ' must be a share between 0% and 100%, got ' + JSON.stringify(v));
      return f;
    }

    var pace = {};
    Object.keys(PACE).forEach(function (k) { pace[k] = PACE[k]; });
    Object.keys(spec.pace || {}).forEach(function (k) {
      if (!(k in PACE)) throw new Error('Score: pace.' + k + ' is not a pace field (' + Object.keys(PACE).join(', ') + ')');
      pace[k] = num(spec.pace[k], 'Score: pace.' + k);
    });
    if (!(pace.back > 0) || !(pace.rush >= 1) || pace.dwell < 0 || pace.dwell > 1 || pace.reach < 0 || pace.launch < 0 || pace.settle < 0 || pace.smooth < 0 || pace.min < 0)
      throw new Error('Score: pace needs back > 0, rush >= 1, dwell 0..1 and no negative ms');
    var D = {
      body: Object.assign({ ms: BODY_MS, perStep: PER_STEP }, defs.body || {}),
      out: defs.out || null,
      inn: Object.assign({ ms: IN_MS, hold: HOLD_MS }, defs['in'] || {})
    };
    ms(D.body.ms, 'Score: defaults.body.ms'); ms(D.body.perStep, 'Score: defaults.body.perStep', true);

    var prevEnd = -Infinity;
    var majors = spec.majors.map(function (m, i) {
      if (!m.id) throw new Error('Score: major ' + i + ' has no id');
      num(m.start, where(m) + '.start'); num(m.end, where(m) + '.end');
      if (!(m.end > m.start)) throw new Error(where(m) + ': end must be after start');
      if (m.start < prevEnd) throw new Error(where(m) + ': starts before the previous major ends');
      prevEnd = m.end;
      var last = i === spec.majors.length - 1;
      // The default travel applies to every major but the last; a major's own `out` overrides its fields, `null` removes it.
      var out = m.out === null ? null : m.out !== undefined ? Object.assign({}, last ? {} : D.out || {}, m.out) : (last ? null : D.out ? Object.assign({}, D.out) : null);
      var inn = m['in'] ? Object.assign({}, D.inn, m['in']) : null;
      var minors = (m.minors || []).map(function (mn) {
        if (!mn.id) throw new Error(where(m) + ': a minor has no id');
        var beats = (mn.beats || []).map(function (b, k) { return { id: b.id || String(k), at: b.at, value: b.value }; });
        var steps = mn.steps != null ? count(mn.steps, where(m, mn) + '.steps') : 0;
        if (steps && beats.length) throw new Error(where(m, mn) + ': use beats or steps, not both');
        var c = curve(mn.curve);
        var dwell = mn.dwell != null ? num(mn.dwell, where(m, mn) + '.dwell') : (c.linear ? pace.dwell : 0);
        if (dwell < 0 || dwell > 1) throw new Error(where(m, mn) + '.dwell must be between 0 and 1, got ' + dwell);
        return {
          id: mn.id, start: mn.start != null ? mn.start : 0, end: mn.end != null ? mn.end : '100%',
          beats: beats, steps: steps, curve: c,
          pace: mn.pace !== false && mn.glide !== false,
          dwell: dwell, ease: mn.timing != null ? curve(mn.timing) : dwellCurve(dwell)
        };
      });
      var bs = m.body || {};
      var play = bs.play != null ? bs.play : D.body.play;
      if (play != null && (!Array.isArray(play) || play.length !== 2)) throw new Error(where(m) + '.body.play must be [from, to] shares of the body');
      play = play ? [share(play[0], where(m) + '.body.play[0]'), share(play[1], where(m) + '.body.play[1]')] : [0, 1];
      if (!(play[1] > play[0])) throw new Error(where(m) + '.body.play must run forward, got ' + JSON.stringify(m.body && m.body.play));
      var bodyMs = bs.ms != null ? bs.ms : D.body.ms;
      ms(bodyMs, where(m) + '.body.ms');
      var outMs = out && out.ms != null ? ms(out.ms, where(m) + '.out.ms') : OUT_MS;
      if (out && out.settleMs != null) ms(out.settleMs, where(m) + '.out.settleMs');
      if (inn) { ms(inn.ms, where(m) + '.in.ms'); ms(inn.hold, where(m) + '.in.hold', true); }
      var outCurve = curve(out && out.curve);
      return {
        id: m.id, i: i, spec: m, minors: minors,
        inSpec: inn, outSpec: out,
        inCurve: curve(inn && inn.curve), outCurve: outCurve,
        outTiming: curve((out && out.timing) || 'smoothstep'), outSettleMs: out && out.settleMs,
        outStepEase: out && out.timing ? curve(out.timing) : outCurve.linear ? smoothstep : linear,
        outStepMs: outMs, inMs: inn ? inn.ms : IN_MS, hold: inn ? inn.hold : 0,
        bodyMs: bodyMs, play: play, perStep: bs.perStep != null ? bs.perStep : D.body.perStep,
        land: m.land !== undefined ? m.land : defs.land
      };
    });
    var byId = {}; majors.forEach(function (M) { if (byId[M.id]) throw new Error('Score: duplicate major ' + M.id); byId[M.id] = M; });

    var api = { majors: majors, total: 0, glides: [], marks: [], stops: [], stations: [], timeline: [], reach: 0, pace: pace };

    function L(v, basis, k, what) {
      if (v == null) return 0;
      if (typeof v === 'string' && /%$/.test(v)) { var f = parseFloat(v); if (!isFinite(f)) throw new Error(what + ': bad share ' + v); return f / 100 * basis; }
      return num(v, what) * k;
    }

    api.layout = function (vh) {
      vh = Math.max(1, vh || 0);                 // a hidden or not-yet-laid-out viewport still compiles
      var k = scale * vh / 100;
      var glides = [], marks = [];
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

      // Seams, for a reader who stops dead inside one: a camera travel (with its caption crossfade) and an
      // act statement handing over. Minors are no seams: the body is where a reader may rest anywhere.
      majors.forEach(function (M, i) {
        var N = majors[i + 1];
        marks.push(M.landing, M.bodyStart, M.bodyEnd);
        if (N && M.outLen > 0) glides.push({ from: M.bodyEnd, to: N.landing, ms: M.outSettleMs, ease: M.outTiming, kind: 'out', major: M.id });
        if (M.seamIn) { glides.push({ from: M.seamIn.from, to: M.seamIn.to, ease: PRESETS.smoothstep, kind: 'in', major: M.id }); marks.push(M.seamIn.from, M.seamIn.to); }
        M.minors.forEach(function (mn) { if (mn.pace) for (var n = 1; n < mn.fr.length; n++) marks.push(clamp(lerp(mn.a, mn.z, mn.fr[n]), M.bodyStart, M.bodyEnd)); });
      });
      api.total = majors[majors.length - 1].end;

      // Stations: the very top, then where each major's content is done.
      var stations = [0];
      majors.forEach(function (M) { stations.push(M.bodyEnd); });
      api.stations = stations;
      api.reach = pace.reach * vh;
      marks = marks.concat(stations);
      marks.sort(function (a, b) { return a - b; });
      api.marks = marks.filter(function (v, n) { return n === 0 || v - marks[n - 1] > 2; });
      api.stops = api.marks;

      api.timeline = buildTimeline();
      api.glides = glides;
      return api.total;
    };

    // The nominal pace of the whole film: an ordered, gapless list of { y0, y1, ms, ease, kind } that a
    // move reads its speed profile from.
    function buildTimeline() {
      var segs = [], warned = false;
      function push(y0, y1, t, ease, kind, M) { segs.push({ y0: y0, y1: y1, ms: t, ease: ease || linear, kind: kind, major: M.id }); }
      majors.forEach(function (M, i) {
        var prev = majors[i - 1], travel = prev ? M.start - prev.bodyEnd : 0;
        if (prev && travel > 0) push(prev.bodyEnd, M.start, prev.outStepMs, prev.outStepEase, 'out', prev);
        if (M.inLen > 0) {
          var land = clamp(M.landing, M.start, M.bodyStart);
          // The arrival goes on at the travel's own pace, to the card's landing; it stands there to be read; then the handover.
          if (land > M.start) push(M.start, land, travel > 0 ? prev.outStepMs * (land - M.start) / travel : M.inMs * 0.5, linear, 'arrive', M);
          if (M.hold > 0) push(land, land, M.hold, linear, 'hold', M);
          if (M.bodyStart > land) push(land, M.bodyStart, M.inMs, smoothstep, 'in', M);
        }
        // The body: cut at the play window and at every beat of a minor that paces; each stretch gets time in
        // proportion to its length (dead stretches at 1/rush of it) and eases as its minor says.
        var a0 = M.bodyStart, a1 = M.bodyEnd, B = M.body, p0 = a0 + M.play[0] * B, p1 = a0 + M.play[1] * B;
        if (!(B > 0.5)) return;
        var stretches = [], pts = [a0, a1, p0, p1];
        M.minors.forEach(function (mn) {
          if (!mn.pace) return;
          for (var n = 0; n < mn.fr.length - 1; n++) {
            var a = lerp(mn.a, mn.z, mn.fr[n]), z = lerp(mn.a, mn.z, mn.fr[n + 1]);
            stretches.push({ a: a, z: z, mn: mn }); pts.push(a, z);
          }
        });
        if (!warned) stretches.forEach(function (x) { stretches.forEach(function (y) { if (!warned && x.mn !== y.mn && Math.min(x.z, y.z) - Math.max(x.a, y.a) > 2) { warned = true; console.warn('Score: ' + M.id + ': the minors ' + x.mn.id + ' and ' + y.mn.id + ' both pace the same stretch; give one of them pace: false'); } }); });
        pts = pts.filter(function (v) { return v >= a0 - 1e-6 && v <= a1 + 1e-6; }).sort(function (a, b) { return a - b; });
        pts = pts.filter(function (v, n) { return n === 0 || v - pts[n - 1] > 0.5; });
        pts[0] = a0; pts[pts.length - 1] = a1;
        var parts = [], W = 0;
        for (var n = 0; n < pts.length - 1; n++) {
          var a = pts[n], z = pts[n + 1];
          var live = a >= p0 - 0.5 && z <= p1 + 0.5;
          var owner = null; for (var q = 0; q < stretches.length && !owner; q++) if (stretches[q].a <= a + 0.5 && z <= stretches[q].z + 0.5) owner = stretches[q];
          var w = (z - a) * (live ? 1 : 1 / pace.rush); W += w;
          parts.push({ a: a, z: z, w: w, mn: owner && owner.mn, ease: owner ? owner.mn.ease : linear });
        }
        // A stepped minor needs steps x perStep ms to read: lengthen the body rather than blur the roll.
        var bm = M.bodyMs;
        M.minors.forEach(function (mn) {
          if (!mn.pace || !mn.steps) return;
          var wsum = 0; parts.forEach(function (x) { if (x.mn === mn) wsum += x.w; });
          var have = bm * wsum / W, need = mn.steps * M.perStep;
          if (wsum > 0 && have < need) bm *= need / have;
        });
        M.bodyMsEff = bm;
        parts.forEach(function (x) { push(x.a, x.z, bm * x.w / W, x.ease, 'body', M); });
      });
      segs.forEach(function (x) { x.ms *= paceScale; });
      return segs;
    }

    function majorAt(y) { var i = 0; while (i < majors.length - 1 && y >= majors[i + 1].start) i++; return majors[i]; }
    function idx(m) { return typeof m === 'number' ? majors[m] : byId[m]; }

    function marksPassed(y) { var s = api.marks, lo = 0, hi = s.length; while (lo < hi) { var mid = (lo + hi) >> 1; if (s[mid] <= y + 1) lo = mid + 1; else hi = mid; } return lo; }
    // The station y is ON (within `reach`), or -1.
    function stationAt(y) {
      var S = api.stations;
      for (var n = 0; n < S.length; n++) if (Math.abs(y - S[n]) <= api.reach) return n;
      return -1;
    }
    api.index = function (id) { return byId[id] ? byId[id].i : -1; };
    api.where = function (y) {
      var S = api.stations, N = S.length - 1, n = 0;
      while (n < N && y >= S[n + 1]) n++;
      var f = n < N ? clamp((y - S[n]) / (S[n + 1] - S[n]), 0, 1) : 0;
      var st = stationAt(y), M = majorAt(y);
      return {
        progress: N > 0 ? clamp((n + f) / N, 0, 1) : 0,       // one floor per section, however long the scroll
        station: st, last: N, count: S.length, at: st >= 0,
        hasNext: st < N, hasPrev: st > 0 || st < 0,
        id: M.id, section: M.i + 1, sections: majors.length
      };
    };
    api.at = function (y) {
      var M = majorAt(y);
      var enter = M.inLen > 0 ? seg(y, M.start, M.bodyStart) : 1;
      // Rests sit up to a px past their stop (rounding, device pixels): a px of slack keeps the body whole there.
      var exit = M.outLen > 0 ? seg(y, M.bodyEnd + 1, M.end) : 0;
      var w = api.where(y);
      return {
        i: M.i, id: M.id, major: M,
        p: seg(y, M.start, M.end),                 // through the whole major
        stay: seg(y, M.start, M.bodyEnd),          // through everything before it starts to leave
        enter: enter, enterT: M.inCurve(enter),
        body: seg(y, M.bodyStart, M.bodyEnd),      // the exhibit's timeline (linear)
        exit: exit, exitT: M.outCurve(exit),
        stop: marksPassed(y),                      // how many marks lie at or behind y: changes exactly on a station or a story beat
        station: w.station, progress: w.progress,
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

    /* ---------- moves ----------
       One press = one move between two stations. Its speed profile is read off the timeline: sample the
       clipped stretch, smooth the speed, ramp it up from rest and down to rest (so every move starts and
       ends at v = 0, even one that starts mid-body), integrate, and hand back the result as an ease. */
    api.move = function (y, dir, o) {
      o = o || {};
      var S = api.stations, reach = o.turn ? 1 : api.reach, j = -1, n;
      if (!S.length || !(dir > 0 || dir < 0)) return null;
      if (dir > 0) { for (n = 0; n < S.length; n++) if (S[n] > y + reach) { j = n; break; } }
      else { for (n = S.length - 1; n >= 0; n--) if (S[n] < y - reach) { j = n; break; } }
      if (j < 0) return null;
      var tgt = S[j], a = Math.min(y, tgt), b = Math.max(y, tgt), fwd = dir > 0;
      var P = profile(a, b, fwd);
      return {
        from: y, to: Math.ceil(tgt), station: j, kind: fwd ? 'forward' : 'back',
        ms: fwd ? P.ms : Math.max(P.ms * pace.back, pace.min * paceScale),
        ease: fwd ? P.ease : function (u) { return 1 - P.ease(1 - u); }
      };
    };

    function profile(a, b, fwd) {
      var T = api.timeline, pieces = [], total = 0, n;
      T.forEach(function (s) {
        if (s.kind === 'hold') { if (fwd && s.y0 > a + 1 && s.y0 < b - 1) { pieces.push({ hold: true, ms: s.ms, y: s.y0 }); total += s.ms; } return; }
        var lo = Math.max(a, s.y0), hi = Math.min(b, s.y1);
        if (hi - lo < 0.5 || !(s.y1 > s.y0)) return;
        var u0 = inverse(s.ease, (lo - s.y0) / (s.y1 - s.y0)), u1 = inverse(s.ease, (hi - s.y0) / (s.y1 - s.y0));
        var t = s.ms * (u1 - u0); if (!(t > 0)) return;
        pieces.push({ y0: lo, y1: hi, ms: t, s: s, u0: u0, u1: u1, e0: s.ease(u0), e1: s.ease(u1) }); total += t;
      });
      var minMs = pace.min * paceScale;
      if (!pieces.length || !(total > 0)) {
        var vh = (api.reach / pace.reach) || 1;
        return { ms: Math.max(minMs, (300 + 500 * Math.abs(b - a) / vh) * paceScale), ease: smoothstep };
      }
      var D = Math.max(total, minMs), N = SAMPLES;
      var ys = [], j, t0, p;
      function at(tau) {
        t0 = 0;
        for (var q = 0; q < pieces.length; q++) {
          p = pieces[q];
          if (tau <= t0 + p.ms + 1e-9) {
            if (p.hold) return p.y;
            var f = (p.s.ease(p.u0 + (p.u1 - p.u0) * ((tau - t0) / p.ms)) - p.e0) / (p.e1 - p.e0 || 1);
            return lerp(p.y0, p.y1, clamp(f, 0, 1));
          }
          t0 += p.ms;
        }
        return b;
      }
      for (j = 0; j <= N; j++) ys.push(at(j / N * total));
      var v = []; for (j = 0; j < N; j++) v.push(Math.max(0, ys[j + 1] - ys[j]));
      var w = Math.max(1, Math.round(pace.smooth * paceScale / D * N));         // a Hann window
      var ker = [], ks = 0; for (j = -w; j <= w; j++) { var kv = 0.5 + 0.5 * Math.cos(Math.PI * j / (w + 1)); ker.push(kv); ks += kv; }
      var launch = pace.launch * paceScale, settle = pace.settle * paceScale, tot = 0, vr = [];
      for (j = 0; j < N; j++) {
        var s = 0; for (n = -w; n <= w; n++) { var qj = j + n; if (qj >= 0 && qj < N) s += v[qj] * ker[n + w]; }
        var tau = (j + 0.5) / N * D;
        var x = (s / ks) * smoothstep(launch > 0 ? clamp(tau / launch, 0, 1) : 1) * smoothstep(settle > 0 ? clamp((D - tau) / settle, 0, 1) : 1);
        vr.push(x); tot += x;
      }
      if (!(tot > 0)) return { ms: D, ease: smoothstep };
      var E = [0]; for (j = 0; j < N; j++) E.push(E[j] + vr[j] / tot);
      E[N] = 1;
      return { ms: D, ease: function (u) {
        if (u <= 0) return 0; if (u >= 1) return 1;
        var x = u * N, i = Math.floor(x); return lerp(E[i], E[i + 1], x - i);
      } };
    }

    api.landing = function (m) { return idx(m).landing; };
    api.qPx = function (m, q) { var M = idx(m); return M.bodyStart + clamp(q, 0, 1) * M.body; };
    return api;
  }

  /* A page's view of the stations, as a stream of changes. Call tell(y, { moving }) every frame; cb fires when
     the readout changes. `ready` is the "section done" signal: at rest on a station that has a next one. */
  function watch(score, cb) {
    var last = null, ly = 0, li = null;
    function tell(y, info) {
      ly = y; li = info;
      var w = score.where(y), moving = !!(info && (info.moving || info.playing));
      var p = last && Math.abs(w.progress - last.progress) < 0.0005 && w.progress > 0 && w.progress < 1 ? last.progress : w.progress;
      var n = {
        progress: p, station: w.station, stations: w.count, section: w.section, sections: w.sections, at: w.at, moving: moving,
        ready: !moving && w.at && w.hasNext, hasNext: w.hasNext, hasPrev: w.hasPrev, id: w.id
      };
      if (last) {
        var same = true; for (var k in n) if (n[k] !== last[k]) { same = false; break; }
        if (same) return;
      }
      last = n; cb(n);
    }
    tell.force = function () { last = null; if (li) tell(ly, li); };
    return tell;
  }

  window.Score = { compile: compile, curve: curve, presets: PRESETS, watch: watch };
})();
