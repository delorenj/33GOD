// The query-mode director: a waybill built from a Candystore query (recorder.mode 'query', additive to SPEC section 2).
// A query is not one prompt. It is a window of the archive that the builder folds into chapters (spans of kind
// 'chapter', at most 12) and batches (kind 'batch': one type at one component in one chapter, counted, with a
// per-minute sparkline). Kept events (rare ones, failures, dead letters, anything a finding names) stay as themselves,
// each with a `publish:<id>` span at its resolved component.
//
// The tour opens at the archive with the question, walks the chapters in order (at most 5 stops each, 60 in all:
// the chapter's overview with a pallet per station, then the returned mail, the loudest failure (a second one only when
// there is room; the rest fold into the first), the biggest pallet, the rare notes and one stop of agent activity: the
// tool calls, model calls or hooks the builder synthesized, folded per kind into one stop with a count), and ends on
// what did not happen, with the conservation recount: kept + batched == matched + dead letters. Every kind of stop the
// file can fill (pallet, rare note, tools, model calls, hooks) appears at least once in the tour.
// Pure and deterministic, like the capture director; one pass over spans and events, so a 100k-event night is cheap.
import type { BatchInfo, Direction, JobCard, Pallet, Stop, ToolCount } from './director'
import { resolveEvent } from './resolve'
import type { Placement } from './stations'
import { fmtInt, fmtMs, short, spanDur, type BusEvent, type Span, type Waybill } from './types'

export const MAX_STOPS = 60
export const PER_CHAPTER = 5
export const MAX_CHAPTERS = 12
/** the most pallets a chapter overview stands on the floor */
const MAX_PALLETS = 10

export interface ChapterInfo {
  n: number; name: string; t0: number; t1: number; span: string | null
  events: number; kept: number; batches: number; failed: number; dead: number
  hub: { count: number; failed: number }
}
export interface Conservation {
  /** events Candystore matched (origin.query.total) */
  total: number
  /** dead letters Candystore refused in the window */
  dead: number
  /** events kept as themselves in this file (dead letters included) */
  kept: number
  /** events folded into batches */
  batched: number
  batches: number
  /** the player's own recount: kept + batched == total + dead */
  ok: boolean
  /** what the file says (stats.conservation_ok), when it says */
  fileOk: boolean | null
  /** total + dead - kept - batched: > 0 means events went missing, < 0 means some were counted twice */
  missing: number
  unresolved: number
}
export interface QueryDirection {
  label: string; since: string; until: string; clock: string
  filters: [string, string][]
  chapters: ChapterInfo[]
  conservation: Conservation
  /** the window carries hook-hub heartbeats at all (the dock lamp is drawn) */
  hubSeen: boolean
}

const FAIL_RE = /(failed|exhausted|denied|breached)/
const BAD = new Set(['failed', 'timeout', 'dropped'])
const pl1 = (n: number, one: string, many = one + 's') => `${fmtInt(n)} ${n === 1 ? one : many}`
const listAnd = (xs: string[]) => (xs.length <= 1 ? xs.join('') : `${xs.slice(0, -1).join(', ')} and ${xs[xs.length - 1]}`)
const num = (v: unknown, d = 0) => { const n = typeof v === 'number' ? v : typeof v === 'string' && v.trim() !== '' ? Number(v) : NaN; return Number.isFinite(n) ? n : d }
const strs = (v: unknown) => (Array.isArray(v) ? v.map((x) => String(x)).filter(Boolean) : [])
/** 'bloodbank.cron.candybar.invoked' -> 'cron.candybar.invoked' */
export const queryType = (t: string) => t.replace(/^bloodbank\./, '').replace(/^evt\./, '')
/** the words on a post-it: 'cron candybar invoked', 'tool requested' */
const words = (t: string) => queryType(t).replace(/^conversation\./, '').replace(/[._]/g, ' ')
const isHubBeat = (t: string) => /(^|\.)system\.hook\.updated$/.test(t)

/** A dead letter: a note Candystore refused (its archive consumer dropped it). */
export const isDeadLetter = (e: BusEvent) => e.consumers.some((c) => c.outcome === 'dropped' && (/candystore/.test(c.name) || c.component === 'candystore'))

