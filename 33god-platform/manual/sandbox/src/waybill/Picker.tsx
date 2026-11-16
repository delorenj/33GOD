// The sample picker, the drop zone and the "Play a waybill" entry points. Mounted in every mode.
import { useEffect, useRef, useState } from 'react'
import { fetchSamples, loadFile, loadFromUrl, sampleUrl, type Sample } from './load'
import { useWb, wb } from './state'
import { fmtMs } from './types'

export function PlayWaybillButton({ className }: { className?: string }) {
  return <button className={className} onClick={() => wb.openPicker(true)} title="Load a recorded prompt and watch it cross the floor">Play a waybill</button>
}

/** Drag a .json anywhere on the page: a full-screen drop target appears. */
function useDrop() {
  const [over, setOver] = useState(false)
  useEffect(() => {
    let depth = 0
    const has = (e: DragEvent) => !!e.dataTransfer && [...(e.dataTransfer.types ?? [])].includes('Files')
    const enter = (e: DragEvent) => { if (!has(e)) return; e.preventDefault(); depth++; setOver(true) }
    const overH = (e: DragEvent) => { if (has(e)) e.preventDefault() }
    const leave = (e: DragEvent) => { if (!has(e)) return; depth = Math.max(0, depth - 1); if (!depth) setOver(false) }
    const drop = (e: DragEvent) => {
      if (!has(e)) return
      e.preventDefault(); depth = 0; setOver(false)
      const f = e.dataTransfer?.files?.[0]
      if (f) void loadFile(f)
    }
    window.addEventListener('dragenter', enter); window.addEventListener('dragover', overH); window.addEventListener('dragleave', leave); window.addEventListener('drop', drop)
    return () => { window.removeEventListener('dragenter', enter); window.removeEventListener('dragover', overH); window.removeEventListener('dragleave', leave); window.removeEventListener('drop', drop) }
  }, [])
  return over
}

const isFixture = (s: Sample) => !!s.fixture || /^fixture/i.test(s.file)
/** Real recordings first, in the order the index lists them; the hand-made fixture goes last. */
const ordered = (list: Sample[]) => [...list.filter((s) => !isFixture(s)), ...list.filter(isFixture)]

function Picker() {
  const load = useWb((s) => s.load)
  const [samples, setSamples] = useState<Sample[] | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [url, setUrl] = useState('')
  const file = useRef<HTMLInputElement>(null)
  useEffect(() => {
    let off = false
    fetchSamples().then((s) => !off && setSamples(s)).catch((e: Error) => !off && (setSamples([]), setErr(e.message)))
    return () => { off = true }
  }, [])
  const busy = load.state === 'loading'
  return (
    <div className="wb-modal" onClick={(e) => { if (e.target === e.currentTarget) wb.openPicker(false) }} role="dialog" aria-modal="true" aria-label="Play a waybill">
      <div className="wb-pick">
        <button className="x" onClick={() => wb.openPicker(false)} aria-label="Close">×</button>
        <div className="eyebrow">Waybill player</div>
        <h2>Follow one prompt across the floor</h2>
        <p className="muted">A waybill is one recorded prompt: every hook, event, model call and side effect it caused, with real timings. Pick a sample, or drop your own file.</p>
        {load.state === 'error' && (
          <div className="wb-err" role="alert">
            <b>That did not load.</b> {load.message}
            {load.retry && <button onClick={() => void loadFromUrl(load.retry!)}>Try again</button>}
          </div>
        )}
        {busy && <p className="wb-busy">Loading {load.source}…</p>}
        <h4>Samples</h4>
        {samples === null && <p className="muted small">Looking for samples…</p>}
        {samples && samples.length === 0 && <p className="muted small">{err ? `No sample list (${err}).` : 'No samples are published here yet.'} Drop a file instead.</p>}
        <ul className="wb-samples">
          {samples && ordered(samples).map((s) => (
            <li key={s.file} className={isFixture(s) ? 'fixture' : undefined}>
              <button disabled={busy} onClick={() => void loadFromUrl(sampleUrl(s))}>
                <b>{s.title}</b>
                <span>{[isFixture(s) ? 'hand-made fixture' : 'real recording', s.cli, s.surface, s.duration_ms ? fmtMs(s.duration_ms) : null, s.recorded_at?.slice(0, 10)].filter(Boolean).join(' · ')}</span>
              </button>
            </li>
          ))}
        </ul>
        <div className="wb-drop" onClick={() => file.current?.click()} role="button" tabIndex={0} onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') file.current?.click() }}>
          Drop a <code>.waybill.json</code> (or <code>.json.gz</code>) anywhere, or choose a file
          <input ref={file} type="file" accept=".json,.gz,application/json,application/gzip" hidden onChange={(e) => { const f = e.target.files?.[0]; if (f) void loadFile(f); e.target.value = '' }} />
        </div>
        <form className="wb-url" onSubmit={(e) => { e.preventDefault(); if (url.trim()) void loadFromUrl(url.trim()) }}>
          <input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="or paste a link to a waybill .json or .json.gz" aria-label="Waybill URL" />
          <button disabled={busy || !url.trim()}>Load</button>
        </form>
      </div>
    </div>
  )
}

export function WaybillGlobal() {
  const over = useDrop()
  const picker = useWb((s) => s.picker)
  const load = useWb((s) => s.load)
  useEffect(() => {
    if (!picker) return
    const k = (e: KeyboardEvent) => { if (e.key === 'Escape') { e.stopPropagation(); wb.openPicker(false) } }
    window.addEventListener('keydown', k, true)
    return () => window.removeEventListener('keydown', k, true)
  }, [picker])
  return (
    <>
      {over && <div className="wb-dropveil"><div>Drop a waybill to play it</div></div>}
      {picker && <Picker />}
      {!picker && load.state === 'error' && <div className="wb-toast" role="alert">{load.message}<button onClick={() => wb.setLoad({ state: 'idle' })}>×</button></div>}
    </>
  )
}
