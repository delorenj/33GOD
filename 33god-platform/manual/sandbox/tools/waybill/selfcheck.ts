// Self-check for the pure parts (types, stations, director). No test framework:
//   node --import ./tools/waybill/register.mjs --experimental-strip-types tools/waybill/selfcheck.ts [file.waybill.json ...]
// With no file it checks every sample listed in public/waybills/index.json. Add --captions to print copy.
import { readFileSync } from 'node:fs'
import { gunzipSync } from 'node:zlib'
import { direct, readerGroups } from '../../src/waybill/director'
import { lineId, narrationFor, speakable } from '../../src/waybill/narration'
import { place, stationOf } from '../../src/waybill/stations'
import { normalize, parseWaybill } from '../../src/waybill/types'

let bad = 0
const ok = (cond: unknown, msg: string) => { if (!cond) { bad++; console.log('FAIL ' + msg) } else console.log('ok   ' + msg) }
const args = process.argv.slice(2)
const captions = args.includes('--captions')
let files = args.filter((a) => !a.startsWith('--'))
if (!files.length) {
  const idx = JSON.parse(readFileSync('public/waybills/index.json', 'utf8')) as { samples: { file: string }[] }
  files = idx.samples.map((s) => `public/waybills/${s.file}`)
}

// the tolerant reader
ok(!normalize({ format: '33god.waybill', version: 2 }).ok, 'rejects an unknown major version')
ok(!normalize({ format: 'nope', version: 1 }).ok, 'rejects a wrong format')
ok(!parseWaybill('{not json').ok, 'rejects bad JSON with a message')
const bare = normalize({ format: '33god.waybill', version: 1, spans: [{ id: 'a', kind: 'wibble', component: 'zz', t0: 5 }] })
ok(bare.ok && bare.waybill.spans[0].kind === 'wibble' && Array.isArray(bare.waybill.events) && !!bare.waybill.components.zz, 'defaults missing arrays, keeps unknown kinds, adds missing components')
if (bare.ok) {
  const d = direct(bare.waybill)
  ok(d.stops.some((s) => s.set === 'kiosk:zz'), 'an unknown kind on an unknown component lands on a kiosk')
}
ok(speakable('Read ×2 took 5.00 s (cached) → claude-opus-5-5 at 8.4k: SessionStart') === 'Read, twice took 5 seconds, cached, to Claude Opus 5 point 5 at 8.4 thousand, Session Start', 'speakable() turns HUD shorthand into words')
const rg = readerGroups([
  { name: 'bloodbank-ntfy-router', component: 'ntfy-router', kind: 'core', filter: null, outcome: 'unknown', evidence: 'inferred' },
  { name: 'ntfy-router', component: 'ntfy-router', kind: 'core', filter: null, outcome: 'routed', evidence: 'observed', t: 4 },
  ...Array.from({ length: 30 }, (_, i) => ({ name: `inf-${i}`, component: `svc-${i % 3}`, kind: 'durable' as const, filter: null, outcome: 'unknown' as const, evidence: 'inferred' as const })),
], (c) => c)
ok(rg.length === 4 && rg[0].component === 'ntfy-router' && rg[0].observed === 1 && rg[0].outcome === 'routed', 'readers group by component, observed first, one row per component')

