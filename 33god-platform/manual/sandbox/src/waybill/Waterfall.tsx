// The DevTools-style waterfall: rows grouped by component, bars on the recording's real ms axis.
// Two things keep it usable on real recordings. The axis can be log (a 40 s turn next to 2 ms handlers),
// negative times included (a headless SessionStart lands before Enter). And the rows are virtualized:
// a big turn has hundreds of spans, but only the ~30 on screen ever reach the DOM.
import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import { useWb, wb, wbClock } from './state'
import { queryType } from './query'
import { fmtInt, fmtMs, timeRange, type Waybill } from './types'

/** `lane` is a query-mode row: every batch of one type at one component, as posts per minute in segments (one per chapter). */
interface Lane { segs: { t0: number; v: number[]; bad: boolean }[]; count: number }
interface Row { id: string; sel: string; label: string; t0: number; t1: number; sync: boolean; status: string; kind: string; event?: boolean; ticks?: number[]; lane?: Lane; ids?: string[] }
/** `folded` holds the routine rows (a model call's usage / allowance notes that were only filed and collected): one summary row, open on demand. */
interface Group { id: string; name: string; rows: Row[]; folded: Row[]; t0: number; /** the number on the header (events, in query mode) */ count?: number; foldLabel?: string }

/** A usage / allowance note nobody did anything with except file it: 2 of them per model call is noise by default. */
function routineUsage(e: Waybill['events'][number]): boolean {
  if (!/\.llm\.(usage|allowance)\./.test(e.type)) return false
  return e.consumers.every((c) => c.evidence !== 'observed' || (/^(candystore|holocene)/.test(c.component) && (c.outcome === 'archived' || c.outcome === 'collected')))
}

const MINUTE = 60000
const num = (v: unknown) => (typeof v === 'number' && Number.isFinite(v) ? v : 0)

/** Query mode: a 'Chapters' group, then one group per component, busiest first. A component's batches are lanes (one row per
 *  type: posts per minute, drawn as one SVG path, not a node per note); its failures stay as rows; its rare kept notes fold. */
function buildQueryRows(w: Waybill): Group[] {
  const by = new Map<string, Group>()
  const g = (id: string) => by.get(id) ?? by.set(id, { id, name: w.components[id]?.name ?? id, rows: [], folded: [], t0: Infinity, count: 0 }).get(id)!
  const chapters: Group = { id: '·chapters', name: 'Chapters', rows: [], folded: [], t0: -1, count: 0 }
  const lanes = new Map<string, Row>()
  const chStart = new Map<string, number>()
  for (const s of w.spans) if (s.kind === 'chapter') chStart.set(s.id, s.t0)
  const pubOf = new Map<string, string>()
  for (const s of w.spans) if (s.kind === 'publish' && typeof s.refs?.event_id === 'string') pubOf.set(s.refs.event_id, s.component)
  for (const s of w.spans) {
    if (s.kind === 'chapter') {
      chapters.rows.push({ id: s.id, sel: s.id, label: s.name, t0: s.t0, t1: s.t1 ?? s.t0, sync: false, status: s.status, kind: 'chapter' })
      chapters.count!++
    } else if (s.kind === 'batch') {
      const a = s.attrs ?? {}
      const pm = Array.isArray(a.per_minute) ? a.per_minute.map(num) : []
      const type = queryType(String(a.type ?? s.name))
      const key = `${s.component}|${type}`
      const gr = g(s.component)
      let lane = lanes.get(key)
      if (!lane) {
        lane = { id: `lane:${key}`, sel: s.id, label: type, t0: s.t0, t1: s.t1 ?? s.t0, sync: false, status: 'ok', kind: 'batch', lane: { segs: [], count: 0 }, ids: [] }
        lanes.set(key, lane)
        gr.rows.push(lane)
      }
      // per_minute[0] is the chapter's first minute; the chapter span's t0 anchors it
      lane.lane!.segs.push({ t0: (s.parent ? chStart.get(s.parent) : undefined) ?? s.t0, v: pm, bad: num(a.failed) > 0 })
      lane.lane!.count += num(a.count)
      lane.ids!.push(s.id)
      lane.t0 = Math.min(lane.t0, s.t0); lane.t1 = Math.max(lane.t1, s.t1 ?? s.t0)
      if (num(a.failed) > 0) lane.status = 'failed'
      gr.count! += num(a.count)
    } else if (s.kind !== 'publish' && s.kind !== 'prompt' && s.kind !== 'turn') {
      g(s.component).rows.push({ id: s.id, sel: s.id, label: s.name, t0: s.t0, t1: s.t1 ?? s.t0, sync: !!s.sync, status: s.status, kind: s.kind })
    }
  }
  for (const lane of lanes.values()) lane.label = `${lane.label} · ${fmtInt(lane.lane!.count)}`
  for (const e of w.events) {
    const dead = e.consumers.some((c) => c.outcome === 'dropped' && /candystore/.test(c.name))
    const comp = pubOf.get(e.id) ?? 'unknown'
    const failed = dead || /(failed|exhausted|denied|breached)/.test(e.type)
    const gr = g(dead ? 'candystore' : comp)
    gr.count!++
    const row: Row = { id: `evt:${e.id}`, sel: `evt:${e.id}`, label: queryType(e.type) + (dead ? ' · returned' : ''), t0: e.t, t1: e.t, sync: false, status: failed ? 'failed' : 'ok', kind: 'event', event: true, ticks: [] }
    ;(failed ? gr.rows : gr.folded).push(row)
    gr.t0 = Math.min(gr.t0, e.t)
  }
  const out = [...by.values()].filter((x) => x.rows.length || x.folded.length)
  out.forEach((x) => { x.foldLabel = `${fmtInt(x.folded.length)} rare notes kept as themselves`; x.folded.sort((a, b) => a.t0 - b.t0); x.rows.sort((a, b) => (b.lane?.count ?? -1) - (a.lane?.count ?? -1) || a.t0 - b.t0) })
  out.sort((a, b) => (b.count ?? 0) - (a.count ?? 0) || a.name.localeCompare(b.name))
  return chapters.rows.length ? [chapters, ...out] : out
}

