import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { stationById, type StationId } from '../content'
import { DOMAINS, domainById, type DomainId } from '../domains'
import { ui, useWorld } from '../sim/store'
import { viewAt } from '../world/Camera'
import { drawConn } from './conn'
import { buildL1, type L1, type Sel } from './drawL1'
import { buildL2, type L2 } from './drawL2'
import { mapPortrait, mapViewBox } from './frame'
import { JOURNEYS, KINDS, L2_PLATE, L2_VIEWBOX, LEGEND, LEGEND_SUMMARY, atOf, partById, type Kind } from './graph'
import { el } from './svg'

// The overworld map, drawn like a LEGO build manual on blueprint paper over the top-down view.
// Level 1 is the whole platform (zones = numbered bags, parts = bricks, lines = typed connections).
// Level 2 is one zone up close (Bloodbank). Both are plain SVG in world metres; the chrome is DOM.

/** Esc asks the map to step back from level 2 first; returns true when it did */
export const mapNav = { back: (): boolean => false }

const nums = (vb: string) => vb.split(' ').map(Number)
const L1VB = nums(mapViewBox(false))
const L2VB = nums(L2_VIEWBOX)
const ASPECT = L1VB[2] / L1VB[3]

function vbPx(svg: SVGSVGElement, vb: number[], x: number, z: number) {
  const W = svg.clientWidth
  const H = svg.clientHeight
  const s = Math.min(W / vb[2], H / vb[3])
  return { x: (W - vb[2] * s) / 2 + (x - vb[0]) * s, y: (H - vb[3] * s) / 2 + (z - vb[1]) * s, s }
}

function drillTo(id: DomainId) {
  const [x0, z0, x1, z1] = domainById[id].rect
  const span = Math.max(z1 - z0, (x1 - x0) / (innerWidth / innerHeight))
  ui.fly(viewAt([(x0 + x1) / 2, 0, (z0 + z1) / 2], Math.min(30, span * 1.1)))
}

function openPart(id: string) {
  const p = partById[id]
  if (p.station && p.station in stationById) ui.openStation(p.station as StationId)
  else { const [x, z] = atOf(id); ui.fly(viewAt([x, 0, z], 12)) }
}

/** a legend sample: the same line, arrowhead and riding object the map uses */
function legendIcon(k: Kind) {
  const s = el(null, 'svg', { viewBox: '0 0 3.8 1.2', width: 70, height: 22 })
  drawConn(s, [[0.3, 0.6], [3.4, 0.6]], k, { hl: 0.5, objAt: 0.3, round: 0.1 })
  return s
}

