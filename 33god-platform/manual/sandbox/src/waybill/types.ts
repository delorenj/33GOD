// Waybill v1: the file format from 33god-platform/waybill/SPEC.md section 2, mirrored exactly,
// plus a tolerant reader. Readers ignore unknown fields and reject an unknown MAJOR version.
// This file has no runtime imports, so `node` can run it directly (see selfcheck.ts).

export type SpanKind =
  | 'prompt' | 'hook' | 'handler' | 'context' | 'memory' | 'publish' | 'consume'
  | 'state' | 'notify' | 'llm' | 'tool' | 'file' | 'turn'
  // query mode (recorder.mode 'query'): a slice of the window, and a folded pile of one type at one component
  | 'chapter' | 'batch'
  | (string & {})

export type Phase = 'prompt_submit' | 'model_call' | 'pre_tool' | 'tool' | 'post_tool' | 'turn_end' | 'async_after' | 'session_start' | 'session_end' | (string & {})
export type SpanStatus = 'ok' | 'skipped' | 'failed' | 'timeout' | 'pending' | 'dropped' | 'unknown'
export type Severity = 'info' | 'warn' | 'broken'

export interface Component {
  id: string
  name: string
  kind: 'cli' | 'service' | 'handler-host' | 'bus' | 'store' | 'memory' | 'model' | 'device' | 'external' | (string & {})
  registry: boolean
}

export interface SpanRefs {
  invocation_id?: string
  event_id?: string
  tool_use_id?: string
  request_id?: string
  seq?: number
  handler_id?: string
  [k: string]: unknown
}

export interface Span {
  id: string
  kind: SpanKind
  component: string
  name: string
  summary: string
  phase: Phase
  t0: number
  t1: number | null
  status: SpanStatus
  reason?: string | null
  sync?: boolean
  parent?: string | null
  refs?: SpanRefs
  attrs?: Record<string, unknown>
  payload?: string
  evidence: string[]
}

export interface Consumer {
  name: string
  component: string
  kind: 'durable' | 'ephemeral' | 'core'
  filter: string | null
  outcome: 'archived' | 'collected' | 'routed' | 'rate-limited' | 'digested' | 'ignored' | 'enriched' | 'delivered' | 'dropped' | 'unknown'
  t?: number | null
  evidence: 'observed' | 'inferred'
  span?: string | null
}

export interface BusEvent {
  id: string
  type: string
  subject: string | null
  stream: string | null
  seq: number | null
  t: number
  stored?: number | null
  archived?: number | null
  correlationid: string | null
  causationid: string | null
  producer: string | null
  publisher_span: string | null
  consumers: Consumer[]
  payload?: string
  schema?: { file: string | null; valid: boolean | null; errors?: string[] }
}

export interface Link {
  from: string
  to: string
  kind: 'calls' | 'runs' | 'publishes' | 'delivers' | 'injects' | 'feeds' | 'triggers' | 'writes' | 'records' | 'mirrors' | 'causes' | (string & {})
  label?: string
}

export interface Artifact { mime: string; bytes: number; sha256: string; truncated: boolean; text?: string; json?: unknown; note?: string }

export interface Gap { component: string; what: string; why: string; severity: Severity; span?: string | null }

export interface Finding { severity: Severity; title: string; detail: string; component: string; evidence: string[] }

export interface Source { id: string; kind: string; locator: string; status: 'ok' | 'empty' | 'error' | 'skipped'; items: number; ms: number; error?: string | null }

/** origin.query: the Candystore query a query-mode waybill answers (additive to SPEC section 2). */
export interface QueryInfo {
  since: string
  until: string
  /** which Candystore clock the window is cut on */
  clock: 'received_at' | 'time' | (string & {})
  filters: { type?: string; producer?: string; project?: string; correlation?: string; scope?: string; lens?: string; q?: string; [k: string]: unknown }
  /** events Candystore matched (the events table) */
  total: number
  /** dead letters Candystore refused in the window */
  dead_letters: number
  candystore: string
  /** human words for the window: 'Last night, 18:02 to 07:41' */
  label: string
}

export type RecorderMode = 'record' | 'capture' | 'query'