/** One lane as an SVG path over the axis: posts per minute, bucketed to ~400 cells, tallest bucket fills the lane. */
function lanePaths(lane: Lane, x: (t: number) => number): { ok: string; bad: string } {
  const NB = 400
  const ok = new Float32Array(NB), bad = new Float32Array(NB)
  for (const seg of lane.segs) {
    const arr = seg.bad ? bad : ok
    for (let i = 0; i < seg.v.length; i++) {
      const v = seg.v[i]
      if (!v) continue
      const p = x(seg.t0 + i * MINUTE)
      if (p < 0 || p > 1) continue
      arr[Math.min(NB - 1, Math.floor(p * NB))] += v
    }
  }
  let peak = 1
  for (let k = 0; k < NB; k++) peak = Math.max(peak, ok[k] + bad[k])
  const path = (arr: Float32Array) => {
    let d = ''
    for (let k = 0; k < NB; k++) if (arr[k]) { const h = Math.max(1.5, (arr[k] / peak) * 18); d += `M${(k * 1000) / NB} 20v${-h.toFixed(1)}h${(1000 / NB).toFixed(2)}v${h.toFixed(1)}z` }
    return d
  }
  return { ok: path(ok), bad: path(bad) }
}

export function buildRows(w: Waybill): Group[] {
  if (w.recorder.mode === 'query') return buildQueryRows(w)
  const by = new Map<string, Group>()
  const g = (id: string) => by.get(id) ?? by.set(id, { id, name: w.components[id]?.name ?? id, rows: [], folded: [], t0: Infinity }).get(id)!
  const put = (id: string, r: Row, fold = false) => { const x = g(id); (fold ? x.folded : x.rows).push(r); x.t0 = Math.min(x.t0, r.t0) }
  for (const s of w.spans) {
    if (s.kind === 'turn') continue
    put(s.component, { id: s.id, sel: s.id, label: s.name, t0: s.t0, t1: s.t1 ?? s.t0, sync: !!s.sync, status: s.status, kind: s.kind })
  }
  for (const e of w.events) {
    let end = Math.max(e.t, e.archived ?? e.t)
    const ticks: number[] = []
    for (const c of e.consumers) { const t = c.t ?? e.t; ticks.push(t); if (t > end) end = t }
    put('bb-nats', { id: `evt:${e.id}`, sel: `evt:${e.id}`, label: e.type.replace(/^bloodbank\./, ''), t0: e.t, t1: end, sync: false, status: 'ok', kind: 'event', event: true, ticks }, routineUsage(e))
  }
  const out = [...by.values()].filter((x) => x.rows.length || x.folded.length)
  out.forEach((x) => { x.rows.sort((a, b) => a.t0 - b.t0); x.folded.sort((a, b) => a.t0 - b.t0) })
  return out.sort((a, b) => a.t0 - b.t0)
}

