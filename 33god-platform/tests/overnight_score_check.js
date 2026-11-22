// Checks for score.js's stepping model, against the real score.json and manifest.json. Plain node, no dependencies.
//
//   node tests/overnight_score_check.js            # exits 1 and says what broke
//   node tests/overnight_score_check.js --json     # the move table: { vh: { stations, forwardMs, total } }
//
// Run by tests/test_overnight_site.py (test_score_stations_node), skipped when node is missing.
'use strict';
const fs = require('fs');
const path = require('path');
const site = process.env.OVERNIGHT_SITE || path.join(__dirname, '..', 'overnight', 'site');

global.window = {};
new Function(fs.readFileSync(path.join(site, 'score.js'), 'utf8'))();
const Score = window.Score;
const spec = JSON.parse(fs.readFileSync(path.join(site, 'score.json'), 'utf8'));
const M = JSON.parse(fs.readFileSync(path.join(site, 'manifest.json'), 'utf8'));
const B = {}; M.beats.forEach(b => { B[b.id] = b; });
const T = M.transcript;
// The same counts overnight.js's scoreFor reads out of the copy.
const vars = {
  staff: B.staff.copy.staff.length, loop: B['runs-on-itself'].copy.steps.length, checklist: B.pjangler.copy.checklist.length,
  pipeline: B.flume.copy.pipeline.length, standup: B['holocene-auto'].copy.standup.length,
  speakers: T.speakers.length, judgments: T.judgments.length, tickets: T.tickets.length
};

const fails = [];
function check(ok, msg) { if (!ok) fails.push(msg); }
const TOTAL_MS = 158000;   // documented in README "The pace": the whole tour, 21 presses, at the default pace

