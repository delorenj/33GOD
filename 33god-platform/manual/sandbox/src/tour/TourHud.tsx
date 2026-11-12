import { useEffect, useRef, useState } from 'react'
import { bulbById } from '../content'
import { ui, useWorld } from '../sim/store'
import { CAST, END_CARD, OFF_ROUTE, TOUR } from './script'
import { setFor } from './sets'

const CPS = 55 // typewriter characters per second

export const tour = {
  start() {
    useWorld.setState({ mode: 'tour', intro: false, beat: 0, line: 0, station: null, inspect: null, bulb: null, speed: 1, paused: false, dockShut: false })
    fly(0)
  },
  leave() {
    useWorld.setState({ mode: 'sandbox', beat: 0, line: 0 })
    ui.overview()
  },
  next() {
    const s = useWorld.getState()
    const beat = TOUR[s.beat]
    if (s.line < beat.lines.length - 1) return useWorld.setState({ line: s.line + 1 })
    if (s.beat < TOUR.length - 1) {
      useWorld.setState({ beat: s.beat + 1, line: 0, bulb: null })
      fly(s.beat + 1)
    } else useWorld.setState({ line: beat.lines.length }) // the end card
  },
  back() {
    const s = useWorld.getState()
    if (s.line > 0) return useWorld.setState({ line: s.line - 1 })
    if (s.beat > 0) {
      const prev = TOUR[s.beat - 1]
      useWorld.setState({ beat: s.beat - 1, line: prev.lines.length - 1 })
      fly(s.beat - 1)
    }
  },
}

function fly(i: number) {
  const v = setFor(TOUR[i].set).view
  useWorld.setState((s) => ({ focus: { id: 'custom', nonce: (s.focus?.nonce ?? 0) + 1, view: v } }))
}

function Typewriter({ text, onDone }: { text: string; onDone: () => void }) {
  const [n, setN] = useState(0)
  const done = useRef(false)
  const cb = useRef(onDone)
  cb.current = onDone
  useEffect(() => {
    setN(0)
    done.current = false
    const t0 = performance.now()
    const id = setInterval(() => {
      const k = Math.min(text.length, Math.floor(((performance.now() - t0) / 1000) * CPS))
      setN(k)
      if (k >= text.length) {
        clearInterval(id)
        if (!done.current) { done.current = true; cb.current() }
      }
    }, 16)
    return () => clearInterval(id)
  }, [text])
  return <>{text.slice(0, n)}<span className="caret" style={{ opacity: n < text.length ? 1 : 0 }}>▍</span></>
}

export function TourHud() {
  const bi = useWorld((s) => s.beat)
  const li = useWorld((s) => s.line)
  const bulb = useWorld((s) => s.bulb)
  const [typed, setTyped] = useState(false)
  const [arrived, setArrived] = useState(false)
  const beat = TOUR[bi]
  const ended = li >= beat.lines.length && bi === TOUR.length - 1
  const line = beat.lines[Math.min(li, beat.lines.length - 1)]
  const who = CAST[line.who]

  // let the camera land before the first line types out
  useEffect(() => {
    setArrived(false)
    const t = setTimeout(() => setArrived(true), 1300)
    return () => clearTimeout(t)
  }, [bi])
  useEffect(() => setTyped(false), [bi, li])

  const advance = () => {
    if (!arrived) return setArrived(true)
    if (!typed) return setTyped(true)
    tour.next()
  }

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (useWorld.getState().bulb) return
      if (e.key === ' ' || e.key === 'Enter' || e.key === 'ArrowRight') { e.preventDefault(); advance() }
      if (e.key === 'ArrowLeft') tour.back()
      if (e.key === 'Escape') tour.leave()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  })

  const learned = TOUR.slice(0, bi + (li >= beat.lines.length - 1 && typed ? 1 : 0)).map((b) => b.teaches)

  if (ended) {
    return (
      <div className="tour-end">
        <div className="intro-card">
          <div className="eyebrow">Tour complete</div>
          <h1>{END_CARD.headline}</h1>
          <p>{END_CARD.ask}</p>
          <details className="notebook">
            <summary>Your notebook · {TOUR.length}</summary>
            <ol className="learned-list">{TOUR.map((b) => <li key={b.id}>{b.teaches}</li>)}</ol>
          </details>
          <details className="notebook">
            <summary>{END_CARD.offRouteTitle} · {OFF_ROUTE.length}</summary>
            <ul className="learned-list">{OFF_ROUTE.map((r) => <li key={r.name}><b>{r.name}</b> ({r.real}). {r.why}</li>)}</ul>
          </details>
          <button className="primary" onClick={() => tour.leave()}>Explore the floor freely</button>
          <button className="ghost" onClick={() => tour.start()}>Take the tour again</button>
        </div>
      </div>
    )
  }

  return (
    <div className="tour">
      <div className="tour-top">
        <div className="tour-caption">
          <span className="eyebrow">Stop {bi + 1} of {TOUR.length}</span>
          <b>{beat.caption}</b>
        </div>
        <div className="tour-dots">{TOUR.map((b, i) => <i key={b.id} className={i < bi ? 'past' : i === bi ? 'now' : ''} />)}</div>
        <button className="tour-leave" onClick={() => tour.leave()}>Leave tour</button>
      </div>

      {learned.length > 0 && (
        <details className="notebook" open={window.innerWidth > 720}>
          <summary>Your notebook · {learned.length}</summary>
          <ol>{learned.map((t, i) => <li key={i}>{t}</li>)}</ol>
        </details>
      )}

      <div className={`dialogue ${arrived ? 'in' : ''}`} onClick={advance} role="button" tabIndex={0} aria-live="polite">
        {arrived && (
          <>
            <div className="speaker" style={{ background: who?.color ?? '#2a2418' }}>
              {who?.name ?? line.who}
              {who && <span>{who.role}</span>}
            </div>
            <p className="say">{typed ? line.text : <Typewriter key={`${bi}-${li}`} text={line.text} onDone={() => setTyped(true)} />}</p>
            <div className="dialogue-foot">
              {beat.bulb && li === beat.lines.length - 1 && typed && !bulb && (
                <button className="bulbbtn" onClick={(e) => { e.stopPropagation(); ui.openBulb(beat.bulb!) }}>💡 {bulbById[beat.bulb].title}</button>
              )}
              <span className="hint">{li + 1}/{beat.lines.length} · click or space</span>
              <button className="back" onClick={(e) => { e.stopPropagation(); tour.back() }} disabled={bi === 0 && li === 0}>◂</button>
              <button className="next" onClick={(e) => { e.stopPropagation(); advance() }}>{li === beat.lines.length - 1 ? (bi === TOUR.length - 1 ? 'Finish' : 'Next stop ▸') : '▸'}</button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