const LOG_TAU = 40
const ROW_H = 20
const OVERSCAN = 8
type Axis = { x: (t: number) => number; ticks: { at: number; label: string }[] }

/** Symmetric log: a few ms and a few seconds both get room, and a negative time mirrors a positive one. */
const slog = (t: number) => Math.sign(t) * Math.log1p(Math.abs(t) / LOG_TAU)

/** Drop tick labels that would overprint: keep one only if it clears the last kept one by `minPx`. */
function thin(ticks: Axis['ticks'], widthPx: number, minPx = 64): Axis['ticks'] {
  const gap = minPx / Math.max(200, widthPx)
  const out: Axis['ticks'] = []
  let last = -Infinity
  for (const t of ticks) if (t.at - last >= gap) { out.push(t); last = t.at }
  return out
}

export function axisFor(zoom: 'fit' | 'stop' | 'log', lo: number, hi: number, st: { t0: number; t1: number } | undefined, widthPx = 800): Axis {
  if (zoom === 'log') {
    const a = slog(lo), span = Math.max(1e-6, slog(hi) - a)
    const x = (t: number) => (slog(t) - a) / span
    const marks = [0]
    for (let m = 10; m <= Math.max(Math.abs(lo), hi) * 1.001; m *= m < 1000 ? 10 : m < 10000 ? 10 : 6) marks.push(m, -m)
    marks.push(...[60000, 300000].filter((m) => m <= hi * 1.001 && !marks.includes(m)))
    const ticks = [...new Set(marks)].filter((m) => m >= lo && m <= hi).sort((p, q) => p - q).map((m) => ({ at: x(m), label: m === 0 ? '0' : (m > 0 ? '' : '−') + fmtMs(Math.abs(m)) }))
    return { x, ticks }
  }
  let a = lo, b = hi
  if (zoom === 'stop' && st) {
    const pad = Math.max(20, (st.t1 - st.t0) * 0.15)
    a = Math.max(lo, st.t0 - pad)
    b = Math.min(hi, st.t1 + pad)
    if (b - a < 60) b = a + 60
  }
  const span = Math.max(1, b - a)
  const raw = span / 5
  const mag = Math.pow(10, Math.floor(Math.log10(raw)))
  const step = [1, 2, 5, 10].map((m) => m * mag).find((s) => s >= raw) ?? raw
  const ticks: Axis['ticks'] = []
  for (let t = Math.ceil(a / step) * step; t <= b + 1e-6; t += step) ticks.push({ at: (t - a) / span, label: fmtMs(t) })
  return { x: (t) => (t - a) / span, ticks: thin(ticks, widthPx) }
}

const clamp = (v: number) => Math.max(0, Math.min(1, v))

type Item = { key: string; head: Group } | { key: string; row: Row } | { key: string; fold: Group; open: boolean }