const table = {};
[720, 860, 1080].forEach(vh => {
  const tag = vh + 'px: ';
  const S = Score.compile(spec, { vars: vars }); S.layout(vh);
  const st = S.stations, N = S.majors.length;
  check(st.length === N + 1, tag + 'stations are the top plus one per major, got ' + st.length + ' for ' + N);
  check(st[0] === 0, tag + 'the first station is the top');
  for (let k = 0; k < st.length; k++) {
    if (k > 0) check(st[k] > st[k - 1], tag + 'stations must strictly increase at ' + k);
    if (k > 0) check(Math.abs(st[k] - S.majors[k - 1].bodyEnd) < 1e-6, tag + 'station ' + k + ' must be ' + S.majors[k - 1].id + '.bodyEnd');
    S.glides.forEach(g => check(!(st[k] > g.from + 1 && st[k] < g.to - 1), tag + 'station ' + k + ' sits inside the ' + g.kind + ' seam of ' + g.major));
  }
  // Minors are no seams and no stops.
  check(S.glides.every(g => g.kind === 'out' || g.kind === 'in'), tag + 'only camera travels and act handovers are seams');
  const total = S.total;

  // Moves.
  const fwd = [];
  for (let k = 0; k < N; k++) {
    const f = S.move(st[k], 1), b = S.move(st[k + 1] + 1, -1);
    check(f && f.station === k + 1 && f.kind === 'forward', tag + 'forward from ' + k + ' goes to ' + (k + 1));
    check(b && b.station === k && b.kind === 'back', tag + 'back from ' + (k + 1) + ' goes to ' + k);
    if (!f || !b) continue;
    fwd.push(f.ms);
    [f, b].forEach(m => {
      check(m.ms >= spec.pace.min && m.ms <= 40000, tag + m.kind + ' move ' + k + ' takes ' + Math.round(m.ms) + 'ms, outside [' + spec.pace.min + ', 40000]');
      check(Math.abs(m.ease(0)) < 1e-9 && Math.abs(m.ease(1) - 1) < 1e-9, tag + m.kind + ' move ' + k + ' ease must run 0 to 1');
      let prev = 0, mono = true, vmax = 0;
      for (let i = 1; i <= 400; i++) { const e = m.ease(i / 400); if (e < prev - 1e-9) mono = false; vmax = Math.max(vmax, (e - prev) * 400); prev = e; }
      check(mono, tag + m.kind + ' move ' + k + ' ease must be monotone');
      // starts and ends at rest: in the first and last 25ms the film covers a small part of what the average speed would
      const eps = 25 / m.ms, v0 = m.ease(eps) / eps, v1 = (1 - m.ease(1 - eps)) / eps;
      check(v0 < 0.3 && v1 < 0.3, tag + m.kind + ' move ' + k + ' must start and end at rest (speed over the first and last 25ms, in averages: ' + v0.toFixed(2) + ', ' + v1.toFixed(2) + ')');
      check(Math.abs(m.to - Math.ceil(st[m.station])) < 1e-9, tag + m.kind + ' move ' + k + ' must land on its station');
    });
    // An act statement's hold is a plateau; nothing else is.
    const act = !!B[S.majors[k].id].interlude;
    const holdMs = S.majors[k].hold || 0;
    if (act && holdMs > 0) {
      const w = 0.5 * holdMs / f.ms; let low = 1;
      for (let u = 0; u + w <= 1; u += 0.01) low = Math.min(low, f.ease(u + w) - f.ease(u));
      check(low < 0.03, tag + S.majors[k].id + ' opens an act: its move must hold on the statement (least progress over half the hold: ' + low.toFixed(3) + ')');
    }
  }
  const holds = S.timeline.filter(s => s.kind === 'hold');
  check(holds.every(h => B[h.major].interlude), tag + 'only a major that opens an act may hold');
  check(holds.length === M.beats.filter(b => b.interlude).length, tag + 'every act holds once, got ' + holds.length);
  const sum = fwd.reduce((a, b) => a + b, 0);
  check(Math.abs(sum / TOTAL_MS - 1) < 0.25, tag + 'the tour takes ' + Math.round(sum / 1000) + 's, documented as ' + TOTAL_MS / 1000 + 's +-25%');
  table[vh] = { stations: st, forwardMs: fwd.map(Math.round), total: Math.round(sum) };

  // A move from the middle of a body plays the rest of it, starting at rest.
  const mid = (st[3] + st[4]) / 2, part = S.move(mid, 1);
  check(part && part.station === 4 && part.ms >= spec.pace.min && part.ms < fwd[3], tag + 'a move from mid-section is shorter than the whole one');
  check(S.move(total + 400, 1) === null, tag + 'there is no move past the last station');
  const up = S.move(total + 400, -1);
  check(up && up.station === N, tag + 'Up from the footer goes to the last station');
  check(S.move(0, -1) === null, tag + 'there is no move before the top');
  check(S.move(st[1] + 2, 1).station === 2, tag + 'a few px past a station counts as being on it');
  check(S.move(st[1] + 2, -1, { turn: true }).station === 1, tag + 'a turn-around goes back to the station it left');

  // where(): the elevator.
  check(S.where(0).progress === 0 && S.where(0).station === 0, tag + 'where(0) is the top');
  check(S.where(total).progress === 1 && S.where(total).last === N && !S.where(total).hasNext, tag + 'where(total) is the ground');
  let pp = -1, mono = true;
  for (let y = 0; y <= total + 10; y += 3) { const p = S.where(y).progress; if (p < pp - 1e-9) mono = false; pp = p; }
  check(mono, tag + 'progress must never go backwards');
  for (let k = 0; k < st.length; k++) check(S.where(st[k]).station === k && Math.abs(S.where(st[k]).progress - k / N) < 1e-9, tag + 'where(station ' + k + ') must be station ' + k + ', k/N');
  check(S.where((st[2] + st[3]) / 2).station === -1, tag + 'between stations is no station');

  // watch(): ready is "this section is done and there is a next one", never while moving.
  const seen = [];
  const tell = Score.watch(S, s => seen.push(s));
  for (let k = 0; k < st.length; k++) {
    seen.length = 0; tell(st[k] + (k ? 1 : 0), { moving: true });
    tell(st[k] + (k ? 1 : 0), { moving: false });
    const last = seen[seen.length - 1];
    check(last && last.at && last.station === k && last.ready === (k < N), tag + 'at station ' + k + ' the caret is ' + (k < N ? 'ready' : 'hidden') + ', got ' + JSON.stringify(last));
    check(seen.every(s => !(s.moving && s.ready)), tag + 'ready while moving at station ' + k);
  }
  seen.length = 0; tell((st[2] + st[3]) / 2, { moving: false });
  check(seen.length && !seen[seen.length - 1].ready, tag + 'resting between stations is not "done"');
  const n0 = seen.length; tell((st[2] + st[3]) / 2, { moving: false }); check(seen.length === n0, tag + 'watch only fires on change');

  // The perStep floor: a stepped minor never gets less than steps x perStep ms.
  S.majors.forEach(m => m.minors.forEach(mn => {
    if (!mn.pace || !mn.steps) return;
    let ms = 0; S.timeline.forEach(s => { if (s.kind === 'body' && s.major === m.id && s.y0 >= mn.a - 0.5 && s.y1 <= mn.z + 0.5) ms += s.ms; });
    check(ms + 1 >= mn.steps * m.perStep, tag + m.id + '/' + mn.id + ' gets ' + Math.round(ms) + 'ms for ' + mn.steps + ' steps: under ' + m.perStep + 'ms each');
  }));
});

// A paceScale scales every ms.
{
  const S = Score.compile(spec, { vars: vars, paceScale: 0.2 }); S.layout(860);
  let sum = 0; for (let k = 0; k < S.stations.length - 1; k++) sum += S.move(S.stations[k], 1).ms;
  check(sum > TOTAL_MS * 0.2 * 0.7 && sum < TOTAL_MS * 0.2 * 1.3, 'paceScale 0.2 gives ' + Math.round(sum) + 'ms for the tour');
}

// Bad pace fields say which one.
function bad(mut, re) {
  const s = JSON.parse(JSON.stringify(spec)); mut(s);
  try { Score.compile(s, { vars: vars }).layout(860); check(false, 'a bad score was accepted: ' + re); }
  catch (e) { check(re.test(e.message), 'wrong error for ' + re + ': ' + e.message); }
}
bad(s => { s.pace.bogus = 1; }, /pace\.bogus/);
bad(s => { s.majors[3].body.play = ['80%', '20%']; }, /org-chart\.body\.play/);
bad(s => { s.majors[1].body.ms = -5; }, /thesis\.body\.ms/);
bad(s => { s.majors.find(m => m.id === 'staff').minors[0].dwell = 2; }, /staff\/roll\.dwell/);

if (process.argv.includes('--json')) { console.log(JSON.stringify(table)); process.exit(fails.length ? 1 : 0); }
if (fails.length) { console.error(fails.slice(0, 40).join('\n')); process.exit(1); }
console.log('ok: ' + Object.keys(table).length + ' viewports, ' + Object.values(table)[0].stations.length + ' stations, the tour takes ' + Math.round(table[860].total / 1000) + 's');