for (const file of files) {
  console.log(`\n=== ${file}`)
  // a .waybill.json.gz (or any file that starts with the gzip magic bytes) is inflated first, like the player's loader does
  const raw = readFileSync(file)
  const text = raw[0] === 0x1f && raw[1] === 0x8b ? gunzipSync(raw).toString('utf8') : raw.toString('utf8')
  const t0 = performance.now()
  const r = parseWaybill(text)
  const tParse = performance.now() - t0
  ok(r.ok, `parses ${file}`)
  if (!r.ok) { console.log(r.error); continue }
  const w = r.waybill

  const a = JSON.stringify(place(w)), b = JSON.stringify(place(w))
  ok(a === b, 'place() is deterministic')
  const pl = place(w)
  ok(pl.setOf['hook-hub'] === 'dock' && (pl.setOf['bb-hook'] ?? 'courier') === 'courier' && pl.setOf['candystore'] === 'archive', 'registry stations map')
  const unplaced = Object.keys(w.components).filter((id) => !stationOf(id) && !pl.kioskById[id])
  ok(unplaced.length === 0, `every unmapped component has a kiosk${unplaced.length ? ' (missing: ' + unplaced.join(', ') + ')' : ''}`)

  const t1 = performance.now()
  const d = direct(w, pl)
  const tDir = performance.now() - t1
  ok(direct(w) === direct(w), 'direct() is memoized per waybill')
  const d2 = direct(w, place(w))
  ok(JSON.stringify(d.stops) === JSON.stringify(d2.stops), 'direct() is deterministic')
  ok(tDir < 400, `direct() is fast (${tDir.toFixed(0)} ms for ${w.spans.length} spans, parse ${tParse.toFixed(0)} ms)`)
  const kinds = d.stops.map((s) => s.kind)
  const lines = d.stops.map(narrationFor)
  ok(lines.every((l) => l.length > 10 && !l.startsWith('(') && !/[“”→×]/.test(l)), 'every stop has a speakable narration line (no stage-direction parenthesis, no arrows or quotes)')
  ok(lines.every((l) => lineId(l) === lineId(l) && /^wbn-[a-z0-9]+$/.test(lineId(l))), 'narration ids are stable content hashes')
  ok(kinds[0] === 'prompt' && kinds[kinds.length - 1] === 'end', 'starts at the prompt, ends at "what did not happen"')
  const docks = d.stops.filter((s) => s.kind === 'dock')
  ok(docks.length > 0 && docks.every((s) => s.cards !== undefined), 'hooks become dock stops with job cards')
  ok(docks.every((s) => s.spanIds.filter((id) => id.startsWith('hook:') && !/transition/.test(w.spans.find((x) => x.id === id)?.name ?? '')).length === 1), 'one native hook per dock stop')
  const loops = d.stops.filter((s) => s.kind === 'loop')
  ok(loops.every((l) => l.tools!.reduce((n, t) => n + t.count, 0) === l.spanIds.filter((id) => id.startsWith('tool:')).length), 'every tool-loop round counts the tools in it')
  ok(loops.every((l) => l.tools!.reduce((n, t) => n + t.count, 0) <= 6 || !l.part), 'a split tool loop has at most 6 tool calls per round')
  ok(loops.every((l, i) => !l.part || (l.part.of === loops.filter((x) => x.part).length && l.part.n >= 1)), 'round numbers agree with the number of rounds')
  ok(d.stops.every((s) => s.kind === 'end' || s.hero === 'none' || !!s.heroLabel?.real), 'every stop with a hero has a hero label')
  ok(d.stops.every((s) => s.kind !== 'briefing' || (s.travel && s.travel.from !== s.travel.to)), 'a briefing card travels between two stations')
  ok(!d.stops.some((s) => /\+-/.test(s.caption + s.detail + s.tag + s.notes.join(' '))), 'no doubled signs (+-) in the copy')
  const tools = w.spans.filter((s) => s.kind === 'tool').length
  const inLoops = d.stops.filter((s) => s.kind === 'loop' || s.kind === 'crew').reduce((n, s) => n + (s.tools?.reduce((m, t) => m + t.count, 0) ?? 0), 0)
  ok(inLoops === tools, `every tool call sits in the loop or a crew stop (${inLoops}/${tools})`)
  ok(kinds.filter((k) => k === 'courier').length <= 1, 'at most one courier')
  const seen = new Set(d.stops.flatMap((s) => s.spanIds))
  const lost = w.spans.filter((s) => s.kind !== 'turn' && !seen.has(s.id)).map((s) => s.id)
  ok(lost.length === 0, `every span is in a stop${lost.length ? ' (missing: ' + lost.slice(0, 5).join(', ') + ')' : ''}`)
  const seenE = new Set(d.stops.flatMap((s) => s.eventIds))
  const lostE = w.events.filter((e) => !seenE.has(e.id)).map((e) => e.type)
  ok(lostE.length === 0, `every event is in a stop${lostE.length ? ' (missing: ' + lostE.join(', ') + ')' : ''}`)
  const dupS = d.stops.flatMap((s) => s.spanIds).length - seen.size
  ok(dupS === 0, 'no span is in two stops')
  const end = d.stops[d.stops.length - 1]
  ok(end.notes.length === w.findings.length + w.gaps.length, 'end stop lists every finding and gap')
  ok(new Set(d.stops.map((s) => s.id)).size === d.stops.length, 'stop ids are unique')
  ok(d.stops.every((s) => s.t1 >= s.t0 && s.title && s.caption), 'stops have sane times and copy')
  ok(d.stops.every((s) => !/undefined|NaN|\[object/.test(s.title + s.caption + s.detail + s.tag)), 'no undefined/NaN in the copy')
  ok(d.stops.length <= 60, `a watchable number of stops (${d.stops.length})`)
  const hold = d.stops.filter((s) => s.kind !== 'end').length

  console.log(`\nstops (${hold} + end):`)
  d.stops.forEach((s, i) => {
    console.log(`${String(i + 1).padStart(2)}. [${s.kind}] ${s.set} ${Math.round(s.t0)}..${Math.round(s.t1)} ${s.waited ? 'WAIT ' + Math.round(s.waitedMs) + 'ms' : 'side'} | ${s.title}`)
    if (captions) { console.log(`      ${s.caption}`); if (s.detail) console.log(`      · ${s.detail}`); if (s.tag) console.log(`      # ${s.tag}`) }
  })
}
console.log(bad ? `\n${bad} check(s) failed` : '\nall checks passed')
process.exit(bad ? 1 : 0)
