// The waybill HUD: header, stop card, transport, waterfall, inspector and the end card.
import { useEffect, useState } from 'react'
import { Inspector } from './Inspector'
import { PlayWaybillButton } from './Picker'
import { placeName } from './stations'
import { useWb, wb } from './state'
import { MiniStrip, Waterfall } from './Waterfall'
import { fmtInt, fmtMs, short } from './types'
import type { Stop } from './director'

const RATES = [0.5, 1, 2, 4]

function usePhone() {
  const [p, setP] = useState(() => matchMedia('(max-width: 720px)').matches)
  useEffect(() => {
    const m = matchMedia('(max-width: 720px)')
    const f = () => setP(m.matches)
    m.addEventListener('change', f)
    return () => m.removeEventListener('change', f)
  }, [])
  return p
}

function Header() {
  const w = useWb((s) => s.waybill)!
  const dir = useWb((s) => s.dir)!
  const warnings = useWb((s) => s.warnings)
  const broken = w.findings.filter((f) => f.severity === 'broken').length
  const warn = w.findings.filter((f) => f.severity === 'warn').length
  const tin = w.stats.tokens_in, tout = w.stats.tokens_out
  const o = w.origin
  return (
    <div className="wb-head card">
      <div className="wb-title">
        <b title={w.title}>{w.title}</b>
        <span>{[o.cli, o.surface, o.project, short(o.session_id)].filter(Boolean).join(' · ')}</span>
      </div>
      <div className="wb-meta">
        <span title="From Enter to the last thing we saw">{fmtMs(w.clock.duration_ms)}</span>
        {tin !== undefined && <span title="Tokens in / out, all model calls">{fmtInt(tin)} in · {fmtInt(tout ?? 0)} out</span>}
        <button className={`wb-find${broken ? ' bad' : warn ? ' warn' : ''}`} onClick={() => wb.go(dir.stops.length - 1)} title="What did not happen">
          {broken ? `${broken} broken` : warn ? `${warn} warning${warn > 1 ? 's' : ''}` : `${w.findings.length} finding${w.findings.length === 1 ? '' : 's'}`}
        </button>
        {warnings.length > 0 && <span className="wb-warn" title={warnings.join('\n')}>{warnings.length} note{warnings.length > 1 ? 's' : ''} on the file</span>}
        <PlayWaybillButton className="wb-ghost" />
        <button className="wb-leave" onClick={() => wb.leave()} title="Leave (Esc)">Leave <kbd>Esc</kbd></button>
      </div>
    </div>
  )
}

function StopCard({ stop, n, total }: { stop: Stop; n: number; total: number }) {
  const dir = useWb((s) => s.dir)!
  const w = useWb((s) => s.waybill)!
  const [more, setMore] = useState(false)
  useEffect(() => setMore(false), [stop.id])
  const names = stop.components.map((c) => w.components[c]?.name ?? c)
  return (
    <div className="wb-stop card" key={stop.id}>
      <div className="wb-stop-top">
        <span className="chip">stop {n} of {total}</span>
        {stop.kind !== 'end' && <span className="wb-time">+{fmtMs(stop.t0)}{stop.t1 > stop.t0 ? ` → +${fmtMs(stop.t1)} · ${fmtMs(stop.t1 - stop.t0)}` : ''}</span>}
      </div>
      <h3>{stop.title}</h3>
      <p>{stop.caption}</p>
      {(stop.detail || stop.tag) && (
        <div className="wb-real">
          {stop.detail && <div className="wb-detail">{stop.detail}</div>}
          {stop.tag && <code className="wb-tag">{stop.tag}</code>}
        </div>
      )}
      {stop.waited && stop.waitedMs > 0 && <div className="wb-wait">The prompt waited here <b>{fmtMs(stop.waitedMs)}</b></div>}
      {stop.side && <div className="wb-side">{stop.afterReply ? 'After the answer was finished: nobody waited for this.' : 'Alongside: nobody waited for this.'}</div>}
      {stop.inferred && <div className="wb-inf">Drawn from inference: no source recorded this part.</div>}
      {stop.notes.length > 0 && (
        <>
          <ul className="wb-notes">{(more ? stop.notes : stop.notes.slice(0, 2)).map((t, i) => <li key={i}>{t}</li>)}</ul>
          {stop.notes.length > 2 && <button className="wb-more" onClick={() => setMore(!more)}>{more ? 'Less' : `${stop.notes.length - 2} more`}</button>}
        </>
      )}
      <div className="wb-chips">
        {names.slice(0, 7).map((c, i) => <code key={i}>{c}</code>)}
        <span>{placeName(stop.set, dir.placement)}</span>
      </div>
      {(stop.spanIds.length + stop.eventIds.length > 0) && (
        <button className="wb-open" onClick={() => wb.select(stop.spanIds[0] ?? `evt:${stop.eventIds[0]}`)}>Inspect</button>
      )}
    </div>
  )
}

