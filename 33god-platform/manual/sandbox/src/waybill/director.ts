// The director: a pure function from a waybill to a list of camera stops, seen from the prompt's
// point of view. No randomness and no clock: the same file always plays the same tour.
//
// Rules (SPEC section 5), as the real recorder emits them:
// - stops follow causal and time order from `prompt` (a headless run's SessionStart comes before the
//   prompt reaches hook-hub, so it plays right after the prompt, at its real negative time);
// - a hook and its handlers are ONE dock stop (job cards: sync at the window, async in the back room);
//   hook-hub's ASM re-entry ("transition") invocations ride with the post-it that caused them;
// - the injected context is its own "briefing card back to the CLI" moment (split cards fold into it);
// - each bus event is ONE belt stop: the publish, the post-it, every reader (grouped by component,
//   observed before inferred), the ASM edge and ntfy notice it caused, the log line the poster wrote;
// - the main tool loop (tools, their hooks and events, the model calls between them) is ONE stop;
//   subagents (SubagentStart and everything under it) are ONE crew stop per launching tool;
// - model calls stop at the staffing desk with their usage records, a sync recall at the library,
//   ASM / notify / files / unknowns at kiosks when nothing else claims them;
// - the last stop lists what did not happen: findings and gaps.
//
// Captions lead with plain words (what happened, where, how long the prompt waited); `detail` carries the
// recorder's own summary sentence with real ids and numbers, shown smaller.
import { place, type Placement } from './stations'
import { spanDur, fmtMs, fmtInt, type BusEvent, type Consumer, type Span, type Waybill } from './types'

export type HeroForm = 'parcel' | 'postit' | 'envelope' | 'card' | 'phone' | 'slip' | 'toolbox' | 'lamp' | 'none'
export type StopKind = 'prompt' | 'courier' | 'dock' | 'briefing' | 'publish' | 'belt' | 'llm' | 'memory' | 'loop' | 'crew' | 'kiosk' | 'reader' | 'end'

export interface JobCard { span: string; handler: string; mode: 'sync' | 'async'; status: Span['status']; reason: string | null; t0: number; t1: number; order: number }
export interface ToolCount { name: string; count: number; ms: number }
/** All the readers of a stop's post-its, one row per component: observed and inferred kept apart. */
export interface ReaderGroup { component: string; name: string; observed: number; inferred: number; outcome: Consumer['outcome']; outcomes: Partial<Record<Consumer['outcome'], number>>; consumers: string[]; t: number | null }

export interface Stop {
  id: string
  kind: StopKind
  /** station / set id, 'kiosk:<component>' or 'overview' */
  set: string
  components: string[]
  spanIds: string[]
  eventIds: string[]
  t0: number
  t1: number
  /** plain words: what happened and where */
  title: string
  /** plain words: one or two sentences, how long the prompt waited */
  caption: string
  /** the recorder's own sentence: real ids and numbers, shown smaller */
  detail: string
  /** the real names behind the title (hook name, component id, belt number), shown small */
  tag: string
  notes: string[]
  hero: HeroForm
  /** the prompt was waiting on this stop (a sync handler, the model, a tool) */
  waited: boolean
  waitedMs: number
  /** async: nothing waited for it */
  side: boolean
  /** it happened after the answer was finished (after Stop) */
  afterReply: boolean
  /** drawn from inference, not from a recorded source */
  inferred: boolean
  cards?: JobCard[]
  fanout?: { eventId: string; type: string; seq: number | null; consumers: Consumer[] }[]
  readers?: ReaderGroup[]
  tools?: ToolCount[]
  /** span / event ids in this stop that failed or are named by a finding */
  problems: string[]
}

export interface Direction { stops: Stop[]; placement: Placement; stopOfSpan: Record<string, number>; stopOfEvent: Record<string, number> }

/** 'bloodbank.conversation.turn.started' -> 'turn.started' (the real short type). */
export const shortType = (t: string) => t.replace(/^bloodbank\./, '').replace(/^(conversation|agent)\./, '')
/** The post-it headline: past tense words, no dots ('turn started'). */
const headline = (t: string) => shortType(t).replace(/[._]/g, ' ')
const isMirror = (e: BusEvent) => /\.hook\.updated$/.test(e.type)
const isUsage = (e: BusEvent) => /\.llm\.usage\./.test(e.type) || /\.llm\.allowance\./.test(e.type)
const isCommand = (e: BusEvent) => /(^|\.)cmd\./.test(e.subject ?? '') || /\.cmd\./.test(e.type)
const BAD = new Set(['failed', 'timeout', 'dropped'])
const pl1 = (n: number, one: string, many = one + 's') => `${fmtInt(n)} ${n === 1 ? one : many}`
const listAnd = (xs: string[]) => (xs.length <= 1 ? xs.join('') : `${xs.slice(0, -1).join(', ')} and ${xs[xs.length - 1]}`)
const chars = (n: unknown) => { const v = Number(n); return !Number.isFinite(v) ? '' : v >= 1000 ? `${(v / 1000).toFixed(v >= 10000 ? 0 : 1)}k characters` : `${v} characters` }
const tokens = (n: unknown) => { const v = Number(n); return !Number.isFinite(v) ? '?' : v >= 1000 ? `${(v / 1000).toFixed(v >= 100000 ? 0 : 1)}k` : String(v) }
const minOf = (xs: number[]) => xs.reduce((a, b) => (b < a ? b : a), Infinity)
const maxOf = (xs: number[]) => xs.reduce((a, b) => (b > a ? b : a), -Infinity)

/** Length of the union of [t0, t1] intervals (ms the prompt actually spent waiting, without double counting). */
function unionMs(iv: [number, number][]): number {
  const s = iv.filter(([a, b]) => b > a).sort((x, y) => x[0] - y[0])
  let total = 0, cur: [number, number] | null = null
  for (const [a, b] of s) {
    if (!cur || a > cur[1]) { if (cur) total += cur[1] - cur[0]; cur = [a, b] } else cur[1] = Math.max(cur[1], b)
  }
  if (cur) total += cur[1] - cur[0]
  return total
}

/** What a reader did with its copy, in plain words. */
const DID: Record<Consumer['outcome'], string> = {
  archived: 'files it', collected: 'collects it', routed: 'sends a phone notice', 'rate-limited': 'drops it (too many notices)',
  digested: 'folds it into a digest', ignored: 'ignores it', enriched: 'annotates it', delivered: 'receives it', dropped: 'rejects it', unknown: 'reads it',
}

