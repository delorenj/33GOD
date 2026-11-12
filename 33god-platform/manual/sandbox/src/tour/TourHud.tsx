import { useEffect, useRef, useState } from 'react'
import { bulbById, isPortrait, type Vec3 } from '../content'
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
  /** Jump straight to a stop (deep link ?tour=N, 1-based). */
  go(i: number) {
    const k = Math.max(0, Math.min(TOUR.length - 1, i))
    useWorld.setState({ mode: 'tour', intro: false, beat: k, line: 0, station: null, inspect: null, bulb: null })
    fly(k)
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
  const set = setFor(TOUR[i].set)
  const base = set.view
  // a phone is narrow: back the camera off along its own line so the speakers either side stay in frame
  const k = isPortrait() ? (set.portraitK ?? 1.6) : 1
  const pos = base.pos.map((p, j) => base.target[j] + (p - base.target[j]) * k) as Vec3
  const v = { pos, target: base.target }
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

  // the tour frames people, not the belt's instruments: hide ruler, parcel, desk and puff tags while it runs
  useEffect(() => {
    document.body.classList.add('tour-on')
    return () => document.body.classList.remove('tour-on')
  }, [])
  // let the camera land before the first line types out
  useEffect(() => {
    setArrived(false)
    const t = setTimeout(() => setArrived(true), 1300)
    return () => clearTimeout(t)
  }, [bi])
  useEffect(() => setTyped(false), [bi, li])
  // a line's hold is a beat of silence after it finishes typing, before the next can come (the pause is the joke)
  const holdT = useRef<number | undefined>(undefined)
  useEffect(() => () => clearTimeout(holdT.current), [bi, li])
  const finishTyping = () => {
    const ms = beat.lines[Math.min(li, beat.lines.length - 1)]?.hold ?? 0
    clearTimeout(holdT.current)
    if (ms > 0) holdT.current = window.setTimeout(() => setTyped(true), ms)
    else setTyped(true)
  }

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
          <span className="eyebrow">Stop {bi + 1} of {TOUR.length}{beat.side ? ' · side scene' : ''}</span>
          <b>{beat.caption}</b>
          {beat.side && <span className="side-ribbon">Not on this errand’s route</span>}
        </div>
        {beat.split && <div className="padclock" title="The pad's working clock, from a real traced memo"><span>⏱</span>{beat.split}</div>}
        <div className="tour-dots">{TOUR.map((b, i) => <i key={b.id} className={i < bi ? 'past' : i === bi ? 'now' : ''} />)}</div>
        <button className="tour-leave" onClick={() => tour.leave()}>Leave tour</button>
      </div>

      {learned.length > 0 && (
        <details className="notebook">
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
            <p className="say">{typed ? line.text : <Typewriter key={`${bi}-${li}`} text={line.text} onDone={finishTyping} />}</p>
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
