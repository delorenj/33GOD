// Deterministic query-mode waybill fixtures (hand-made to the query contract, additive to SPEC section 2), so the Factory's
// query mode can be built and checked before the Python builder ships.
//   node --import ./tools/waybill/register.mjs --experimental-strip-types tools/waybill/query-fixture.ts
// writes public/waybills/fixture-query.waybill.json            (12 chapters, ~200 batches, ~150 kept notes)
//        public/waybills/fixture-query-100k.waybill.json.gz    (the same night at 100k events, folded: perf only, not in index.json)
import { writeFileSync } from 'node:fs'
import { gzipSync } from 'node:zlib'
import { resolveProducer } from '../../src/waybill/resolve'
import { familyOf } from '../../src/waybill/resolve'
import { standOf } from '../../src/waybill/stations'

const MIN = 60000
const SINCE = Date.parse('2026-11-20T23:02:00Z')
const UNTIL = Date.parse('2026-11-21T12:41:00Z')
const DURATION = UNTIL - SINCE
const KEPT_CAP = 400

function rng(seed: number) {
  let a = seed >>> 0
  return () => {
    a = (a + 0x6d2b79f5) >>> 0
    let t = a
    t = Math.imul(t ^ (t >>> 15), t | 1)
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61)
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

const TOPICS = [
  'Evening hooks and the PM desks', 'Candybar and the PM desks', 'Usage and allowance', 'Tool loops at the desks', 'Plane webhooks and momo',
  'The quiet hours', 'Hub goes dark', 'Overnight cron and the steward', 'Earshot and the phones', 'Tenants wake up', 'Morning ramp: opencode joins', 'Last hour before 07:41',
]
const EST = 5 * 3600000
const hhmm = (ms: number) => new Date(ms - EST).toISOString().slice(11, 16)

type Stream = { producer: string; type: string; rate: number; chapters?: number[]; source?: string }
const BASE: Stream[] = [
  { producer: 'hook-hub', type: 'agent.hook.updated', rate: 38 },
  { producer: 'hook-hub', type: 'system.hook.updated', rate: 1 },
  { producer: 'candybar', type: 'cron.candybar.invoked', rate: 4 },
  { producer: 'candybar', type: 'cron.candybar.completed', rate: 3.6 },
  { producer: 'candybar', type: 'cron.candybar.skipped', rate: 0.9 },
  { producer: 'candybar', type: 'cron.tick.fired', rate: 1 },
  { producer: 'automaticai-usage-exporter', type: 'llm.usage.updated', rate: 7 },
  { producer: 'automaticai-usage-exporter', type: 'allowance.window.updated', rate: 1.5 },
  { producer: 'claude-code', type: 'conversation.tool.requested', rate: 9, chapters: [1, 2, 4, 5, 11, 12] },
  { producer: 'claude-code', type: 'conversation.turn.completed', rate: 2, chapters: [1, 2, 4, 5, 11, 12] },
  { producer: 'hermes-agent:33god-pm', type: 'agent.hook.updated', rate: 5 },
  { producer: 'hermes-agent:33god-pm', type: 'agent.tool.executed', rate: 3 },
  { producer: 'hermes-agent:gruvato-pm', type: 'agent.hook.updated', rate: 3 },
  { producer: 'hermes-agent:tolt-pm', type: 'agent.hook.updated', rate: 2.4 },
  { producer: 'hermes-agent:holocene-momo', type: 'agent.hook.updated', rate: 2.2, chapters: [1, 2, 3, 5, 8, 9, 12] },
  { producer: 'hermes-agent:.hermes', type: 'agent.hook.updated', rate: 1.2 },
  { producer: 'n8n-plane-webhook', type: 'plane.issue.updated', rate: 1.6, chapters: [1, 2, 3, 5, 10, 11, 12] },
  { producer: 'turn-enricher', type: 'conversation.turn.enriched', rate: 2.4, chapters: [1, 2, 4, 5, 11, 12] },
  { producer: 'wax', type: 'wax.transcript.chunked', rate: 2.6, chapters: [3, 9, 10] },
  { producer: 'opencode', type: 'conversation.tool.requested', rate: 5, chapters: [11, 12] },
]

const DESKS = ['33god-pm', 'gruvato-pm', 'tolt-pm', 'bloodbank-pm', 'holocene-pm', 'flume-pm', 'pilot-pm', 'candystore-pm', 'candybar-pm', 'monitoring-pm', 'manual-pm', 'atlas-pm', 'waybill-pm', 'earshot-pm', 'heyma-pm',
  'vox-pm', 'milkshake-pm', 'curator-pm', 'deckard-pm', 'krebs-pm', 'plane-pm', 'hindsight-pm', 'aai-pm', 'delosip-pm', 'crank-pm', 'launch-director', 'jev-pm', 'ntfy-pm', 'asm-pm', 'cost-pm',
  'artifact-pm', 'sentinel-pm', 'target-pm', 'wax-pm', 'tiller-pm', 'gib-pm', 'hands-pm', 'staffing-pm', 'lessons-pm']

export interface FixtureOpts { big?: boolean }

export function buildQuery(opts: FixtureOpts = {}): Record<string, unknown> {
  const big = !!opts.big
  const r = rng(big ? 33001 : 20261121)
  const uuid = () => {
    const h = (n: number) => Array.from({ length: n }, () => Math.floor(r() * 16).toString(16)).join('')
    return `${h(8)}-${h(4)}-5${h(3)}-a${h(3)}-${h(12)}`
  }
  const N = 12
  const edges = Array.from({ length: N + 1 }, (_, i) => Math.round((DURATION * i) / N / MIN) * MIN)
  const chapters = Array.from({ length: N }, (_, i) => ({ n: i + 1, t0: edges[i], t1: i === N - 1 ? DURATION : edges[i + 1] }))
  const mins = (c: { t0: number; t1: number }) => Math.ceil((c.t1 - c.t0) / MIN)
  const SILENT = 7

  const components: Record<string, { id: string; name: string; kind: string; registry: boolean }> = {}
  const unresolved = new Set<string>()
  const compOf = (producer: string, type: string) => {
    const res = resolveProducer(producer, type, null)
    const id = res.id
    if (id === 'unknown' && producer) unresolved.add(producer)
    if (!components[id]) {
      const s = standOf(id)
      const fam = familyOf(id)
      components[id] = { id, name: s?.name ?? fam?.name ?? id, kind: id.startsWith('ext:') ? 'external' : id === 'unknown' ? 'external' : 'service', registry: !!s?.registry }
    }
    return id
  }
  for (const id of ['candystore', 'bb-nats']) compOf(id, '')

  const streams: Stream[] = [...BASE]
  if (big) for (const d of DESKS) for (const t of ['agent.hook.updated', 'agent.tool.executed', 'conversation.turn.completed', 'agent.session.updated']) streams.push({ producer: `hermes-agent:${d}`, type: t, rate: 0.2 + (d.length % 3) * 0.1 })

  // ---- batches: one type at one component in one chapter ----
  interface B { comp: string; type: string; ch: number; per: number[]; producers: Set<string>; exemplars: string[]; failed: number; t0: number; t1: number }
  const batches = new Map<string, B>()
  const typeOf = (t: string) => `bloodbank.${t}`
  const bucket = (comp: string, type: string, ch: number, ci: number) => {
    const k = `${comp}|${type}|${ch}`
    let b = batches.get(k)
    if (!b) { b = { comp, type, ch, per: new Array(mins(chapters[ci])).fill(0), producers: new Set(), exemplars: [], failed: 0, t0: Infinity, t1: -Infinity }; batches.set(k, b) }
    return b
  }
  const scale = 1
  for (const c of chapters) {
    for (const s of streams) {
      if (s.chapters && !s.chapters.includes(c.n)) continue
      if (s.type === 'system.hook.updated' && c.n === SILENT) continue
      const b = bucket(compOf(s.producer, typeOf(s.type)), s.type, c.n, c.n - 1)
      b.producers.add(s.producer)
      const wave = 0.55 + 0.9 * Math.abs(Math.sin((c.n * 1.7 + s.rate) * 0.9))
      for (let m = 0; m < b.per.length; m++) {
        const lull = m % 23 < 3 ? 0.15 : 1
        const burst = r() < 0.05 ? 3 : 1
        const v = Math.max(0, Math.round(s.rate * scale * wave * lull * burst * (0.6 + r() * 0.8)))
        b.per[m] += v
        if (v) { const t = c.t0 + m * MIN; b.t0 = Math.min(b.t0, t + Math.floor(r() * 20000)); b.t1 = Math.max(b.t1, t + 40000) }
      }
      while (b.exemplars.length < 3) b.exemplars.push(uuid())
    }
  }
  for (const [k, b] of [...batches]) if (b.per.every((v) => v === 0)) batches.delete(k)

  // ---- kept notes: rare ones, failures, dead letters ----
  interface K { id: string; type: string; producer: string; t: number; ch: number; fail: boolean; by?: string; dead?: string; consumers?: string; why?: string }
  const kept: K[] = []
  const at = (ch: number, f: number) => chapters[ch - 1].t0 + Math.round(f * (chapters[ch - 1].t1 - chapters[ch - 1].t0))
  const add = (producer: string, type: string, ch: number, count: number, o: Partial<K> = {}) => {
    for (let i = 0; i < count; i++) kept.push({ id: uuid(), type: typeOf(type), producer, t: at(ch, 0.04 + 0.9 * r()), ch, fail: false, ...o })
  }
  const fail = { fail: true }
  // candybar failures: ~90, heaviest in chapters 3, 4 and 8
  const cf = [0, 3, 14, 31, 4, 2, 1, 22, 6, 3, 2, 2]
  cf.forEach((n, i) => n && add('candybar', 'cron.candybar.failed', i + 1, n, fail))
  add('tiller', 'tenant.sync.completed', 9, 4); add('tiller', 'tenant.sync.breached', 9, 1, fail)
  add('local-script:gruvato', 'deploy.completed', 10, 1)
  add('zellij-sentinel', 'sentinel.session.resumed', 6, 2); add('zellij-sentinel', 'sentinel.session.failed', 6, 1, fail)
  add('pjangler', 'crank.nudge.sent', 8, 2)
  add('agent-pad-upload', 'audio.earshot.transcribed', 9, 5)
  add('n8n', 'telephony.call.received', 9, 3)
  add('candybar', 'steward_task.completed', 8, 4); add('candybar', 'steward_task.failed', 8, 1, fail)
  add('antigravity-cli', 'conversation.turn.completed', 11, 2)
  add('manual-test', 'manual.test.pinged', 5, 1); add('traefik-deathwatch', 'traefik.deathwatch.tripped', 6, 1)
  add('hook-hub', 'hook.invocation.failed', 3, 2, { fail: true, by: 'data' })
  add('automaticai-usage-exporter', 'allowance.window.exhausted', 3, 2, fail)
  add('gib-arena', 'tenant.arena.joined', 10, 6)
  add('holocene-auto', 'holocene.auto.started', 12, 1)
  const kimi = kept.length
  add('kimi', 'llm.usage.updated', 2, 3)
  const kimiIds = kept.slice(kimi).map((k) => k.id)
  const tools = kept.length
  add('hermes-agent:launch-director', 'agent.tool.executed', 4, 3)
  const toolEv = kept.slice(tools)
  const hookFail = kept.filter((k) => k.type.endsWith('hook.invocation.failed'))
  // dead letters: refused by Candystore's archive
  const dead: K[] = []
  const addDead = (producer: string, type: string, ch: number, why: string, n = 1) => { for (let i = 0; i < n; i++) dead.push({ id: uuid(), type: typeOf(type), producer, t: at(ch, 0.1 + 0.8 * r()), ch, fail: true, dead: why }) }
  addDead('hermes-agent:33god-pm', 'repo.decision.recorded', 4, 'schema: data.repo is required', 3)
  addDead('hermes-agent:33god-pm', 'repo.decision.recorded', 5, 'schema: data.repo is required', 3)
  addDead('hermes-agent:holocene-momo', 'unparseable', 8, 'envelope is not a CloudEvent', 1); addDead('', 'unparseable', 8, 'envelope is not a CloudEvent', 1)
  addDead('watch-lab', 'watch.lab.ticked', 6, 'unknown type', 1)
  // overflow: past the cap the rarest extra notes fold back into their batches (big only)
  const extra: K[] = []
  if (big) for (let i = 0; i < 520; i++) extra.push({ id: uuid(), type: typeOf('cron.candybar.failed'), producer: 'candybar', t: at(1 + (i % N), 0.05 + 0.9 * r()), ch: 1 + (i % N), fail: true })
  const keptLive = [...kept, ...extra]
  const room = KEPT_CAP - dead.length
  const priority = [...keptLive.keys()] // the named notes first, then the overflow failures
  const keepSet = new Set(priority.slice(0, room))
  const overflow = keptLive.filter((_, i) => !keepSet.has(i))
  for (const o of overflow) {
    const comp = compOf(o.producer, o.type)
    const b = bucket(comp, o.type.replace(/^bloodbank\./, ''), o.ch, o.ch - 1)
    const m = Math.min(b.per.length - 1, Math.floor((o.t - chapters[o.ch - 1].t0) / MIN))
    b.per[m] += 1; b.failed += 1; b.producers.add(o.producer)
    b.t0 = Math.min(b.t0, o.t); b.t1 = Math.max(b.t1, o.t)
    if (!b.exemplars.length) b.exemplars.push(o.id)
  }
  const final = keptLive.filter((_, i) => keepSet.has(i))

  // ---- spans, events, findings, gaps ----
  const spans: Record<string, unknown>[] = []
  const events: Record<string, unknown>[] = []
  const gaps: Record<string, unknown>[] = []
  const findings: Record<string, unknown>[] = []
  const chName = (c: { n: number; t0: number; t1: number }) => `${hhmm(SINCE + c.t0)}-${hhmm(SINCE + c.t1)} · ${TOPICS[c.n - 1]}`
  const perCh = chapters.map((c) => ({ events: 0, kept: 0, batches: 0 }))
  let batchTotal = 0
  const batchSpans: Record<string, unknown>[] = []
  for (const b of [...batches.values()].sort((x, y) => x.ch - y.ch || x.comp.localeCompare(y.comp) || x.type.localeCompare(y.type))) {
    const count = b.per.reduce((n, v) => n + v, 0)
    batchTotal += count
    perCh[b.ch - 1].events += count; perCh[b.ch - 1].batches++
    const short = b.type
    batchSpans.push({
      id: `batch:${b.comp}:${short}:${b.ch}`, kind: 'batch', component: b.comp, name: short, summary: `${count} × ${short}`, phase: 'async_after',
      t0: b.t0 === Infinity ? chapters[b.ch - 1].t0 : b.t0, t1: b.t1 === -Infinity ? chapters[b.ch - 1].t1 : b.t1, status: b.failed ? 'failed' : 'ok', parent: `chapter:${b.ch}`, refs: {},
      attrs: { count, type: short, producers: [...b.producers].sort(), chapter: b.ch, per_minute: b.per, exemplars: b.exemplars.slice(0, 3), failed: b.failed }, evidence: ['candystore'],
    })
  }
  const evOf = (k: K, dead = false) => {
    const comp = compOf(k.producer, k.type)
    const pid = `publish:${k.id}`
    spans.push({
      id: pid, kind: 'publish', component: comp, name: k.type.replace(/^bloodbank\./, ''), summary: `${k.producer || 'no producer'} posted ${k.type.replace(/^bloodbank\./, '')}`, phase: 'async_after',
      t0: k.t, t1: k.t + 40, status: dead ? 'dropped' : k.by ? 'failed' : 'ok', reason: dead ? k.dead : null, parent: `chapter:${k.ch}`, refs: { event_id: k.id },
      attrs: k.by ? { failed_by: k.by } : {}, evidence: ['candystore'],
    })
    events.push({
      id: k.id, type: k.type, subject: `bloodbank.evt.${k.type.replace(/^bloodbank\./, '')}`, stream: 'BLOODBANK_EVENTS', seq: 10_500_000 + events.length, t: k.t, stored: k.t + 2, archived: dead ? null : k.t + 9,
      correlationid: null, causationid: null, producer: k.producer || null, publisher_span: pid,
      consumers: [{ name: 'candystore-events', component: 'candystore', kind: 'durable', filter: 'bloodbank.evt.>', outcome: dead ? 'dropped' : 'archived', t: k.t + 9, evidence: 'observed', span: null }],
      ...(dead ? { schema: { file: null, valid: false, errors: [k.dead] } } : {}),
    })
    perCh[k.ch - 1].kept++
    if (!dead) perCh[k.ch - 1].events++
  }
  for (const k of final.sort((a, b) => a.t - b.t)) evOf(k)
  for (const k of dead.sort((a, b) => a.t - b.t)) {
    evOf(k, true)
    gaps.push({ component: 'candystore', what: `A note was refused and never archived (${k.type.replace(/^bloodbank\./, '')} from ${k.producer || 'no producer'}).`, why: k.dead ?? 'refused', severity: 'warn', span: `publish:${k.id}` })
  }
  // synthesized spans: tool pairs, llm calls, hook invocations
  toolEv.forEach((k, i) => {
    const tid = `toolu_${String(i + 1).padStart(4, '0')}`
    spans.push({ id: `tool:${tid}`, kind: 'tool', component: 'hermes-desk:launch-director', name: i % 2 ? 'Read' : 'Bash', summary: i % 2 ? 'Read a file' : 'Ran a command', phase: 'tool', t0: k.t, t1: k.t + 1800, status: 'ok', parent: `chapter:${k.ch}`, refs: { tool_use_id: tid, event_id: k.id }, attrs: {}, evidence: ['candystore'] })
  })
  kimiIds.forEach((id, i) => {
    const k = final.find((x) => x.id === id)!
    const rid = i === 2 ? 'bg_0x1f' : `req_${String(i + 1).padStart(6, '0')}`
    spans.push({ id: `llm:${rid}`, kind: 'llm', component: 'aai-gateway', name: i === 2 ? 'background call' : 'model call', summary: i === 2 ? 'A background model call (no turn)' : 'A kimi model call', phase: 'model_call', t0: k.t - 2400, t1: k.t, status: 'ok', parent: `chapter:${k.ch}`, refs: { request_id: rid, event_id: id }, attrs: {}, evidence: ['candystore'] })
  })
  hookFail.forEach((k, i) => spans.push({ id: `hook:inv_${i + 1}`, kind: 'hook', component: 'hook-hub', name: 'hook invocation', summary: 'A hook invocation that failed in hook-hub', phase: 'pre_tool', t0: k.t - 300, t1: k.t, status: 'failed', parent: `chapter:${k.ch}`, refs: { invocation_id: `inv_${i + 1}`, event_id: k.id }, attrs: {}, evidence: ['candystore'] }))
  spans.push(
    { id: 'prompt', kind: 'prompt', component: 'candystore', name: 'prompt', summary: 'You asked the archive.', phase: 'prompt_submit', t0: 0, t1: 600, status: 'ok', parent: null, refs: {}, attrs: {}, evidence: ['query'] },
    { id: 'turn', kind: 'turn', component: 'candystore', name: 'query', summary: 'Candystore answered.', phase: 'turn_end', t0: 600, t1: 4100, status: 'ok', parent: null, refs: {}, attrs: {}, evidence: ['query'] },
  )
  const chSpans = chapters.map((c, i) => ({
    id: `chapter:${c.n}`, kind: 'chapter', component: 'candystore', name: chName(c), summary: `${perCh[i].events} events in chapter ${c.n}`, phase: 'async_after', t0: c.t0, t1: c.t1, status: 'ok', parent: null, refs: {},
    attrs: { index: c.n, events: perCh[i].events + perCh[i].kept * 0, kept: perCh[i].kept, batches: perCh[i].batches }, evidence: ['candystore'],
  }))
  const deadN = dead.length
  const keptN = events.length
  const query_total = batchTotal + (keptN - deadN)

  findings.push(
    { severity: 'warn', title: 'hook-hub heartbeat went silent for a whole chapter', detail: `No system.hook.updated in chapter ${SILENT} (${chName(chapters[SILENT - 1])}). Either hook-hub was down or its heartbeat stopped.`, component: 'hook-hub', evidence: [`chapter:${SILENT}`] },
    { severity: 'broken', title: '2 allowance windows were exhausted', detail: 'The usage exporter reported allowance.window.exhausted twice in chapter 3.', component: 'aai-llm-observability', evidence: final.filter((k) => k.type.endsWith('allowance.window.exhausted')).map((k) => `evt:${k.id}`) },
    { severity: 'warn', title: `${deadN} notes were refused by the archive`, detail: 'Dead letters: malformed repo.decision.recorded from the 33god PM desk, two unparseable envelopes and one from watch-lab.', component: 'candystore', evidence: dead.map((k) => `evt:${k.id}`) },
    { severity: 'warn', title: 'A tenant sync was breached', detail: 'tiller reported tenant.sync.breached once.', component: 'tenant:tiller', evidence: final.filter((k) => k.type.endsWith('sync.breached')).map((k) => `evt:${k.id}`) },
    { severity: 'info', title: `${unresolved.size} producers could not be placed`, detail: `Resolved to unknown: ${[...unresolved].sort().join(', ')}.`, component: 'unknown', evidence: [] },
  )
  gaps.push({ component: 'bb-nats', what: 'Commands are not archived, so nothing a command asked for is in this window.', why: 'BLOODBANK_COMMANDS is not consumed by Candystore.', severity: 'warn', span: null })
  if (big) gaps.push({ component: 'candystore', what: `Past 400 kept notes, ${overflow.length} more failures were folded into their pallets.`, why: 'The waybill keeps at most 400 notes as themselves.', severity: 'warn', span: null })

  const sha12 = (big ? 'a1b2c3d4e5f6' : '9f3c71d2ab04')
  const label = 'everything the company did last night, 18:02 to 07:41'
  return {
    format: '33god.waybill', version: 1, id: `wb_q_${sha12}`, title: `Query · ${label}`, recorded_at: '2026-11-21T12:46:00Z',
    recorder: { name: 'waybill', version: '0.2.0', host: 'big-chungus', mode: 'query', profile: 'public', argv: [big ? 'hand-made fixture: the same night folded at 100k events (perf)' : 'hand-made fixture to the query-mode contract'] },
    origin: {
      cli: 'candystore', surface: 'query', session_id: `q_${sha12}`, turn_id: null, turn_index: null, cwd: null, project: null, model: null,
      query: { since: new Date(SINCE).toISOString(), until: new Date(UNTIL).toISOString(), clock: 'received_at', filters: {}, total: query_total, dead_letters: deadN, candystore: 'http://candystore.delo.sh', label },
    },
    prompt: { text: `You asked the archive: ${label}`, chars: 0, sha256: '', truncated: false },
    clock: { t0: new Date(SINCE).toISOString(), t_end: new Date(UNTIL).toISOString(), duration_ms: DURATION, settle_ms: 0 },
    components, spans: [...chSpans, ...batchSpans, ...spans], events, links: [], artifacts: {}, gaps, findings,
    sources: [{ id: 'candystore', kind: 'http', locator: 'http://candystore.delo.sh/events', status: 'ok', items: query_total, ms: 4100 }],
    stats: { query_total, kept_events: keptN, batched_events: batchTotal, batches: batchSpans.length, chapters: N, dead_letters: deadN, conservation_ok: keptN + batchTotal === query_total + deadN ? 1 : 0, unresolved_producers: unresolved.size },
  }
}

if (process.argv[1] && /query-fixture\.ts$/.test(process.argv[1])) {
  const out = (f: string) => new URL(`../../public/waybills/${f}`, import.meta.url)
  const small = buildQuery()
  writeFileSync(out('fixture-query.waybill.json'), JSON.stringify(small))
  const big = buildQuery({ big: true })
  writeFileSync(out('fixture-query-100k.waybill.json.gz'), gzipSync(JSON.stringify(big)))
  for (const [n, w] of [['small', small], ['big', big]] as const) {
    const s = (w as { stats: Record<string, number> }).stats
    console.log(n, JSON.stringify(s), 'spans', (w as { spans: unknown[] }).spans.length)
  }
}
