// Self-check for the pure parts (types, stations, director). No test framework:
//   node --import ./tools/waybill/register.mjs --experimental-strip-types tools/waybill/selfcheck.ts [file.waybill.json ...]
// With no file it checks every sample listed in public/waybills/index.json, and the real-shaped night kept next to
// this script (tools/waybill/real-last-night.waybill.json.gz: a public-profile build of a real 81,003-event night, so the
// director is held to data that has failures in every chapter, hundreds of pallets and tool, model and hook spans).
// Every file is also validated against waybill/schema/waybill.v1.schema.json. Add --captions to print copy.
import { existsSync, readFileSync } from 'node:fs'
import { gunzipSync } from 'node:zlib'
import Ajv2020 from 'ajv/dist/2020.js'
import { direct, readerGroups } from '../../src/waybill/director'
import { lineId, narrationFor, speakable } from '../../src/waybill/narration'
import { place, stationOf } from '../../src/waybill/stations'
import { isQuery, normalize, parseWaybill, type Waybill } from '../../src/waybill/types'
import { isDeadLetter, MAX_STOPS, PER_CHAPTER } from '../../src/waybill/query'

let bad = 0
const ok = (cond: unknown, msg: string) => { if (!cond) { bad++; console.log('FAIL ' + msg) } else console.log('ok   ' + msg) }
const args = process.argv.slice(2)
const captions = args.includes('--captions')
let files = args.filter((a) => !a.startsWith('--'))
if (!files.length) {
  const idx = JSON.parse(readFileSync('public/waybills/index.json', 'utf8')) as { samples: { file: string }[] }
  files = idx.samples.map((s) => `public/waybills/${s.file}`)
  if (existsSync('tools/waybill/real-last-night.waybill.json.gz')) files.push('tools/waybill/real-last-night.waybill.json.gz')
}
const ajv = new Ajv2020({ strict: false, allErrors: false, validateFormats: false })
const validateWaybill = ajv.compile(JSON.parse(readFileSync('../../waybill/schema/waybill.v1.schema.json', 'utf8')))

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
  const okSchema = validateWaybill(JSON.parse(text))
  ok(okSchema, `${file} validates against waybill.v1.schema.json${okSchema ? '' : ': ' + ajv.errorsText(validateWaybill.errors?.slice(0, 3))}`)
  const w = r.waybill

  const a = JSON.stringify(place(w)), b = JSON.stringify(place(w))
  ok(a === b, 'place() is deterministic')
  const pl = place(w)
  // a file that never names hook-hub (a query of one component, a night without agents) has no dock to check
  ok((!('hook-hub' in w.components) || pl.setOf['hook-hub'] === 'dock') && (pl.setOf['bb-hook'] ?? 'courier') === 'courier' && (!('candystore' in w.components) || pl.setOf['candystore'] === 'archive'), 'registry stations map')
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
  const q = isQuery(w)
  if (q) queryChecks(w, d)
  // the capture-only checks: a query has no dock hooks, tool loops, courier or briefing
  const docks = q ? [] : d.stops.filter((s) => s.kind === 'dock')
  ok(q || docks.length > 0 && docks.every((s) => s.cards !== undefined), 'hooks become dock stops with job cards')
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
  ok(q || inLoops === tools, `every tool call sits in the loop or a crew stop (${inLoops}/${tools})`)
  ok(kinds.filter((k) => k === 'courier').length <= (q ? 0 : 1), 'at most one courier')
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
  if (q) ok(end.title === (d.query!.conservation.ok ? 'What did not happen' : 'What did not add up') && /accounted for|do not add up/.test(end.caption), 'the end card states the conservation sum')
  ok(new Set(d.stops.map((s) => s.id)).size === d.stops.length, 'stop ids are unique')
  ok(d.stops.every((s) => s.t1 >= s.t0 && s.title && s.caption), 'stops have sane times and copy')
  ok(d.stops.every((s) => !/undefined|NaN|\[object/.test(s.title + s.caption + s.detail + s.tag)), 'no undefined/NaN in the copy')
  ok(d.stops.length <= MAX_STOPS, `a watchable number of stops (${d.stops.length})`)
  const hold = d.stops.filter((s) => s.kind !== 'end').length

  console.log(`\nstops (${hold} + end):`)
  d.stops.forEach((s, i) => {
    console.log(`${String(i + 1).padStart(2)}. [${s.kind}] ${s.set} ${Math.round(s.t0)}..${Math.round(s.t1)} ${s.waited ? 'WAIT ' + Math.round(s.waitedMs) + 'ms' : 'side'} | ${s.title}`)
    if (captions) { console.log(`      ${s.caption}`); if (s.detail) console.log(`      · ${s.detail}`); if (s.tag) console.log(`      # ${s.tag}`) }
  })
}
// ---- query mode: the director's promises, and the 100k-event night ----
function queryChecks(w: Waybill, d: ReturnType<typeof direct>) {
  const qd = d.query
  ok(!!qd, 'a query waybill is directed in query mode')
  if (!qd) return
  const first = d.stops[0]
  ok(first.kind === 'prompt' && first.set === 'archive' && /^You asked the archive: /.test(first.title), 'opens at the archive with "You asked the archive: <label>"')
  const nums = d.stops.map((s) => s.chapter?.n ?? 0).filter((n) => n > 0)
  ok(nums.every((n, i) => i === 0 || n >= nums[i - 1]), 'chapters are walked in order')
  const per = new Map<number, number>()
  for (const s of d.stops) if (s.chapter) per.set(s.chapter.n, (per.get(s.chapter.n) ?? 0) + 1)
  ok([...per.values()].every((n) => n <= PER_CHAPTER) && per.size === qd.chapters.length, `at most ${PER_CHAPTER} stops per chapter, every chapter visited (${qd.chapters.length} chapters)`)
  const returned = d.stops.filter((s) => s.kind === 'returned')
  const inReturned = new Set(returned.flatMap((s) => s.eventIds))
  const dead = w.events.filter(isDeadLetter)
  ok(dead.length === qd.conservation.dead && dead.every((e) => inReturned.has(e.id)) && returned.every((s) => s.set === 'archive' && s.returned && s.returned.count === s.eventIds.length), `every dead letter is in a returned-mail stop at the archive (${dead.length})`)
  const problems = new Set(d.stops.flatMap((s) => s.problems))
  const failed = w.events.filter((e) => !isDeadLetter(e) && (/(failed|exhausted|denied|breached)/.test(e.type) || w.spans.some((s) => s.id === e.publisher_span && (s.status === 'failed'))))
  const unflagged = failed.filter((e) => !problems.has(`evt:${e.id}`))
  ok(unflagged.length === 0, `every failure is in a stop's problems (${failed.length})${unflagged.length ? ', missing ' + unflagged.length : ''}`)
  const batched = w.spans.filter((s) => s.kind === 'batch').reduce((n, s) => n + Number((s.attrs ?? {}).count ?? 0), 0)
  const c = qd.conservation
  ok(c.batched === batched && c.kept === w.events.length && c.ok === (c.kept + batched === c.total + c.dead) && c.ok === (c.fileOk ?? c.ok), `conservation recount: ${c.kept} kept + ${batched} batched = ${c.total} matched + ${c.dead} dead (${c.ok ? 'balanced' : 'OFF'})`)
  const bstops = d.stops.filter((s) => s.kind === 'batch')
  ok(bstops.every((s) => s.hero === 'pallet' && s.batch && s.batch.perMinute.length > 0 && /^×/.test(s.heroLabel?.real ?? '')), `a batch stop stands a pallet at its component with a count badge and a sparkline (${bstops.length})`)
  const busyCh = new Set(qd.chapters.filter((ch) => ch.events > 0).map((ch) => ch.n))
  ok(d.stops.filter((s) => s.kind === 'chapter').every((s) => (s.pallets?.length ?? 0) <= 10 && ((s.pallets?.length ?? 0) > 0 || !busyCh.has(s.chapter?.n ?? -1))), 'every chapter overview that has events stands its pallets (at most 10)')
  // the tour is not all failures: every kind of stop the file can fill appears at least once
  const failPer = new Map<number, number>()
  for (const s of d.stops) if (s.kind === 'failure' && s.chapter) failPer.set(s.chapter.n, (failPer.get(s.chapter.n) ?? 0) + 1)
  ok([...failPer.values()].every((n) => n <= 2), 'at most two failure stops per chapter (the rest fold into them)')
  const failedEv = (e: Waybill['events'][number]) => /(failed|exhausted|denied|breached)/.test(e.type) || w.spans.some((s) => s.id === e.publisher_span && s.status === 'failed')
  const rareEv = w.events.filter((e) => !isDeadLetter(e) && !failedEv(e))
  const calm = w.spans.filter((s) => s.kind === 'batch' && Number((s.attrs ?? {}).failed ?? 0) === 0 && s.status !== 'failed')
  const has = (k: string) => d.stops.some((s) => s.kind === k)
  ok(!calm.length || has('batch'), `at least one pallet stop when the file has calm pallets (${calm.length})`)
  ok(!rareEv.length || has('belt'), `at least one belt stop when the file has rare notes (${rareEv.length})`)
  ok(!w.spans.some((s) => s.kind === 'tool') || d.stops.some((s) => s.kind === 'loop' && s.hero === 'toolbox' && (s.tools?.length ?? 0) > 0), 'tool calls get a toolbox stop with a count per tool')
  ok(!w.spans.some((s) => s.kind === 'llm') || d.stops.some((s) => s.kind === 'llm' && s.hero === 'phone' && !!s.model), 'model calls get a phone stop at the gateway')
  ok(!w.spans.some((s) => s.kind === 'hook') || d.stops.some((s) => s.kind === 'dock' && s.hero === 'parcel'), 'hooks get a parcel stop at the dock')
  ok(!qd.hubSeen || d.stops.every((s) => !!s.hub), 'the hub lamp has a reading at every stop')
  const silent = qd.chapters.filter((ch) => ch.hub.count === 0)
  ok(!qd.hubSeen || silent.length === 0 || d.stops.filter((s) => s.chapter && silent.some((x) => x.n === s.chapter!.n)).every((s) => s.hub?.count === 0), `a chapter with no heartbeat shows a silent lamp (${silent.length})`)
  const desks = Object.keys(w.components).filter((id) => id.startsWith('hermes-desk:'))
  const pl = d.placement
  ok(desks.every((id) => pl.setOf[id]?.startsWith('kiosk:') && pl.kioskById[id]?.near === 'crew'), `one crew-hall desk per Hermes profile (${desks.length})`)
}