export interface Waybill {
  format: '33god.waybill'
  version: 1
  id: string
  title: string
  recorded_at: string
  recorder: { name: 'waybill'; version: string; host: string; mode: RecorderMode; profile: 'full' | 'public'; argv?: string[] }
  origin: {
    cli: 'claude' | 'codex' | (string & {})
    surface: 'claude-code' | 'claude-code-headless' | 'codex-cli' | 'codex-exec' | 'codex-desktop' | (string & {})
    session_id: string
    turn_id: string | null
    turn_index: number | null
    cwd: string | null
    project: string | null
    model: { requested: string | null; served: string | null } | null
    query?: QueryInfo | null
  }
  prompt: { text: string | null; chars: number; sha256: string; truncated: boolean }
  clock: { t0: string; t_end: string; duration_ms: number; settle_ms: number }
  components: Record<string, Component>
  spans: Span[]
  events: BusEvent[]
  links: Link[]
  artifacts: Record<string, Artifact>
  gaps: Gap[]
  findings: Finding[]
  sources: Source[]
  stats: Record<string, number>
}

/** The span kinds the player draws specially. Anything else is drawn as a generic kiosk moment. */
export const KNOWN_KINDS = ['prompt', 'hook', 'handler', 'context', 'memory', 'publish', 'consume', 'state', 'notify', 'llm', 'tool', 'file', 'turn', 'chapter', 'batch'] as const
export type KnownKind = (typeof KNOWN_KINDS)[number] | 'generic'
export const kindOf = (s: { kind: string }): KnownKind => ((KNOWN_KINDS as readonly string[]).includes(s.kind) ? (s.kind as KnownKind) : 'generic')

// ---------- the tolerant reader ----------

export type Parsed = { ok: true; waybill: Waybill; warnings: string[] } | { ok: false; error: string }

type Obj = Record<string, unknown>
const isObj = (v: unknown): v is Obj => typeof v === 'object' && v !== null && !Array.isArray(v)
const str = (v: unknown, d = ''): string => (typeof v === 'string' ? v : v == null ? d : String(v))
const strOrNull = (v: unknown): string | null => (typeof v === 'string' && v !== '' ? v : null)
const num = (v: unknown, d = 0): number => {
  const n = typeof v === 'number' ? v : typeof v === 'string' && v.trim() !== '' ? Number(v) : NaN
  return Number.isFinite(n) ? n : d
}
const numOrNull = (v: unknown): number | null => {
  if (v === null || v === undefined || v === '') return null
  const n = num(v, NaN)
  return Number.isFinite(n) ? n : null
}
const arr = (v: unknown): unknown[] => (Array.isArray(v) ? v : [])
const pick = <T extends string>(v: unknown, allowed: readonly T[], d: T): T => (allowed.includes(v as T) ? (v as T) : d)

const STATUSES = ['ok', 'skipped', 'failed', 'timeout', 'pending', 'dropped', 'unknown'] as const
const SEVERITIES = ['info', 'warn', 'broken'] as const
const OUTCOMES = ['archived', 'collected', 'routed', 'rate-limited', 'digested', 'ignored', 'enriched', 'delivered', 'dropped', 'unknown'] as const

/** Major version of a `version` field (1, '1', '1.2' -> 1). NaN when unreadable. */
export function majorOf(v: unknown): number {
  if (typeof v === 'number') return Math.floor(v)
  if (typeof v === 'string') return Number(v.split('.')[0])
  return NaN
}