/** Plain titles for the native hook names (the real name stays in the tag). */
const HOOK_WORDS: Record<string, string> = {
  UserPromptSubmit: 'The dock opens your prompt',
  SessionStart: 'The session opens',
  SessionEnd: 'The session closes',
  Stop: 'The answer is finished',
  SubagentStart: 'A helper starts',
  SubagentStop: 'A helper finishes',
  PreToolUse: 'A check before a tool runs',
  PostToolUse: 'A report after a tool ran',
  PreCompact: 'The conversation is compacted',
  Notification: 'The CLI raises a notice',
  transition: 'hook-hub reacts to a state change',
}

/** Group a list of consumers by component. Observed beats inferred; the same reader under two names counts once. */
export function readerGroups(consumers: Consumer[], names: (c: string) => string): ReaderGroup[] {
  const by = new Map<string, ReaderGroup & { _inf: Set<string>; _obs: Set<string> }>()
  for (const c of consumers) {
    const g = by.get(c.component) ?? { component: c.component, name: names(c.component), observed: 0, inferred: 0, outcome: c.outcome, outcomes: {}, consumers: [], t: null, _inf: new Set<string>(), _obs: new Set<string>() }
    if (!g.consumers.includes(c.name)) g.consumers.push(c.name)
    if (c.evidence === 'observed') {
      g.observed++
      g._obs.add(c.name)
      g.outcomes[c.outcome] = (g.outcomes[c.outcome] ?? 0) + 1
      if (g.t === null || (c.t != null && c.t < g.t)) g.t = c.t ?? g.t
    } else g.inferred++
    by.set(c.component, g)
  }
  return [...by.values()].map(({ _inf, _obs, ...g }) => {
    void _inf; void _obs
    const top = (Object.entries(g.outcomes) as [Consumer['outcome'], number][]).sort((a, b) => b[1] - a[1])[0]
    return { ...g, outcome: top ? top[0] : 'unknown' }
  }).sort((a, b) => (b.observed > 0 ? 1 : 0) - (a.observed > 0 ? 1 : 0) || (a.t ?? Infinity) - (b.t ?? Infinity) || a.name.localeCompare(b.name))
}

const memo = new WeakMap<Waybill, Direction>()

/** The director, memoized per waybill object: replays and re-renders never recompute it. */
export function direct(wb: Waybill, placement?: Placement): Direction {
  if (!placement) {
    const hit = memo.get(wb)
    if (hit) return hit
  }
  const d = directUncached(wb, placement ?? place(wb))
  if (!placement) memo.set(wb, d)
  return d
}