/** The agent-activity spans the builder synthesizes (tool, llm, hook and its handlers), folded per kind into one stop. */
type ActKind = 'loop' | 'llm' | 'dock'
const ACT_KINDS: ActKind[] = ['loop', 'llm', 'dock']
const actKind = (s: Span): ActKind | null => (s.kind === 'tool' ? 'loop' : s.kind === 'llm' ? 'llm' : s.kind === 'hook' || s.kind === 'handler' ? 'dock' : null)
interface Ch extends ChapterInfo {
  spans: Span[]
  batchSpans: Span[]
  rare: BusEvent[]
  failedEv: BusEvent[]
  deadEv: BusEvent[]
  other: Span[]
  act: Record<ActKind, Span[]>
}
type CandKind = 'returned' | 'failure' | 'batch' | 'rare' | ActKind
interface Cand { kind: CandKind; ch: Ch; comp: string; weight: number; first: boolean; batches: Span[]; events: BusEvent[]; spans: Span[] }
const tally = <T>(xs: T[], key: (x: T) => string): [string, number][] => {
  const m = new Map<string, number>()
  for (const x of xs) { const k = key(x); m.set(k, (m.get(k) ?? 0) + 1) }
  return [...m.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
}

export function directQuery(wb: Waybill, placement: Placement): Direction {
  const q = wb.origin.query ?? null
  const cname = (id: string) => wb.components[id]?.name ?? id
  const setOf = (c: string) => placement.setOf[c] ?? 'dock'
  const evById = new Map(wb.events.map((e) => [e.id, e]))
  const spanById = new Map(wb.spans.map((s) => [s.id, s]))
  const duration = Math.max(1, wb.clock.duration_ms)

  const flagged = new Set<string>()
  for (const f of wb.findings) for (const e of f.evidence) flagged.add(e.replace(/^evt:/, ''))
  for (const g of wb.gaps) if (g.span) flagged.add(g.span)

  // ---- the publish span of each kept event: where it stands, and whether its poster said it failed ----
  const pubOf = new Map<string, Span>()
  for (const s of wb.spans) {
    if (s.kind !== 'publish') continue
    const id = typeof s.refs?.event_id === 'string' ? s.refs.event_id : s.id.startsWith('publish:') ? s.id.slice(8) : null
    if (id && evById.has(id) && !pubOf.has(id)) pubOf.set(id, s)
  }
  for (const e of wb.events) if (e.publisher_span && !pubOf.has(e.id)) { const s = spanById.get(e.publisher_span); if (s) pubOf.set(e.id, s) }
  const compOf = (e: BusEvent) => pubOf.get(e.id)?.component ?? resolveEvent(e).id
  const failedEvent = (e: BusEvent) => FAIL_RE.test(queryType(e.type)) || BAD.has(pubOf.get(e.id)?.status ?? 'ok')

  // ---- chapters: the file's, in order; one virtual chapter for a file without any; never more than 12 ----
  const chIndex = (s: Span) => num(s.attrs?.index, num(/^chapter:(\d+)$/.exec(s.id)?.[1], Infinity))
  const chSpans = wb.spans.filter((s) => s.kind === 'chapter').sort((a, b) => chIndex(a) - chIndex(b) || a.t0 - b.t0)
  const blank = (n: number, name: string, t0: number, t1: number, span: string | null, spans: Span[]): Ch => ({
    n, name, t0, t1, span, spans, events: 0, kept: 0, batches: 0, failed: 0, dead: 0, hub: { count: 0, failed: 0 },
    batchSpans: [], rare: [], failedEv: [], deadEv: [], other: [], act: { loop: [], llm: [], dock: [] },
  })
  let chapters: Ch[]
  if (!chSpans.length) chapters = [blank(1, q?.label || wb.title, 0, duration, null, [])]
  else {
    const per = Math.ceil(chSpans.length / MAX_CHAPTERS)
    chapters = []
    for (let i = 0; i < chSpans.length; i += per) {
      const part = chSpans.slice(i, i + per)
      const name = part.length === 1 ? part[0].name : `${part[0].name} (and ${part.length - 1} more)`
      chapters.push(blank(chapters.length + 1, name, part[0].t0, Math.max(...part.map((s) => s.t1 ?? s.t0)), part[0].id, part))
    }
  }
  const chOfSpanId = new Map<string, Ch>()
  for (const c of chapters) for (const s of c.spans) chOfSpanId.set(s.id, c)
  const chByNumber = new Map<number, Ch>()
  chSpans.forEach((s) => { const c = chOfSpanId.get(s.id)!; const k = chIndex(s); if (Number.isFinite(k)) chByNumber.set(k, c) })
  const starts = chapters.map((c) => c.t0)
  /** the chapter whose slice holds t: the last one that starts at or before it (binary search) */
  const chAt = (t: number): Ch => {
    let lo = 0, hi = starts.length
    while (lo < hi) { const mid = (lo + hi) >> 1; if (starts[mid] <= t) lo = mid + 1; else hi = mid }
    return chapters[Math.max(0, lo - 1)]
  }
  const chOfSpan = (s: Span): Ch => (s.parent ? chOfSpanId.get(s.parent) : undefined) ?? chByNumber.get(num(s.attrs?.chapter, NaN)) ?? chAt(s.t0)

  // ---- one pass: every span and event lands in exactly one chapter bucket ----
  const promptSpans: Span[] = []
  for (const s of wb.spans) {
    if (s.kind === 'chapter') continue
    if (s.kind === 'prompt' || s.kind === 'turn') { promptSpans.push(s); continue }
    if (s.kind === 'publish' && pubOfSpan(s)) continue
    const c = chOfSpan(s)
    const ak = actKind(s)
    if (s.kind === 'batch') c.batchSpans.push(s)
    else if (ak) c.act[ak].push(s)
    else c.other.push(s)
  }
  function pubOfSpan(s: Span): boolean { const id = typeof s.refs?.event_id === 'string' ? s.refs.event_id : s.id.startsWith('publish:') ? s.id.slice(8) : ''; return pubOf.get(id) === s }
  const chOfEvent = (e: BusEvent): Ch => { const p = pubOf.get(e.id); return (p?.parent ? chOfSpanId.get(p.parent) : undefined) ?? chAt(e.t) }
  for (const e of wb.events) {
    const c = chOfEvent(e)
    if (isDeadLetter(e)) c.deadEv.push(e)
    else if (failedEvent(e)) c.failedEv.push(e)
    else c.rare.push(e)
  }

  const binfo = (s: Span, c: Ch): BatchInfo => {
    const a = s.attrs ?? {}
    const perMinute = Array.isArray(a.per_minute) ? a.per_minute.map((x) => num(x, 0)) : []
    return {
      span: s.id, count: num(a.count, perMinute.reduce((n, x) => n + x, 0)), type: queryType(String(a.type ?? s.name)), perMinute, t0: c.t0,
      failed: num(a.failed, s.status === 'failed' ? 1 : 0), producers: strs(a.producers), exemplars: strs(a.exemplars).slice(0, 3),
    }
  }
  const binfoMemo = new Map<string, BatchInfo>()
  const bi = (s: Span) => binfoMemo.get(s.id) ?? binfoMemo.set(s.id, binfo(s, chOfSpan(s))).get(s.id)!
  const batchFailed = (s: Span) => bi(s).failed > 0 || s.status === 'failed'

  // ---- totals per chapter, the hub heartbeat, the conservation recount ----
  let batched = 0, batchCount = 0, hubSeen = false
  for (const c of chapters) {
    for (const s of c.batchSpans) {
      const b = bi(s)
      c.events += b.count; c.batches++; c.failed += b.failed; batched += b.count; batchCount++
      if (isHubBeat(b.type)) { c.hub.count += b.count; c.hub.failed += b.failed; hubSeen = true }
    }
    c.dead = c.deadEv.length
    c.kept = c.rare.length + c.failedEv.length + c.dead   // a returned note is kept as itself too (conservation counts it)
    c.events += c.kept
    c.failed += c.failedEv.length
    for (const e of [...c.rare, ...c.failedEv]) if (isHubBeat(queryType(e.type))) { c.hub.count++; if (failedEvent(e)) c.hub.failed++; hubSeen = true }
  }
  const deadAll = chapters.reduce((n, c) => n + c.dead, 0)
  const stat = (k: string) => (k in wb.stats ? wb.stats[k] : undefined)
  const total = q?.total ?? stat('query_total') ?? (wb.events.length - deadAll + batched)
  const dead = q?.dead_letters ?? stat('dead_letters') ?? deadAll
  const kept = wb.events.length
  const unresolvedIds = new Set<string>()
  for (const e of wb.events) if (compOf(e) === 'unknown' && e.producer) unresolvedIds.add(e.producer)
  for (const c of chapters) for (const s of c.batchSpans) if (s.component === 'unknown') for (const p of bi(s).producers) unresolvedIds.add(p)
  const conservation: Conservation = {
    total, dead, kept, batched, batches: batchCount, ok: kept + batched === total + dead,
    fileOk: stat('conservation_ok') === undefined ? null : stat('conservation_ok') === 1,
    missing: total + dead - kept - batched, unresolved: stat('unresolved_producers') ?? unresolvedIds.size,
  }

  // ---- per chapter, the stops worth making ----
  // Slots (PER_CHAPTER - 1 after the overview) are filled in this order: returned mail, the loudest failure, the biggest
  // pallet, the rare notes, one stop of agent activity, a second failure, the next pallets. A failure stop that finds no
  // slot folds into the first one, so every failure is still in some stop's problems.
  const SLOTS = PER_CHAPTER - 1
  const mk = (kind: CandKind, c: Ch, comp: string, weight: number, first: boolean, extra: Partial<Cand> = {}): Cand => ({ kind, ch: c, comp, weight, first, batches: [], events: [], spans: [], ...extra })
  const fold = (into: Cand, from: Cand) => { into.events.push(...from.events); into.batches.push(...from.batches); into.weight += from.weight }
  const failChapters = new Map<string, Set<number>>()
  const shown = new Set<ActKind>()
  const pools: Cand[][] = []
  const cands: Cand[][] = chapters.map((c) => {
    const returned = c.deadEv.length ? mk('returned', c, 'candystore', c.deadEv.length, true, { events: c.deadEv }) : null
    const fail = new Map<string, Cand>()
    const failCand = (comp: string) => fail.get(comp) ?? fail.set(comp, mk('failure', c, comp, 0, true)).get(comp)!
    for (const e of c.failedEv) { const f = failCand(compOf(e)); f.events.push(e); f.weight++ }
    for (const s of c.batchSpans) if (batchFailed(s)) { const f = failCand(s.component); f.batches.push(s); f.weight += Math.max(1, bi(s).failed) }
    const fails = [...fail.values()].sort((a, b) => b.weight - a.weight || a.comp.localeCompare(b.comp))
    for (const f of fails) (failChapters.get(f.comp) ?? failChapters.set(f.comp, new Set()).get(f.comp)!).add(c.n)
    const f1 = fails[0] ?? null
    let f2: Cand | null = null
    if (fails.length > 1) { f2 = mk('failure', c, fails[1].comp, 0, false); for (const f of fails.slice(1)) fold(f2, f) }
    const big = c.batchSpans.filter((s) => !batchFailed(s)).sort((a, b) => bi(b).count - bi(a).count || a.id.localeCompare(b.id))
    const batches = big.map((s, i) => mk('batch', c, s.component, bi(s).count, i === 0, { batches: [s] }))
    const rare = c.rare.length ? mk('rare', c, 'bb-nats', c.rare.length, true, { events: c.rare }) : null
    const acts = ACT_KINDS.filter((k) => c.act[k].length).map((k) => mk(k, c, tally(c.act[k], (s) => s.component)[0][0], c.act[k].length, true, { spans: c.act[k] }))
    // the kind this tour has not shown yet goes first; else the busiest
    acts.sort((a, b) => Number(shown.has(a.kind as ActKind)) - Number(shown.has(b.kind as ActKind)) || b.weight - a.weight || a.kind.localeCompare(b.kind))
    const fill = [returned, f1, batches[0] ?? null, rare, acts[0] ?? null, f2, ...batches.slice(1), ...acts.slice(1)].filter((x): x is Cand => !!x)
    const out = fill.slice(0, SLOTS)
    pools.push(fill.slice(SLOTS))
    if (f2 && f1 && !out.includes(f2)) { fold(f1, f2); pools[pools.length - 1] = pools[pools.length - 1].filter((x) => x !== f2) }
    for (const x of out) if (x.kind === 'loop' || x.kind === 'llm' || x.kind === 'dock') shown.add(x.kind)
    return out
  })
  const kindCount = (k: CandKind) => cands.reduce((n, xs) => n + xs.filter((x) => x.kind === k).length, 0)
  const dropCand = (x: Cand) => {
    const xs = cands[x.ch.n - 1]
    xs.splice(xs.indexOf(x), 1)
    if (x.kind === 'failure' && !x.first) { const f1 = xs.find((y) => y.kind === 'failure' && y.first); if (f1) fold(f1, x) }
  }
  // every kind of stop the file can fill appears at least once: put the heaviest unplaced one in, in place of something
  // that is not the last of its kind (a second failure folds, an extra pallet goes, then a doubled kind)
  const OPTIONAL: CandKind[] = ['batch', 'rare', 'loop', 'llm', 'dock']
  for (const kind of OPTIONAL) {
    if (kindCount(kind)) continue
    const spare = pools.flat().filter((x) => x.kind === kind).sort((a, b) => b.weight - a.weight || a.ch.n - b.ch.n)
    for (const sp of spare) {
      const xs = cands[sp.ch.n - 1]
      if (xs.length < SLOTS) { xs.push(sp); break }
      const victim = xs.find((y) => y.kind === 'failure' && !y.first) ?? xs.find((y) => y.kind === 'batch' && !y.first)
        ?? [...xs].reverse().find((y) => OPTIONAL.includes(y.kind) && y.kind !== kind && kindCount(y.kind) > 1)
      if (!victim) continue
      dropCand(victim)
      xs.push(sp)
      break
    }
  }

  // ---- the whole tour fits in 60 stops: the least interesting go first, never a failure, returned mail or the last of a kind ----
  let count = 2 + chapters.length + cands.reduce((n, xs) => n + xs.length, 0)
  const lightest = (xs: Cand[]) => xs.sort((a, b) => a.weight - b.weight || b.ch.n - a.ch.n)[0]
  while (count > MAX_STOPS) {
    const all = cands.flat()
    let victim: Cand | undefined = lightest(all.filter((x) => x.kind === 'batch' && !x.first)) ?? lightest(all.filter((x) => x.kind === 'failure' && !x.first))
    if (!victim) {
      const kind = OPTIONAL.filter((k) => kindCount(k) > 1).sort((a, b) => kindCount(b) - kindCount(a))[0]
      if (kind) victim = lightest(all.filter((x) => x.kind === kind))
    }
    if (!victim) break
    dropCand(victim)
    count--
  }

  // ---- build the stops ----
  const of = chapters.length
  const hubOf = (c: Ch) => (hubSeen ? { ...c.hub } : undefined)
  const base = (c: Ch | null) => ({
    id: '', waited: false, waitedMs: 0, side: false, afterReply: false, inferred: false, detail: '', tag: '', notes: [] as string[], problems: [] as string[],
    chapter: c ? { n: c.n, of, name: c.name } : undefined, hub: c ? hubOf(c) : undefined,
  })
  const tOf = (ts: number[], d: number) => (ts.length ? { t0: Math.min(...ts), t1: Math.max(...ts) } : { t0: d, t1: d })

  const stops: Stop[] = []
  const label = q?.label || wb.title
  const promptText = wb.prompt.text && /^you asked the archive/i.test(wb.prompt.text) ? wb.prompt.text : `You asked the archive: ${label}`
  const filters = Object.entries(q?.filters ?? {}).filter(([, v]) => v !== null && v !== undefined && v !== '').map(([k, v]) => [k, String(v)] as [string, string])
  const keptLive = kept - deadAll
  {
    const b = base(null)
    const caption = `The archive answers with ${pl1(total, 'event')}${dead ? `, and ${pl1(dead, 'note')} it refused as dead letters` : ''}. They are folded into ${pl1(batchCount, 'pallet')} over ${pl1(of, 'chapter')}; ${pl1(keptLive, 'rare note or failure', 'rare notes and failures')} ${keptLive === 1 ? 'stays as itself' : 'stay as themselves'}. The tour walks the chapters in order: the biggest piles, every failure and every returned note.`
    b.notes.push(filters.length ? `Filters: ${filters.map(([k, v]) => `${k} = ${v}`).join(', ')}.` : 'No filters: everything in the window.')
    if (q?.since) b.notes.push(`Window: ${q.since} to ${q.until}, on Candystore's ${q.clock === 'time' ? 'event time' : 'archived-at'} clock.`)
    if (q?.candystore) b.notes.push(`Asked of ${q.candystore}.`)
    stops.push({
      ...b, hub: hubSeen ? { count: chapters.reduce((n, c) => n + c.hub.count, 0), failed: chapters.reduce((n, c) => n + c.hub.failed, 0) } : undefined,
      kind: 'prompt', set: 'archive', components: ['candystore', ...new Set(promptSpans.map((s) => s.component).filter((c) => c !== 'candystore'))],
      spanIds: promptSpans.map((s) => s.id), eventIds: [], t0: 0, t1: duration,
      title: promptText, caption,
      detail: `${filters.length ? filters.map(([k, v]) => `${k}=${v}`).join(' ') : 'no filters'} · ${q?.clock ?? 'received_at'} clock`,
      tag: `candystore query · ${wb.origin.session_id || wb.id}`,
      hero: 'card', heroLabel: { real: 'your question', sub: label },
    })
  }

  const eventStop = new Map<string, Stop>()
  const placedSpans = new Set<string>()
  for (const c of chapters) {
    const xs = cands[c.n - 1]
    const inStop = new Set<string>()
    xs.forEach((x) => { x.batches.forEach((s) => inStop.add(s.id)); x.events.forEach((e) => inStop.add(`evt:${e.id}`)) })
    // the chapter overview: every pallet of the chapter, by station
    const byComp = new Map<string, { count: number; failed: number; types: Map<string, number> }>()
    const bump = (comp: string, type: string, n: number, failed: number) => {
      const g = byComp.get(comp) ?? byComp.set(comp, { count: 0, failed: 0, types: new Map() }).get(comp)!
      g.count += n; g.failed += failed; g.types.set(type, (g.types.get(type) ?? 0) + n)
    }
    for (const s of c.batchSpans) bump(s.component, bi(s).type, bi(s).count, bi(s).failed)
    for (const e of [...c.rare, ...c.failedEv]) bump(compOf(e), queryType(e.type), 1, failedEvent(e) ? 1 : 0)
    const bySet = new Map<string, Pallet>()
    for (const [comp, g] of [...byComp.entries()].sort((a, b) => b[1].count - a[1].count || a[0].localeCompare(b[0]))) {
      const set = setOf(comp)
      const top = [...g.types.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))[0][0]
      const p = bySet.get(set)
      if (p) { p.count += g.count; p.failed += g.failed; if (!p.name.endsWith('more')) p.name = `${p.name} +1 more`; else p.name = p.name.replace(/\+(\d+) more$/, (_, k: string) => `+${Number(k) + 1} more`) }
      else bySet.set(set, { component: comp, set, name: cname(comp), count: g.count, failed: g.failed, type: top })
    }
    const pallets = [...bySet.values()].sort((a, b) => b.count - a.count || a.set.localeCompare(b.set)).slice(0, MAX_PALLETS)
    const comps = [...byComp.keys()]
    {
      const b = base(c)
      const top3 = pallets.slice(0, 3)
      const quiet = !c.events && !c.dead
      const parts = quiet
        ? ['Nothing in this slice of the window matched the query.']
        : [
          `${pl1(c.events, 'event')} in ${fmtMs(c.t1 - c.t0)}, from ${pl1(comps.length, 'component')}.`,
          top3.length ? `The biggest piles: ${listAnd(top3.map((p) => `${p.name} (${fmtInt(p.count)})`))}.` : '',
          c.failed ? `${pl1(c.failed, 'thing')} failed.` : 'Nothing failed.',
          c.dead ? `${pl1(c.dead, 'note')} came back unread.` : '',
          hubSeen && !c.hub.count ? "hook-hub's heartbeat lamp is dark: no heartbeat in this chapter." : '',
        ]
      const rest = c.batchSpans.filter((s) => !inStop.has(s.id))
      const restEv = [...c.rare, ...c.failedEv].filter((e) => !inStop.has(`evt:${e.id}`))
      if (rest.length) b.notes.push(`${pl1(rest.length, 'smaller pallet')} in this chapter: ${rest.slice(0, 6).map((s) => `${cname(s.component)} ${words(bi(s).type)} (${fmtInt(bi(s).count)})`).join(', ')}${rest.length > 6 ? ', …' : ''}.`)
      for (const p of pallets.slice(0, 6)) b.notes.push(`${p.name}: ${pl1(p.count, 'event')}, mostly ${words(p.type)}${p.failed ? `, ${fmtInt(p.failed)} failed` : ''}.`)
      const stop: Stop = {
        ...b, kind: 'chapter', set: 'overview', components: pallets.map((p) => p.component),
        spanIds: [...c.spans.map((s) => s.id), ...rest.map((s) => s.id)], eventIds: restEv.map((e) => e.id), t0: c.t0, t1: Math.max(c.t0, c.t1),
        title: c.name.replace(/\s+·\s+/g, ': '), caption: parts.filter(Boolean).join(' '),
        detail: c.spans[0]?.summary ?? '', tag: `chapter ${c.n} of ${of} · ${pl1(c.batches, 'batch', 'batches')} · ${pl1(c.kept, 'kept note')}`,
        hero: 'none', pallets,
      }
      stop.problems.push(...restEv.filter((e) => flagged.has(e.id)).map((e) => `evt:${e.id}`))
      restEv.forEach((e) => eventStop.set(e.id, stop))
      stops.push(stop)
    }
    const details: Stop[] = []
    for (const x of xs) {
      const b = base(c)
      if (x.kind === 'returned') {
        const reasons = new Map<string, number>()
        for (const e of x.events) { const r = deadReason(e); reasons.set(r, (reasons.get(r) ?? 0) + 1) }
        const rs = [...reasons.entries()].sort((a, b2) => b2[1] - a[1] || a[0].localeCompare(b2[0])).map(([reason, count]) => ({ reason, count }))
        const n = x.events.length
        x.events.forEach((e) => b.notes.push(`${words(e.type)} from ${e.producer ?? 'no producer'} · ${deadReason(e)} · ${short(e.id)}`))
        details.push({
          ...b, kind: 'returned', set: 'archive', components: ['candystore'], spanIds: [], eventIds: x.events.map((e) => e.id), ...tOf(x.events.map((e) => e.t), c.t0),
          title: `${pl1(n, 'note')} came back unread`,
          caption: `Candystore refused ${n === 1 ? 'this note' : `these ${fmtInt(n)} notes`} and put ${n === 1 ? 'it' : 'them'} in the returned-mail tray: ${listAnd(rs.map((r) => `${fmtInt(r.count)} ${r.reason}`))}. A refused note never reaches the archive, so no later query finds it.`,
          detail: `dead_letter · ${pl1(n, 'row')}`, tag: `candystore-events · dropped`,
          hero: 'envelope', heroLabel: { real: `${fmtInt(n)} returned`, sub: rs[0]?.reason ?? 'refused' }, returned: { count: n, reasons: rs },
          problems: x.events.map((e) => `evt:${e.id}`), fanout: fanout(x.events),
        })
      } else if (x.kind === 'failure') {
        const types = new Map<string, number>()
        for (const e of x.events) types.set(queryType(e.type), (types.get(queryType(e.type)) ?? 0) + 1)
        let folded = 0
        for (const s of x.batches) { const f = Math.max(1, bi(s).failed); folded += f; types.set(bi(s).type, (types.get(bi(s).type) ?? 0) + f) }
        const ts = [...types.entries()].sort((a, b2) => b2[1] - a[1] || a[0].localeCompare(b2[0]))
        const n = x.events.length + folded
        const comps2 = [...new Set([x.comp, ...x.events.map(compOf), ...x.batches.map((s) => s.component)])]
        x.events.slice(0, 8).forEach((e) => b.notes.push(`${words(e.type)} from ${e.producer ?? cname(compOf(e))} · ${short(e.id)}`))
        if (x.events.length > 8) b.notes.push(`… and ${fmtInt(x.events.length - 8)} more, every one in the waterfall.`)
        const chronic = failChapters.get(x.comp)?.size ?? 0
        if (chronic >= 3) b.notes.push(`${cname(x.comp)} fails in ${fmtInt(chronic)} of ${pl1(of, 'chapter')}: a standing problem, not a blip.`)
        details.push({
          ...b, kind: 'failure', set: setOf(x.comp), components: comps2, spanIds: x.batches.map((s) => s.id), eventIds: x.events.map((e) => e.id),
          ...tOf([...x.events.map((e) => e.t), ...x.batches.flatMap((s) => [s.t0, s.t1 ?? s.t0])], c.t0),
          title: `${cname(x.comp)}: ${pl1(n, 'failure')}${comps2.length > 1 ? `, with ${comps2.length - 1} more` : ''}`,
          caption: `${listAnd(ts.slice(0, 3).map(([t, k]) => `${fmtInt(k)} “${words(t)}”`))}${ts.length > 3 ? `, and ${ts.length - 3} more kinds` : ''} in this chapter. ${x.events.length ? (x.events.length === n ? (n === 1 ? 'It is kept as itself, so you can open it.' : 'All of them are kept as themselves, so you can open each one.') : `${fmtInt(x.events.length)} of them ${x.events.length === 1 ? 'is' : 'are'} kept as themselves, so you can open ${x.events.length === 1 ? 'it' : 'each one'}.`) : ''}${folded ? ` ${fmtInt(folded)} more were folded into a pallet after the file's cap on kept notes.` : ''}`.trim(),
          detail: ts.map(([t, k]) => `${k} × ${t}`).join(' · '), tag: `${x.comp} · ${pl1(n, 'failure')}`,
          hero: 'flag', heroLabel: { real: `${fmtInt(n)} failed`, sub: words(ts[0]?.[0] ?? 'failed') },
          problems: [...x.events.map((e) => `evt:${e.id}`), ...x.batches.map((s) => s.id)], fanout: fanout(x.events),
        })
      } else if (x.kind === 'batch') {
        const s = x.batches[0], info = bi(s)
        const dur = Math.max(0, (s.t1 ?? s.t0) - s.t0)
        const peak = info.perMinute.reduce((m, v) => (v > m ? v : m), 0)
        const mins = Math.max(1, Math.round(dur / 60000))
        const posted = info.producers.length && !(info.producers.length === 1 && info.producers[0] === s.component) ? ` They were posted as ${listAnd(info.producers.slice(0, 4))}${info.producers.length > 4 ? ` and ${info.producers.length - 4} more` : ''}.` : ''
        if (info.exemplars.length) b.notes.push(`Examples you can look up in Candystore: ${info.exemplars.map((id) => short(id)).join(', ')}.`)
        if (s.summary) b.notes.push(s.summary)
        details.push({
          ...b, kind: 'batch', set: setOf(s.component), components: [s.component], spanIds: [s.id], eventIds: [], t0: s.t0, t1: Math.max(s.t0, s.t1 ?? s.t0),
          title: `${cname(s.component)} posts ${fmtInt(info.count)} “${words(info.type)}” notes`,
          caption: `Over ${fmtMs(dur || 60000)} of this chapter, ${cname(s.component)} stuck ${pl1(info.count, 'post-it')} of this kind on the belt, about ${fmtInt(Math.max(1, Math.round(info.count / mins)))} a minute${peak ? `, at most ${fmtInt(peak)} in one minute` : ''}. Too many to walk one by one, so they are stacked here as one pallet; the archive filed every one.${posted}`,
          detail: s.summary || `${info.count} × ${info.type}`, tag: `${s.id} · ${info.type}`,
          hero: 'pallet', heroLabel: { real: `×${fmtInt(info.count)}`, sub: words(info.type) }, batch: info,
        })
      } else if (x.kind === 'loop') {
        const sp = [...x.spans].sort((a, b2) => a.t0 - b2.t0 || a.id.localeCompare(b2.id))
        const byName = new Map<string, ToolCount>()
        for (const t of sp) { const nm = String(t.attrs?.tool ?? t.name); const g = byName.get(nm) ?? byName.set(nm, { name: nm, count: 0, ms: 0 }).get(nm)!; g.count++; g.ms += spanDur(t) }
        const tc = [...byName.values()].sort((a, b2) => b2.count - a.count || a.name.localeCompare(b2.name))
        const where = tally(sp, (t) => t.component)
        const bad = sp.filter((t) => BAD.has(t.status))
        const ms = sp.reduce((n, t) => n + spanDur(t), 0)
        const top3 = tc.slice(0, 3).map((t) => `${t.name} ×${fmtInt(t.count)}`).join(' · ')
        where.slice(0, 5).forEach(([comp, k]) => b.notes.push(`${cname(comp)}: ${pl1(k, 'tool call')}.`))
        details.push({
          ...b, kind: 'loop', set: setOf(where[0][0]), components: [...new Set([where[0][0], ...sp.map((t) => t.component)])].slice(0, 8),
          spanIds: sp.map((t) => t.id), eventIds: [], ...tOf(sp.flatMap((t) => [t.t0, t.t1 ?? t.t0]), c.t0),
          title: `${pl1(sp.length, 'tool call')} in this chapter: ${top3}${tc.length > 3 ? ' …' : ''}`,
          caption: `Agents ran ${pl1(sp.length, 'tool call')} in this slice of the window, mostly at ${listAnd(where.slice(0, 3).map(([comp, k]) => `${cname(comp)} (${fmtInt(k)})`))}. Too many to follow one by one, so they sit in one toolbox${bad.length ? `; ${fmtInt(bad.length)} of them ended in an error` : ''}.`,
          detail: `${pl1(sp.length, 'tool span')} · ${fmtMs(ms)} of tool time`, tag: `${pl1(sp.length, 'tool call')} · ${pl1(where.length, 'place')}`,
          hero: 'toolbox', tools: tc, toolRuns: sp.slice(0, 120).map((t) => ({ name: String(t.attrs?.tool ?? t.name), t0: t.t0, t1: t.t1 ?? t.t0 })),
          heroLabel: { real: top3 + (tc.length > 3 ? ' …' : ''), sub: `${pl1(sp.length, 'tool call')} · ${fmtMs(ms)}` },
          problems: bad.map((t) => t.id),
        })
      } else if (x.kind === 'llm') {
        const sp = [...x.spans].sort((a, b2) => a.t0 - b2.t0 || a.id.localeCompare(b2.id))
        const models = tally(sp, (t) => t.name)
        const bad = sp.filter((t) => BAD.has(t.status))
        const usage = (t: Span, k: string) => num((t.attrs?.usage as Record<string, unknown> | undefined)?.[k], 0)
        const tin = sp.reduce((n, t) => n + usage(t, 'input_tokens'), 0), tout = sp.reduce((n, t) => n + usage(t, 'output_tokens'), 0)
        models.slice(0, 5).forEach(([m, k]) => b.notes.push(`${m}: ${pl1(k, 'model call')}.`))
        details.push({
          ...b, kind: 'llm', set: setOf(x.comp), components: [...new Set(sp.map((t) => t.component))], spanIds: sp.map((t) => t.id), eventIds: [],
          ...tOf(sp.flatMap((t) => [t.t0, t.t1 ?? t.t0]), c.t0),
          title: `${pl1(sp.length, 'model call')} through the gateway: ${listAnd(models.slice(0, 2).map(([m]) => m))}${models.length > 2 ? ` and ${models.length - 2} more` : ''}`,
          caption: `${pl1(sp.length, 'call')} went to the staffing desk, the AutomaticAI gateway, in this slice: ${listAnd(models.slice(0, 3).map(([m, k]) => `${fmtInt(k)} to ${m}`))}.${bad.length ? ` ${fmtInt(bad.length)} of them failed.` : ''}${tin + tout ? ` The models read ${fmtInt(tin)} tokens and wrote ${fmtInt(tout)}.` : ''}`,
          detail: `${pl1(sp.length, 'llm span')}`, tag: `${x.comp} · ${pl1(sp.length, 'model call')}`,
          hero: 'phone', model: models[0][0], modelCalls: sp.length, heroLabel: { real: models[0][0], sub: `${pl1(sp.length, 'model call')}${bad.length ? ` · ${fmtInt(bad.length)} failed` : ''}` },
          problems: bad.map((t) => t.id),
        })
      } else if (x.kind === 'dock') {
        const sp = [...x.spans].sort((a, b2) => a.t0 - b2.t0 || a.id.localeCompare(b2.id))
        const hooks = sp.filter((t) => t.kind === 'hook'), handlers = sp.filter((t) => t.kind === 'handler')
        const natives = tally(hooks.length ? hooks : handlers, (t) => String(t.attrs?.native ?? t.name))
        const bad = sp.filter((t) => BAD.has(t.status))
        const byHandler = new Map<string, Span[]>()
        for (const h of handlers) (byHandler.get(h.name) ?? byHandler.set(h.name, []).get(h.name)!).push(h)
        const cards: JobCard[] = [...byHandler.entries()].sort((a, b2) => b2[1].length - a[1].length || a[0].localeCompare(b2[0])).slice(0, 8).map(([name, ss], i) => ({
          span: ss[0].id, handler: name, mode: ss.every((t) => t.sync) ? 'sync' : 'async',
          status: (ss.some((t) => BAD.has(t.status)) ? 'failed' : ss.some((t) => t.status === 'skipped') ? 'skipped' : 'ok') as Span['status'],
          reason: ss.find((t) => t.reason)?.reason ?? null, t0: Math.min(...ss.map((t) => t.t0)), t1: Math.max(...ss.map((t) => t.t1 ?? t.t0)), order: i,
        }))
        natives.slice(0, 5).forEach(([nm, k]) => b.notes.push(`${nm}: ${pl1(k, 'hook')}.`))
        const nHook = hooks.length || handlers.length
        details.push({
          ...b, kind: 'dock', set: 'dock', components: [...new Set(sp.map((t) => t.component))], spanIds: sp.map((t) => t.id), eventIds: [],
          ...tOf(sp.flatMap((t) => [t.t0, t.t1 ?? t.t0]), c.t0),
          title: `The dock handles ${pl1(nHook, hooks.length ? 'hook' : 'handler job')}: ${listAnd(natives.slice(0, 3).map(([nm, k]) => `${nm} ×${fmtInt(k)}`))}`,
          caption: `hook-hub took ${pl1(hooks.length, 'hook')} from the agents in this slice${handlers.length ? ` and ran ${pl1(handlers.length, 'handler job')} for them` : ''}${bad.length ? `; ${fmtInt(bad.length)} failed or were skipped with a fault` : ''}. They are stacked as one parcel at the dock.`,
          detail: `${pl1(hooks.length, 'hook span')}, ${pl1(handlers.length, 'handler span')}`, tag: `hook-hub · ${pl1(hooks.length, 'hook')}`,
          hero: 'parcel', cards, heroLabel: { real: `${fmtInt(nHook)} ${hooks.length ? 'hook' : 'handler'} ${nHook === 1 ? 'parcel' : 'parcels'}`, sub: natives[0] ? natives[0][0] : undefined },
          problems: bad.map((t) => t.id),
        })
      } else {
        const groups = new Map<string, { type: string; comp: string; n: number }>()
        for (const e of x.events) { const k = `${compOf(e)}|${queryType(e.type)}`; const g = groups.get(k) ?? groups.set(k, { type: queryType(e.type), comp: compOf(e), n: 0 }).get(k)!; g.n++ }
        const gs = [...groups.values()].sort((a, b2) => b2.n - a.n || a.type.localeCompare(b2.type))
        const n = x.events.length
        const comps2 = [...new Set(gs.map((g) => g.comp)), 'bb-nats']
        x.events.slice(0, 10).forEach((e) => b.notes.push(`${words(e.type)} from ${e.producer ?? cname(compOf(e))} (${cname(compOf(e))})`))
        details.push({
          ...b, kind: 'belt', set: 'belt', components: comps2, spanIds: [], eventIds: x.events.map((e) => e.id), ...tOf(x.events.map((e) => e.t), c.t0),
          title: `${pl1(n, 'rare note')} ${n === 1 ? 'goes' : 'go'} on the belt`,
          caption: `Things that happened only a few times in the whole window, each kept as itself: ${listAnd(gs.slice(0, 4).map((g) => `${g.n > 1 ? `${g.n} ` : ''}“${words(g.type)}” from ${cname(g.comp)}`))}${gs.length > 4 ? `, and ${gs.length - 4} more kinds` : ''}. The archive filed every one.`,
          detail: gs.map((g) => `${g.n} × ${g.type}`).join(' · '), tag: `${pl1(gs.length, 'kind')} · ${pl1(n, 'kept note')}`,
          hero: 'postit', heroLabel: { real: words(gs[0].type), sub: `${pl1(n, 'rare note')}` },
          problems: x.events.filter((e) => flagged.has(e.id)).map((e) => `evt:${e.id}`), fanout: fanout(x.events),
        })
      }
      const d = details[details.length - 1]
      x.events.forEach((e) => eventStop.set(e.id, d))
    }
    details.sort((a, b) => a.t0 - b.t0 || a.kind.localeCompare(b.kind))
    stops.push(...details)
    // the chapter's other spans (tool / llm / hook spans the builder synthesized): with their event, else with a stop
    // about their component, else in the overview
    const chapterStop = stops[stops.length - 1 - details.length]
    for (const k of ACT_KINDS) if (!xs.some((x) => x.kind === k)) c.other.push(...c.act[k])
    for (const k of ACT_KINDS) for (const x of xs) if (x.kind === k) x.spans.forEach((t) => placedSpans.add(t.id))
    for (const s of c.other) {
      const evId = typeof s.refs?.event_id === 'string' ? s.refs.event_id : null
      const home = (evId ? eventStop.get(evId) : undefined) ?? details.find((d) => d.components.includes(s.component)) ?? chapterStop
      home.spanIds.push(s.id)
      if (BAD.has(s.status) && !home.problems.includes(s.id)) home.problems.push(s.id)
    }
  }
  // each kept event's publish span rides with its event
  for (const [id, s] of pubOf) { const st = eventStop.get(id); if (st && !placedSpans.has(s.id)) st.spanIds.push(s.id) }

  // ---- the end card: what did not happen, and whether every event is accounted for ----
  const sev = (k: string) => wb.findings.filter((f) => f.severity === k).length
  const cons = conservation.ok
    ? `Every one of the ${pl1(total + dead, 'note')} is accounted for: ${fmtInt(kept)} kept as themselves${deadAll ? ` (${fmtInt(deadAll)} of them returned)` : ''} and ${fmtInt(batched)} folded into ${pl1(batchCount, 'pallet')}.`
    : `The counts do not add up: Candystore matched ${pl1(total, 'event')} and ${pl1(dead, 'dead letter')}, but this file holds ${fmtInt(kept + batched)}. ${conservation.missing > 0 ? `${pl1(conservation.missing, 'note')} went missing on the way.` : `${pl1(-conservation.missing, 'note')} ${conservation.missing === -1 ? 'is' : 'are'} counted twice.`}`
  const endT = Math.max(duration, ...stops.map((s) => s.t1))
  stops.push({
    ...base(null), hub: stops[0].hub,
    kind: 'end', set: 'overview', components: [...new Set([...wb.findings.map((f) => f.component), ...wb.gaps.map((g) => g.component)])],
    spanIds: [], eventIds: [], t0: endT, t1: endT,
    title: conservation.ok ? 'What did not happen' : 'What did not add up',
    caption: `${cons} ${pl1(sev('broken'), 'thing')} broken, ${pl1(sev('warn'), 'warning')}, ${pl1(sev('info'), 'note')}, and ${pl1(wb.gaps.length, 'gap')} the recorder could not see into.`,
    notes: [...wb.findings.map((f) => `${f.severity}: ${f.title}`), ...wb.gaps.map((g) => `gap: ${g.what}`)],
    hero: 'none', afterReply: true, problems: wb.findings.flatMap((f) => f.evidence),
  })

  stops.forEach((s, i) => { s.id = `s${i + 1}-${s.kind}` })
  const stopOfSpan: Record<string, number> = {}
  const stopOfEvent: Record<string, number> = {}
  stops.forEach((s, i) => { s.spanIds.forEach((id) => (stopOfSpan[id] ??= i)); s.eventIds.forEach((id) => (stopOfEvent[id] ??= i)) })
  for (const s of wb.spans) if (!(s.id in stopOfSpan)) stopOfSpan[s.id] = 0

  const query: QueryDirection = {
    label, since: q?.since ?? wb.clock.t0, until: q?.until ?? wb.clock.t_end, clock: q?.clock ?? 'received_at', filters,
    chapters: chapters.map(({ spans: _s, batchSpans: _b, rare: _r, failedEv: _f, deadEv: _d, other: _o, ...info }) => { void _s; void _b; void _r; void _f; void _d; void _o; return info }),
    conservation, hubSeen,
  }
  return { stops, placement, stopOfSpan, stopOfEvent, query }

  function fanout(es: BusEvent[]) { return es.map((e) => ({ eventId: e.id, type: e.type, seq: e.seq, consumers: e.consumers })) }
  function deadReason(e: BusEvent): string {
    const err = e.schema?.errors?.[0]
    if (err) return err
    const pub = pubOf.get(e.id)
    const g = wb.gaps.find((x) => (pub && x.span === pub.id) || x.span === `evt:${e.id}` || x.what.includes(e.id))
    return (pub?.reason ?? g?.why ?? 'malformed').replace(/\.$/, '')
  }
}