export function MapOverlay() {
  const open = useWorld((s) => s.mapOpen)
  const [shown, setShown] = useState(false)
  const [portrait, setPortrait] = useState(mapPortrait)
  const [view, setView] = useState<'l1' | 'l2'>('l1')
  const [sel, setSel] = useState<Sel>('calm')
  const [keyOpen, setKeyOpen] = useState(false)
  const l1Ref = useRef<SVGSVGElement>(null)
  const l2Ref = useRef<SVGSVGElement>(null)
  const scrollRef = useRef<HTMLDivElement>(null)
  const ctl = useRef<{ l1: L1; l2: L2 } | null>(null)
  const viewRef = useRef(view)
  const goRef = useRef<(to: 'l1' | 'l2') => void>(() => {})

  useEffect(() => {
    if (!open) return setShown(false)
    const t = requestAnimationFrame(() => setShown(true))
    return () => cancelAnimationFrame(t)
  }, [open])
  useEffect(() => {
    const f = () => setPortrait(mapPortrait())
    addEventListener('resize', f)
    return () => removeEventListener('resize', f)
  }, [])

  // slide the pannable map (phones) so the thing we are looking at is in view
  const centreOn = (v: 'l1' | 'l2', smooth = false) => {
    const sc = scrollRef.current
    if (!sc || sc.scrollWidth <= sc.clientWidth + 2) return
    const x = v === 'l1' ? (-7.9 - L1VB[0]) / L1VB[2] : ((L2_PLATE[0] + L2_PLATE[2]) / 2 - L2VB[0]) / L2VB[2]
    sc.scrollTo({ left: Math.max(0, x * sc.scrollWidth - sc.clientWidth / 2), behavior: smooth ? 'smooth' : 'auto' })
  }

  // draw once per opening: imperative SVG, in world metres
  useEffect(() => {
    if (!open || !l1Ref.current || !l2Ref.current) return
    const a = l1Ref.current
    const b = l2Ref.current
    const go = (to: 'l1' | 'l2') => goRef.current(to)
    ctl.current = {
      l1: buildL1(a, { zone: (id) => (id === 'bloodbank' ? go('l2') : drillTo(id)), part: openPart }),
      l2: buildL2(b, { zone: drillTo }),
    }
    b.style.opacity = '0'
    b.style.pointerEvents = 'none'
    viewRef.current = 'l1'
    setView('l1')
    setSel('calm')
    setKeyOpen(false)
    return () => { a.replaceChildren(); b.replaceChildren(); ctl.current = null }
  }, [open])

  useLayoutEffect(() => { if (open && portrait) centreOn(viewRef.current) }, [open, portrait])
  useEffect(() => { ctl.current?.l1.apply(sel); ctl.current?.l2.apply(sel) }, [sel, open])

  goRef.current = (to) => {
    const a = l1Ref.current
    const b = l2Ref.current
    if (!a || !b || viewRef.current === to) return
    // zoom from the Bloodbank rectangle into page 2 (and back), crossfading the two drawings
    const [x0, z0, x1, z1] = domainById.bloodbank.rect
    const P1 = vbPx(a, L1VB, (x0 + x1) / 2, (z0 + z1) / 2)
    const P2 = vbPx(b, L2VB, (L2_PLATE[0] + L2_PLATE[2]) / 2, (L2_PLATE[1] + L2_PLATE[3]) / 2)
    const s0 = ((x1 - x0) * P1.s) / ((L2_PLATE[2] - L2_PLATE[0]) * P2.s)
    const tiny = `translate(${P1.x - P2.x}px,${P1.y - P2.y}px) scale(${s0})`
    const big = `translate(${P2.x - P1.x}px,${P2.y - P1.y}px) scale(${1 / s0})`
    a.style.transformOrigin = `${P1.x}px ${P1.y}px`
    b.style.transformOrigin = `${P2.x}px ${P2.y}px`
    if (to === 'l2') {
      b.style.transition = 'none'
      b.style.transform = tiny
      b.style.opacity = '0'
      void b.getBoundingClientRect()
      b.style.transition = ''
      b.style.transform = 'none'
      b.style.opacity = '1'
      b.style.pointerEvents = 'auto'
      a.style.transform = big
      a.style.opacity = '0'
      a.style.pointerEvents = 'none'
    } else {
      a.style.transform = 'none'
      a.style.opacity = '1'
      a.style.pointerEvents = 'auto'
      b.style.transform = tiny
      b.style.opacity = '0'
      b.style.pointerEvents = 'none'
    }
    viewRef.current = to
    setView(to)
    if (portrait) centreOn(to, true)
  }
  useEffect(() => {
    mapNav.back = () => {
      if (viewRef.current !== 'l2') return false
      goRef.current('l1')
      return true
    }
    return () => { mapNav.back = () => false }
  }, [])

  if (!open) return null
  const act = typeof sel === 'number' ? JOURNEYS[sel - 1] : null
  const stageW = portrait ? Math.round(innerHeight * 0.7 * ASPECT) : undefined
  const pick = (s: Sel) => setSel((cur) => (cur === s ? 'calm' : s))
  return (
    <div className={`map-overlay ${shown ? 'in' : ''} ${portrait ? 'portrait' : ''}`}>
      <div className="map-scroll" ref={scrollRef}>
        <div className="map-stage" style={stageW ? { width: stageW } : undefined}>
          <svg ref={l1Ref} className="map-svg" viewBox={mapViewBox(false)} preserveAspectRatio="xMidYMid meet" />
          <svg ref={l2Ref} className="map-svg" viewBox={L2_VIEWBOX} preserveAspectRatio="xMidYMid meet" />
        </div>
      </div>
      <div className="map-top">
        {view === 'l2' ? (
          <button className="mp-back" onClick={() => goRef.current('l1')}>‹ back to the whole map</button>
        ) : (
          <span className="mp-level"><b>The map</b> · the whole warehouse</span>
        )}
        <div className="mp-chips" role="group" aria-label="Builds">
          <button className={`mp-chip ${sel === 'all' ? 'on' : ''}`} onClick={() => pick('all')} title="Show every line">All</button>
          {JOURNEYS.map((j, i) => (
            <button key={j.name} className={`mp-chip ${sel === i + 1 ? 'on' : ''}`} onClick={() => pick((i + 1) as Sel)}>
              <i>{i + 1}</i>{j.name}
            </button>
          ))}
        </div>
        <button className="mp-close" onClick={() => useWorld.setState({ mapOpen: false })} aria-label="Close the map">Close <kbd>Esc</kbd></button>
      </div>
      <div className="map-bottom">
        {act ? (
          <ol className="mp-steps">{act.cap.map((t, i) => <li key={t}><b>{i + 1}</b>{t}</li>)}</ol>
        ) : (
          <p className="mp-hint">
            {view === 'l2'
              ? 'Bloodbank up close. Click a coloured pill to go to the zone it leads to.'
              : 'Pick a build to follow one trip. Click a zone to fly in, or a brick to read about it.'}
          </p>
        )}
        <div className="mp-legend">
          <span>{LEGEND_SUMMARY}</span>
          <button onClick={() => setKeyOpen((k) => !k)} aria-expanded={keyOpen}>Key</button>
        </div>
      </div>
      {keyOpen && (
        <div className="map-key" role="dialog" aria-label="What the lines mean">
          <div className="mk-head">What the lines mean<button onClick={() => setKeyOpen(false)} aria-label="Close the key">×</button></div>
          <div className="mk-grid">
            {LEGEND.map((k) => (
              <div key={k} className="mk-item">
                <span className="mk-ic" ref={(n) => { if (n && !n.firstChild) n.appendChild(legendIcon(k)) }} />
                <b>{KINDS[k].name}</b><em>{KINDS[k].say}</em>
              </div>
            ))}
          </div>
          <p className="mk-note">{DOMAINS.length} zones, numbered like the bags in a LEGO box. Bricks are parts. “1x” means one of them.</p>
        </div>
      )}
    </div>
  )
}
