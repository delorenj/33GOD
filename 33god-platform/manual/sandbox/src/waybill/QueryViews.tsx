// Query-mode pieces of the HUD: wall-clock times, the per-minute sparkline of a pallet, the bars of a chapter overview,
// the reasons on returned mail and the conservation sum. Plain SVG and divs, drawn from the director's stops.
import type { Conservation } from './query'
import type { Stop } from './director'
import { fmtInt, type Waybill } from './types'

/** The label's clock is the owner's (the file says 'last night, 18:02 to 07:41'): the sandbox shows it on the same one. */
const QUERY_TZ = 'America/New_York'
const hm = new Intl.DateTimeFormat('en-GB', { hour: '2-digit', minute: '2-digit', hourCycle: 'h23', timeZone: QUERY_TZ })
/** The wall-clock time of `ms` into a query window: '19:10'. */
export const wallAt = (w: Waybill, ms: number) => hm.format(new Date(Date.parse(w.clock.t0) + ms))
export const wallSpan = (w: Waybill, s: Stop) => (s.t1 > s.t0 + 59000 ? `${wallAt(w, s.t0)} to ${wallAt(w, s.t1)}` : wallAt(w, s.t0))

/** A pallet's posts per minute across its chapter, one bar per minute, with the busiest minute named. */
export function Sparkline({ stop, w }: { stop: Stop; w: Waybill }) {
  const b = stop.batch
  if (!b || !b.perMinute.length) return null
  const pm = b.perMinute
  const peak = Math.max(1, ...pm)
  const W = 300, H = 36, bw = W / pm.length
  const path = pm.map((v, i) => { const h = Math.max(v ? 1 : 0, (v / peak) * (H - 2)); return v ? `M${(i * bw).toFixed(2)} ${H}v${(-h).toFixed(2)}h${Math.max(0.6, bw - 0.4).toFixed(2)}v${h.toFixed(2)}z` : '' }).join('')
  const top = pm.indexOf(peak)
  return (
    <figure className="wbq-spark" aria-label={`Posts per minute, busiest minute ${fmtInt(peak)}`}>
      <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" role="img"><path d={path} /></svg>
      <figcaption><span>{wallAt(w, b.t0)}</span><b>{fmtInt(b.count)} notes · peak {fmtInt(peak)} a minute{top >= 0 ? ` at ${wallAt(w, b.t0 + top * 60000)}` : ''}</b><span>{wallAt(w, b.t0 + pm.length * 60000)}</span></figcaption>
    </figure>
  )
}

/** A chapter overview: a bar per station's pallet, scaled to the biggest. */
export function PalletBars({ stop }: { stop: Stop }) {
  const ps = stop.pallets
  if (!ps?.length) return null
  const max = Math.max(1, ...ps.map((p) => p.count))
  return (
    <ul className="wbq-bars">
      {ps.slice(0, 6).map((p) => (
        <li key={p.set} className={p.failed ? 'bad' : ''}>
          <span className="n">{p.name}</span>
          <span className="bar"><i style={{ width: `${Math.max(2, (p.count / max) * 100)}%` }} /></span>
          <b>{fmtInt(p.count)}</b>
        </li>
      ))}
    </ul>
  )
}

/** Why Candystore sent notes back: one line per reason with its count. */
export function Reasons({ stop }: { stop: Stop }) {
  const r = stop.returned
  if (!r) return null
  return <ul className="wbq-reasons">{r.reasons.map((x) => <li key={x.reason}><b>{fmtInt(x.count)}</b> {x.reason}</li>)}</ul>
}

/** kept + batched = matched + dead letters, with the verdict. */
export function ConservationSum({ c }: { c: Conservation }) {
  return (
    <div className={`wbq-cons${c.ok ? ' ok' : ' bad'}`} role="group" aria-label="Conservation of events">
      <div className="eq">
        <span><b>{fmtInt(c.kept)}</b> kept</span><i>+</i><span><b>{fmtInt(c.batched)}</b> in {fmtInt(c.batches)} pallets</span>
        <i>{c.ok ? '=' : '≠'}</i>
        <span><b>{fmtInt(c.total)}</b> matched</span><i>+</i><span><b>{fmtInt(c.dead)}</b> returned</span>
      </div>
      <div className="verdict">{c.ok ? 'Every event is accounted for.' : `Off by ${fmtInt(Math.abs(c.missing))}: ${c.missing > 0 ? 'missing' : 'counted twice'}.`}{c.fileOk !== null && c.fileOk !== c.ok ? ' The file disagrees with this count.' : ''}</div>
    </div>
  )
}