function EndCard() {
  const w = useWb((s) => s.waybill)!
  const dir = useWb((s) => s.dir)!
  const stop = dir.stops[dir.stops.length - 1]
  return (
    <div className="wb-end">
      <div className="wb-end-card">
        <div className="eyebrow">The end of the waybill</div>
        <h2>{stop.title}</h2>
        <p className="muted">{stop.caption}</p>
        {w.findings.length > 0 && <h4>Findings</h4>}
        <ul className="wb-fl">
          {w.findings.map((f, i) => (
            <li key={i} className={`f-${f.severity}`}>
              <span className="sev">{f.severity}</span>
              <div><b>{f.title}</b><p>{f.detail}</p>
                <code>{w.components[f.component]?.name ?? f.component}</code>
                {f.evidence.slice(0, 3).map((e) => <a key={e} onClick={() => wb.jump(e)}>{w.spans.find((s) => s.id === e)?.name ?? short(e, 22)}</a>)}
              </div>
            </li>
          ))}
        </ul>
        {w.gaps.length > 0 && <h4>Gaps: what the recorder could not see</h4>}
        <ul className="wb-fl">
          {w.gaps.map((g, i) => (
            <li key={i} className="f-gap"><span className="sev">gap</span><div><b>{g.what}</b><p>{g.why}</p><code>{w.components[g.component]?.name ?? g.component}</code></div></li>
          ))}
        </ul>
        <div className="wb-end-actions">
          <button className="primary" onClick={() => wb.replay()}>Replay</button>
          <button className="ghost" onClick={() => wb.explore()}>Explore the floor</button>
        </div>
      </div>
    </div>
  )
}

function Transport() {
  const dir = useWb((s) => s.dir)!
  const si = useWb((s) => s.stop)
  const playing = useWb((s) => s.playing)
  const rate = useWb((s) => s.rate)
  return (
    <div className="wb-tr" onClick={(e) => (e.target as HTMLElement).closest('button')?.blur()}>
      <button onClick={() => wb.prev()} disabled={si === 0} aria-label="Previous stop">⏮</button>
      <button className="wb-play" onClick={() => wb.toggle()} aria-label={playing ? 'Pause' : 'Play'}>{playing ? '❚❚' : '▶'}</button>
      <button onClick={() => wb.next()} disabled={si >= dir.stops.length - 1} aria-label="Next stop">⏭</button>
      <select value={rate} onChange={(e) => wb.setRate(Number(e.target.value))} aria-label="Speed">
        {RATES.map((r) => <option key={r} value={r}>{r}×</option>)}
      </select>
      <div className="wb-dots" role="tablist" aria-label="Stops">
        {dir.stops.map((s, i) => (
          <button key={s.id} role="tab" aria-selected={i === si} aria-label={`Stop ${i + 1}: ${s.title}`} title={`${i + 1}. ${s.title}`}
            className={`${i < si ? 'past' : i === si ? 'now' : ''}${s.problems.length ? ' bad' : ''}${s.side ? ' side' : ''}`}
            onClick={() => wb.go(i)} />
        ))}
      </div>
      <span className="wb-keys">space · ← →</span>
    </div>
  )
}

export function WaybillHud() {
  const w = useWb((s) => s.waybill)
  const dir = useWb((s) => s.dir)
  const si = useWb((s) => s.stop)
  const sel = useWb((s) => s.sel)
  const phone = usePhone()
  const [open, setOpen] = useState(false)

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement | null
      if (t && /^(INPUT|SELECT|TEXTAREA)$/.test(t.tagName)) return
      const s = useWb.getState()
      if (e.key === 'Escape') {
        e.stopPropagation()
        if (s.sel) wb.select(null)
        else wb.leave()
      } else if (e.key === ' ' && t?.tagName !== 'BUTTON') { e.preventDefault(); wb.toggle() }
      else if (e.key === 'ArrowRight') { e.preventDefault(); wb.next() }
      else if (e.key === 'ArrowLeft') { e.preventDefault(); wb.prev() }
    }
    window.addEventListener('keydown', onKey, true)
    return () => window.removeEventListener('keydown', onKey, true)
  }, [])
  useEffect(() => setOpen(false), [si])
  if (!w || !dir) return null
  const stop = dir.stops[si]
  return (
    <div className={`wb-hud${sel ? ' has-insp' : ''}${phone ? ' phone' : ''}`}>
      <Header />
      {stop.kind === 'end' ? <EndCard /> : <StopCard stop={stop} n={si + 1} total={dir.stops.length} />}
      <Inspector />
      <div className="wb-bottom card">
        <Transport />
        {phone && !open ? <MiniStrip onOpen={() => setOpen(true)} /> : (
          <>
            {phone && <button className="wb-fold" onClick={() => setOpen(false)}>Fold the waterfall ▾</button>}
            <Waterfall compact={phone} />
          </>
        )}
      </div>
    </div>
  )
}
