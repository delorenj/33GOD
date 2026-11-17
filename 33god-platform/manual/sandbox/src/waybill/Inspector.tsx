// The inspector: everything the waybill recorded about one span or one bus event.
import { useMemo, useState } from 'react'
import { DockGrip, useDock } from '../ui/dock'
import { usePhone } from '../ui/usePhone'
import { placeName } from './stations'
import { useWb, wb } from './state'
import { fmtMs, fmtInt, fmtT, short, type Artifact, type BusEvent, type Span, type Waybill } from './types'

const PAYLOAD_CAP = 1800

function Payload({ id, w }: { id: string | undefined; w: Waybill }) {
  const a: Artifact | undefined = id ? w.artifacts[id] : undefined
  if (!id) return null
  if (!a) return <p className="wbi-note">Payload <code>{id}</code> is not in this file.</p>
  let text = a.text ?? (a.json !== undefined ? JSON.stringify(a.json, null, 2) : '')
  const cut = text.length > PAYLOAD_CAP
  if (cut) text = text.slice(0, PAYLOAD_CAP)
  return (
    <div className="wbi-payload">
      <div className="wbi-ph"><b>Payload</b><span>{a.mime} · {fmtInt(a.bytes)} bytes{a.truncated ? ' · truncated by the recorder' : ''}</span></div>
      {text ? <pre>{text}{cut ? '\n… (preview cut)' : ''}</pre> : <p className="wbi-note">{a.note ?? 'No text was stored for this one.'}</p>}
      {a.text && a.note && <p className="wbi-note">{a.note}</p>}
    </div>
  )
}

/** An id, cut to 8 characters; click copies the whole thing. */
function Id({ id }: { id: string }) {
  const [done, setDone] = useState(false)
  const copy = () => { try { void navigator.clipboard?.writeText(id).then(() => { setDone(true); setTimeout(() => setDone(false), 1200) }) } catch { /* no clipboard here */ } }
  return <code className="wbi-id" title={`${id}\n(click to copy)`} onClick={copy} role="button" tabIndex={0} onKeyDown={(e) => { if (e.key === 'Enter') copy() }}>{done ? 'copied' : short(id, 8)}</code>
}

/** 'before'/'after' in words for a gap between two stamps. */
const later = (d: number) => (d < 0 ? `${fmtMs(-d)} earlier` : `${fmtMs(d)} later`)

function Row({ k, v, hint }: { k: string; v: React.ReactNode; hint?: string }) {
  return <><dt title={hint}>{k}</dt><dd>{v}</dd></>
}