if (!process.argv.includes('--no-perf')) {
  console.log('\n=== perf')
  const raw = readFileSync('public/waybills/fixture-query-100k.waybill.json.gz')
  const tp = performance.now()
  const r = parseWaybill(gunzipSync(raw).toString('utf8'))
  const parseMs = performance.now() - tp
  if (!r.ok) ok(false, 'the 100k fixture parses')
  else {
    const w = r.waybill
    const times: number[] = []
    for (let i = 0; i < 3; i++) { const copy = JSON.parse(JSON.stringify(w)) as Waybill; const pl = place(copy); const t = performance.now(); direct(copy, pl); times.push(performance.now() - t) }
    const best = Math.min(...times), worst = Math.max(...times)
    const total = w.origin.query?.total ?? 0
    ok(w.recorder.mode === 'query' && total >= 90000, `the folded fixture stands for ${total.toLocaleString('en-US')} events in ${w.spans.length} spans (${w.events.length} kept, ${w.stats.batches} pallets), parse ${parseMs.toFixed(0)} ms`)
    console.log(`PERF direct() on the folded 100k-event query: best ${best.toFixed(1)} ms, worst ${worst.toFixed(1)} ms (budget 400 ms)`)
    ok(worst < 400, `direct() < 400 ms on the 100k-event fixture (${worst.toFixed(1)} ms)`)
  }
  // a capture with thousands of hooks, tools and events whose publisher_span is null: the old director searched every span for each
  const base = parseWaybill(gunzipSync(readFileSync('public/waybills/claude-big-turn.waybill.json.gz')).toString('utf8'))
  if (base.ok) {
    const b = base.waybill
    const REP = 8, span = b.clock.duration_ms + 1000
    const sfx = (id: string | null | undefined, k: number) => (id ? `${id}~${k}` : id)
    const big = JSON.parse(JSON.stringify(b)) as Waybill
    for (let k = 1; k < REP; k++) {
      for (const s of b.spans) if (s.kind !== 'prompt' && s.kind !== 'turn') big.spans.push({ ...s, id: `${s.id}~${k}`, t0: s.t0 + k * span, t1: s.t1 === null ? null : s.t1 + k * span, parent: s.parent ? `${s.parent}~${k}` : s.parent, refs: s.refs ? Object.fromEntries(Object.entries(s.refs).map(([a, v]) => [a, typeof v === 'string' ? `${v}~${k}` : v])) : s.refs })
      for (const e of b.events) big.events.push({ ...e, id: `${e.id}~${k}`, t: e.t + k * span, archived: e.archived == null ? e.archived : e.archived + k * span, publisher_span: k % 2 ? null : sfx(e.publisher_span, k), correlationid: sfx(e.correlationid, k), causationid: sfx(e.causationid, k) })
    }
    big.clock.duration_ms = span * REP
    const pl = place(big)
    const t = performance.now()
    const dd = direct(big, pl)
    const ms = performance.now() - t
    console.log(`PERF capture stress: ${big.spans.length} spans, ${big.events.length} events, ${dd.stops.length} stops in ${ms.toFixed(1)} ms`)
    ok(ms < 400, `direct() < 400 ms on a ${big.spans.length}-span, ${big.events.length}-event capture with null publisher_span events (${ms.toFixed(0)} ms)`)
  }
}

console.log(bad ? `\n${bad} check(s) failed` : '\nall checks passed')
process.exit(bad ? 1 : 0)