/** Read any JSON value as a v1 waybill: default what is missing, refuse what cannot be one. */
export function normalize(raw: unknown): Parsed {
  if (!isObj(raw)) return { ok: false, error: 'This file is not a JSON object, so it cannot be a waybill.' }
  if (raw.format !== '33god.waybill') {
    return { ok: false, error: `This JSON is not a waybill: "format" is ${raw.format === undefined ? 'missing' : JSON.stringify(raw.format)}, expected "33god.waybill".` }
  }
  const major = majorOf(raw.version)
  if (major !== 1) {
    return { ok: false, error: `This waybill is format version ${JSON.stringify(raw.version)}. This player reads version 1 only; a newer player is needed.` }
  }
  const warnings: string[] = []

  const components: Record<string, Component> = {}
  if (isObj(raw.components)) {
    for (const [k, c] of Object.entries(raw.components)) {
      const o = isObj(c) ? c : {}
      const id = str(o.id, k) || k
      components[k] = { id, name: str(o.name, id) || id, kind: str(o.kind, 'service') || 'service', registry: o.registry === true }
    }
  }
  const ensureComponent = (id: string) => {
    if (!id || components[id]) return
    components[id] = { id, name: id.replace(/^ext:/, ''), kind: id.startsWith('ext:') ? 'external' : 'service', registry: false }
    warnings.push(`component ${id} was used but not listed; added it`)
  }

  const seen = new Set<string>()
  const spans: Span[] = []
  arr(raw.spans).forEach((s, i) => {
    if (!isObj(s)) return
    let id = str(s.id) || `span:${i}`
    if (seen.has(id)) { warnings.push(`duplicate span id ${id}; kept the first`); return }
    seen.add(id)
    const kind = str(s.kind, 'generic') || 'generic'
    if (!(KNOWN_KINDS as readonly string[]).includes(kind)) warnings.push(`span ${id}: unknown kind "${kind}", drawn as a generic kiosk`)
    const component = str(s.component, 'unknown') || 'unknown'
    ensureComponent(component)
    const t0 = num(s.t0, 0)
    const t1 = numOrNull(s.t1)
    spans.push({
      id, kind, component,
      name: str(s.name, id) || id,
      summary: str(s.summary),
      phase: str(s.phase, 'async_after') || 'async_after',
      t0,
      t1: t1 !== null && t1 < t0 ? t0 : t1,
      status: pick(s.status, STATUSES, 'unknown'),
      reason: strOrNull(s.reason),
      sync: s.sync === true,
      parent: strOrNull(s.parent),
      refs: isObj(s.refs) ? (s.refs as SpanRefs) : {},
      attrs: isObj(s.attrs) ? s.attrs : {},
      payload: strOrNull(s.payload) ?? undefined,
      evidence: arr(s.evidence).map((e) => str(e)).filter(Boolean),
    })
  })

  const events: BusEvent[] = []
  const seenEvt = new Set<string>()
  arr(raw.events).forEach((e, i) => {
    if (!isObj(e)) return
    const id = str(e.id) || `event:${i}`
    if (seenEvt.has(id)) return
    seenEvt.add(id)
    const consumers: Consumer[] = arr(e.consumers).filter(isObj).map((c) => {
      const component = str(c.component, str(c.name, 'unknown')) || 'unknown'
      ensureComponent(component)
      return {
        name: str(c.name, component) || component,
        component,
        kind: pick(c.kind, ['durable', 'ephemeral', 'core'] as const, 'core'),
        filter: strOrNull(c.filter),
        outcome: pick(c.outcome, OUTCOMES, 'unknown'),
        t: numOrNull(c.t),
        evidence: c.evidence === 'observed' ? 'observed' : 'inferred',
        span: strOrNull(c.span),
      }
    })
    const schema = isObj(e.schema) ? { file: strOrNull(e.schema.file), valid: typeof e.schema.valid === 'boolean' ? e.schema.valid : null, errors: arr(e.schema.errors).map((x) => str(x)) } : undefined
    events.push({
      id,
      type: str(e.type, 'unknown') || 'unknown',
      subject: strOrNull(e.subject),
      stream: strOrNull(e.stream),
      seq: numOrNull(e.seq),
      t: num(e.t, 0),
      stored: numOrNull(e.stored),
      archived: numOrNull(e.archived),
      correlationid: strOrNull(e.correlationid),
      causationid: strOrNull(e.causationid),
      producer: strOrNull(e.producer),
      publisher_span: strOrNull(e.publisher_span),
      consumers,
      payload: strOrNull(e.payload) ?? undefined,
      schema,
    })
  })

  const links: Link[] = arr(raw.links).filter(isObj).map((l) => ({ from: str(l.from), to: str(l.to), kind: str(l.kind, 'causes') || 'causes', label: strOrNull(l.label) ?? undefined })).filter((l) => l.from && l.to)

  const artifacts: Record<string, Artifact> = {}
  if (isObj(raw.artifacts)) {
    for (const [k, a] of Object.entries(raw.artifacts)) {
      if (!isObj(a)) continue
      artifacts[k] = {
        mime: str(a.mime, 'text/plain') || 'text/plain', bytes: num(a.bytes, 0), sha256: str(a.sha256), truncated: a.truncated === true,
        text: typeof a.text === 'string' ? a.text : undefined, json: a.json, note: strOrNull(a.note) ?? undefined,
      }
    }
  }

  const gaps: Gap[] = arr(raw.gaps).filter(isObj).map((g) => ({ component: str(g.component, 'unknown'), what: str(g.what), why: str(g.why), severity: pick(g.severity, SEVERITIES, 'info'), span: strOrNull(g.span) }))
  const findings: Finding[] = arr(raw.findings).filter(isObj).map((f) => ({ severity: pick(f.severity, SEVERITIES, 'info'), title: str(f.title), detail: str(f.detail), component: str(f.component, 'unknown'), evidence: arr(f.evidence).map((x) => str(x)) }))
  const sources: Source[] = arr(raw.sources).filter(isObj).map((s) => ({
    id: str(s.id), kind: str(s.kind), locator: str(s.locator), status: pick(s.status, ['ok', 'empty', 'error', 'skipped'] as const, 'ok'),
    items: num(s.items, 0), ms: num(s.ms, 0), error: strOrNull(s.error),
  }))
  const stats: Record<string, number> = {}
  if (isObj(raw.stats)) for (const [k, v] of Object.entries(raw.stats)) if (Number.isFinite(Number(v))) stats[k] = Number(v)

  const o = isObj(raw.origin) ? raw.origin : {}
  const model = isObj(o.model) ? { requested: strOrNull(o.model.requested), served: strOrNull(o.model.served) } : null
  const p = isObj(raw.prompt) ? raw.prompt : {}
  const c = isObj(raw.clock) ? raw.clock : {}
  const r = isObj(raw.recorder) ? raw.recorder : {}
  // a loop, not Math.max(...spread): a big file would blow the argument stack
  let lastT = 0
  for (const s of spans) { const t = s.t1 ?? s.t0; if (t > lastT) lastT = t }
  for (const e of events) { const t = Math.max(e.t, e.archived ?? 0); if (t > lastT) lastT = t }

  if (!spans.length && !events.length) warnings.push('this waybill has no spans and no events')

  const waybill: Waybill = {
    format: '33god.waybill',
    version: 1,
    id: str(raw.id, 'wb_unknown') || 'wb_unknown',
    title: str(raw.title) || 'Untitled waybill',
    recorded_at: str(raw.recorded_at),
    recorder: {
      name: 'waybill', version: str(r.version, '?'), host: str(r.host, '?'),
      // an unknown mode plays as a capture (SPEC: readers ignore what they do not know)
      mode: r.mode === 'record' ? 'record' : r.mode === 'query' ? 'query' : 'capture', profile: r.profile === 'full' ? 'full' : 'public',
      argv: Array.isArray(r.argv) ? r.argv.map((x) => str(x)) : undefined,
    },
    origin: {
      cli: str(o.cli, 'unknown') || 'unknown',
      surface: str(o.surface, str(o.cli, 'unknown')) || 'unknown',
      session_id: str(o.session_id),
      turn_id: strOrNull(o.turn_id),
      turn_index: numOrNull(o.turn_index),
      cwd: strOrNull(o.cwd),
      project: strOrNull(o.project),
      model,
      query: readQuery(o.query),
    },
    prompt: { text: typeof p.text === 'string' ? p.text : null, chars: num(p.chars, typeof p.text === 'string' ? p.text.length : 0), sha256: str(p.sha256), truncated: p.truncated === true },
    clock: { t0: str(c.t0), t_end: str(c.t_end), duration_ms: num(c.duration_ms, lastT), settle_ms: num(c.settle_ms, 0) },
    components, spans, events, links, artifacts, gaps, findings, sources, stats,
  }
  return { ok: true, waybill, warnings }
}

