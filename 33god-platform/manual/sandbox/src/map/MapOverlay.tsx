import { useEffect, useState } from 'react'
import { stationById, type StationId } from '../content'
import { DOMAINS, PARTS, type Domain } from '../domains'
import { ui, useWorld } from '../sim/store'
import { MAP_VIEWBOX, viewAt } from '../world/Camera'

// The overworld map: drawn on blueprint paper over the top-down view, in the same world units,
// so every mark sits on the thing it names. v0: geography and mechanics; the visual grammar comes next.

// monospace: every glyph is 0.6em wide, so the box fits the name without measuring
const partW = (name: string) => name.length * 0.62 * 0.6 + 0.9

function drillTo(d: Domain) {
  const [x0, z0, x1, z1] = d.rect
  const span = Math.max(z1 - z0, (x1 - x0) / (innerWidth / innerHeight))
  ui.fly(viewAt([(x0 + x1) / 2, 0, (z0 + z1) / 2], Math.min(30, span * 1.1)))
}

export function MapOverlay() {
  const open = useWorld((s) => s.mapOpen)
  const [shown, setShown] = useState(false)
  useEffect(() => {
    if (!open) return setShown(false)
    const t = requestAnimationFrame(() => setShown(true))
    return () => cancelAnimationFrame(t)
  }, [open])
  if (!open) return null
  return (
    <div className={`map-overlay ${shown ? 'in' : ''}`}>
      <svg className="map-svg" viewBox={MAP_VIEWBOX()} preserveAspectRatio="xMidYMid meet">
        <defs>
          <pattern id="bp-grid" width="1" height="1" patternUnits="userSpaceOnUse">
            <path d="M 1 0 L 0 0 0 1" fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="0.03" />
          </pattern>
        </defs>
        <rect x="-40" y="-30" width="80" height="60" fill="url(#bp-grid)" />
        {DOMAINS.map((d) => {
          const [x0, z0, x1, z1] = d.rect
          return (
            <g key={d.id} className="map-domain" onClick={() => drillTo(d)}>
              <rect x={x0 + 0.25} y={z0 + 0.25} width={x1 - x0 - 0.5} height={z1 - z0 - 0.5} rx="0.6" fill="rgba(255,255,255,0.04)" stroke="#E6F0FF" strokeWidth="0.09" strokeDasharray="0.5 0.3" />
              {/* titled at the front-left corner, like the stencils painted on the floor */}
              <text x={x0 + 0.8} y={z1 - 1.5} className="map-dname">{d.name}</text>
              <text x={x0 + 0.85} y={z1 - 0.75} className="map-dsays">{d.says}</text>
            </g>
          )
        })}
        {PARTS.map((p) => (
          <g key={p.id} className="map-part" transform={`translate(${p.at[0]} ${p.at[1]})`}
            onClick={(e) => { e.stopPropagation(); if (p.station && p.station in stationById) ui.openStation(p.station as StationId); else ui.fly(viewAt([p.at[0], 0, p.at[1]], 12)) }}>
            <rect x={-partW(p.name) / 2} y="-0.55" width={partW(p.name)} height="1.1" rx="0.25" fill="#0B3B8C" stroke="#E6F0FF" strokeWidth="0.07" />
            <text y="0.2" textAnchor="middle" className="map-pname">{p.name}</text>
          </g>
        ))}
      </svg>
      <div className="map-chrome">
        <b>The map</b>
        <span>Click a zone to fly in. Click a part to open it. Esc closes the map.</span>
        <button onClick={() => useWorld.setState({ mapOpen: false })}>Close map</button>
      </div>
    </div>
  )
}
