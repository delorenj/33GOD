// The inspector: everything the waybill recorded about one span or one bus event.
import { useMemo } from 'react'
import { placeName } from './stations'
import { useWb, wb } from './state'
import { fmtMs, fmtInt, type Artifact, type BusEvent, type Span, type Waybill } from './types'

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
        <Row k="starts" v={`+${fmtMs(s.t0)}`} />
        <Row k="ends" v={s.t1 === null ? 'never recorded' : `+${fmtMs(s.t1)}`} />
        <Row k="took" v={s.t1 === null ? '—' : fmtMs(s.t1 - s.t0)} />
        {r.invocation_id && <Row k="invocation" v={<code>{r.invocation_id}</code>} hint="hook-hub's id for this one hook call" />}
        {r.event_id && <Row k="Note ID" v={<><code>{r.event_id}</code> <a onClick={() => wb.jump(`evt:${r.event_id}`)}>open the note</a></>} hint="the event id" />}
        {r.seq !== undefined && <Row k="belt number" v={`#${r.seq}`} hint="the stream sequence" />}
        {r.handler_id && <Row k="handler" v={<code>{r.handler_id}</code>} />}
        {r.tool_use_id && <Row k="tool use" v={<code>{r.tool_use_id}</code>} />}
        {r.request_id && <Row k="request" v={<code>{r.request_id}</code>} />}
        {Object.entries(r).filter(([k]) => !['invocation_id', 'event_id', 'seq', 'handler_id', 'tool_use_id', 'request_id'].includes(k)).map(([k, v]) => <Row key={k} k={k} v={<code>{String(v)}</code>} />)}
        {s.parent && <Row k="inside" v={<a onClick={() => wb.jump(s.parent!)}>{s.parent}</a>} />}
      </dl>
      {attrs.length > 0 && (
        <table className="wbi-attrs"><tbody>{attrs.map(([k, v]) => <tr key={k}><th>{k}</th><td>{typeof v === 'object' ? JSON.stringify(v) : String(v)}</td></tr>)}</tbody></table>
      )}
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
        <Row k="Note ID" v={<code>{e.id}</code>} hint="the event id: never changes" />
        {e.seq !== null && <Row k="belt number" v={`#${e.seq}`} hint="the stream sequence" />}
        {e.correlationid && <Row k="barcode" v={<code>{e.correlationid}</code>} hint="correlationid: one per conversation" />}
        {e.causationid && <Row k="caused by" v={<code>{e.causationid}</code>} hint="causationid" />}
        {e.subject && <Row k="subject" v={<code>{e.subject}</code>} />}
        {e.stream && <Row k="stream" v={<code>{e.stream}</code>} />}
        <Row k="published" v={`+${fmtMs(e.t)}`} />
        {e.stored != null && <Row k="stored" v={`+${fmtMs(e.stored)} (${fmtMs(e.stored - e.t)} later)`} />}
        {e.archived != null && <Row k="archived" v={`+${fmtMs(e.archived)} (${fmtMs(e.archived - e.t)} later)`} />}
        {e.publisher_span && <Row k="posted by" v={<a onClick={() => wb.jump(e.publisher_span!)}>{e.publisher_span}</a>} />}
      </dl>
      <h4>Readers ({observed.length} seen{inferredBy.length ? `, ${e.consumers.length - observed.length} inferred` : ''})</h4>
      <ul className="wbi-cons">
        {observed.map((c, i) => (
          <li key={i} className={c.evidence}>
            <b>{w.components[c.component]?.name ?? c.component}</b>
            <span>{c.kind === 'durable' ? 'clip' : c.kind === 'ephemeral' ? "visitor's pass" : 'core subscriber'} · {c.outcome}{c.t != null ? ` at +${fmtMs(c.t)}` : ''}</span>
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
  if (!sel) return null
  const s = spans.get(sel)
  const e = sel.startsWith('evt:') ? events.get(sel.slice(4)) : undefined
  if (!s && !e) return null
  return (
    <aside className="wbi" aria-label="Inspector">
      <button className="wbi-x" onClick={() => wb.select(null)} aria-label="Close the inspector">×</button>
      {s ? <SpanView s={s} w={w} /> : <EventView e={e!} w={w} />}
    </aside>
  )
}
