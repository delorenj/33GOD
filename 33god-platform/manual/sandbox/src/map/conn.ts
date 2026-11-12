import { HALO, INK, along, el, grp, rpath, type Pt } from './svg'
import { KINDS, type Kind, type ObjKind } from './graph'

const sw = { stroke: INK, 'stroke-width': 0.07, 'stroke-linejoin': 'round', 'stroke-linecap': 'round' } as const

/** the little thing that rides each kind of line: it is the second cue, after colour */
export function obj(p: Element, kind: ObjKind, x: number, z: number, scale = 1) {
  const g = el(p, 'g', { transform: `translate(${x} ${z}) scale(${scale})`, class: 'obj' })
  const R = (a: Record<string, string | number>) => el(g, 'rect', { ...sw, ...a })
  const Pt = (d: string, a?: Record<string, string | number>) => el(g, 'path', { d, fill: 'none', ...sw, ...(a ?? {}) })
  if (kind === 'postit') {
    R({ x: -0.38, y: -0.38, width: 0.76, height: 0.76, fill: '#FFE066' })
    Pt('M.38 .12L.12 .38V.12Z', { fill: '#e0b800' })
    Pt('M-.22 -.15H.2M-.22 .02H.1', { 'stroke-width': 0.05 })
  }
  if (kind === 'env' || kind === 'ghost') {
    const gh = kind === 'ghost'
    R({ x: -0.46, y: -0.32, width: 0.92, height: 0.64, rx: 0.06, fill: gh ? '#e9eef3' : '#fff', stroke: gh ? '#8a97a8' : '#D6404B', 'stroke-dasharray': gh ? '.14 .1' : '' })
    Pt('M-.46 -.32L0 .06L.46 -.32', { stroke: gh ? '#8a97a8' : '#D6404B' })
    if (gh) Pt('M-.12 .0L.12 .22M.12 .0L-.12 .22', { stroke: '#8a97a8', 'stroke-width': 0.06 })
  }
  if (kind === 'parcel') {
    R({ x: -0.4, y: -0.32, width: 0.8, height: 0.64, rx: 0.05, fill: '#E3AE4A' })
    Pt('M0 -.32V.32', { stroke: '#8a5a10' })
    Pt('M-.4 0H.4', { stroke: '#8a5a10', 'stroke-width': 0.04 })
  }
  if (kind === 'card') {
    R({ x: -0.4, y: -0.3, width: 0.8, height: 0.6, rx: 0.06, fill: '#fff', stroke: '#B7791F' })
    Pt('M-.24 -.1H.24M-.24 .08H.1', { stroke: '#B7791F', 'stroke-width': 0.05 })
  }
  if (kind === 'copy') {
    R({ x: -0.28, y: -0.36, width: 0.52, height: 0.64, rx: 0.05, fill: '#d7f3e6', stroke: '#1E9E6A' })
    R({ x: -0.12, y: -0.26, width: 0.52, height: 0.64, rx: 0.05, fill: '#fff', stroke: '#1E9E6A' })
    Pt('M0 -.06H.28M0 .1H.2', { stroke: '#1E9E6A', 'stroke-width': 0.05 })
  }
  if (kind === 'plug') {
    el(g, 'circle', { ...sw, r: 0.32, fill: '#fff' })
    Pt('M.06 -.22L-.12 .04H.04L-.06 .24L.14 -.04H-.02Z', { fill: INK, 'stroke-width': 0.03 })
  }
  if (kind === 'grab') {
    el(g, 'circle', { ...sw, r: 0.34, fill: '#fff', stroke: '#D6404B' })
    Pt('M-.16 .0L-.04 .13L.18 -.13', { stroke: '#D6404B', 'stroke-width': 0.09 })
  }
  if (kind === 'globe') {
    el(g, 'circle', { ...sw, r: 0.34, fill: '#fff', stroke: '#4a5568' })
    Pt('M-.34 0H.34M0 -.34Q-.2 0 0 .34Q.2 0 0 -.34', { stroke: '#4a5568', 'stroke-width': 0.05 })
  }
  return g
}

export interface ConnOpts { hl?: number; wScale?: number; round?: number; objAt?: number; objScale?: number; objs?: boolean }
export interface ConnEls { g: SVGGElement; halo: SVGPathElement; ln: SVGPathElement; w: number; mid: { x: number; y: number } }

/** one typed line: paper halo (so crossings read), the line, an arrowhead, and the object riding it */
export function drawConn(p: Element, route: Pt[], kind: Kind, o: ConnOpts = {}): ConnEls {
  const k = KINDS[kind]
  const HL = o.hl ?? 0.55
  const w = k.w * (o.wScale ?? 1)
  const pts = route.map((q) => [q[0], q[1]] as Pt)
  const n = pts.length
  const a = pts[n - 2]
  const b = pts[n - 1]
  const dx = b[0] - a[0]
  const dz = b[1] - a[1]
  const L = Math.hypot(dx, dz)
  const ux = dx / L
  const uz = dz / L
  pts[n - 1] = [b[0] - ux * (HL - 0.08), b[1] - uz * (HL - 0.08)]
  const d = rpath(pts, o.round ?? 0.45)
  const g = grp(p, 'conn')
  const hl = el(g, 'path', { d, fill: 'none', stroke: HALO, 'stroke-width': w + 0.34, 'stroke-linecap': 'round', 'stroke-linejoin': 'round', class: 'halo' })
  const ln = el(g, 'path', { d, fill: 'none', stroke: k.col, 'stroke-width': w, 'stroke-linecap': kind === 'http' ? 'round' : 'butt', 'stroke-linejoin': 'round', class: 'ln' })
  if (k.dash) ln.setAttribute('stroke-dasharray', k.dash)
  const hw = HL * 0.55
  el(g, 'polygon', { points: `${b[0]},${b[1]} ${b[0] - ux * HL + uz * hw},${b[1] - uz * HL - ux * hw} ${b[0] - ux * HL - uz * hw},${b[1] - uz * HL + ux * hw}`, fill: k.col, stroke: INK, 'stroke-width': 0.05, 'stroke-linejoin': 'round', class: 'head' })
  const mid = along(route, o.objAt ?? 0.5)
  if (o.objs !== false) obj(g, k.obj, mid.x, mid.y, o.objScale ?? 1)
  return { g, halo: hl, ln, w, mid }
}