function SpanView({ s, w }: { s: Span; w: Waybill }) {
  const dir = useWb((x) => x.dir)!
  const set = dir.placement.setOf[s.component] ?? 'dock'
  const comp = w.components[s.component]
  const r = s.refs ?? {}
  const attrs = Object.entries(s.attrs ?? {})
  return (
    <>
      <h3>{s.name}</h3>
      <div className="wbi-sub"><code>{s.component}</code> · {comp?.name ?? s.component} <span>({placeName(set, dir.placement)})</span></div>
      <div className="wbi-badges">
        <span className={`wbi-b s-${s.status}`}>{s.status}{s.reason ? `: ${s.reason}` : ''}</span>
        <span className="wbi-b">{s.sync ? 'the prompt waited' : 'alongside'}</span>
        <span className="wbi-b">{s.kind}</span>
        {!comp?.registry && <span className="wbi-b dim">not in the registry</span>}
      </div>
      <p className="wbi-sum">{s.summary}</p>
      <dl>
        <Row k="when" v={`${fmtT(s.t0)}${s.t1 !== null && s.t1 > s.t0 ? `, for ${fmtMs(s.t1 - s.t0)}` : ''}`} hint="on the recording's clock: 0 is Enter" />
        <Row k="who" v={comp?.name ?? s.component} />
        <Row k="outcome" v={`${s.status}${s.reason ? `: ${s.reason}` : ''}`} />
        {r.event_id && <Row k="note" v={<a onClick={() => wb.jump(`evt:${r.event_id}`)}>open the note on the belt</a>} />}
        {s.parent && <Row k="inside" v={<a onClick={() => wb.jump(s.parent!)}>{s.parent.length > 30 ? short(s.parent, 28) + '…' : s.parent}</a>} />}
      </dl>
      <details className="wbi-det">
        <summary>Details</summary>
        <dl>
          <Row k="starts" v={fmtT(s.t0)} />
          {s.t1 !== null && <Row k="ends" v={fmtT(s.t1)} />}
          {r.invocation_id && <Row k="invocation" v={<Id id={String(r.invocation_id)} />} hint="hook-hub's id for this one hook call" />}
          {r.event_id && <Row k="event id" v={<Id id={String(r.event_id)} />} hint="the event id" />}
          {r.seq !== undefined && <Row k="belt number" v={`#${r.seq}`} hint="the stream sequence" />}
          {r.handler_id && <Row k="handler" v={<code>{r.handler_id}</code>} />}
          {r.tool_use_id && <Row k="tool use" v={<Id id={String(r.tool_use_id)} />} />}
          {r.request_id && <Row k="request" v={<Id id={String(r.request_id)} />} />}
          {Object.entries(r).filter(([k]) => !['invocation_id', 'event_id', 'seq', 'handler_id', 'tool_use_id', 'request_id'].includes(k)).map(([k, v]) => <Row key={k} k={k} v={<code>{String(v)}</code>} />)}
        </dl>
        {attrs.length > 0 && (
          <table className="wbi-attrs"><tbody>{attrs.map(([k, v]) => <tr key={k}><th>{k}</th><td>{typeof v === 'object' ? JSON.stringify(v) : String(v)}</td></tr>)}</tbody></table>
        )}
      </details>
      <Payload id={s.payload} w={w} />
      <p className="wbi-ev">Seen in: {s.evidence.length ? s.evidence.join(', ') : 'no source listed'}</p>
    </>
  )
}