function readQuery(v: unknown): QueryInfo | null {
  if (!isObj(v)) return null
  const f = isObj(v.filters) ? v.filters : {}
  const filters: QueryInfo['filters'] = {}
  for (const [k, x] of Object.entries(f)) if (x !== null && x !== undefined && x !== '') filters[k] = x
  return {
    since: str(v.since), until: str(v.until), clock: str(v.clock, 'received_at') || 'received_at', filters,
    total: num(v.total, 0), dead_letters: num(v.dead_letters, 0), candystore: str(v.candystore), label: str(v.label),
  }
}

/** A query-mode waybill: a Candystore query folded into chapters and batches, not one prompt. */
export const isQuery = (w: Pick<Waybill, 'recorder'>) => w.recorder.mode === 'query'

/** Parse text (a dropped file, a fetch body) into a waybill. */
export function parseWaybill(text: string): Parsed {
  let raw: unknown
  try {
    raw = JSON.parse(text)
  } catch (e) {
    return { ok: false, error: `This file is not valid JSON (${(e as Error).message}).` }
  }
  return normalize(raw)
}

// ---------- small shared helpers ----------

export const spanEnd = (s: Span) => s.t1 ?? s.t0
export const spanDur = (s: Span) => (s.t1 === null ? 0 : s.t1 - s.t0)
export const short = (id: string | null | undefined, n = 8) => (id ? (id.length > n + 1 ? id.slice(0, n) : id) : '—')

