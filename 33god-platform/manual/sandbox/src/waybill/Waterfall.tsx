// The DevTools-style waterfall: rows grouped by component, bars on the recording's real ms axis.
// Two things keep it usable on real recordings. The axis can be log (a 40 s turn next to 2 ms handlers),
// negative times included (a headless SessionStart lands before Enter). And the rows are virtualized:
// a big turn has hundreds of spans, but only the ~30 on screen ever reach the DOM.
import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import { useWb, wb, wbClock } from './state'
import { fmtMs, timeRange, type Waybill } from './types'

interface Row { id: string; sel: string; label: string; t0: number; t1: number; sync: boolean; status: string; kind: string; event?: boolean; ticks?: number[] }
interface Group { id: string; name: string; rows: Row[]; t0: number }

export function buildRows(w: Waybill): Group[] {
  const by = new Map<string, Group>()
  const g = (id: string) => by.get(id) ?? by.set(id, { id, name: w.components[id]?.name ?? id, rows: [], t0: Infinity }).get(id)!
  const put = (id: string, r: Row) => { const x = g(id); x.rows.push(r); x.t0 = Math.min(x.t0, r.t0) }
  for (const s of w.spans) {
    if (s.kind === 'turn') continue
    put(s.component, { id: s.id, sel: s.id, label: s.name, t0: s.t0, t1: s.t1 ?? s.t0, sync: !!s.sync, status: s.status, kind: s.kind })
  }
  for (const e of w.events) {
    let end = Math.max(e.t, e.archived ?? e.t)
    const ticks: number[] = []
    for (const c of e.consumers) { const t = c.t ?? e.t; ticks.push(t); if (t > end) end = t }
    put('bb-nats', { id: `evt:${e.id}`, sel: `evt:${e.id}`, label: e.type.replace(/^bloodbank\./, ''), t0: e.t, t1: end, sync: false, status: 'ok', kind: 'event', event: true, ticks })
  }
  const out = [...by.values()].filter((x) => x.rows.length)
  out.forEach((x) => x.rows.sort((a, b) => a.t0 - b.t0))
  return out.sort((a, b) => a.t0 - b.t0)
}

const LOG_TAU = 40
const ROW_H = 20
const OVERSCAN = 8
type Axis = { x: (t: number) => number; ticks: { at: number; label: string }[] }

/** Symmetric log: a few ms and a few seconds both get room, and a negative time mirrors a positive one. */
const slog = (t: number) => Math.sign(t) * Math.log1p(Math.abs(t) / LOG_TAU)

export function axisFor(zoom: 'fit' | 'stop' | 'log', lo: number, hi: number, st: { t0: number; t1: number } | undefined): Axis {
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
  return { x: (t) => (t - a) / span, ticks }
}

const clamp = (v: number) => Math.max(0, Math.min(1, v))

type Item = { key: string; head: Group } | { key: string; row: Row }

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
  const axis = useMemo(() => axisFor(zoom, lo, hi, stop && stop.kind !== 'end' ? stop : undefined), [zoom, lo, hi, stop])
  const head = useRef<HTMLDivElement>(null)
  const inStop = useMemo(() => new Set(stop?.spanIds ?? []), [stop])
  const inStopEv = useMemo(() => new Set((stop?.eventIds ?? []).map((e) => `evt:${e}`)), [stop])

  // flat, fixed-height items: group headers and the rows of the groups that are open
  const items = useMemo<Item[]>(() => {
    const out: Item[] = []
    for (const gr of groups) {
      out.push({ key: `g:${gr.id}`, head: gr })
      if (!shut.has(gr.id)) for (const r of gr.rows) out.push({ key: r.id, row: r })
    }
    return out
  }, [groups, shut])

  // the viewport: scrollTop and height are state, so only the rows in view are rendered
  const scroller = useRef<HTMLDivElement>(null)
  const [view, setView] = useState({ top: 0, h: 240 })
  useLayoutEffect(() => {
    const el = scroller.current
    if (!el) return
    const read = () => setView((v) => (v.top === el.scrollTop && v.h === el.clientHeight ? v : { top: el.scrollTop, h: el.clientHeight }))
    read()
    const ro = new ResizeObserver(read)
    ro.observe(el)
    return () => ro.disconnect()
  }, [])
  // follow the story: bring the active stop's first row into view when the stop changes
  useEffect(() => {
    const el = scroller.current
    if (!el) return
    const i = items.findIndex((it) => 'row' in it && (inStop.has(it.row.id) || inStopEv.has(it.row.id)))
    if (i < 0) return
    const y = i * ROW_H
    if (y < el.scrollTop || y + ROW_H > el.scrollTop + el.clientHeight) el.scrollTop = Math.max(0, y - ROW_H * 2)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stop])

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
                    <em>{gr.rows.length}</em>
                  </button>
                </div>
              )
            }
            const r = it.row
            const act = inStop.has(r.id) || inStopEv.has(r.id)
            return (
              <div key={it.key} className={`wf-row wf-slot${act ? ' on' : ''}${sel === r.sel ? ' sel' : ''}`} style={{ top }} onClick={() => wb.jump(r.sel)} role="button" tabIndex={0} onKeyDown={(e) => { if (e.key === 'Enter') wb.jump(r.sel) }}>
                <div className="wf-lab" title={r.label}>{r.label}</div>
                <div className="wf-track">
                  {r.event ? (
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
        <span className="wf-leg"><i className="lg sync" />waited on</span>
        <span className="wf-leg"><i className="lg async" />alongside</span>
        <span className="wf-leg"><i className="lg bad" />failed</span>
        <span className="wf-sp" />
        {(['fit', 'stop', 'log'] as const).map((z) => (
          <button key={z} className={`wf-z${zoom === z ? ' on' : ''}`} onClick={() => useWb.setState({ zoom: z })}>{z === 'fit' ? 'linear' : z === 'stop' ? 'fit stop' : 'log'}</button>
        ))}
      </div>
      {body}
    </div>
  )
}

/** The phone's mini-strip: one thin lane per group, tap to open the full waterfall. A busy lane is bucketed so it stays a handful of DOM nodes. */
export function MiniStrip({ onOpen }: { onOpen: () => void }) {
  const w = useWb((s) => s.waybill)!
  const dir = useWb((s) => s.dir)!
  const si = useWb((s) => s.stop)
  const groups = useMemo(() => buildRows(w), [w])
  const { min: lo, max: hi } = useMemo(() => timeRange(w), [w])
  const axis = useMemo(() => axisFor('log', lo, hi, undefined), [lo, hi])
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
      <span className="wf-mini-hint">waterfall ▴ (log scale)</span>
    </button>
  )
}
