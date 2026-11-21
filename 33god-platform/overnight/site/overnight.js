/* 33GOD Overnight: the launch page.
   One night at the company, told by the clock. Scrolling is the dolly.

   The seven laws this file is held to (see the design system README):
   1. Ochre is you.            2. Light means work.        3. The clock is the timeline.
   4. One shot, one cut.       5. Real, or labelled staged. 6. Spectacle is a budget.
   7. Content is data: every word comes from manifest.json. This file owns staging only. */
(function () {
  'use strict';

  var React = window.React;
  var ReactDOM = window.ReactDOM;
  var h = React.createElement;
  var O = window.Overnight;
  var useState = React.useState;
  var useEffect = React.useEffect;
  var useRef = React.useRef;
  var useMemo = React.useMemo;
  var useCallback = React.useCallback;

  /* ---------- staging constants ---------- */
  // Where every beat sits on the scroll, and the timelines inside it, is score.json (read by score.js):
  // one major per beat, minors for the set pieces' story beats. Thresholds below read the score.
  var SC = null;         // the compiled score, set at boot
  var RV = 1 / 9;       // how much q an rv() reveal takes at its default rate: a reveal that should be
                         // up at a story beat starts this much before it
  var PER = 8;           // windows per floor
  var FLOORS = 12;       // floors until PJangler builds one more
  var BW = 384, PITCH_X = 44, PITCH_Y = 36, PAD = 24, WIN_W = 28, WIN_H = 20; // Building size 'lg', from the tokens
  var GROUND = 48;       // px from the scene's bottom edge to the ground line
  var STEPS = 60;        // how finely a hold is cut for discrete changes (window states)
  var YOU = { f: 7, c: 5 };
  var HIRE = { f: 9, c: 3 };   // never lit until Flume fills the role
  var PLACED = {               // seats the set pieces need in fixed places
    'WAX': [8, 2], 'JEV': [8, 4], 'KREBS': [5, 1], 'PILOT': [5, 2],
    'HOLOCENE': [10, 6], 'PM · HOLOCENE': [10, 5],
    'HEYMA': [3, 3], 'PM · HEYMA': [3, 2], 'VINYL': [3, 4], 'SHORTWAVE': [3, 5], 'PHONOGRAPH': [3, 6],
    'CANDYBAR': [6, 0], 'SKILLEX': [1, 4], 'FLUME': [9, 1],
    'GATEWAY': [0, 3]          // the power company sits on the ground floor
  };
  // The gateway beat's story beats are the score's gateway/router minor: pool 01 runs dry and the
  // router moves on (switch), the 04:37 scout lands (scout), the new pool settles (settled).
  /* Where you are lives in the URL: the hash names the beat you last rested on (or jumped to), and a tab keeps the
     exact station in sessionStorage, so a reload comes back to the same place. Both are conveniences: any of it may throw. */
  var STATION_KEY = 'overnight.station';
  function setHash(id) {
    try { history.replaceState(null, '', location.pathname + location.search + (id ? '#' + id : '')); } catch (e) { /* no history */ }
  }
  function rememberStation(n, id) {
    setHash(id);
    try { sessionStorage.setItem(STATION_KEY, JSON.stringify({ n: n, id: id })); } catch (e) { /* private window */ }
  }
  function savedStation() {
    try { return JSON.parse(sessionStorage.getItem(STATION_KEY)); } catch (e) { return null; }
  }
  function gwBeat(q) { return SC.minor('gateway', 'router', q).beat; }   // -1 before the switch
  function gwAt(id) { return SC.beatQ('gateway', 'router', id); }
  // Each pool's meter, scrubbed by CSS off --q: remaining share runs from..to across q in [a, b].
  function gwMeters() {
    var sw = gwAt('switch'), sc = gwAt('scout');
    return [
      { from: 0.34, to: 0.02, a: 0.06, b: sw },
      { from: 0.86, to: 0.7, a: sw, b: 0.95 },
      { from: 1, to: 1, a: 0, b: 1 },
      { from: 0.58, to: 0.68, a: sc, b: sc + 0.08 }
    ];
  }
  function poolAt(n, q, words) {
    var k = gwBeat(q);
    if (n === 0) return k < 0 ? ['working', words.drawing] : ['dark', words.spent];
    if (n === 1) return k < 0 ? ['lit', words.standby] : ['working', words.drawing];
    if (n === 2) return ['lit', words.standby];
    return k >= 1 ? [k < 2 ? 'shipped' : 'lit', words.grown] : ['lit', words.lastResort];
  }
  // Which of the router's decisions is on the card: before the switch, after it, after the scout lands.
  function decisionAt(q) { return Math.min(2, gwBeat(q) + 1); }
  var TICKET_SEATS = ['HOLOCENE', 'HEYMA', 'SHORTWAVE', 'CANDYBAR'];
  var NEW_FLOOR = { board: 1, repo: 2, pm: 3, notebook: 4, launch: 6 };

  /* ---------- small maths ---------- */
  function clamp(v, a, b) { return Math.max(a, Math.min(b, v)); }
  function lerp(a, b, t) { return a + (b - a) * t; }
  function seg(v, a, b) { return clamp((v - a) / (b - a), 0, 1); }
  function hash(f, c) { return ((f * 37 + c * 101 + f * c * 17 + 11) % 97) / 97; }
  function rgb(hex) { var n = parseInt(hex.slice(1), 16); return [(n >> 16) & 255, (n >> 8) & 255, n & 255]; }
  function mix(a, b, t) {
    var x = rgb(a), y = rgb(b);
    return 'rgb(' + Math.round(lerp(x[0], y[0], t)) + ',' + Math.round(lerp(x[1], y[1], t)) + ',' + Math.round(lerp(x[2], y[2], t)) + ')';
  }
  // Minutes since noon-before, so the night runs forward through midnight.
  function mins(t) { var p = t.split(':'); var m = (+p[0]) * 60 + (+p[1]); return m < 720 ? m + 1440 : m; }
  function fmt(m) { m = Math.floor(m) % 1440; var hh = Math.floor(m / 60), mm = m % 60; return (hh < 10 ? '0' : '') + hh + ':' + (mm < 10 ? '0' : '') + mm; }
  function pad3(n) { return n < 10 ? '00' + n : n < 100 ? '0' + n : '' + n; }
  function cssVar(name) { return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); }
  function rv(at, cls, rate) {
    var style = { '--at': at };
    if (rate) style['--rate'] = rate;
    return { className: 'rv' + (cls ? ' ' + cls : ''), style: style };
  }
  // The optional long form of any list entry: `line` / `label` stay short, `detail` is the rest.
  // Shown as a popover on hover/focus (and in full in the log view), never in the flow, so it cannot move the layout.
  function detailOf(x) { return x && typeof x.detail === 'string' ? x.detail : ''; }
  function withDetail(entry, id, i, n) {
    return detailOf(entry) ? { className: ' has-detail', tabIndex: 0, 'aria-describedby': id } : null;
  }
  function Detail(id, text, up) { return h('span', { key: 'detail', id: id, role: 'tooltip', className: 'detail' + (up ? ' detail--up' : '') }, text); }
  // An rv() row that may also carry a detail popover: merges className/props, lower half of a list opens upward.
  function rowProps(at, cls, entry, id, i, n, key) {
    var base = rv(at, cls), d = withDetail(entry, id, i, n);
    var o = { key: key, className: base.className + (d ? d.className : ''), style: base.style };
    if (d) { o.tabIndex = d.tabIndex; o['aria-describedby'] = d['aria-describedby']; }
    return o;
  }
  function detailKid(entry, id, i, n) { return detailOf(entry) ? Detail(id, detailOf(entry), i >= n / 2) : null; }
  // Flagships are numbered by page order (a beat with flagship: true), so adding one never renumbers by hand.
  function pad2(n) { return n < 10 ? '0' + n : '' + n; }
  function flagshipsOf(M) { return M.beats.filter(function (x) { return x.flagship; }); }
  function kickerOf(M, b) {
    if (!b.flagship) return b.kicker;
    return 'F-' + pad2(flagshipsOf(M).indexOf(b) + 1) + (b.kicker ? ' · ' + b.kicker : '');
  }
  function fill(M, text) {
    var n = flagshipsOf(M).length;
    return (text || '').replace('{flagships}', n > 1 ? 'F-01–F-' + pad2(n) : 'F-01');
  }

  /* ---------- the real night: a 33god.night digest (waybill night) ---------- */
  // Seat names that are not just their registry id, upper-cased.
  var CID = { 'HERMES': 'hermes-fleet', 'VAULT-PROJECTOR': 'artifact-vault-projector', 'GATEWAY-WATCHDOG': 'hermes-gateway-watchdog', 'GATEWAY': 'aai-gateway' };
  var RECENT = 3;   // minutes: a window is working if its component published in the last three
  function cidOf(name) { return name ? (CID[name] || name.toLowerCase()) : null; }
  function deskOf(name) { return name && name.indexOf('PM · ') === 0 ? name.slice(5).toLowerCase() + '-pm' : null; }
  // Per-key prefix sums over the night's minutes, so "how much in [a, b]" is one subtraction.
  // Beats whose windows follow the real night (the rest of the film is staged, and says so).
  var NIGHT_BEATS = { premise: 1, thesis: 1, numbers: 1, staff: 1, pjangler: 1, gateway: 1, heyma: 1, flume: 1 };
  function usesNight(id) { return !!NIGHT_BEATS[id]; }
  function prepNight(N, times) {
    var W = N && N.window;
    if (N.version !== 1) throw new Error('33god.night version ' + N.version + ' is not 1');
    if (!W || !(W.minutes > 0) || W.minutes !== Math.floor(W.minutes)) throw new Error('33god.night: window.minutes is not a positive integer');
    if (!/^\d{4}-\d\d-\d\dT\d\d:\d\d$/.test(W.local_since || '')) throw new Error('33god.night: bad window.local_since');
    if (!Array.isArray(N.components)) N.components = [];
    if (!Array.isArray(N.moments)) N.moments = [];
    if (!Array.isArray(N.idle)) N.idle = [];
    if (!Array.isArray(N.events_by_minute)) N.events_by_minute = [];
    var len = W.minutes;
    function sums(pairs) { var a = new Float64Array(len + 1); var d = new Float64Array(len); (pairs || []).forEach(function (p) { if (p[0] >= 0 && p[0] < len) d[p[0]] += p[1]; }); for (var k = 0; k < len; k++) a[k + 1] = a[k] + d[k]; return a; }
    var comp = {}, desk = {};
    Object.keys(N.minutes || {}).forEach(function (k) { comp[k] = sums(N.minutes[k]); });
    Object.keys(N.desks || {}).forEach(function (k) { desk[k] = sums(N.desks[k]); });
    var total = new Float64Array(len + 1);
    (N.events_by_minute || []).forEach(function (n, k) { total[k + 1] = total[k] + n; });
    var start = mins(W.local_since.slice(11, 16));
    if (isNaN(start)) throw new Error('33god.night: bad window.local_since');
    // The film's clock must land inside the night somewhere, or nothing it shows would be real.
    if (times && !times.some(function (m) { return m - start >= 0 && m - start < len; })) throw new Error('33god.night: the window ' + W.local_since + ' + ' + len + 'm misses the film\'s clock');
    return { N: N, len: len, comp: comp, desk: desk, total: total, start: start, label: W.label || '' };
  }
  function nightMinute(R, clockMins) { return Math.floor(clockMins - R.start); }
  function range(a, lo, hi, len) { lo = clamp(lo, 0, len); hi = clamp(hi, 0, len); return hi > lo ? a[hi] - a[lo] : 0; }
  function seatBusy(R, seat, mi) {
    if (!R || mi < 0 || mi >= R.len) return false;
    var a = (seat.desk && R.desk[seat.desk]) || (seat.cid && R.comp[seat.cid]);
    return !!a && range(a, mi - RECENT + 1, mi + 1, R.len) > 0;
  }
  function eventsSoFar(R, mi) { return R ? R.total[clamp(mi, 0, R.len)] : 0; }   // events before minute mi

  /* ---------- the building's seating plan ---------- */
  function buildSeats(M, R) {
    var byKey = {}, list = [];
    function put(f, c, seat) { seat.f = f; seat.c = c; seat.h = hash(f, c); byKey[f + ':' + c] = seat; list.push(seat); return seat; }
    var lines = {}, details = {};
    var beat = {};
    M.beats.forEach(function (b) { beat[b.id] = b; });
    beat['org-chart'].copy.departments.forEach(function (d) { lines[d.name] = d.line; });
    beat.staff.copy.staff.forEach(function (s) { lines[s.name] = s.line; });
    beat.heyma.copy.parts.forEach(function (p) { lines[p.name] = p.line; });
    // Any named entry in any beat's copy lists may carry a long-form `detail`; the hover plate shows it.
    M.beats.forEach(function (b) {
      Object.keys(b.copy || {}).forEach(function (k) {
        var a = b.copy[k];
        if (Array.isArray(a)) a.forEach(function (e) { if (e && typeof e === 'object' && e.name && detailOf(e)) details[e.name] = detailOf(e); });
      });
    });
    function detailFor(name) { return name ? (details[name] || details[name.split(' · ')[0]] || '') : ''; }
    Object.keys(M.nameplates || {}).forEach(function (k) { lines[k] = M.nameplates[k]; });

    put(YOU.f, YOU.c, { kind: 'you' });
    put(HIRE.f, HIRE.c, { kind: 'hire' });
    Object.keys(PLACED).forEach(function (name) {
      put(PLACED[name][0], PLACED[name][1], { kind: 'comp', name: name, line: lines[name] || lines[name.split(' · ')[0]] || '', detail: detailFor(name) });
    });
    var free = [];
    for (var f = 0; f < FLOORS; f++) for (var c = 0; c < PER; c++) if (!byKey[f + ':' + c]) free.push({ f: f, c: c, h: hash(f, c) });
    free.sort(function (a, b) { return a.h - b.h; });
    // 22 stay dark all night ("off, or not part of tonight"); with the hire's seat that leaves 72 that can light,
    // one per first-party component counted in the registry.
    free.slice(0, 22).forEach(function (s) { put(s.f, s.c, { kind: 'off' }); });
    var comps = free.slice(22);
    // The staff roll climbs the building, so seat the staff by floor.
    var staff = beat.staff.copy.staff;
    var climb = comps.slice().sort(function (a, b) { return a.f - b.f || a.h - b.h; });
    var taken = {};
    var staffSeats = staff.map(function (s, i) {
      var pick = climb[Math.floor(i * climb.length / staff.length)];
      taken[pick.f + ':' + pick.c] = true;
      return put(pick.f, pick.c, { kind: 'comp', name: s.name, line: s.line, detail: detailOf(s), staff: i });
    });
    var rest = comps.filter(function (s) { return !taken[s.f + ':' + s.c]; });
    var others = beat['org-chart'].copy.departments.map(function (d) { return d.name; })
      .concat(['ENRICHER', 'PJANGLER', 'GENESIS', 'DECKARD'])
      .filter(function (n, i, a) { return !PLACED[n] && !staff.some(function (s) { return s.name === n; }) && a.indexOf(n) === i; });
    // On a real night, the seats left over go to the components that worked tonight and have no seat of their own.
    var seated = {};
    list.forEach(function (s) { if (s.name) seated[cidOf(s.name)] = true; });
    others.forEach(function (n) { seated[cidOf(n)] = true; });
    // Then the first-party components that were quiet tonight (lit, never working); a seat left after both stays dark.
    // First-party PM desks that worked tonight and have no PM seat get one too (a desk lights its own seat).
    var deskSeated = {};
    list.concat(others.map(function (n) { return { name: n }; })).forEach(function (s) { var d = deskOf(s.name); if (d) deskSeated[d] = true; });
    var desks = R ? Object.keys(R.N.desks || {}).filter(function (d) { return /-pm$/.test(d) && !/^desk-\d+$/.test(d) && !deskSeated[d]; })
      .map(function (d) { return { id: 'desk:' + d, plate: 'PM · ' + d.slice(0, -3).toUpperCase(), summary: (M.site.night && M.site.night.deskLine) || '' }; }) : [];
    var extra = R ? R.N.components.filter(function (c) { return !seated[c.id]; }).concat(desks, (R.N.idle || []).filter(function (c) { return !seated[c.id]; })) : [];
    rest.forEach(function (s, i) {
      var name = others[i] || null, line = name ? (lines[name] || '') : '';
      if (!name && extra.length) { var c = extra.shift(); name = c.plate || c.id.toUpperCase(); line = c.summary || c.name; }
      put(s.f, s.c, { kind: 'comp', name: name, line: line, detail: detailFor(name), overtime: !R && i === others.length + 2 });
    });
    var named = {};
    list.forEach(function (s) { if (s.name) { named[s.name] = s; s.cid = cidOf(s.name); s.desk = deskOf(s.name); } });
    return { byKey: byKey, list: list, named: named, staffSeats: staffSeats };
  }

  /* ---------- which window is in which state, at any instant ---------- */
  function windowStates(ctx) {
    var id = ctx.id, q = ctx.q, step = ctx.step, I = ctx.I, i = ctx.i, seats = ctx.seats;
    var floors = ctx.floors;
    var states = new Array(floors * PER);
    var staffK = Math.min(seats.staffSeats.length - 1, SC.minor('staff', 'roll', q).step);

    var R = ctx.night, mi = ctx.minute;
    // A real night lights a seat only if a component sits in it: a spare seat has nothing to replay.
    function real(s) { return !s.name ? 'dark' : seatBusy(R, s, mi) ? 'working' : 'lit'; }
    function ambient(s) {
      if (R) return real(s);
      if (s.overtime) return 'overtime';
      var r = (Math.floor(s.h * 97) + Math.floor(step / 8)) % 12;
      return r === 0 ? 'working' : 'lit';
    }
    function comp(s) {
      var n = s.name;
      if (i === I.premise) return seg(q, 0.5, 0.95) > (s.f + s.h * 0.9) / 12.6 ? (R ? real(s) : 'lit') : 'dark';
      if (i === I.thesis) return R ? real(s) : 'lit';   // the building is held, fully lit, as in the hero
      if (i === I.numbers) return R ? real(s) : 'lit';
      if (i < I.transcript) return 'lit';     // Act III: the building is offstage, and staged
      if (i === I.transcript) return n === 'WAX' ? 'working' : (seg(q, 0.04, 0.3) > s.h * 0.98 ? 'dark' : 'lit');
      if (i < I['pm-krebs']) return n === 'WAX' ? 'working' : 'dark';
      if (i === I['pm-krebs']) {
        if (n === 'WAX' && q < 0.3) return 'working';
        if (seg(q, 0.06, 0.34) <= s.h * 0.98) return 'dark';
        if ((n === 'KREBS' || n === 'PILOT') && q > 0.4) return 'working';
        var t = TICKET_SEATS.indexOf(n);
        if (t >= 0 && q > 0.66 + t * 0.07) return 'working';
        return 'lit';
      }
      if (i === I['pms-talk']) {
        if (n === 'KREBS') return 'working';
        if (n === 'HEYMA' && q > 0.78) return 'shipped';
        if (TICKET_SEATS.indexOf(n) >= 0) return 'working';
        if (q > 0.14 && q < 0.86) {
          var turn = Math.floor(step / 4) % 2;
          if (n === 'PM · HOLOCENE') return turn === 0 ? 'working' : 'lit';
          if (n === 'PM · HEYMA') return turn === 1 ? 'working' : 'lit';
        }
        return 'lit';
      }
      if (i === I.skillex) {
        if (n === 'HOLOCENE') return 'working';
        if (s.f === PLACED.SKILLEX[0]) {
          var sk = SC.minor('skillex', 'ship', q).beat;   // -1 before build, then build, shipped, settled
          if (sk < 0) return n === 'SKILLEX' ? 'working' : 'lit';
          if (sk < 1) return n === 'SKILLEX' ? 'working' : ((step + s.c) % 2 ? 'lit' : 'dark');
          if (sk < 2) return 'shipped';
        }
        return 'lit';
      }
      if (i === I.staff) {
        if (s.staff != null) {
          if (s.staff === staffK) return 'working';
          if (s.staff === staffK - 1 || s.staff === staffK - 2) return 'shipped';
          return 'lit';
        }
        return ambient(s);
      }
      if (i === I.pjangler) return ambient(s);
      // The power company works all night; when a pool runs dry, the rest of the building does not notice.
      if (i === I.gateway) return n === 'GATEWAY' ? 'working' : ambient(s);
      if (i === I.heyma) {
        if (n === 'HEYMA' || n === 'WAX' || n === 'VINYL' || n === 'PHONOGRAPH') return 'working';
        if (n === 'SHORTWAVE') return q > 0.62 ? 'working' : 'lit';
        if (s.f === 6 && q > 0.74) return seg(q, 0.74, 0.92) * PER > s.c ? 'working' : ambient(s);
        return ambient(s);
      }
      if (i === I.flume) return n === 'FLUME' ? 'working' : ambient(s);
      if (i === I['holocene-auto']) return 'lit';
      if (i === I['hired-well']) return seg(q, 0.45, 0.95) > (floors - 1 - s.f + s.h * 0.9) / (floors + 0.2) ? 'dark' : 'lit';
      return 'dark';
    }
    function hire() {
      if (i < I.flume || i === I.ask) return 'dark';
      if (i === I.flume) return q < SC.range('flume', 'hire').from ? 'dark' : SC.minor('flume', 'shipped', q).active ? 'shipped' : 'lit';
      if (i === I['hired-well']) return seg(q, 0.45, 0.95) > (floors - 1 - HIRE.f) / floors ? 'dark' : 'lit';
      return 'lit';
    }
    function newFloor(c) {
      if (i === I.ask) return 'dark';
      if (i === I['hired-well']) return seg(q, 0.45, 0.95) > 0.02 ? 'dark' : (c === NEW_FLOOR.board || c === NEW_FLOOR.repo || c === NEW_FLOOR.pm || c === NEW_FLOOR.notebook || c === NEW_FLOOR.launch ? 'lit' : 'dark');
      var done = i > I.pjangler ? 6 : checklistDone(q);
      if (c === NEW_FLOOR.board) return done >= 2 ? 'lit' : 'dark';
      if (c === NEW_FLOOR.repo) return done >= 3 ? 'lit' : 'dark';
      if (c === NEW_FLOOR.pm) return done >= 4 ? (i === I.pjangler ? 'working' : 'lit') : 'dark';
      if (c === NEW_FLOOR.notebook) return done >= 5 ? 'lit' : 'dark';
      if (c === NEW_FLOOR.launch) return done >= 6 ? (i === I.pjangler ? 'working' : 'lit') : 'dark';
      return 'dark';
    }

    for (var f = 0; f < floors; f++) {
      for (var c = 0; c < PER; c++) {
        var idx = (floors - 1 - f) * PER + c;
        if (f >= FLOORS) { states[idx] = newFloor(c); continue; }
        var s = seats.byKey[f + ':' + c];
        states[idx] = s.kind === 'comp' ? comp(s) : s.kind === 'hire' ? hire() : 'dark';
      }
    }
    var youLit = (i === I.premise && q < 0.28) || (i === I.ask && ctx.submitted);
    return { states: states, youLit: youLit, you: (floors - 1 - YOU.f) * PER + YOU.c, staffK: staffK };
  }
  function checklistDone(q) { return SC.minor('pjangler', 'checklist', q).step; }

  /* ---------- the camera: where the building sits in each beat ---------- */
  // x, y: shift as a share of the scene; s: scale; o: the building's opacity.
  function cam(id, q) {
    var t;
    switch (id) {
      case 'premise': case 'thesis': return { x: 0.2, y: 0, s: 1, o: 1 };
      case 'numbers': return { x: 0.3, y: 0, s: 0.9, o: 1 };
      case 'org-chart': case 'bus': case 'layers': case 'runs-on-itself': return { x: 0.36, y: 0, s: 0.86, o: 0 };
      case 'transcript': t = SC.minor('transcript', 'push-in', q).t; return { x: 0, y: 0, s: Math.pow(9, t), o: 1 - seg(t, 0.2, 0.7) };
      case 'jev': case 'speakers': case 'dictionary': case 'harvest': return { x: 0, y: 0, s: 9, o: 0 };
      case 'pm-krebs': t = SC.minor('pm-krebs', 'pull-back', q).t; return { x: 0.2 * t, y: 0, s: Math.pow(9, 1 - t), o: seg(t, 0.15, 0.7) };
      case 'pms-talk': case 'skillex': return { x: 0.2, y: 0, s: 1, o: 1 };
      case 'staff': return { x: 0.2, y: lerp(-0.035, 0.025, q), s: 1, o: 1 };
      case 'pjangler': case 'gateway': case 'heyma': case 'flume': return { x: 0.2, y: 0.025, s: 1, o: 1 };
      case 'holocene-auto': return { x: 0.2, y: 0.025, s: 1, o: 0 };
      case 'hired-well': t = SC.minor('hired-well', 'pull-back', q).t; return { x: 0.12, y: 0, s: lerp(1.7, 1, t), o: seg(t, 0, 0.6) };
      default: return { x: 0.12, y: 0, s: 1, o: 1 };
    }
  }
  // A beat whose camera moves at the top of its hold lands where that move ends: score.json's
  // "land" names the minor (pm-krebs, hired-well), so a glide into the beat never rests mid-move.
  function glassAt(id, q) {
    if (id === 'transcript') return SC.minor('transcript', 'glass', q).p;
    if (id === 'jev' || id === 'speakers' || id === 'dictionary' || id === 'harvest') return 1;
    if (id === 'pm-krebs') return 1 - SC.minor('pm-krebs', 'glass-out', q).p;
    return 0;
  }

  /* ---------- the mark: never recoloured, rotated or animated ---------- */
  function Mark(props) {
    return h('svg', { width: props.size || 20, height: props.size || 20, viewBox: '0 0 24 24', 'aria-hidden': 'true', className: 'mark' },
      h('path', { className: 'mark__ink', d: 'M11 1.5A5.25 5.25 0 0 0 11 12ZM11 12a5.25 5.25 0 0 0 0 10.5ZM13 1.5A5.25 5.25 0 0 1 13 12Z' }),
      h('path', { className: 'mark__you', d: 'M13 12a5.25 5.25 0 0 1 0 10.5Z' }));
  }

  /* ---------- the clock: its own little island so the night can tick without redrawing the building ---------- */
  function LiveClock(props) {
    var st = useState({ time: props.initial, precise: null, count: null, label: props.label });
    props.api.current = st[1];
    return h('div', { className: 'hud__clockin' },
      h(O.Clock, { time: st[0].time, precise: st[0].precise, staged: true, stagedLabel: st[0].label || props.label }),
      st[0].count != null && props.counter ? h('span', { className: 'hud__count' }, props.counter.replace('{n}', Math.round(st[0].count).toLocaleString('en-US'))) : null);
  }

  /* ---------- the elevator: a thin shaft on the left edge, a small car that goes from the top floor to the ground ----------
     Floors are the stations (the top, then the end of each section); the four act openings get a longer tick.
     Written by the page's watch (refs, never React state), so it costs nothing per frame. */
  function Gauge(props) {
    var n = props.count, ticks = [];
    for (var k = 0; k < n; k++) ticks.push(h('i', { key: k, className: 'gauge__tick' + (props.acts.indexOf(k) >= 0 ? ' gauge__tick--act' : ''), style: { top: 'calc(7.5px + (100% - 17px) * ' + (k / (n - 1)).toFixed(5) + ')' } }));
    return h('div', { className: 'gauge', ref: props.gaugeRef, role: 'progressbar', 'aria-label': props.label, 'aria-valuemin': 0, 'aria-valuemax': 100 },
      h('span', { className: 'gauge__rail', 'aria-hidden': 'true' }), ticks,
      h('span', { className: 'gauge__ground', 'aria-hidden': 'true' }),
      h('span', { className: 'gauge__car', 'aria-hidden': 'true' }));
  }
  // The section is done and the reader is ready to go on: a thin chevron that bobs, only there and then.
  function Caret(props) {
    return h('button', { type: 'button', className: 'next', ref: props.caretRef, 'aria-label': props.label,
      onMouseDown: function (e) { e.preventDefault(); },      // a click must not take the arrow keys' focus
      onClick: props.onNext },
      h('svg', { width: 20, height: 10, viewBox: '0 0 20 10', 'aria-hidden': 'true', focusable: 'false' }, h('path', { d: 'M1.5 1.5 10 8.5l8.5-7', fill: 'none', stroke: 'currentColor', strokeWidth: 1.25, strokeLinecap: 'round', strokeLinejoin: 'round' })));
  }

  function Header(props) {
    var M = props.M, site = M.site;
    return h('header', { className: 'hud' },
      h('a', { className: 'hud__brand', href: '#top', onClick: function (e) { e.preventDefault(); props.jump(0, 0); } },
        h(Mark, { size: 22 }), h('span', { className: 'hud__name' }, site.name), h('span', { className: 'hud__rule', 'aria-hidden': 'true' }), h('span', { className: 'hud__status' }, site.status)),
      h('nav', { className: 'hud__nav', 'aria-label': 'The night' },
        props.view === 'film' ? site.nav.map(function (n) {
          return h('a', { key: n.beat, className: 'hud__link', href: '#' + n.beat, onClick: function (e) { e.preventDefault(); props.jumpTo(n.beat); } }, n.label);
        }) : null,
        h('button', { type: 'button', className: 'btn btn--quiet', 'aria-pressed': props.view === 'log', onClick: props.toggleView },
          props.view === 'log' ? site.viewFilm : site.viewLog),
        site.viewSimulationHref ? h('a', { className: 'btn btn--quiet hud__sim', href: site.viewSimulationHref, target: '_blank', rel: 'noopener' }, site.viewSimulation) : null,
        props.view === 'film' ? h('a', { className: 'hud__cta', href: '#ask', onClick: function (e) { e.preventDefault(); props.jumpTo('ask', 0.5); } }, site.cta) : null),
      h('div', { className: 'hud__clock' }, props.clock));
  }

  /* ---------- the ask: the form's gate is one of the five places ochre may appear ---------- */
  function Ask(props) {
    var copy = props.copy;
    var st = useState('');
    if (props.submitted) {
      return h('div', { className: 'gate gate--done', role: 'status' },
        h('span', { className: 'gate__glyph', 'aria-hidden': 'true' }),
        h('p', { className: 'gate__done' }, copy.done),
        h('p', { className: 'gate__note' }, copy.previewNote));
    }
    return h('form', { className: 'gate', onSubmit: function (e) { e.preventDefault(); if (st[0].trim()) props.onSubmit(); } },
      h('span', { className: 'gate__glyph', 'aria-hidden': 'true' }),
      h('label', { className: 'eyebrow', htmlFor: props.id }, copy.label),
      h('div', { className: 'gate__row' },
        h('input', { id: props.id, type: 'email', name: 'email', autoComplete: 'email', required: true, placeholder: copy.placeholder, value: st[0], onChange: function (e) { st[1](e.target.value); } }),
        h('button', { type: 'submit', className: 'btn btn--primary' }, copy.button)),
      h('p', { className: 'gate__note' }, copy.previewNote));
  }

  /* ---------- captions: the words of a beat, set by the design system's Caption ---------- */
  function BeatCaption(props) {
    var b = props.beat, M = props.M, copy = b.copy || {};
    var actBeats = M.beats.filter(function (x) { return x.act === b.act && x.n; });
    var eyebrow = h('p', { className: 'instrument cap__eyebrow' },
      'Act ' + b.act + ' · ' + M.acts[b.act],
      b.n ? h('span', { className: 'cap__count' }, b.n + ' / ' + (actBeats.length < 10 ? '0' : '') + actBeats.length) : null);

    if (b.id === 'premise') {
      return h('div', { className: 'cap cap--hero' },
        h('p', { className: 'eyebrow' }, b.kicker),
        h('h1', { className: 'statement-hero' }, h('span', null, b.title), h('span', { className: 'statement-hero__turn' }, b.titleTurn)),
        h('p', { className: 'cap__lede' }, b.body),
        h('div', { className: 'cap__actions' },
          h('button', { type: 'button', className: 'btn btn--primary', onClick: function () { props.jumpTo('ask', 0.5); } }, M.site.cta),
          h('a', { href: '#transcript', onClick: function (e) { e.preventDefault(); props.jumpTo('transcript'); } }, copy.secondary)),
        h('p', { className: 'instrument cap__hint' }, M.site.scrollHint));
    }
    if (b.id === 'hired-well') {
      return h('div', { className: 'cap' }, eyebrow,
        h('p', { className: 'on-caption__kicker' }, b.kicker),
        h('h2', { className: 'statement-act statement-act--turn' }, b.title));
    }
    return h('div', { className: 'cap' }, eyebrow,
      h(O.Caption, { beat: { kicker: kickerOf(M, b), title: b.title, body: b.body, tags: b.tags }, as: 'h2' }),
      b.id === 'org-chart' ? h('figure', { className: 'cap__quote' }, h('blockquote', null, copy.quote), h('figcaption', { className: 'eyebrow' }, copy.quoteSource)) : null,
      b.id === 'staff' ? h('p', { className: 'cap__aside' }, copy.more) : null,
      b.id === 'staff' ? h('p', { className: 'instrument cap__hint' }, copy.hoverHint) : null,
      b.id === 'holocene-auto' ? h('p', { className: 'cap__aside' }, copy.note) : null,
      copy.aside ? h('p', { className: 'cap__aside' }, copy.aside) : null,
      b.id === 'ask' ? h(Ask, { id: 'ask-email', copy: copy, submitted: props.submitted, onSubmit: props.onSubmit }) : null);
  }

  /* ---------- Act I and II set pieces: ink and hairlines only ---------- */
  function Directory(props) {
    var copy = props.beat.copy;
    return h('div', { className: 'sp directory', style: { width: props.width } },
      copy.figures.map(function (fig, i) {
        var id = 'fig-detail-' + i, n = copy.figures.length;
        return h('div', rowProps(0.06 + i * 0.1, 'directory__row', fig, id, i, n, i),
          h('span', { className: 'directory__n' }, fig.n), h('span', { className: 'directory__label' }, fig.label), detailKid(fig, id, i, n));
      }),
      h('p', rv(0.62, 'caption-note'), copy.stamp));
  }

  function OrgChart(props) {
    var copy = props.beat.copy;
    return h('div', { className: 'sp org' },
      h('div', rv(0.02, 'org__you'),
        h('span', { className: 'org__node', 'aria-hidden': 'true' }),
        h('span', { className: 'instrument org__name' }, copy.you.label),
        h('span', { className: 'org__line' }, copy.you.line)),
      h('div', { className: 'org__trunk draw-x', style: { '--at': 0.06 } }),
      h('div', { className: 'org__grid' }, copy.departments.map(function (d, i) {
        var id = 'dept-detail-' + i, n = copy.departments.length;
        return h('div', rowProps(0.12 + i * 0.055, 'org__cell', d, id, i, n, d.name),
          h('span', { className: 'eyebrow' }, d.dept),
          h('span', { className: 'instrument org__name' }, d.name),
          h('span', { className: 'org__line' }, d.line),
          detailKid(d, id, i, n));
      })));
  }

  function Bus(props) {
    var copy = props.beat.copy, q = props.q;
    var at = [0.17, 0.38, 0.59, 0.8];
    return h('div', { className: 'sp bus' },
      h('div', { className: 'bus__lane' },
        h('span', { className: 'instrument bus__label' }, 'BLOODBANK'),
        h('div', { className: 'bus__line draw-x', style: { '--at': 0 } }),
        h('div', { className: 'bus__event' }, h(O.Window, { state: 'lit', size: 'lg', label: 'An event, in transit' }), h('span', { className: 'instrument-log' }, copy.event))),
      h('div', { className: 'bus__listeners' }, copy.listeners.map(function (l, i) {
        var heard = q > at[i];
        return h('div', { key: l.name, className: 'bus__listener' + (heard ? ' is-heard' : '') },
          h('span', { className: 'bus__tap', 'aria-hidden': 'true' }),
          h(O.Window, { state: heard ? 'lit' : 'dark', size: 'lg' }),
          h('span', { className: 'instrument' }, l.name),
          h('span', { className: 'bus__does' }, l.does));
      })),
      h('p', rv(0.84, 'punch'), copy.punch),
      h('div', { className: 'tape', 'aria-hidden': 'true' },
        h('div', { className: 'tape__row tape__row--a' }, copy.tapeA.concat(copy.tapeA).map(function (t, i) { return h('span', { key: i }, t); })),
        h('div', { className: 'tape__row tape__row--b' }, copy.tapeB.concat(copy.tapeB).map(function (t, i) { return h('span', { key: i }, t); }))),
      h('p', { className: 'caption-note' }, copy.tapeNote));
  }

  function Layers(props) {
    var copy = props.beat.copy;
    return h('div', { className: 'sp layers' },
      h('div', { className: 'layers__stack' }, copy.layers.map(function (l, i) {
        return h('div', Object.assign({ key: l.role }, rv(0.05 + i * 0.13, 'layers__row')),
          h('span', { className: 'eyebrow' }, l.role),
          h('span', { className: 'instrument layers__names' }, l.names),
          i < copy.layers.length - 1 ? h('span', { className: 'layers__down', 'aria-hidden': 'true' }) : null);
      })),
      h('p', rv(0.74, 'punch'), copy.punch),
      h('p', rv(0.8, 'caption-note'), copy.note));
  }

  function Loop(props) {
    var copy = props.beat.copy, q = props.q;
    var n = copy.steps.length;
    var lp = SC.minor('runs-on-itself', 'loop', q);
    var passed = lp.p > 0 ? lp.step + 1 : 0;   // a pip lights as the dot reaches it
    return h('div', { className: 'sp loop' },
      h('div', { className: 'loop__ring' },
        h('svg', { viewBox: '0 0 100 100', 'aria-hidden': 'true' },
          h('circle', { cx: 50, cy: 50, r: 46, className: 'loop__track' }),
          h('circle', { cx: 50, cy: 50, r: 46, className: 'loop__drawn', pathLength: 1 })),
        // The ring and its dot follow --turn (CSS, read off the playhead every frame); only the pips step.
        h('span', { className: 'loop__dot', 'aria-hidden': 'true' }, h(O.Window, { state: 'lit' })),
        copy.steps.map(function (s, i) {
          var a = (i / n) * Math.PI * 2 - Math.PI / 2;
          return h('div', { key: i, className: 'loop__step' + (i < passed ? ' is-passed' : ''), style: { left: (50 + Math.cos(a) * 46) + '%', top: (50 + Math.sin(a) * 46) + '%' }, 'data-side': Math.cos(a) < -0.2 ? 'left' : Math.cos(a) > 0.2 ? 'right' : (Math.sin(a) < 0 ? 'top' : 'bottom') },
            h('span', { className: 'loop__pip', 'aria-hidden': 'true' }),
            h('span', { className: 'loop__text' }, h('span', { className: 'instrument' }, '0' + (i + 1)), h('span', null, s)));
        }),
        h('div', { className: 'loop__core' }, h('span', { className: 'loop__count' }, copy.count), h('span', { className: 'eyebrow' }, copy.countLabel))));
  }

  /* ---------- Act III: one transcript, pinned on the conference-room glass, changed eight times ---------- */
  function Glass(props) {
    var M = props.M, T = M.transcript, id = props.id, q = props.q, I = props.I, i = props.i;
    var labelled = i > I.speakers ? 99 : i === I.speakers ? SC.minor('speakers', 'voices', q).step : 0;
    var found = i > I.jev ? 99 : i === I.jev ? SC.minor('jev', 'judgments', q).step : 0;
    var learned = i > I.dictionary ? 99 : i === I.dictionary ? SC.minor('dictionary', 'words', q).step : 0;
    var peeled = i > I.harvest ? 99 : i === I.harvest ? SC.minor('harvest', 'tickets', q).step : 0;
    var pCount = 0, wCount = 0, words = [];

    function renderText(text) {
      var out = [], re = /\{(p|w):([^}]+)\}/g, last = 0, m, k = 0;
      while ((m = re.exec(text))) {
        if (m.index > last) out.push(text.slice(last, m.index));
        if (m[1] === 'p') { var on = pCount < found; pCount++; out.push(h('span', { key: k++, className: 'tx-project' + (on ? ' is-found' : '') }, m[2])); }
        else { var lit = wCount < learned; if (lit) words.push(m[2]); wCount++; out.push(h('span', { key: k++, className: 'tx-word' + (lit ? ' is-learned' : '') + (lit && i === I.dictionary ? ' is-fresh' : '') }, m[2])); }
        last = m.index + m[0].length;
      }
      if (last < text.length) out.push(text.slice(last));
      return out;
    }
    var seen = {};
    var lines = T.lines.map(function (l, n) {
      var named = false;
      if (labelled > 0) { var order = Object.keys(seen).length; if (!(l.s in seen)) seen[l.s] = order; named = seen[l.s] < labelled; }
      var taken = l.ticket != null && l.ticket < peeled;
      var props2 = id === 'transcript' ? rv(0.6 + n * 0.055, 'tx-line', 12) : { className: 'tx-line' };
      return h('div', Object.assign({ key: n }, props2, { 'data-taken': taken ? 'yes' : null }),
        h('span', { className: 'tx-speaker' + (named ? ' is-named' : '') }, named ? T.speakers[l.s] : ''),
        h('p', { className: 'tx-text' }, renderText(l.text)));
    });

    var side = null;
    if (i === I.jev) {
      side = h('div', { className: 'glass__panel' },
        h('p', { className: 'instrument' }, 'JEV'),
        T.judgments.map(function (j, n) {
          return h('div', { key: n, className: 'judgment' + (n < found ? ' is-in' : '') }, h('span', null, j.q), h('span', { className: 'judgment__a' }, j.a));
        }));
    } else if (i === I.speakers) {
      side = h('div', { className: 'glass__panel' },
        h('p', { className: 'instrument' }, 'VOICES'),
        T.speakers.map(function (s, n) {
          return h('div', { key: n, className: 'voice' + (n < labelled ? ' is-in' : '') },
            h('span', { className: 'voice__print', 'aria-hidden': 'true' }, [3, 7, 5, 9, 4, 8, 6].map(function (v, k) { return h('i', { key: k, style: { height: ((v * (n + 2) * 7) % 13 + 4) + 'px' } }); })),
            h('span', null, n < labelled ? s : ''));
        }));
    } else if (i === I.dictionary) {
      side = h('div', { className: 'glass__panel' },
        h('p', { className: 'instrument' }, T.dictionaryTitle),
        words.map(function (w) { return h('div', { key: w, className: 'dict-word' }, w); }));
    } else if (i >= I.harvest) {
      side = h('div', { className: 'glass__panel glass__panel--tickets' },
        h('p', { className: 'instrument' }, 'PILOT'),
        T.tickets.map(function (t, n) {
          return h('div', { key: n, className: 'ticket' + (n < peeled ? ' is-in' : '') }, h('span', { className: 'instrument ticket__board' }, t.board), h('span', { className: 'ticket__title' }, t.title));
        }));
    } else {
      side = h('div', { className: 'glass__panel' }, h('p', rv(0.62, 'instrument', 12), 'WAX'), h('p', rv(0.9, 'caption-note', 12), props.waxLine));
    }
    var beat = M.beats[i];
    var dots = ['01', '02', '03', '04', '05', '06', '07', '08'];
    return h('div', { className: 'glass', ref: props.glassRef, style: { transformOrigin: props.origin } },
      h('div', { className: 'glass__pane' },
        h('div', { className: 'glass__head' }, h('span', { className: 'instrument' }, T.room), h(O.Window, { state: 'working', label: 'The conference room window, working' })),
        h('div', { className: 'glass__body' }, h('div', { className: 'glass__lines' }, lines), side),
        h('div', { className: 'glass__foot' },
          h('span', { className: 'glass__dots', 'aria-hidden': 'true' }, dots.map(function (d) { return h('i', { key: d, className: beat && beat.n && d <= beat.n ? 'is-on' : '' }); })),
          h('span', { className: 'instrument' }, (beat && beat.n ? beat.n : '06') + ' / 08'))));
  }

  /* ---------- Act V: the one cut, to the car ---------- */
  function Car(props) {
    var copy = props.beat.copy, s = copy.screen, q = props.q;
    return h('div', { className: 'sp car' },
      h('div', { className: 'car__bezel' },
        h('div', { className: 'car__screen', 'data-theme': 'night' },
          h('div', { className: 'car__head' },
            h('span', { className: 'car__brand' }, h(Mark, { size: 16 }), h('span', { className: 'hud__name hud__name--sm' }, props.M.site.name), h('span', { className: 'hud__rule', 'aria-hidden': 'true' }), h('span', { className: 'hud__status' }, s.product)),
            h('span', { className: 'car__signal' }, h('span', { className: 'orbit', 'aria-hidden': 'true' }), s.signal)),
          h('p', { className: 'car__line' }, s.line),
          h('div', { className: 'car__foot' },
            h('span', { className: 'car__need' }, h('span', { className: 'car__gate', 'aria-hidden': 'true' }), h('span', { className: 'instrument car__count' }, s.count)),
            h('span', { className: 'car__sub' }, s.sub)))),
      h('div', { className: 'car__standup' },
        h('p', { className: 'eyebrow' }, copy.standupTitle),
        // Bar heights are written by the dolly every frame (waveAt), so the voice moves smoothly.
        h('div', { className: 'car__wave', 'aria-hidden': 'true' }, Array.from({ length: 28 }, function (_, k) { return h('i', { key: k }); })),
        copy.standup.map(function (line, n) {
          return h('div', Object.assign({ key: n }, rv(SC.stopQ('holocene-auto', 'standup', n + 1) - RV, 'car__item')), h('span', { className: 'instrument' }, '0' + (n + 1)), h('span', null, line));
        })));
  }

  function waveAt(k, q) { return 4 + Math.abs(Math.sin(k * 1.7 + q * 26)) * Math.abs(Math.sin(k * 0.45 + q * 9)) * 26; }

  /* ---------- the app ---------- */
  function App(props) {
    var M = props.M;
    var beats = M.beats;
    var I = useMemo(function () { var m = {}; beats.forEach(function (b, n) { m[b.id] = n; }); return m; }, [beats]);
    var R = props.night;
    var NC = M.site.night || {};
    var realLabel = R ? (NC.label || '{label}').replace('{label}', R.label) : '';
    var seats = useMemo(function () { return buildSeats(M, R); }, [M, R]);
    var times = useMemo(function () { return beats.map(function (b) { return mins(b.time); }); }, [beats]);

    var prefersLog = useMemo(function () {
      return window.matchMedia('(prefers-reduced-motion: reduce)').matches || window.matchMedia('(max-width: 760px)').matches;
    }, []);
    var wantView = useMemo(function () { var v = new URLSearchParams(location.search).get('view'); return v === 'log' || v === 'film' ? v : null; }, []);
    var viewSt = useState(wantView || (prefersLog ? 'log' : 'film')); var view = viewSt[0], setView = viewSt[1];
    var posSt = useState({ i: 0, step: 0, q: 0, minute: -1 }); var pos = posSt[0], setPos = posSt[1];
    var sizeSt = useState({ w: 760, h: 640, bs: 1 }); var size = sizeSt[0], setSize = sizeSt[1];
    var subSt = useState(false); var submitted = subSt[0], setSubmitted = subSt[1];
    var hoverSt = useState(null); var hover = hoverSt[0], setHover = hoverSt[1];
    var crankSt = useState(false); var crank = crankSt[0], setCrank = crankSt[1];

    var stageRef = useRef(null), trackRef = useRef(null), sceneRef = useRef(null), worldRef = useRef(null), overlayRef = useRef(null);
    var glassRef = useRef(null), spRef = useRef(null), capRef = useRef(null), interRef = useRef(null), horizonRef = useRef(null);
    var clockApi = useRef(null), last = useRef({ i: -1, step: -1, minute: -1, sig: '', clock: '', precise: null, label: '', theme: '' });
    var camNow = useRef({ x: 0, y: 0, s: 1, o: 1 });
    var dollyRef = useRef(null), playY = useRef(0);
    var gaugeRef = useRef(null), caretRef = useRef(null), tellRef = useRef(null), infoRef = useRef(null);
    var sizeRef = useRef(size); sizeRef.current = size;

    var b = beats[pos.i];
    var floors = pos.i > I.pjangler || (pos.i === I.pjangler && pos.q >= 0.06) ? FLOORS + 1 : FLOORS;

    /* layout: the score in px, and the scene's size */
    var measure = useCallback(function () {
      var vh = window.innerHeight, y = SC.layout(vh);
      if (trackRef.current) trackRef.current.style.height = (y + vh) + 'px';
      if (sceneRef.current) {
        var r = sceneRef.current.getBoundingClientRect();
        var H13 = PAD * 2 + 13 * WIN_H + 12 * (PITCH_Y - WIN_H) + 1;
        var bs = clamp(Math.min((r.height - GROUND - 56) / (H13 + 24), (r.width * 0.56) / BW), 0.45, 1.3);
        setSize(function (s) { return Math.abs(s.w - r.width) < 1 && Math.abs(s.h - r.height) < 1 ? s : { w: r.width, h: r.height, bs: bs }; });
      }
    }, [beats]);

    // A nav jump lands where a reader arriving at the beat would (a rest point), or at body progress q.
    var jump = useCallback(function (i, q) {   // q: the beat's body progress (its set piece's timeline)
      var top = trackRef.current ? trackRef.current.offsetTop : 0;
      var px = top + Math.ceil(q != null ? SC.qPx(i, q) : SC.landing(i));
      setHash(i > 0 ? beats[i].id : '');
      if (dollyRef.current) dollyRef.current.jump(px); else window.scrollTo({ top: px, behavior: 'auto' });
    }, [beats]);
    var jumpTo = useCallback(function (id, q) { jump(I[id], q); }, [I, jump]);

    /* the dolly: scroll position in, camera, clock and sky out */
    var frame = useCallback(function (yAbs, info) {
      if (yAbs == null) yAbs = playY.current; else playY.current = yAbs;
      if (info) infoRef.current = info;
      var stage = stageRef.current; if (!stage || !trackRef.current) return;
      if (!SC.total) return;
      if (tellRef.current) tellRef.current(yAbs - trackRef.current.offsetTop, infoRef.current);   // the gauge, the caret, the crank
      var y = clamp(yAbs - trackRef.current.offsetTop, 0, SC.total - 1);
      var S = SC.at(y), Mj = S.major;
      var i = S.i, bt = beats[i], next = beats[i + 1];
      // p: through the whole beat; hold: through everything before it leaves; tr: the travel out;
      // q: the set piece's own timeline. An act statement takes the beat's `in` (INTER of the hold).
      var p = S.p, hold = S.stay, tr = next ? S.exit : 0, q = S.body;
      var INTER = Mj.inLen / (Mj.bodyEnd - Mj.start);

      // camera
      var a = cam(bt.id, q), K = a;
      if (next && tr > 0 && !next.cut) { var z = cam(next.id, 0), e = S.exitT; K = { x: lerp(a.x, z.x, e), y: lerp(a.y, z.y, e), s: lerp(a.s, z.s, e), o: lerp(a.o, z.o, e) }; }
      camNow.current = K;
      var sz = sizeRef.current;
      var tx = K.x * sz.w, ty = K.y * sz.h;
      if (worldRef.current) { worldRef.current.style.transform = 'translate(' + tx + 'px,' + ty + 'px) scale(' + K.s + ')'; worldRef.current.style.opacity = K.o; }
      if (overlayRef.current) { overlayRef.current.style.transform = 'translate(' + tx + 'px,' + ty + 'px)'; overlayRef.current.style.opacity = Math.max(0, Math.min(K.o, 1 - tr * 1.6, i === 0 ? 1 : seg(p, 0.02, 0.07)) * (1 - seg(K.s, 1, 1.05))); }
      var g = glassAt(bt.id, q);
      if (glassRef.current) { glassRef.current.style.opacity = g; glassRef.current.style.transform = 'scale(' + lerp(0.55, 1, g) + ')'; glassRef.current.style.visibility = g > 0.01 ? 'visible' : 'hidden'; }

      // words
      var capO = Math.min(i === 0 ? 1 : seg(p, 0, 0.05), next ? 1 - seg(p, 0.9, 1) : 1) * (bt.interlude ? seg(hold, INTER - 0.05, INTER + 0.03) : 1);
      if (capRef.current) { capRef.current.style.opacity = capO; capRef.current.style.pointerEvents = capO > 0.5 ? 'auto' : 'none'; }
      if (spRef.current) spRef.current.style.opacity = capO;
      if (interRef.current) {
        var io = bt.interlude ? Math.min(seg(p, 0, 0.03), 1 - seg(hold, INTER - 0.07, INTER - 0.01)) : 0;
        interRef.current.style.opacity = io; interRef.current.style.visibility = io > 0.01 ? 'visible' : 'hidden';
      }
      stage.style.setProperty('--p', p.toFixed(4));
      stage.style.setProperty('--q', q.toFixed(4));
      if (bt.id === 'holocene-auto' && spRef.current) {
        var bars = spRef.current.querySelectorAll('.car__wave i');
        for (var k = 0; k < bars.length; k++) bars[k].style.height = waveAt(k, q).toFixed(1) + 'px';
      }

      // clock and sky
      var m = next ? lerp(times[i], times[i + 1], tr) : times[i];
      var morning = i >= I['holocene-auto'];
      var theme = morning ? 'morning' : 'night';
      if (theme !== last.current.theme) { last.current.theme = theme; document.documentElement.setAttribute('data-theme', theme); }
      var C = props.colors;
      var sky = morning ? C.sky0730 : m < mins('22:00') ? mix(C.sky1802, C.sky2200, seg(m, mins('18:02'), mins('22:00'))) : mix(C.sky2200, C.sky0200, seg(m, mins('22:00'), mins('02:00')));
      stage.style.setProperty('--sky', sky);
      if (horizonRef.current) {
        horizonRef.current.style.opacity = morning ? 0 : seg(m, mins('04:00'), mins('05:00'));
        horizonRef.current.style.setProperty('--band', mix(C.sky0500, C.sky0630, seg(m, mins('05:00'), mins('06:30'))));
      }
      var clock = fmt(m), precise = bt.id === 'jev' && tr === 0 ? '07.' + pad3(31 + Math.floor(q * 48)) : null;
      // The clock says "real" only over beats whose windows replay the night; the counter is the real
      // night at this clock time either way.
      var realBeat = !!R && usesNight(bt.id);
      var label = realBeat ? realLabel : M.site.stagedLabel;
      var nightMi = R ? nightMinute(R, m) : -1, minute = realBeat ? nightMi : -1;
      if (clockApi.current && (clock !== last.current.clock || precise !== last.current.precise || label !== last.current.label)) {
        last.current.clock = clock; last.current.precise = precise; last.current.label = label;
        clockApi.current({ time: clock, precise: precise, label: label, count: R ? eventsSoFar(R, nightMi) : null });
      }

      // Re-render on a new step of the hold, on every score stop (so a story beat the dolly rests on is
      // drawn at exactly that beat, not a step short of it), and when a real minute flips some seat's
      // busy bit (windows follow the night during travels too; a minute that changes no window re-renders nothing).
      var step = Math.floor(q * STEPS);
      var sig = '';
      if (minute >= 0) for (var k2 = 0; k2 < seats.list.length; k2++) { var st2 = seats.list[k2]; if (st2.name && seatBusy(R, st2, minute)) sig += k2 + ','; }
      if (i !== last.current.i || step !== last.current.step || S.stop !== last.current.stop || sig !== last.current.sig) {
        last.current.i = i; last.current.step = step; last.current.stop = S.stop; last.current.minute = minute; last.current.sig = sig; setPos({ i: i, step: step, q: q, minute: minute });
      }
    }, [beats, times, I, props.colors, R, realLabel, M.site.stagedLabel, seats]);

    // Seams and moves come from the score. A seam is a camera travel with its caption crossfade or an act's
    // statement handing over: stop in one and the dolly finishes it. A move is what one press of Down makes:
    // the whole of the next section, from where you are to where its content is done (see score.js, dolly.js).
    var seam = useCallback(function (t) { return SC.total ? SC.seam(t) : null; }, []);
    var move = useCallback(function (t, dir, o) { return SC.total ? SC.move(t, dir, o) : null; }, []);

    useEffect(function () {
      if (view !== 'film') { document.documentElement.setAttribute('data-theme', 'night'); last.current.theme = 'night'; return; }
      var idle = 0;
      var want = ''; try { want = decodeURIComponent(location.hash.slice(1)); } catch (e) { want = ''; }
      var restored = false;
      try { if ('scrollRestoration' in history) history.scrollRestoration = 'manual'; } catch (e) { /* ignore */ }
      last.current.clock = ''; last.current.precise = null; last.current.label = '';   // a fresh clock island: tell it everything
      measure();
      // The page's view of the stations: the elevator, the caret, and the crank (which waits for the film to come to rest).
      var tell = window.Score.watch(SC, function (s) {
        var g = gaugeRef.current, c = caretRef.current, st = stageRef.current;
        if (g) {
          g.style.setProperty('--gauge', s.progress.toFixed(4));
          var pct = String(Math.round(s.progress * 100));
          if (g.getAttribute('aria-valuenow') !== pct) g.setAttribute('aria-valuenow', pct);
          g.setAttribute('aria-valuetext', M.site.gaugeText.replace('{n}', s.section).replace('{total}', s.sections));
        }
        if (c) {
          c.setAttribute('data-ready', s.ready ? 'true' : 'false');
          // Not ready: out of the tab order and the reading order, but never yanked from a hand that holds focus
          // (a keyboard user who pressed it keeps it through the move and can press again).
          var held = document.activeElement === c;
          c.tabIndex = s.ready || held ? 0 : -1;
          if (s.ready || held) c.removeAttribute('aria-hidden'); else c.setAttribute('aria-hidden', 'true');
          if (!s.hasNext && !s.moving && held) c.blur();
        }
        if (restored && s.at && !s.moving && s.station >= 0) rememberStation(s.station, s.station > 0 ? beats[s.station - 1].id : '');
        if (st) { st.dataset.station = s.station; st.dataset.motion = s.moving ? 'moving' : 'rest'; }
        // Scroll events fire every frame during a move, so the crank keys off rest, not off scroll.
        if (s.moving !== wasMoving) { wasMoving = s.moving; clearTimeout(idle); setCrank(false); if (!s.moving) idle = setTimeout(armCrank, 20000); }
      });
      var wasMoving = false;
      function armCrank() { if (last.current.i < beats.length - 1) setCrank(true); }
      tellRef.current = tell;
      var dolly = window.Dolly.create({ onFrame: frame, seam: seam, move: move, origin: function () { return trackRef.current ? trackRef.current.offsetTop : 0; } });
      dollyRef.current = dolly;
      // Once, after the first measure: come back to the place the URL names. The hash wins over a stale session;
      // the same beat in this tab's session comes back to its exact station, else the beat's landing.
      function restore() {
        restored = true;
        if (typeof I[want] !== 'number' || !trackRef.current) return;
        var saved = savedStation(), top = trackRef.current.offsetTop;
        if (saved && saved.id === want && saved.n > 0 && SC.stations[saved.n] != null) dolly.jump(top + Math.ceil(SC.stations[saved.n]));
        else jump(I[want], null);
        tell.force();
      }
      function onResize() {
        var top = trackRef.current ? trackRef.current.offsetTop : 0;
        var f = SC.total ? clamp((window.scrollY - top) / SC.total, 0, 1) : 0;
        dolly.cancel();
        measure();
        dolly.rescale(f, function (fr) { return top + fr * SC.total; });
        if (!restored) restore();
        tell.force();
      }
      idle = setTimeout(armCrank, 20000);
      window.addEventListener('resize', onResize);
      var fonts = document.fonts && document.fonts.ready; if (fonts) fonts.then(onResize); else onResize();
      return function () { dolly.destroy(); dollyRef.current = null; tellRef.current = null; window.removeEventListener('resize', onResize); clearTimeout(idle); };
    }, [view, frame, seam, move, measure, beats.length]);
    // Set pieces mount as beats change (a nav jump can land mid-night); give them their scrubbed styles at once.
    React.useLayoutEffect(function () { if (view === 'film') frame(); }, [size, view, frame, posSt[0].i]);

    // Leaving either view starts the other at the top; reset the film's state so it never mounts a stale beat.
    var toggleView = useCallback(function () {
      setView(function (v) { return v === 'film' ? 'log' : 'film'; });
      window.scrollTo(0, 0);
      playY.current = 0; last.current.i = -1; last.current.step = -1; last.current.minute = -1; last.current.sig = ''; last.current.clock = ''; last.current.label = '';
      setPos({ i: 0, step: 0, q: 0, minute: -1 });
    }, []);
    var clock = h(LiveClock, { api: clockApi, initial: beats[0].time, label: R && usesNight(beats[0].id) ? realLabel : M.site.stagedLabel, counter: R ? NC.counter : null });

    if (view === 'log') return h(LogView, { M: M, toggleView: toggleView, submitted: submitted, onSubmit: function () { setSubmitted(true); }, I: I, night: R });

    /* geometry: where a window is, in the scene */
    var wst = windowStates({ id: b.id, q: pos.q, step: pos.step, I: I, i: pos.i, seats: seats, floors: floors, submitted: submitted, night: R, minute: pos.minute });
    function at(f, c) { return { x: size.w / 2 + (PAD + c * PITCH_X + WIN_W / 2 - BW / 2) * size.bs, y: size.h - GROUND - (PAD + f * PITCH_Y + WIN_H / 2) * size.bs }; }
    var bLeft = size.w / 2 - BW / 2 * size.bs;
    var K0 = cam(b.id, pos.q);
    var room = Math.max(150, bLeft + K0.x * size.w - 36);   // free width to the left of the building
    var waxAt = at(PLACED.WAX[0], PLACED.WAX[1]);

    // withMore: the hover plate also shows the seat's long-form `detail`; it opens upward from the lower half so it
    // always stays between the header and the bottom of the screen. The auto-advancing staff roll never does.
    function plate(seat, state, key, withMore) {
      var p = at(seat.f, seat.c), more = withMore && seat.detail ? seat.detail : '';
      var up = p.y > size.h - 170 || (more && p.y > size.h / 2);
      return h('div', { key: key || 'plate', className: 'plate' + (up ? ' plate--up' : ''), style: more ? { top: p.y, right: size.w - bLeft + 22, width: Math.min(room, 240) } : { top: p.y, right: size.w - bLeft + 22, maxWidth: room } },
        more ? h('div', { className: 'plate__col' }, h(O.Nameplate, { name: seat.name, line: seat.line, state: state }), h('div', { className: 'plate__detail' }, more))
             : h(O.Nameplate, { name: seat.name, line: seat.line, state: state }),
        h('span', { className: 'plate__lead', 'aria-hidden': 'true', style: { width: p.x - bLeft + 22 - WIN_W / 2 * size.bs - 4 } }));
    }
    function card(children, cls, topF) {
      // Tall cards stand on the ground line; short ones hang level with a floor.
      var st = { right: size.w - bLeft + 22, width: Math.min(room, 320) };
      if (topF != null) st.top = Math.max(0, at(topF, 0).y - 12); else st.bottom = GROUND + 14 + K0.y * size.h;
      return h('div', { key: 'card', className: 'scard ' + (cls || ''), style: st }, children);
    }

    /* overlays that ride with the building */
    var over = [];
    var id = b.id, q = pos.q;
    if (id === 'premise') {
      var yp = at(YOU.f, YOU.c);
      over.push(h('span', { key: 'leave', className: 'instrument leave', style: { left: yp.x + WIN_W * size.bs / 2 + 10, top: yp.y } }, b.copy.youLeave));
    }
    if (id === 'pm-krebs') {
      M.transcript.tickets.forEach(function (t, n) {
        var to = at(seats.named[TICKET_SEATS[n]].f, seats.named[TICKET_SEATS[n]].c);
        var from = { x: bLeft - 60, y: size.h * 0.34 + n * 34 };
        over.push(h('span', { key: 't' + n, className: 'instrument flyer', style: { left: from.x, top: from.y, '--dx': (to.x - from.x) + 'px', '--dy': (to.y - from.y) + 'px', '--at': 0.4 + n * 0.07 } }, t.board));
      });
      over.push(plate(seats.named.KREBS, q > 0.4 ? 'working' : 'lit', 'krebs'));
    }
    if (id === 'pms-talk') {
      var pa = at(PLACED['PM · HOLOCENE'][0], PLACED['PM · HOLOCENE'][1]), pb = at(PLACED['PM · HEYMA'][0], PLACED['PM · HEYMA'][1]);
      var len = Math.hypot(pb.x - pa.x, pb.y - pa.y), ang = Math.atan2(pb.y - pa.y, pb.x - pa.x) * 180 / Math.PI;
      over.push(h('span', { key: 'sig', className: 'signal', 'aria-hidden': 'true', style: { left: pa.x, top: pa.y, width: len, transform: 'rotate(' + ang + 'deg)' } },
        h('i', { style: { left: (Math.floor(pos.step / 4) % 2 === 0 ? seg((pos.step % 4) / 4, 0, 1) : 1 - seg((pos.step % 4) / 4, 0, 1)) * 100 + '%' } })));
      over.push(h('div', { key: 'pa', className: 'plate', style: { top: pa.y, right: size.w - bLeft + 22, maxWidth: room } }, h(O.Nameplate, { name: 'PM · HOLOCENE', line: seats.named['PM · HOLOCENE'].line })));
      over.push(h('div', { key: 'pb', className: 'plate', style: { top: pb.y, right: size.w - bLeft + 22, maxWidth: room } }, h(O.Nameplate, { name: 'PM · HEYMA', line: b.copy.message })));
    }
    if (id === 'skillex') { var skb = SC.minor('skillex', 'ship', q).beat; over.push(plate(seats.named.SKILLEX, skb < 1 ? 'working' : skb < 2 ? 'shipped' : 'lit', 'skillex')); }
    if (id === 'staff' && !hover) {
      var ss = seats.staffSeats[wst.staffK];
      over.push(plate(ss, 'working', 'staff'));
      over.push(h('span', { key: 'roll', className: 'instrument roll', style: { right: size.w - bLeft + 22, top: at(FLOORS, 0).y - 40 } }, (wst.staffK + 1 < 10 ? '0' : '') + (wst.staffK + 1) + ' / ' + seats.staffSeats.length));
    }
    if (id === 'pjangler') {
      var done = checklistDone(q);
      over.push(card([
        h('p', { key: 'h', className: 'eyebrow' }, b.copy.cardTitle),
        h('p', { key: 'n', className: 'caption-note' }, b.copy.cardNote)
      ].concat(b.copy.checklist.map(function (c, n) {
        return h('div', { key: n, className: 'check' + (n < done ? ' is-done' : '') }, h(O.Window, { state: n < done ? 'shipped' : 'dark' }), h('span', null, c));
      })), 'scard--list', 11));
    }
    if (id === 'gateway') {
      var gc = b.copy, dn = gc.decisions[decisionAt(q)], meters = gwMeters();
      over.push(card([
        h('div', { key: 'h', className: 'gw__head' }, h('span', { className: 'instrument gw__name' }, gc.cardTitle), h('span', { className: 'caption-note' }, gc.cardNote))
      ].concat(gc.pools.map(function (p, n) {
        var st = poolAt(n, q, gc.states), mt = meters[n];
        return h('div', { key: 'p' + n, className: 'gw__pool' + (st[0] === 'working' || st[0] === 'shipped' ? ' is-on' : st[0] === 'dark' ? ' is-out' : '') },
          h('div', { className: 'gw__poolhead' }, h(O.Window, { state: st[0] }), h('span', { className: 'instrument gw__poolname' }, p.name)),
          h('div', { className: 'gw__poolfoot' },
            h('span', { className: 'gw__meter', 'aria-hidden': 'true' }, h('i', { style: { '--from': mt.from, '--to': mt.to, '--a': mt.a, '--b': mt.b } })),
            h('span', { className: 'gw__state' }, st[1])));
      })).concat([
        h('div', { key: 'd' + decisionAt(q), className: 'gw__decision', role: 'status' }, h('span', { className: 'instrument-log gw__route' }, dn.route), h('span', null, dn.line)),
        h('p', Object.assign({ key: 'punch' }, rv(gwAt('switch') + 0.03, 'call__said gw__punch')), gc.punch),
        h('p', { key: 'stamp', className: 'caption-note gw__stamp' }, gc.stamp)
      ]), 'scard--list gw', null));
    }
    if (id === 'heyma') {
      var call = b.copy.call;
      over.push(card([
        h('div', { key: 'parts', className: 'parts' }, b.copy.parts.map(function (p) {
          return h('div', { key: p.name, className: 'parts__row' }, h('span', { className: 'instrument' }, p.name), h('span', null, p.line));
        })),
        h('p', { key: 'pn', className: 'caption-note' }, b.copy.partsNote),
        h('div', Object.assign({ key: 'call' }, rv(SC.beatQ('heyma', 'call', 'heard') - RV, 'call')),
          h('p', { className: 'eyebrow' }, call.label),
          h('p', { className: 'call__heard' }, call.heard),
          h('p', Object.assign({}, rv(SC.beatQ('heyma', 'call', 'translated') - RV, 'call__said')), call.translated)),
        h('div', Object.assign({ key: 'wh' }, rv(SC.beatQ('heyma', 'call', 'whisper') - RV, 'call')),
          h('p', { className: 'eyebrow' }, call.whisperLabel),
          h('p', { className: 'call__said' }, '“' + call.whisper + '”'))
      ], 'scard--list', null));
    }
    if (id === 'flume') {
      var stageN = SC.minor('flume', 'pipeline', q).step;
      over.push(card([
        h('p', { key: 'h', className: 'eyebrow' }, b.copy.rolesTitle)
      ].concat(b.copy.roles.map(function (r) {
        return h('div', { key: r.name, className: 'parts__row' }, h('span', { className: 'instrument' }, r.name), h('span', null, r.line));
      })).concat([
        h('div', { key: 'pipe', className: 'pipe' }, b.copy.pipeline.map(function (s, n) {
          return h('span', { key: s, className: 'instrument pipe__step' + (n < stageN ? ' is-done' : '') }, s);
        }))
      ]), 'scard--list', 12));
      if (q >= SC.range('flume', 'hire').from) {
        var hp = at(HIRE.f, HIRE.c);
        over.push(h('div', { key: 'hire', className: 'plate plate--right', style: { top: hp.y, left: hp.x + WIN_W * size.bs / 2 + 14, maxWidth: 220 } }, h(O.Nameplate, { name: b.copy.hire.name, line: b.copy.hire.line, state: SC.minor('flume', 'shipped', q).active ? 'shipped' : 'lit' })));
      }
    }
    if (hover && K0.s === 1 && K0.o === 1) {
      var hs = seats.byKey[hover];
      if (hs && (hs.name || hs.kind === 'you')) {
        var hidx = (floors - 1 - hs.f) * PER + hs.c;
        over.push(plate(hs.kind === 'you' ? { f: hs.f, c: hs.c, name: 'You', line: M.beats[I['org-chart']].copy.you.line } : hs, hs.kind === 'you' ? (wst.youLit ? 'you' : 'dark') : wst.states[hidx], 'hover', true));
      }
    }

    function onMove(e) {
      var K = camNow.current; if (K.s !== 1 || K.o < 1) { if (hover) setHover(null); return; }
      var r = sceneRef.current.getBoundingClientRect();
      var x = e.clientX - r.left - K.x * size.w, y = e.clientY - r.top - K.y * size.h;
      var c = Math.round(((x - size.w / 2) / size.bs + BW / 2 - PAD - WIN_W / 2) / PITCH_X);
      var f = Math.round(((size.h - GROUND - y) / size.bs - PAD - WIN_H / 2) / PITCH_Y);
      var k = c >= 0 && c < PER && f >= 0 && f < FLOORS ? f + ':' + c : null;
      if (k) { var p = at(f, c); if (Math.abs(p.x - x) > WIN_W * size.bs * 0.8 || Math.abs(p.y - y) > WIN_H * size.bs * 0.9) k = null; }
      if (k !== hover) setHover(k);
    }

    var sp = null;
    if (id === 'numbers') sp = h(Directory, { beat: b, width: Math.min(room, 400) });
    else if (id === 'org-chart') sp = h(OrgChart, { beat: b });
    else if (id === 'bus') sp = h(Bus, { beat: b, q: q });
    else if (id === 'layers') sp = h(Layers, { beat: b });
    else if (id === 'runs-on-itself') sp = h(Loop, { beat: b, q: q });
    else if (id === 'holocene-auto') sp = h(Car, { beat: b, q: q, M: M });

    var showGlass = pos.i >= I.transcript && pos.i <= I['pm-krebs'];
    var beaconOn = pos.i > I.pjangler ? pos.i < I['hired-well'] : pos.i === I.pjangler && checklistDone(q) >= 6;

    return h(React.Fragment, null,
      h('div', { id: 'top', className: 'track', ref: trackRef },
        h('div', { className: 'stage', ref: stageRef, 'data-beat': id, 'data-act': b.act },
          h('div', { className: 'sky', 'aria-hidden': 'true' }),
          h(Header, { M: M, view: view, jump: jump, jumpTo: jumpTo, toggleView: toggleView, clock: clock }),
          h('div', { className: 'stage__body' },
            h('div', { className: 'captions' + (id === 'premise' ? ' captions--hero' : ''), ref: capRef },
              h(BeatCaption, { key: id, beat: b, M: M, jumpTo: jumpTo, submitted: submitted, onSubmit: function () { setSubmitted(true); } })),
            h('div', { className: 'scene', ref: sceneRef, onMouseMove: onMove, onMouseLeave: function () { if (hover) setHover(null); } },
              h('div', { className: 'horizon', ref: horizonRef, 'aria-hidden': 'true' }),
              h('div', { className: 'world', ref: worldRef, style: { transformOrigin: waxAt.x + 'px ' + waxAt.y + 'px' } },
                h('div', { className: 'ground', 'aria-hidden': 'true' }),
                h('div', { className: 'bldg', style: { '--bs': size.bs } },
                  floors > FLOORS ? h('span', { className: 'beacon' + (beaconOn ? ' is-on' : ''), 'aria-hidden': 'true', style: { left: PAD + NEW_FLOOR.launch * PITCH_X + WIN_W / 2 } }) : null,
                  h(O.Building, { floors: floors, perFloor: PER, states: wst.states, you: wst.you, youLit: wst.youLit, size: 'lg', label: 'The company: a building of ' + floors + ' floors. Yours is the one window that stays dark.' }))),
              h('div', { className: 'overlay' + (hover ? ' is-hovering' : ''), ref: overlayRef }, over),
              showGlass ? h('div', { className: 'glass-wrap' }, h(Glass, { M: M, id: id, q: q, I: I, i: pos.i, glassRef: glassRef, origin: waxAt.x + 'px ' + waxAt.y + 'px', waxLine: seats.named.WAX.line })) : null,
              h('div', { className: 'sp-wrap', ref: spRef }, sp))),
          h('div', { className: 'interlude', ref: interRef, 'aria-hidden': b.interlude ? null : 'true' },
            b.interlude ? h('div', { className: 'interlude__in' },
              h('p', { className: 'eyebrow' }, fill(M, b.interlude.kicker)),
              h('p', { className: 'statement-act' }, b.interlude.line),
              b.interlude.sub ? h('p', { className: 'on-caption__kicker' }, b.interlude.sub) : null) : null),
          h(Gauge, { gaugeRef: gaugeRef, count: SC.stations.length, acts: beats.map(function (bb, n) { return bb.interlude ? n : -1; }), label: M.site.gauge }),
          h(Caret, { caretRef: caretRef, label: M.site.next, onNext: function () { if (dollyRef.current) dollyRef.current.step(1); } }),
          h('p', { className: 'crank' + (crank ? ' is-on' : ''), role: 'status' }, crank ? M.site.crank : ''))),
      h(Footer, { M: M }));
  }

  function Footer(props) {
    var f = props.M.site.footer;
    return h('footer', { className: 'foot' },
      h('div', { className: 'foot__in' },
        h('span', { className: 'foot__brand' }, h(Mark, { size: 20 }), h('span', { className: 'hud__name hud__name--sm' }, props.M.site.name), h('span', { className: 'hud__rule', 'aria-hidden': 'true' }),
          h('span', { className: 'hud__status' }, f.byline, ' · ', h('a', { href: f.link.href }, f.link.label))),
        props.M.site.viewSimulationHref ? h('a', { className: 'foot__sim', href: props.M.site.viewSimulationHref, target: '_blank', rel: 'noopener' }, props.M.site.viewSimulation) : null,
        h('span', { className: 'instrument-log foot__colophon' }, f.colophon)));
  }

  /* ---------- the log view: the same night, no camera ---------- */
  // Real moments from the replayed night between this beat's time and the next one's.
  function realLines(R, M, bt) {
    if (!R) return [];
    var NC = M.site.night || {};
    var n = M.beats.indexOf(bt), next = M.beats[n + 1];
    var a = nightMinute(R, mins(bt.time)), b = next ? nightMinute(R, mins(next.time)) : R.len;
    var names = {}; R.N.components.forEach(function (c) { names[c.id] = (NC.displayNames && NC.displayNames[c.name]) || c.name; });
    // Prefer what was rare tonight, then the first appearance of something routine; the night's first
    // minute catches every routine stream starting at once, so those only fill in when nothing else did.
    var picked = R.N.moments.filter(function (x) { return x.m >= a && x.m < Math.max(b, a + 1); })
      .map(function (x, k) { return { x: x, k: k, rank: !x.first_of ? 0 : x.m > 0 ? 1 : 2 }; })
      .sort(function (p, q) { return p.rank - q.rank || p.k - q.k; }).slice(0, 3)
      .sort(function (p, q) { return p.k - q.k; }).map(function (p) { return p.x; });
    return picked.map(function (x, k) {
      var note = (names[x.component] || x.component) + (x.first_of ? ' · ' + (NC.firstOf || 'first of {n} tonight').replace('{n}', x.first_of.toLocaleString('en-US')) : '');
      return h('div', { key: bt.id + 'real' + k, className: 'logline--real' }, h(O.LogLine, { time: fmt(R.start + x.m), subject: x.type, note: note }));
    });
  }
  // The long form of a beat's list entries, in full: the log view has no hover, so this is also the accessible path to them.
  // Any list in the beat's copy whose items are objects and at least one carries a `detail` is listed, entry by entry.
  function detailRows(bt) {
    var copy = bt.copy || {}, out = [];
    Object.keys(copy).forEach(function (k) {
      var a = copy[k];
      if (!Array.isArray(a) || !a.length || !a.some(function (e) { return e && typeof e === 'object' && detailOf(e); })) return;
      out.push(h('dl', { key: bt.id + ':' + k, className: 'logview__detail', 'aria-label': bt.kicker || bt.title },
        a.map(function (e, n) {
          if (!e || typeof e !== 'object') return null;
          return h(React.Fragment, { key: n },
            h('dt', { className: 'instrument' }, e.name || e.n),
            h('dd', null, e.line || e.label, detailOf(e) ? h('span', { className: 'logview__more' }, detailOf(e)) : null));
        })));
    });
    return out;
  }
  function LogView(props) {
    var M = props.M, first = M.beats[0], ask = M.beats[props.I.ask];
    var acts = Object.keys(M.acts);
    return h('div', { className: 'logview' },
      h(Header, { M: M, view: 'log', jump: function () { window.scrollTo(0, 0); }, jumpTo: function () {}, toggleView: props.toggleView, clock: h(O.Clock, { time: first.time + ' → ' + ask.time, staged: true, stagedLabel: props.night && M.site.night ? M.site.night.label.replace('{label}', props.night.label) : M.site.stagedLabel }) }),
      h('main', { id: 'log', className: 'logview__main' },
        h('p', { className: 'eyebrow' }, first.kicker),
        h('h1', { className: 'statement-act' }, first.title + ' ', h('span', { className: 'statement-hero__turn' }, first.titleTurn)),
        h('p', { className: 'cap__lede' }, M.site.logLead),
        props.night && M.site.night ? h('p', { className: 'caption-note logview__real' }, M.site.night.logNote.replace('{label}', props.night.label)) : null,
        acts.map(function (a) {
          return h('section', { key: a, className: 'logview__act' },
            h('h2', { className: 'instrument' }, 'Act ' + a + ' · ' + M.acts[a]),
            M.beats.filter(function (bt) { return bt.act === a; }).map(function (bt) {
              var staged = (bt.log || []).map(function (l, n) { return h(O.LogLine, { key: bt.id + n, time: bt.time, subject: l.subject, note: l.note }); });
              return staged.concat(detailRows(bt), realLines(props.night, M, bt));
            }));
        }),
        h('section', { className: 'logview__ask' },
          h('div', { className: 'logview__you' }, h(O.Window, { state: props.submitted ? 'you' : 'dark', size: 'lg', label: props.submitted ? 'Your window, lit' : 'Your window, dark' })),
          h(O.Caption, { beat: { title: ask.title, body: ask.body }, as: 'h2' }),
          h(Ask, { id: 'ask-email-log', copy: ask.copy, submitted: props.submitted, onSubmit: props.onSubmit }))),
      h(Footer, { M: M }));
  }

  /* ---------- boot ---------- */
  function boot(M, R) {
    var colors = { sky1802: cssVar('--sky-1802'), sky2200: cssVar('--sky-2200'), sky0200: cssVar('--sky-0200'), sky0500: cssVar('--sky-0500'), sky0630: cssVar('--sky-0630'), sky0730: cssVar('--sky-0730') };
    var root = document.getElementById('root');
    root.textContent = '';
    ReactDOM.createRoot(root).render(h(Boundary, null, h(App, { M: M, colors: colors, night: R })));
  }
  // The score's majors are the manifest's beats, in order; counts the minors step through live in the copy.
  function scoreFor(M, spec) {
    var ids = spec.majors.map(function (m) { return m.id; }).join(','), want = M.beats.map(function (b) { return b.id; }).join(',');
    if (ids !== want) {
      var a = spec.majors.map(function (m) { return m.id; }), b = M.beats.map(function (x) { return x.id; });
      var k = 0; while (k < a.length && k < b.length && a[k] === b[k]) k++;
      throw new Error('score.json majors do not match the manifest beats: beat ' + (k + 1) + ' is ' + (b[k] || '(none)') + ' in the manifest but ' + (a[k] || '(none)') + ' in score.json. Majors: ' + ids + '. Beats: ' + want + '.');
    }
    var B = {}; M.beats.forEach(function (b) { B[b.id] = b; });
    // An act statement lives in the manifest (the words) and the score (its `in`): they must agree.
    spec.majors.forEach(function (m) { if (!!B[m.id].interlude !== !!(m['in'] && m['in'].len)) throw new Error('score.json: ' + m.id + (B[m.id].interlude ? ' opens an act in the manifest but has no "in" in the score' : ' has an "in" but no act statement in the manifest')); });
    var T = M.transcript;
    // ?pace=0.25 plays every move four times faster (authoring and tests); anything else is the score's own pace.
    var ps = parseFloat(new URLSearchParams(location.search).get('pace'));
    var score = window.Score.compile(spec, { paceScale: ps > 0 ? ps : 1, vars: {
      staff: B.staff.copy.staff.length, loop: B['runs-on-itself'].copy.steps.length, checklist: B.pjangler.copy.checklist.length,
      pipeline: B.flume.copy.pipeline.length, standup: B['holocene-auto'].copy.standup.length,
      speakers: T.speakers.length, judgments: T.judgments.length, tickets: T.tickets.length
    } });
    score.layout(window.innerHeight);   // set pieces read minors on their first render, before the film measures
    return score;
  }
  /* ---------- the guard: a manifest that does not read says why, where, and how to fix it ---------- */
  // A JSON parse failure with the file, the message, the line and column, and the offending lines with a caret.
  function parseFailure(src, text, e) {
    var msg = String(e && e.message || e), line = null, col = null, m;
    if ((m = /\(line (\d+) column (\d+)\)/.exec(msg)) || (m = /line (\d+) column (\d+)/.exec(msg))) { line = +m[1]; col = +m[2]; }
    else if ((m = /position (\d+)/.exec(msg))) {
      var before = text.slice(0, +m[1]).split('\n'); line = before.length; col = before[before.length - 1].length + 1;
    }
    var excerpt = '';
    if (line) {
      var rows = text.split('\n'), from = Math.max(1, line - 1), to = Math.min(rows.length, line + 1), w = String(to).length;
      for (var n = from; n <= to; n++) {
        var row = rows[n - 1]; if (row.length > 160) row = row.slice(Math.max(0, col - 60), col + 90);
        excerpt += ('      ' + n).slice(-w) + ' | ' + row + '\n';
        if (n === line) excerpt += new Array(w + 3 + (rows[n - 1].length > 160 ? Math.min(col, 60) : col)).join(' ') + '^\n';
      }
    }
    var hint = /escape/i.test(msg) ? 'A backslash in a string must be \\\\, \\", \\n, \\t or \\uXXXX. A stray \\. or \\\' is what blanked the page once already.' :
      /Unexpected token|Expected/i.test(msg) ? 'Look just before the caret for a missing comma, a stray quote or an unclosed bracket.' : '';
    msg = msg.replace(/\s*\(line \d+ column \d+\)/, '').replace(/ at position \d+/, '');
    var err = new Error(src + ' does not parse: ' + msg);
    err.panel = { file: src, title: src + ' does not parse', message: msg, line: line, col: col, excerpt: excerpt, hint: hint };
    return err;
  }
  function FailPanel(props) {
    var err = props.err || {}, P = err.panel || { title: 'The scene does not match', message: String(err.message || err), excerpt: '', hint: '' };
    return h('main', { className: 'fail', role: 'alert' },
      h('p', { className: 'eyebrow' }, 'The page could not read its words'),
      h('h1', null, P.title),
      h('p', null, P.message + (P.line ? ' (line ' + P.line + (P.col ? ', column ' + P.col : '') + ')' : '')),
      P.excerpt ? h('pre', { className: 'fail__src' }, P.excerpt) : null,
      P.hint ? h('p', null, P.hint) : null,
      h('p', { className: 'caption-note' }, 'Fix the file and refresh. Saving it publishes it; the page re-reads it every time.'));
  }
  // A manifest that parses but has the wrong shape throws while rendering: show the panel, not a blank page.
  function Boundary(p) { React.Component.call(this, p); this.state = { err: null }; }
  Boundary.prototype = Object.create(React.Component.prototype);
  Boundary.prototype.constructor = Boundary;
  Boundary.getDerivedStateFromError = function (e) { return { err: e }; };
  Boundary.prototype.componentDidCatch = function (e) { console.error('Overnight:', e); };
  Boundary.prototype.render = function () { return this.state.err ? h(FailPanel, { err: this.state.err }) : this.props.children; };
  function renderFail(err) {
    var root = document.getElementById('root');
    console.error('Overnight:', err);
    root.textContent = '';
    try { ReactDOM.createRoot(root).render(h(FailPanel, { err: err })); }
    catch (e) { var p = document.createElement('p'); p.className = 'noscript'; p.textContent = 'The scene manifest did not load (' + err.message + ').'; root.appendChild(p); }
  }
  function getJSON(src) {
    return fetch(src, { cache: 'no-cache' })
      .then(function (r) { if (!r.ok) throw new Error(src + ': ' + r.status); return r.text(); })
      .then(function (text) { try { return JSON.parse(text); } catch (e) { throw parseFailure(src, text, e); } });
  }
  Promise.all([getJSON('manifest.json'), getJSON('score.json')])
    .then(function (both) {
      var M = both[0];
      SC = scoreFor(M, both[1]);
      // ?night=YYYY-MM-DD replays another night; ?night=staged turns the replay off.
      var want = new URLSearchParams(location.search).get('night');
      var src = want === 'staged' ? null : want ? 'nights/' + want.replace(/[^0-9-]/g, '') + '.json' : (M.site.night && M.site.night.src);
      if (!src) return boot(M, null);
      return fetch(src, { cache: 'no-cache' })
        .then(function (r) { if (!r.ok) throw new Error(src + ': ' + r.status); return r.json(); })
        .then(function (N) {
          if (!N || N.format !== '33god.night') throw new Error(src + ': not a 33god.night file');
          boot(M, prepNight(N, M.beats.map(function (b) { return mins(b.time); })));
        })
        .catch(function (err) { console.warn('Overnight: no real night, staging instead.', err); boot(M, null); });
    })
    .catch(renderFail);
})();