/** '12 ms', '1.4 s', '2 min 3 s'. Real numbers, rounded the way a person says them. */
export function fmtMs(ms: number | null | undefined): string {
  if (ms === null || ms === undefined || !Number.isFinite(ms)) return '—'
  const a = Math.abs(ms)
  if (a === 0) return '0 ms'
  if (a < 1) return `${ms.toFixed(2)} ms`
  if (a < 10) return `${ms.toFixed(1)} ms`
  if (a < 1000) return `${Math.round(ms)} ms`
  if (a < 60000) return `${(ms / 1000).toFixed(a < 10000 ? 2 : 1)} s`
  // an archive window is hours long: '13 h 39 min', not '819 min 0 s'
  if (a >= 3600000) { const h = Math.floor(a / 3600000), mm = Math.round((a % 3600000) / 60000); return `${ms < 0 ? '-' : ''}${mm === 60 ? h + 1 : h} h${mm && mm !== 60 ? ` ${mm} min` : ''}` }
  const m = Math.floor(a / 60000)
  return `${ms < 0 ? '-' : ''}${m} min ${Math.round((a % 60000) / 1000)} s`
}

/** A time on the recording's axis, signed once: '+1.2 s' after Enter, '-2.43 s' before it (never '+-'). */
export const fmtT = (ms: number | null | undefined) => (ms === null || ms === undefined || !Number.isFinite(ms) ? '—' : ms < 0 ? fmtMs(ms) : `+${fmtMs(ms)}`)
/** Plain words for a time against Enter or against another moment: '2.43 s before', '120 ms after'. */
export const fmtRel = (ms: number, ref = 'Enter') => (ms < 0 ? `${fmtMs(-ms)} before ${ref}` : `${fmtMs(ms)} after ${ref}`)
export const fmtInt = (n: number | null | undefined) => (n === null || n === undefined ? '—' : Math.round(n).toLocaleString('en-US'))

/** The recording's whole time range in ms, negatives included (a headless SessionStart lands before Enter). A loop, not Math.max(...spread), so a huge turn cannot blow the stack. */
const rangeMemo = new WeakMap<Waybill, { min: number; max: number }>()
export function timeRange(w: Waybill): { min: number; max: number } {
  const hit = rangeMemo.get(w)
  if (hit) return hit
  let min = 0, max = Math.max(1, w.clock.duration_ms)
  const see = (t: number | null | undefined) => { if (typeof t === 'number' && Number.isFinite(t)) { if (t < min) min = t; if (t > max) max = t } }
  for (const s of w.spans) { see(s.t0); see(s.t1) }
  for (const e of w.events) { see(e.t); see(e.archived); for (const c of e.consumers) see(c.t) }
  const r = { min, max }
  rangeMemo.set(w, r)
  return r
}

/** A recording is "wide" when the longest and shortest things on it cannot share one linear axis: log reads better. */
export function isWide(w: Waybill): boolean {
  const { min, max } = timeRange(w)
  return max - min > 8000
}