function directUncached(wb: Waybill, placement: Placement): Direction {
  const byId = new Map(wb.spans.map((s) => [s.id, s]))
  const evById = new Map(wb.events.map((e) => [e.id, e]))
  const cname = (id: string) => wb.components[id]?.name ?? id
  const promptSpan = byId.get('prompt') ?? wb.spans.find((s) => s.kind === 'prompt')
  // 'Codex exec (headless)' reads as 'Codex exec' in a sentence; the surface is on the prompt stop's tag
  const cliName = (cname(promptSpan?.component ?? '') || wb.origin.cli).replace(/\s*\([^)]*\)\s*$/, '')
  const linksFrom = new Map<string, typeof wb.links>()
  const linksTo = new Map<string, typeof wb.links>()
  for (const l of wb.links) {
    ;(linksFrom.get(l.from) ?? linksFrom.set(l.from, []).get(l.from)!).push(l)
    ;(linksTo.get(l.to) ?? linksTo.set(l.to, []).get(l.to)!).push(l)
  }
  const children = new Map<string, Span[]>()
  for (const s of wb.spans) if (s.parent) (children.get(s.parent) ?? children.set(s.parent, []).get(s.parent)!).push(s)

  const flagged = new Set<string>()
  for (const f of wb.findings) for (const e of f.evidence) flagged.add(e.replace(/^evt:/, ''))
  for (const g of wb.gaps) if (g.span) flagged.add(g.span)

  const native = (s: Span) => String(s.attrs?.native ?? s.name)
  const isToolHook = (s: Span) => s.kind === 'hook' && (s.phase === 'pre_tool' || s.phase === 'post_tool' || /^(Pre|Post)ToolUse/.test(native(s)))

  // ---- subagents: everything under a SubagentStart hook belongs to that launcher's crew ----
  const crewMemo = new Map<string, string | null>()
  function crewOf(s: Span): string | null {
    if (crewMemo.has(s.id)) return crewMemo.get(s.id)!
    let cur: Span | undefined = s, out: string | null = null
    for (let i = 0; cur && i < 24; i++) {
      if (cur.kind === 'hook' && native(cur) === 'SubagentStart') { out = `crew:${cur.parent ?? cur.id}`; break }
      cur = cur.parent ? byId.get(cur.parent) : undefined
    }
    crewMemo.set(s.id, out)
    return out
  }
  const crewStarts = new Map<string, number>()
  for (const s of wb.spans) if (s.kind === 'hook' && native(s) === 'SubagentStart') { const c = crewOf(s)!; crewStarts.set(c, Math.min(crewStarts.get(c) ?? Infinity, s.t0)) }

  // ---- the main tool loop window: main-thread tools and their hooks ----
  const mainTools = wb.spans.filter((s) => s.kind === 'tool' && !crewOf(s))
  const mainToolIds = new Set(mainTools.map((s) => s.id))
  const loopSpans = [...mainTools, ...wb.spans.filter((s) => isToolHook(s) && !!s.parent && mainToolIds.has(s.parent))]
  const loop = loopSpans.length ? { t0: minOf(loopSpans.map((s) => s.t0)), t1: maxOf(loopSpans.map((s) => s.t1 ?? s.t0)) } : null
  const inLoop = (t: number) => !!loop && t >= loop.t0 && t <= loop.t1

  // ---- which group (future stop) each span and event belongs to ----
  const gm = new Map<string, string | null>()
  const eventIdOfConsume = (s: Span) => (typeof s.refs?.event_id === 'string' ? s.refs.event_id : s.id.split(':').slice(2).join(':'))
  const eventOfPublish = (s: Span): string | null => {
    const l = (linksFrom.get(s.id) ?? []).find((x) => x.kind === 'publishes' && x.to.startsWith('evt:'))
    if (l) return l.to.slice(4)
    if (typeof s.refs?.event_id === 'string') return s.refs.event_id
    return s.id.startsWith('publish:') ? s.id.slice(8) : null
  }
  const publishesEvent = (s: Span) => (linksFrom.get(s.id) ?? []).some((l) => l.kind === 'publishes' && l.to.startsWith('evt:'))
  const passThrough = (g: string | null) => !!g && (g === 'loop' || g.startsWith('crew:'))

  /** Where a handler's effects go: with the post-it it published, else with its hook. */
  function handlerEffectGroup(h: Span, depth: number): string | null {
    const pub = (linksFrom.get(h.id) ?? []).map((l) => byId.get(l.to)).find((x) => x && x.kind === 'publish')
      ?? (children.get(h.id) ?? []).find((x) => x.kind === 'publish')
    return pub ? groupOf(pub, depth + 1) : groupOf(h, depth + 1)
  }
  /** A handler with a sync memory effect keeps its journal line with that memory stop. */
  function memoryOfHandler(h: Span): Span | undefined {
    return (linksFrom.get(h.id) ?? []).map((l) => byId.get(l.to)).find((x) => x && x.kind === 'memory' && x.sync)
  }

  function groupOf(s: Span, depth = 0): string | null {
    if (gm.has(s.id)) return gm.get(s.id)!
    if (depth > 30) return `fx:${s.id}`
    gm.set(s.id, `fx:${s.id}`) // cycle guard
    const parent = s.parent ? byId.get(s.parent) : undefined
    const up = () => (parent ? groupOf(parent, depth + 1) : null)
    let g: string | null
    const crew = s.kind === 'prompt' || s.kind === 'turn' ? null : crewOf(s)
    if (s.kind === 'turn') g = null
    else if (s.kind === 'prompt') g = 'prompt'
    else if (crew) g = crew
    else switch (s.kind) {
      case 'tool': g = 'loop'; break
      case 'handler': g = up() ?? `fx:${s.id}`; break
      case 'hook': {
        if (isToolHook(s) && parent?.kind === 'tool') g = up()
        else if (parent?.kind === 'handler') g = handlerEffectGroup(parent, depth)
        else if (parent && (parent.kind === 'state' || parent.kind === 'notify' || parent.kind === 'consume')) g = up()
        else if (/^Subagent/.test(native(s)) && crewStarts.size) {
          // a SubagentStop the recorder could not tie to its sidechain: the latest crew that started before it
          const c = [...crewStarts.entries()].filter(([, t]) => t <= s.t0).sort((a, b) => b[1] - a[1])[0]
          g = c ? c[0] : `hook:${s.id}`
        } else g = `hook:${s.id}`
        break
      }
      case 'llm': g = inLoop(s.t0) ? 'loop' : `llm:${s.id}`; break
      case 'context': {
        if (parent?.kind === 'context') g = up()
        else g = passThrough(up()) ? up() : `context:${s.id}`
        break
      }
      case 'memory': {
        const u = up()
        g = passThrough(u) ? u : s.sync ? `memory:${s.id}` : (u ?? `memory:${s.id}`)
        break
      }
      case 'publish': {
        const u = up()
        if (parent && (parent.kind === 'llm' || parent.kind === 'consume')) g = u
        else if (passThrough(u)) g = u
        else {
          const rec = (linksTo.get(s.id) ?? []).map((l) => byId.get(l.from)).find((x) => x && x.kind === 'llm')
          if (rec) g = groupOf(rec, depth + 1)
          else { const ev = eventOfPublish(s); g = ev && evById.has(ev) ? `belt:${ev}` : `publish:${s.id}` }
        }
        break
      }
      case 'consume': {
        if (publishesEvent(s)) g = `reader:${s.id}`
        else { const e = evById.get(eventIdOfConsume(s)); g = e ? eventGroup(e, depth + 1) : (up() ?? `fx:${s.id}`) }
        break
      }
      default: {
        // state, notify, file and any kind this player does not know: ride with whatever caused it
        // (the post-it it reacted to, the handler or poster that wrote it); a kiosk moment otherwise
        let found: string | null = null
        for (const l of linksTo.get(s.id) ?? []) {
          if (l.from.startsWith('evt:')) { const e = evById.get(l.from.slice(4)); if (e) { found = eventGroup(e, depth + 1); break } }
          const src = byId.get(l.from)
          if (!src || src.kind === 'turn' || src.kind === 'prompt') continue
          if (src.kind === 'handler') { const m = s.kind === 'file' ? memoryOfHandler(src) : undefined; found = m ? groupOf(m, depth + 1) : groupOf(src, depth + 1); break }
          found = groupOf(src, depth + 1)
          break
        }
        if (!found && parent && parent.kind !== 'turn' && parent.kind !== 'prompt') found = up()
        if (!found && typeof s.refs?.event_id === 'string' && evById.has(s.refs.event_id)) found = eventGroup(evById.get(s.refs.event_id)!, depth + 1)
        g = found ?? `fx:${s.id}`
        if (!found && inLoop(s.t0) && /tool/.test(String(s.attrs?.on ?? s.summary))) g = 'loop'
      }
    }
    gm.set(s.id, g)
    return g
  }
  function eventGroup(e: BusEvent, depth = 0): string {
    const key = `evt:${e.id}`
    if (gm.has(key)) return gm.get(key)!
    gm.set(key, `belt:${e.id}`) // guard against cycles
    let g = `belt:${e.id}`
    const pubLink = (linksTo.get(key) ?? []).find((l) => (l.kind === 'publishes' || l.kind === 'mirrors') && byId.has(l.from))
    const pub = (e.publisher_span ? byId.get(e.publisher_span) : undefined) ?? (pubLink ? byId.get(pubLink.from) : undefined)
    if (isMirror(e)) {
      const hook = (e.correlationid ? byId.get(`hook:${e.correlationid}`) : undefined) ?? (pub?.kind === 'hook' ? pub : undefined)
      if (hook) g = groupOf(hook, depth + 1) ?? g
    } else if (pub && pub.kind === 'consume') {
      g = `belt:${e.id}` // a reader posting a new note: the reader stop, then this belt stop
    } else if (pub) {
      g = groupOf(pub, depth + 1) ?? g
    } else if (isUsage(e)) {
      const rec = (linksTo.get(key) ?? []).map((l) => byId.get(l.from)).find((s) => s && s.kind === 'llm')
      if (rec) g = groupOf(rec, depth + 1) ?? g
    } else if (/\.tool\./.test(e.type) && inLoop(e.t)) g = 'loop'
    gm.set(key, g)
    return g
  }

  interface Group { key: string; spans: Span[]; events: BusEvent[] }
  const groups = new Map<string, Group>()
  const add = (key: string | null, s?: Span, e?: BusEvent) => {
    if (!key) return
    const g = groups.get(key) ?? groups.set(key, { key, spans: [], events: [] }).get(key)!
    if (s) g.spans.push(s)
    if (e) g.events.push(e)
  }
  for (const s of wb.spans) add(groupOf(s), s)
  for (const e of wb.events) add(eventGroup(e), undefined, e)

  // the moment the answer was finished: Stop, else the turn umbrella's end, else the clock
  const stopHook = wb.spans.find((s) => s.kind === 'hook' && native(s) === 'Stop' && !crewOf(s))
  const answerAt = stopHook?.t0 ?? byId.get('turn')?.t1 ?? wb.clock.duration_ms
  const mainLlms = wb.spans.filter((s) => s.kind === 'llm' && /^llm:\d+$/.test(s.id)).length

  // ---- build one stop per group ----
  const stops: Stop[] = []
  const setOfComp = (c: string) => placement.setOf[c] ?? 'dock'
  const readersOf = (es: BusEvent[]) => readerGroups(es.filter((e) => !isMirror(e)).flatMap((e) => e.consumers), cname)
  const readerLine = (rs: ReaderGroup[], max = 4) => {
    const seen = rs.filter((r) => r.observed > 0)
    const guess = rs.filter((r) => r.observed === 0)
    const parts: string[] = []
    if (seen.length) parts.push(`${listAnd(seen.slice(0, max).map((r) => `${r.name} ${DID[r.outcome]}`))}${seen.length > max ? `, and ${seen.length - max} more` : ''}.`)
    if (guess.length) parts.push(`${listAnd(guess.slice(0, 3).map((r) => r.name))}${guess.length > 3 ? ` and ${guess.length - 3} more` : ''} ${guess.length === 1 ? 'is' : 'are'} on the pick list too, but nobody saw ${guess.length === 1 ? 'it' : 'them'} read it.`)
    return parts.join(' ')
  }

  for (const g of groups.values()) {
    const spans = g.spans.sort((a, b) => a.t0 - b.t0)
    const keyId = g.key.slice(g.key.indexOf(':') + 1)
    const head = g.key.startsWith('belt:') || g.key.startsWith('crew:') ? undefined : (byId.get(keyId) ?? spans[0])
    // a belt stop is about the event itself (posted -> last reader); every other stop is about its spans
    const beltEv = g.key.startsWith('belt:') ? g.events : []
    const lo = [...spans.map((s) => s.t0), ...beltEv.map((e) => e.t)]
    const hi = [...spans.map((s) => s.t1 ?? s.t0), ...beltEv.map((e) => Math.max(e.t, e.archived ?? e.t, maxOf(e.consumers.map((c) => c.t ?? e.t))))]
    if (!lo.length) { lo.push(...g.events.map((e) => e.t)); hi.push(...g.events.map((e) => e.t)) }
    // a dock stop starts when hook-hub got the parcel: effects with approximate times must not pull it earlier
    const t0 = g.key.startsWith('hook:') && head ? head.t0 : minOf(lo)
    const t1 = Math.max(t0, maxOf(hi))
    const syncIv: [number, number][] = spans.filter((s) => s.sync && s.kind !== 'prompt' && s.kind !== 'turn' && s.kind !== 'context').map((s) => [s.t0, s.t1 ?? s.t0])
    const waitedMs = unionMs(syncIv)
    const waited = syncIv.length > 0
    const comps = new Set<string>(spans.map((s) => s.component))
    const problems = [...spans.filter((s) => BAD.has(s.status) || flagged.has(s.id)).map((s) => s.id), ...g.events.filter((e) => flagged.has(e.id)).map((e) => `evt:${e.id}`)]
    const notes: string[] = []
    const base = {
      id: '', spanIds: spans.map((s) => s.id), eventIds: g.events.map((e) => e.id), t0, t1, waited, waitedMs,
      side: !waited, afterReply: t0 >= answerAt - 0.001, inferred: false, problems, detail: '', tag: '',
    }
    const usageNotes = () => g.events.filter(isUsage).forEach((e) => {
      const pub = e.publisher_span ? byId.get(e.publisher_span) : undefined
      const rec = pub?.parent ? byId.get(pub.parent) : undefined
      notes.push(`${cname(e.producer ?? 'aai-llm-observability')} posted ${shortType(e.type)}${e.seq !== null ? ` (belt #${e.seq})` : ''}${rec?.kind === 'llm' ? `, ${fmtMs(e.t - (rec.t1 ?? rec.t0))} after the call ended` : ''}.`)
    })
    const fanoutOf = (es: BusEvent[]) => es.filter((e) => !isMirror(e) && !isUsage(e)).map((e) => ({ eventId: e.id, type: e.type, seq: e.seq, consumers: e.consumers }))
    const fan = (es: BusEvent[]) => es.forEach((e) => e.consumers.forEach((c) => comps.add(c.component)))
    const waitLine = (ms: number, who = cliName) => (ms > 0 ? `${who} waited ${fmtMs(ms)}.` : `${who} did not wait for any of it.`)

    if (g.key === 'prompt' && head) {
      const p = wb.prompt
      const headless = /headless|exec/.test(wb.origin.surface)
      if (p.text) notes.push(`“${p.text.length > 200 ? p.text.slice(0, 197) + '…' : p.text}”${p.truncated ? ' (cut by the recorder)' : ''}`)
      if (wb.origin.model?.requested) notes.push(`It asks the model route ${wb.origin.model.requested}${wb.origin.model.served ? `, which served ${wb.origin.model.served}` : ''}.`)
      if (wb.origin.cwd) notes.push(`Working in ${wb.origin.cwd}${wb.origin.project ? ` (project ${wb.origin.project})` : ''}.`)
      const caption = headless
        ? `A script started ${cliName} with this prompt. The prompt leaves the vendor bay as a parcel, and everything after this happened because of it.`
        : `You typed a prompt into ${cliName} and pressed Enter. It leaves the vendor bay as a parcel, and everything after this happened because of it.`
      stops.push({ ...base, kind: 'prompt', set: 'bays', components: [...comps], title: headless ? `${cliName} gets a prompt` : `You press Enter in ${cliName}`, caption, detail: head.summary, tag: `${wb.origin.surface} · session ${wb.origin.session_id.slice(0, 8)}${wb.origin.turn_index != null ? ` · turn ${wb.origin.turn_index}` : ''}`, notes, hero: 'parcel', side: false, afterReply: false, waited: false, waitedMs: 0 })
      continue
    }
    if (g.key.startsWith('hook:') && head) {
      const handlers = spans.filter((s) => s.kind === 'handler' && s.parent === head.id)
      const cards: JobCard[] = handlers.map((h) => ({
        span: h.id, handler: String(h.attrs?.handler_id ?? h.refs?.handler_id ?? h.name), mode: (h.sync || h.attrs?.mode === 'sync' ? 'sync' : 'async') as JobCard['mode'], status: h.status, reason: h.reason ?? null,
        t0: h.t0, t1: h.t1 ?? h.t0, order: Number(h.attrs?.order ?? (h.sync ? h.t0 : -1)),
      })).sort((a, b) => (a.mode === b.mode ? (a.mode === 'sync' ? a.order - b.order || a.t0 - b.t0 : a.t0 - b.t0) : a.mode === 'sync' ? -1 : 1))
      const folded = [...(Array.isArray(head.attrs?.skipped_handlers) ? head.attrs!.skipped_handlers as unknown[] : []), ...(Array.isArray(head.attrs?.folded_handlers) ? head.attrs!.folded_handlers as unknown[] : [])].map(String)
      const sync = cards.filter((c) => c.mode === 'sync'), async = cards.filter((c) => c.mode === 'async')
      const skipped = cards.filter((c) => c.status === 'skipped')
      const nSkipped = skipped.length + (Array.isArray(head.attrs?.skipped_handlers) ? (head.attrs!.skipped_handlers as unknown[]).length : 0)
      const nat = native(head)
      const total = Number(head.attrs?.handler_count ?? cards.length + folded.length) || cards.length + folded.length
      const held = head.sync ? spanDur(head) : 0
      const before = head.t0 < 0 ? ` This happened ${fmtMs(-head.t0)} before the prompt reached the dock: the session opens first.` : ''
      const kept = folded.length ? ` (the recorder folded ${folded.length} of them away to keep the file small)` : ''
      const where = !sync.length && !async.length ? '' : !sync.length ? `${folded.length ? 'the rest' : 'all'} in the back room, alongside.` : !async.length ? `${folded.length ? 'the rest' : 'all'} at the window, one after another.` : `${sync.length} at the window, one after another, and ${async.length} in the back room, alongside.`
      const jobs = total ? `hook-hub ran ${pl1(total, 'job')}${kept}${where ? ': ' + where : '.'}` : 'hook-hub had no jobs for it.'
      const skip = nSkipped ? ` ${nSkipped === 1 ? 'One was' : `${nSkipped} were`} skipped because ${nSkipped === 1 ? 'it' : 'they'} did not apply.` : ''
      const caption = `${cliName} hands the dock a ${nat} parcel. ${jobs}${skip} ${held > 0 ? `${cliName} waited ${fmtMs(held)} before it could go on.` : `Nothing ran at the window, so ${cliName} did not wait.`}${before}`
      if (skipped.length) notes.push(`Skipped: ${skipped.map((c) => `${c.handler} (${c.reason ?? 'no reason given'})`).join(', ')}.`)
      if (folded.length) notes.push(`${pl1(folded.length, 'more job')} folded by the recorder to keep the file small: ${folded.slice(0, 8).join(', ')}${folded.length > 8 ? ', …' : ''}.`)
      spans.filter((s) => s.kind !== 'handler' && s.kind !== 'hook').forEach((s) => notes.push(s.summary))
      g.events.filter(isMirror).slice(0, 1).forEach((e) => notes.push(`hook-hub also posted its own receipt as a hook.updated post-it${e.seq !== null ? ` (belt #${e.seq})` : ''}, so other rooms can see the dock's work.`))
      fan(g.events)
      stops.push({ ...base, kind: 'dock', set: 'dock', components: [...comps], title: HOOK_WORDS[nat] ?? `${nat} at the dock`, caption, detail: head.summary, tag: `${nat} · hook-hub · invocation ${String(head.refs?.invocation_id ?? keyId).slice(0, 8)}`, notes, hero: 'parcel', cards, side: !head.sync, waited: !!head.sync && held > 0, waitedMs: held })
      continue
    }
    if (g.key.startsWith('context:') && head) {
      const a = head.attrs ?? {}
      const who = Array.isArray(a.handlers) ? (a.handlers as unknown[]).map(String) : spans.filter((s) => s !== head).map((s) => s.name)
      const ev = String(a.hook_event ?? '')
      const size = chars(a.chars ?? a.model_saw_chars)
      const caption = `hook-hub hands a briefing card back to ${cliName}${size ? `: ${size}` : ''}${who.length ? ` from ${listAnd(who)}` : ''}. The model reads it together with ${ev === 'SessionStart' ? 'everything that follows' : 'your prompt'}. It never goes on the belt.`
      spans.filter((s) => s !== head).forEach((s) => notes.push(s.summary))
      stops.push({ ...base, kind: 'briefing', set: 'bays', components: [...comps], title: `A briefing card goes back to ${cliName}`, caption, detail: head.summary, tag: `${ev || 'hook'} additionalContext · ${who.join(' · ')}`, notes, hero: 'card', waited: false, waitedMs: 0, side: false })
      continue
    }
    if (g.key === 'loop' || g.key.startsWith('crew:')) {
      const crew = g.key.startsWith('crew:')
      const tools = spans.filter((s) => s.kind === 'tool')
      const counts = new Map<string, ToolCount>()
      for (const t of tools) { const c = counts.get(t.name) ?? { name: t.name, count: 0, ms: 0 }; c.count++; c.ms += spanDur(t); counts.set(t.name, c) }
      const tc = [...counts.values()].sort((a, b) => b.count - a.count || a.name.localeCompare(b.name))
      const llms = spans.filter((s) => s.kind === 'llm')
      const hooks = spans.filter((s) => s.kind === 'hook' && isToolHook(s))
      const evts = g.events.filter((e) => !isMirror(e) && !isUsage(e))
      const list = tc.slice(0, 4).map((t) => `${t.name} ×${t.count}`).join(', ') + (tc.length > 4 ? `, ${tc.length - 4} more` : '')
      const readers = readersOf(g.events)
      fan(g.events)
      if (crew) {
        const starts = spans.filter((s) => s.kind === 'hook' && native(s) === 'SubagentStart')
        const launcher = byId.get(keyId)
        const caption = `${launcher ? `The ${launcher.name} tool` : cliName} sends out ${pl1(starts.length || 1, 'helper')} (subagents) that work side by side. Between them they run ${pl1(tools.length, 'tool call')}${tools.length ? ` (${list})` : ''} and ${pl1(llms.length, 'model call')}. The main conversation does not wait for them.`
        starts.forEach((h) => notes.push(`${String(h.attrs?.agent_type ?? 'helper')}: ${String(h.attrs?.description ?? h.summary)}`))
        if (wb.gaps.some((x) => /sidechain|subagent/i.test(x.what))) notes.push(wb.gaps.find((x) => /sidechain|subagent/i.test(x.what))!.why)
        stops.push({ ...base, kind: 'crew', set: setOfComp(launcher?.component ?? promptSpan?.component ?? 'ext:claude-code'), components: [...comps], title: `${pl1(starts.length || 1, 'helper')} work in parallel`, caption, detail: launcher?.summary ?? '', tag: `${starts.length} × SubagentStart · ${pl1(tools.length, 'tool')} · ${pl1(llms.length, 'model call')}`, notes, hero: 'toolbox', tools: tc, fanout: fanoutOf(g.events), readers, waited: false, waitedMs: 0, side: true })
        continue
      }
      const many = tools.length > 1
      const caption = `The model asks for ${many ? 'tools' : 'a tool'}, ${cliName} runs ${many ? 'them' : 'it'}, and the answer goes back to the model: ${pl1(tools.length, 'tool call')} (${list})${llms.length ? ` with ${pl1(llms.length, 'model call')} in between` : ''}, over ${fmtMs(t1 - t0)}. Each call is checked at the dock before and after${evts.length ? ` and puts ${pl1(evts.length, 'post-it')} on the belt` : ''}. ${waitLine(waitedMs)}`
      tools.slice(0, 12).forEach((t) => notes.push(t.summary))
      if (tools.length > 12) notes.push(`… and ${tools.length - 12} more tool calls (the waterfall has every one).`)
      if (llms.length) notes.push(`${pl1(llms.length, 'model call')} between the tools: ${tokens(llms.reduce((n, l) => n + Number(l.attrs?.tokens_in ?? 0), 0))} tokens in, ${tokens(llms.reduce((n, l) => n + Number(l.attrs?.tokens_out ?? 0), 0))} out.`)
      if (readers.length) notes.push(`Readers of the loop's post-its: ${readers.map((r) => `${r.name} ${r.observed ? `×${r.observed}` : '(inferred)'}`).join(', ')}.`)
      const set = setOfComp(tools[0]?.component ?? promptSpan?.component ?? 'ext:claude-code')
      stops.push({ ...base, kind: 'loop', set, components: [...comps], title: `${cliName} uses its tools: ${tc.slice(0, 3).map((t) => `${t.name} ×${t.count}`).join(' · ')}${tc.length > 3 ? ' …' : ''}`, caption, detail: tools.length === 1 ? tools[0].summary : `${pl1(tools.length, 'tool span')}, ${pl1(hooks.length, 'tool hook')}, ${pl1(llms.length, 'llm span')}, ${pl1(evts.length, 'event')}`, tag: `${pl1(hooks.length, 'tool hook')} · ${pl1(evts.length, 'event')}`, notes, hero: 'toolbox', tools: tc, fanout: fanoutOf(g.events), readers })
      continue
    }
    if (g.key.startsWith('llm:') && head) {
      const a = head.attrs ?? {}
      const n = /^llm:(\d+)$/.exec(head.id)?.[1]
      const bg = !n
      const tin = a.tokens_in ?? a.input_tokens, tout = a.tokens_out ?? a.output_tokens
      const model = String(a.served_model ?? wb.origin.model?.served ?? 'the model')
      usageNotes()
      if (a.stop_reason) notes.push(`It stopped because: ${String(a.stop_reason).replace(/_/g, ' ')}.`)
      if (a.ttft_ms !== undefined) notes.push(`First token after ${fmtMs(Number(a.ttft_ms))}.`)
      const caption = bg
        ? `${cliName} makes a background model call on the side (things like a session title or a summary). The gateway sends it to ${model}. Nobody waits for it.`
        : `${cliName} phones the staffing desk, the AutomaticAI gateway, which puts the call through to ${model}. The model reads ${tokens(tin)} tokens and answers with ${tokens(tout)}. ${head.sync ? waitLine(spanDur(head)) : 'Nobody waited for it.'}`
      stops.push({ ...base, kind: 'llm', set: setOfComp(head.component), components: [...comps], title: bg ? 'A background model call' : mainLlms > 1 ? `The model thinks (call ${n} of ${mainLlms})` : 'The model thinks', caption, detail: head.summary, tag: `${head.id} · ${cname(head.component)}${head.refs?.request_id ? ` · request ${String(head.refs.request_id).slice(-8)}` : ''}`, notes, hero: 'phone', waited: !!head.sync, waitedMs: head.sync ? spanDur(head) : 0, side: !head.sync })
      continue
    }
    if (g.key.startsWith('memory:') && head) {
      spans.filter((s) => s !== head).forEach((s) => notes.push(s.summary))
      const kind = head.id.split(':')[1] ?? head.name
      const wait = head.sync ? waitLine(spanDur(head)) : 'Nobody waited for it.'
      const caption = kind === 'recall'
        ? `hook-hub asks the lessons library (Hindsight) what earlier sessions learned in this project. The answer goes onto the briefing card. ${wait}`
        : kind === 'briefing'
          ? `hook-hub asks the lessons library (Hindsight) for this project's standing notes, to open the session with. The answer goes onto the briefing card. ${wait}`
          : `The lessons library (${cname(head.component)}) files a slip: ${head.name}. ${wait}`
      const mtitle = kind === 'recall' ? 'The lessons library looks things up' : kind === 'briefing' ? 'The lessons library prepares a briefing' : `The lessons library: ${head.name}`
      stops.push({ ...base, kind: 'memory', set: setOfComp(head.component), components: [...comps], title: mtitle, caption: caption.trim(), detail: head.summary, tag: `${head.id.split(':').slice(0, 2).join(':')} · ${cname(head.component)}`, notes, hero: 'slip' })
      continue
    }
    if (g.key.startsWith('publish:') && head) {
      stops.push({ ...base, kind: 'publish', set: setOfComp(head.component), components: [...comps], title: `${cname(head.component)} posts ${head.name}`, caption: `${cname(head.component)} tries to stick a note on the belt. The recorder saw the attempt but not the note itself.`, detail: head.summary, tag: head.id, notes, hero: 'postit' })
      continue
    }
    if (g.key.startsWith('reader:') && head) {
      spans.filter((s) => s !== head).forEach((s) => notes.push(s.summary))
      const e = evById.get(eventIdOfConsume(head))
      const out = (linksFrom.get(head.id) ?? []).filter((l) => l.kind === 'publishes').map((l) => evById.get(l.to.slice(4))).filter(Boolean) as BusEvent[]
      fan(g.events)
      stops.push({ ...base, kind: 'reader', set: setOfComp(head.component), components: [...comps], title: `${cname(head.component)} reads a post-it and writes a new one`, caption: `${cname(head.component)} tears off a copy of ${e ? `“${headline(e.type)}”` : 'a post-it'} and writes a new post-it of its own${out.length ? `: “${headline(out[0].type)}”` : ''}. Nobody waited for it.`, detail: head.summary, tag: `${head.id.split(':').slice(0, 2).join(':')}`, notes, hero: 'postit', fanout: fanoutOf(g.events), readers: readersOf(g.events) })
      continue
    }
    if (g.key.startsWith('belt:')) {
      const e = evById.get(keyId) ?? g.events[0]
      comps.add('bb-nats')
      fan(g.events)
      const pub = spans.find((s) => s.kind === 'publish')
      const poster = cname(pub?.component ?? e.producer ?? 'a poster')
      const readers = readerGroups(e.consumers, cname)
      const asm = spans.filter((s) => s.kind === 'state' && s.attrs?.from != null && s.attrs?.to != null)
      const hl = headline(e.type)
      const parts = [
        `${poster} sticks a “${hl}” ${isCommand(e) ? 'envelope' : 'post-it'} on the belt.`,
        readers.length ? `${pl1(readers.filter((r) => r.observed).length, 'reader')} tore off a copy: ${readerLine(readers)}` : 'Nobody is recorded reading it.',
        asm.length ? `The agent's status board (ASM) moves ${asm.map((s) => `${s.attrs!.from} → ${s.attrs!.to}`).join(', then ')}.` : '',
      ].filter(Boolean)
      const facts = [
        e.type,
        e.seq !== null ? `belt #${e.seq}` : 'core NATS only (no belt number)',
        e.stored != null ? `stored ${fmtT(e.stored - e.t)}` : null,
        e.archived != null ? `archived ${fmtT(e.archived - e.t)}` : null,
      ].filter(Boolean).join(' · ')
      spans.filter((s) => s.kind !== 'handler' && s.kind !== 'hook').forEach((s) => notes.push(s.summary))
      const reentry = spans.filter((s) => s.kind === 'hook')
      if (reentry.length) notes.push(`hook-hub reacted to the state change with ${pl1(reentry.length, 'small job run')} of its own (${spans.filter((s) => s.kind === 'handler').map((s) => s.name).filter((x, i, a) => a.indexOf(x) === i).join(', ')}).`)
      stops.push({ ...base, kind: 'belt', set: 'belt', components: [...comps], title: `“${hl}” goes on the belt`, caption: parts.join(' '), detail: pub?.summary ?? spans.find((s) => s.kind === 'consume' && BAD.has(s.status))?.summary ?? '', tag: facts, notes, hero: isCommand(e) ? 'envelope' : 'postit', side: true, waited: false, waitedMs: 0, fanout: fanoutOf(g.events), readers })
      continue
    }
    // kiosk moments: state, notify, file and unknown kinds
    if (head) {
      spans.filter((s) => s !== head).forEach((s) => notes.push(s.summary))
      const what = head.kind === 'state' ? 'records a state change' : head.kind === 'notify' ? 'lights up' : head.kind === 'file' ? 'writes a file' : 'does something this player has no picture for'
      stops.push({ ...base, kind: 'kiosk', set: setOfComp(head.component), components: [...comps], title: `${cname(head.component)}: ${head.name}`, caption: `${cname(head.component)} ${what}. ${head.sync ? waitLine(spanDur(head)) : 'Nobody waited for it.'}`, detail: head.summary, tag: `${head.kind} · ${head.component}`, notes, hero: head.kind === 'file' ? 'slip' : 'lamp' })
    }
  }

  // ---- order: causal and time; the prompt first ----
  // Clocks on different machines disagree by a few ms, so a post-it can carry an envelope time before
  // the hook that posted it. A stop never plays before the stop that caused it.
  const keyOfStop = (s: Stop) => (s.spanIds.length ? gm.get(s.spanIds[0]) : gm.get(`evt:${s.eventIds[0]}`)) ?? null
  const stopByKey = new Map<string, Stop>()
  for (const s of stops) { const k = keyOfStop(s); if (k) stopByKey.set(k, s) }
  const causeKey = (key: string): string | null => {
    const id = key.slice(key.indexOf(':') + 1)
    if (key.startsWith('belt:')) {
      const e = evById.get(id)
      const pub = e?.publisher_span ? byId.get(e.publisher_span) : wb.spans.find((s) => (linksFrom.get(s.id) ?? []).some((l) => l.kind === 'publishes' && l.to === `evt:${id}`))
      if (pub?.kind === 'consume') return groupOf(pub)
      const h = pub?.parent ? byId.get(pub.parent) : undefined
      return h && h.kind === 'handler' ? groupOf(h) : null
    }
    const s = byId.get(id)
    if (!s) return null
    if (key.startsWith('reader:')) { const e = evById.get(eventIdOfConsume(s)); return e ? eventGroup(e) : null }
    if (key.startsWith('context:') || key.startsWith('memory:')) { const p = s.parent ? byId.get(s.parent) : undefined; return p ? groupOf(p) : null }
    return null
  }
  const sortMemo = new Map<Stop, number>()
  const sortT = (s: Stop, depth = 0): number => {
    if (sortMemo.has(s)) return sortMemo.get(s)!
    sortMemo.set(s, s.t0)
    const k = keyOfStop(s)
    const c = k && depth < 12 ? causeKey(k) : null
    const cs = c && c !== k ? stopByKey.get(c) : undefined
    const v = cs ? Math.max(s.t0, sortT(cs, depth + 1) + 0.001) : s.t0
    sortMemo.set(s, v)
    return v
  }
  const rank: Record<StopKind, number> = { prompt: 0, courier: 1, dock: 2, briefing: 3, llm: 4, loop: 4, crew: 5, memory: 5, publish: 6, kiosk: 6, belt: 7, reader: 8, end: 99 }
  stops.sort((a, b) => (a.kind === 'prompt' ? -1 : b.kind === 'prompt' ? 1 : sortT(a) - sortT(b) || rank[a.kind] - rank[b.kind]))

  // merge neighbours that are one moment at one place (e.g. two ASM edges back to back)
  for (let i = stops.length - 1; i > 0; i--) {
    const a = stops[i - 1], b = stops[i]
    if (a.kind === b.kind && (a.kind === 'kiosk' || a.kind === 'memory') && a.set === b.set && b.t0 - a.t1 < 50) {
      a.spanIds.push(...b.spanIds); a.eventIds.push(...b.eventIds); a.notes.push(b.caption, ...b.notes); a.problems.push(...b.problems)
      a.t1 = Math.max(a.t1, b.t1); a.components = [...new Set([...a.components, ...b.components])]
      stops.splice(i, 1)
    }
  }

  // ---- the courier: bb-hook carries the parcel, but leaves no record of the trip ----
  const promptStop = stops.findIndex((s) => s.kind === 'prompt')
  const promptHook = wb.spans.find((s) => s.kind === 'hook' && (s.parent === 'prompt' || (linksTo.get(s.id) ?? []).some((l) => l.from === 'prompt')))
  const hookStop = promptHook ? stops.findIndex((s) => s.kind === 'dock' && s.spanIds[0] !== undefined && s.spanIds.includes(promptHook.id)) : stops.findIndex((s) => s.kind === 'dock' && s.t0 >= 0)
  if (promptStop >= 0 && hookStop >= 0) {
    const gap = wb.gaps.find((g) => g.component === 'bb-hook')
    const p = stops[promptStop]
    const h = stops[hookStop]
    const at = Math.max(p.t0, promptHook?.t0 ?? h.t0)
    // the prompt also waits on anything that held it before its own hook (a headless SessionStart)
    const heldBefore = stops.slice(promptStop + 1, hookStop).filter((s) => s.waited && s.t1 <= at + 0.001)
    const freeFrom = Math.max(p.t0, ...heldBefore.map((s) => s.t1))
    stops.splice(hookStop, 0, {
      id: '', kind: 'courier', set: 'courier', components: ['bb-hook'], spanIds: [], eventIds: [], t0: p.t0, t1: at,
      title: 'The courier carries the parcel to the dock',
      caption: `${cliName} hands the prompt to a small courier program, bb-hook, which carries it to hook-hub. The dock logged your prompt ${fmtMs(at - p.t0)} after Enter${heldBefore.length ? `; most of that was the session opening first, the trip itself took ${fmtMs(at - freeFrom)}` : ''}.`,
      detail: gap ? `${gap.what}: ${gap.why}` : 'bb-hook records nothing on the client side, so this trip is drawn from the receipt, not seen.',
      tag: 'bb-hook → hook-hub socket',
      notes: [],
      hero: 'parcel', waited: at - freeFrom > 0, waitedMs: Math.max(0, at - freeFrom), side: false, afterReply: false, inferred: true, problems: [],
    })
  }

  // ---- the end card: what did not happen ----
  const sev = (k: string) => wb.findings.filter((f) => f.severity === k).length
  const endT = Math.max(wb.clock.duration_ms, ...stops.map((s) => s.t1))
  stops.push({
    id: '', kind: 'end', set: 'overview', components: [...new Set([...wb.findings.map((f) => f.component), ...wb.gaps.map((g) => g.component)])],
    spanIds: [], eventIds: [], t0: endT, t1: endT,
    title: 'What did not happen',
    caption: `${pl1(sev('broken'), 'thing')} broken, ${pl1(sev('warn'), 'warning')}, ${pl1(sev('info'), 'note')}, and ${pl1(wb.gaps.length, 'gap')} the recorder could not see into.`,
    detail: '', tag: '',
    notes: [...wb.findings.map((f) => `${f.severity}: ${f.title}`), ...wb.gaps.map((g) => `gap: ${g.what}`)],
    hero: 'none', waited: false, waitedMs: 0, side: false, afterReply: true, inferred: false,
    problems: wb.findings.flatMap((f) => f.evidence),
  })

  stops.forEach((s, i) => { s.id = `s${i + 1}-${s.kind}` })
  const stopOfSpan: Record<string, number> = {}
  const stopOfEvent: Record<string, number> = {}
  stops.forEach((s, i) => { s.spanIds.forEach((id) => (stopOfSpan[id] ??= i)); s.eventIds.forEach((id) => (stopOfEvent[id] ??= i)) })
  // spans no stop claimed (the turn umbrella) point at the prompt
  for (const s of wb.spans) if (!(s.id in stopOfSpan)) stopOfSpan[s.id] = Math.max(0, promptStop)
  return { stops, placement, stopOfSpan, stopOfEvent }
}

function fmtT(ms: number | null | undefined) {
  return ms === null || ms === undefined ? '—' : `+${fmtMs(ms)}`
}