function EventView({ e, w }: { e: BusEvent; w: Waybill }) {
  const dir = useWb((x) => x.dir)!
  // seen readers one by one; inferred ones folded by component, so 30 pick-list matches stay readable
  const observed = e.consumers.filter((c) => c.evidence === 'observed')
  const inferredBy = useMemo(() => {
    const by = new Map<string, typeof e.consumers>()
    for (const c of e.consumers) if (c.evidence !== 'observed') by.set(c.component, [...(by.get(c.component) ?? []), c])
    return [...by.entries()]
  }, [e])
  return (
    <>
      <h3>{e.type.replace(/^bloodbank\./, '')}</h3>
      <div className="wbi-sub"><code>{e.producer ?? 'unknown producer'}</code> <span>(a note on the belt)</span></div>
      <div className="wbi-badges">
        <span className="wbi-b">{e.seq !== null ? `belt #${e.seq}` : 'core NATS only'}</span>
        {e.schema && <span className={`wbi-b ${e.schema.valid === false ? 's-failed' : e.schema.valid ? 's-ok' : 'dim'}`}>schema {e.schema.valid === null ? 'not checked' : e.schema.valid ? 'valid' : 'invalid'}</span>}
      </div>
      <dl>
        <Row k="when" v={`posted ${fmtT(e.t)}`} hint="on the recording's clock: 0 is Enter" />
        <Row k="who" v={w.components[e.producer ?? '']?.name ?? e.producer ?? 'unknown producer'} />
        <Row k="read by" v={`${observed.length} seen${e.consumers.length > observed.length ? `, ${e.consumers.length - observed.length} on pick lists` : ''}`} />
        {e.publisher_span && <Row k="posted by" v={<a onClick={() => wb.jump(e.publisher_span!)}>{e.publisher_span.length > 30 ? short(e.publisher_span, 28) + '…' : e.publisher_span}</a>} />}
      </dl>
      <details className="wbi-det">
        <summary>Details</summary>
        <dl>
          <Row k="note id" v={<Id id={e.id} />} hint="the event id: never changes (also the barcode when it matches)" />
          {e.seq !== null && <Row k="belt number" v={`#${e.seq}`} hint="the stream sequence" />}
          {e.correlationid && e.correlationid !== e.id && <Row k="barcode" v={<Id id={e.correlationid} />} hint="correlationid: one per conversation" />}
          {e.causationid && e.causationid !== e.id && <Row k="caused by" v={<Id id={e.causationid} />} hint="causationid" />}
          {e.subject && <Row k="subject" v={<code>{e.subject}</code>} />}
          {e.stream && <Row k="stream" v={<code>{e.stream}</code>} />}
          {e.stored != null && <Row k="stored" v={`${fmtT(e.stored)} (${later(e.stored - e.t)})`} />}
          {e.archived != null && <Row k="archived" v={`${fmtT(e.archived)} (${later(e.archived - e.t)})`} />}
        </dl>
      </details>
      <h4>Readers ({observed.length} seen{inferredBy.length ? `, ${e.consumers.length - observed.length} inferred` : ''})</h4>
      <ul className="wbi-cons">
        {observed.map((c, i) => (
          <li key={i} className={c.evidence}>
            <b>{w.components[c.component]?.name ?? c.component}</b>
            <span>{c.kind === 'durable' ? 'clip' : c.kind === 'ephemeral' ? "visitor's pass" : 'core subscriber'} · {c.outcome}{c.t != null ? ` at ${fmtT(c.t)}` : ''}</span>
            <em>{c.evidence === 'observed' ? 'seen' : 'inferred from its pick list'}</em>
            {c.filter && <code>{c.filter}</code>}
            {c.span && <a onClick={() => wb.jump(c.span!)}>span</a>}
          </li>
        ))}
        {inferredBy.map(([comp, list]) => (
          <li key={comp} className="inferred">
            <b>{w.components[comp]?.name ?? comp}</b>
            <span>{list.length > 1 ? `${list.length} pick lists match` : 'its pick list matches'} · nobody saw it read this</span>
            <em>inferred from its pick list</em>
            <code title={list.map((c) => c.filter ?? c.name).join('\n')}>{list.map((c) => c.name).slice(0, 3).join(', ')}{list.length > 3 ? ` +${list.length - 3}` : ''}</code>
          </li>
        ))}
        {!e.consumers.length && <li className="inferred"><span>nobody is recorded as reading this one</span></li>}
      </ul>
      <Payload id={e.payload} w={w} />
      <p className="wbi-ev">{placeName(dir.placement.setOf[e.producer ?? ''] ?? 'belt', dir.placement)}</p>
    </>
  )
}

export function Inspector() {
  const w = useWb((s) => s.waybill)!
  const sel = useWb((s) => s.sel)
  const spans = useMemo(() => new Map(w.spans.map((s) => [s.id, s])), [w])
  const events = useMemo(() => new Map(w.events.map((e) => [e.id, e])), [w])
  // docked on the right: drag its left edge to widen it for long payloads (a phone gets a bottom sheet instead)
  const phone = usePhone()
  const dock = useDock('inspector', { edge: 'right', min: 300, max: () => Math.max(300, window.innerWidth * 0.7 - 24), initial: () => 380 })
  if (!sel) return null
  const s = spans.get(sel)
  const e = sel.startsWith('evt:') ? events.get(sel.slice(4)) : undefined
  if (!s && !e) return null
  return (
    <aside className="wbi" aria-label="Inspector" style={phone ? undefined : { width: dock.size }}>
      {!phone && <DockGrip dock={dock} label="Inspector width" />}
      <button className="wbi-x" onClick={() => wb.select(null)} aria-label="Close the inspector">×</button>
      <div className="wbi-in">
        {s ? <SpanView s={s} w={w} /> : <EventView e={e!} w={w} />}
      </div>
    </aside>
  )
}