export function Waterfall({ compact }: { compact: boolean }) {
  const w = useWb((s) => s.waybill)!
  const dir = useWb((s) => s.dir)!
  const si = useWb((s) => s.stop)
  const sel = useWb((s) => s.sel)
  const zoom = useWb((s) => s.zoom)
  const groups = useMemo(() => buildRows(w), [w])
  const [shut, setShut] = useState<Set<string>>(new Set())
  const stop = dir.stops[si]
  const { min: lo, max: hi } = useMemo(() => timeRange(w), [w])
  // the track's pixel width decides how many axis labels fit (rounded so a resize does not rebuild the axis every pixel)
  const [trackW, setTrackW] = useState(800)
  const axis = useMemo(() => axisFor(zoom, lo, hi, stop && stop.kind !== 'end' ? stop : undefined, trackW), [zoom, lo, hi, stop, trackW])
  const [unfold, setUnfold] = useState<Set<string>>(new Set())
  const head = useRef<HTMLDivElement>(null)
  const inStop = useMemo(() => new Set(stop?.spanIds ?? []), [stop])
  const inStopEv = useMemo(() => new Set((stop?.eventIds ?? []).map((e) => `evt:${e}`)), [stop])

  // flat, fixed-height items: group headers and the rows of the groups that are open
  const items = useMemo<Item[]>(() => {
    const out: Item[] = []
    for (const gr of groups) {
      out.push({ key: `g:${gr.id}`, head: gr })
      if (shut.has(gr.id)) continue
      for (const r of gr.rows) out.push({ key: r.id, row: r })
      if (gr.folded.length) {
        const open = unfold.has(gr.id)
        out.push({ key: `f:${gr.id}`, fold: gr, open })
        if (open) for (const r of gr.folded) out.push({ key: r.id, row: r })
      }
    }
    return out
  }, [groups, shut, unfold])

  // the viewport: scrollTop and height are state, so only the rows in view are rendered
  const scroller = useRef<HTMLDivElement>(null)
  const [view, setView] = useState({ top: 0, h: 240 })
  useLayoutEffect(() => {
    const el = scroller.current
    if (!el) return
    const read = () => {
      setView((v) => (v.top === el.scrollTop && v.h === el.clientHeight ? v : { top: el.scrollTop, h: el.clientHeight }))
      setTrackW(Math.round((el.clientWidth - (el.clientWidth < 520 ? 96 : 170)) / 40) * 40)
    }
    read()
    const ro = new ResizeObserver(read)
    ro.observe(el)
    return () => ro.disconnect()
  }, [])
  const scrollToRow = (i: number) => {
    const el = scroller.current
    if (!el || i < 0) return
    const y = i * ROW_H
    if (y < el.scrollTop + ROW_H || y + ROW_H * 2 > el.scrollTop + el.clientHeight) el.scrollTop = Math.max(0, y - ROW_H * 2)
  }
  // follow the story: bring the stop's own span row into view when the stop changes. Spans first, in the stop's order
  // (an llm stop must land on its model-call bar, not on an event row that happens to sort earlier); events only when the stop has no span rows.
  useEffect(() => {
    const at = new Map<string, number>()
    items.forEach((it, i) => { if ('row' in it) at.set(it.row.id, i) })
    let i = -1
    for (const id of stop?.spanIds ?? []) { if (at.has(id)) { i = at.get(id)!; break } }
    if (i < 0) for (const id of stop?.eventIds ?? []) { if (at.has(`evt:${id}`)) { i = at.get(`evt:${id}`)!; break } }
    scrollToRow(i)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stop])
  // a selection (a click on a bar, a link in the inspector, the Inspect button) is brought into view too, opening its group first
  useEffect(() => {
    if (!sel) return
    const owner = groups.find((g) => g.rows.some((r) => r.sel === sel) || g.folded.some((r) => r.sel === sel))
    if (owner) {
      if (shut.has(owner.id)) setShut((p) => { const n = new Set(p); n.delete(owner.id); return n })
      if (owner.folded.some((r) => r.sel === sel) && !unfold.has(owner.id)) setUnfold((p) => new Set(p).add(owner.id))
    }
    const i = items.findIndex((it) => 'row' in it && it.row.sel === sel)
    scrollToRow(i)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sel, items.length])

  // the playhead moves by rAF, straight on the DOM: no React re-render per frame
  useEffect(() => {
    let id = 0
    const tick = () => {
      if (head.current) head.current.style.left = `${clamp(axis.x(wbClock.t)) * 100}%`
      id = requestAnimationFrame(tick)
    }
    tick()
    return () => cancelAnimationFrame(id)
  }, [axis])
  const bandL = stop && stop.kind !== 'end' ? clamp(axis.x(stop.t0)) : 0
  const bandR = stop && stop.kind !== 'end' ? clamp(axis.x(Math.max(stop.t1, stop.t0 + 1))) : 0

  const bar = (r: Row) => {
    const l = clamp(axis.x(r.t0)), rr = clamp(axis.x(r.t1))
    return { left: `${l * 100}%`, width: `max(5px, ${(rr - l) * 100}%)` }
  }
  const first = Math.max(0, Math.floor(view.top / ROW_H) - OVERSCAN)
  const last = Math.min(items.length, Math.ceil((view.top + view.h) / ROW_H) + OVERSCAN)
  const body = (
    <div className="wf-body">
      <div className="wf-axis">
        <div className="wf-lab" />
        <div className="wf-track">
          {axis.ticks.map((t) => <span key={t.label + t.at} style={t.at > 0.94 ? { right: 0, left: 'auto', transform: 'none' } : { left: `${t.at * 100}%` }}>{t.label}</span>)}
        </div>
      </div>
      <div className="wf-rows" ref={scroller} onScroll={(e) => { const top = e.currentTarget.scrollTop; setView((v) => (v.top === top ? v : { ...v, top })) }}>
        <div className="wf-content" style={{ height: items.length * ROW_H }}>
          <div className="wf-over"><div className="wf-over-in">
            <div className="wf-band" style={{ left: `${bandL * 100}%`, width: `${Math.max(0.3, (bandR - bandL) * 100)}%` }} />
            <div className="wf-head" ref={head} />
          </div></div>
          {items.slice(first, last).map((it, k) => {
            const top = (first + k) * ROW_H
            if ('head' in it) {
              const gr = it.head, closed = shut.has(gr.id)
              return (
                <div key={it.key} className="wf-slot" style={{ top }}>
                  <button className="wf-ghead" onClick={() => setShut((p) => { const n = new Set(p); n.has(gr.id) ? n.delete(gr.id) : n.add(gr.id); return n })} aria-expanded={!closed}>
                    <span className="wf-caret">{closed ? '▸' : '▾'}</span>
                    <b>{gr.name}</b>
                    <em>{gr.count !== undefined ? fmtInt(gr.count) : gr.rows.length}</em>
                  </button>
                </div>
              )
            }
            if ('fold' in it) {
              const gr = it.fold
              return (
                <div key={it.key} className="wf-slot" style={{ top }}>
                  <button className="wf-fold" onClick={() => setUnfold((p) => { const n = new Set(p); n.has(gr.id) ? n.delete(gr.id) : n.add(gr.id); return n })} aria-expanded={it.open}>
                    <span className="wf-caret">{it.open ? '▾' : '▸'}</span>
                    {gr.foldLabel ?? `${gr.folded.length} routine usage notes (filed and collected only)`} {it.open ? '· hide' : '· show'}
                  </button>
                </div>
              )
            }
            const r = it.row
            const act = inStop.has(r.id) || inStopEv.has(r.id) || !!r.ids?.some((id) => inStop.has(id))
            return (
              <div key={it.key} className={`wf-row wf-slot${act ? ' on' : ''}${sel === r.sel ? ' sel' : ''}`} style={{ top }} onClick={() => wb.jump(r.sel)} role="button" tabIndex={0} onKeyDown={(e) => { if (e.key === 'Enter') wb.jump(r.sel) }}>
                <div className="wf-lab" title={r.label}>{r.label}</div>
                <div className="wf-track">
                  {r.lane ? <LaneSvg lane={r.lane} x={axis.x} title={r.label} /> : r.event ? (
                    <>
                      <i className="wf-ev" style={{ left: `${clamp(axis.x(r.t0)) * 100}%` }} />
                      {r.ticks?.slice(0, 40).map((t, i) => <i key={i} className="wf-tick" style={{ left: `${clamp(axis.x(t)) * 100}%` }} />)}
                    </>
                  ) : (
                    <span className={`wf-bar s-${r.status} ${r.sync ? 'sync' : 'async'}`} style={bar(r)} title={`${r.label} · ${fmtMs(r.t1 - r.t0)}`} />
                  )}
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
  return (
    <div className={`wf${compact ? ' compact' : ''}`}>
      <div className="wf-bar-top">
        <b>Waterfall</b>
        {dir.query ? <span className="wf-leg"><i className="lg async" />posts per minute</span> : <span className="wf-leg"><i className="lg sync" />waited on</span>}
        {!dir.query && <span className="wf-leg"><i className="lg async" />alongside</span>}
        <span className="wf-leg"><i className="lg bad" />failed</span>
        <span className="wf-sp" />
        {(dir.query ? (['fit', 'stop'] as const) : (['fit', 'stop', 'log'] as const)).map((z) => (
          <button key={z} className={`wf-z${zoom === z ? ' on' : ''}`} onClick={() => useWb.setState({ zoom: z })}>{z === 'fit' ? (dir.query ? 'whole window' : 'linear') : z === 'stop' ? 'fit stop' : 'log'}</button>
        ))}
      </div>
      {body}
    </div>
  )
}

function LaneSvg({ lane, x, title }: { lane: Lane; x: (t: number) => number; title: string }) {
  const p = useMemo(() => lanePaths(lane, x), [lane, x])
  return (
    <svg className="wbq-lane" viewBox="0 0 1000 20" preserveAspectRatio="none" role="img" aria-label={title}>
      <title>{title}</title>
      <path d={p.ok} />{p.bad && <path className="bad" d={p.bad} />}
    </svg>
  )
}

/** The phone's mini-strip: one thin lane per group, tap to open the full waterfall. A busy lane is bucketed so it stays a handful of DOM nodes. */
export function MiniStrip({ onOpen }: { onOpen: () => void }) {
  const w = useWb((s) => s.waybill)!
  const dir = useWb((s) => s.dir)!
  const si = useWb((s) => s.stop)
  const groups = useMemo(() => buildRows(w), [w])
  const { min: lo, max: hi } = useMemo(() => timeRange(w), [w])
  const axis = useMemo(() => axisFor(dir.query ? 'fit' : 'log', lo, hi, undefined), [lo, hi, dir.query])
  const x = (t: number) => clamp(axis.x(t))
  const lanes = useMemo(() => {
    const BUCKETS = 240
    return groups.slice(0, 9).map((g) => {
      const cells = new Map<number, { l: number; r: number; status: string; sync: boolean }>()
      for (const r of g.rows) {
        const l = clamp(axis.x(r.t0)), rr = clamp(axis.x(r.t1))
        const k = Math.floor(l * BUCKETS)
        const c = cells.get(k)
        if (!c) cells.set(k, { l, r: rr, status: r.status, sync: r.sync })
        else { c.r = Math.max(c.r, rr); if (!/^(ok|done)$/.test(r.status)) c.status = r.status; c.sync = c.sync || r.sync }
      }
      return { id: g.id, cells: [...cells.entries()] }
    })
  }, [groups, axis])
  const head = useRef<HTMLDivElement>(null)
  useEffect(() => {
    let id = 0
    const tick = () => { if (head.current) head.current.style.left = `${x(wbClock.t) * 100}%`; id = requestAnimationFrame(tick) }
    tick()
    return () => cancelAnimationFrame(id)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [axis])
  const stop = dir.stops[si]
  return (
    <button className="wf-mini" onClick={onOpen} aria-label="Open the waterfall">
      <div className="wf-mini-in">
        {lanes.map((ln) => (
          <div key={ln.id} className="wf-lane">
            {ln.cells.map(([k, c]) => <span key={k} className={`wf-bar s-${c.status} ${c.sync ? 'sync' : 'async'}`} style={{ left: `${c.l * 100}%`, width: `max(3px, ${(c.r - c.l) * 100}%)` }} />)}
          </div>
        ))}
        {stop && stop.kind !== 'end' && <div className="wf-band" style={{ left: `${x(stop.t0) * 100}%`, width: `max(1%, ${(x(stop.t1) - x(stop.t0)) * 100}%)` }} />}
        <div className="wf-head" ref={head} />
      </div>
      <span className="wf-mini-hint">{dir.query ? 'waterfall ▴ (whole window)' : 'waterfall ▴ (log scale)'}</span>
    </button>
  )
}
