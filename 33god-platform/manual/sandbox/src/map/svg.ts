// Tiny imperative SVG kit for the map. World units: 1 = 1 metre on the warehouse floor.
// The map is drawn like a LEGO build manual on blueprint paper: bricks with studs, numbered bags,
// "1x" part chips, and typed lines (colour + dash + a little object riding the line + an arrowhead).

export type Pt = [number, number]
type Attrs = Record<string, string | number>

export const NS = 'http://www.w3.org/2000/svg'
export const INK = '#14304f'
export const INK2 = '#35597e'
export const PAPER = '#d8e8f3'
export const HALO = '#e9f2f9' // paper-light: keeps words readable where a line passes behind them

export function el<K extends keyof SVGElementTagNameMap>(p: Element | null, tag: K, a?: Attrs, txt?: string | number): SVGElementTagNameMap[K] {
  const e = document.createElementNS(NS, tag)
  if (a) for (const k in a) e.setAttribute(k, String(a[k]))
  if (txt != null) e.textContent = String(txt)
  if (p) p.appendChild(e)
  return e
}
export const grp = (p: Element | null, cls = '', a?: Attrs) => el(p, 'g', { class: cls, ...(a ?? {}) })

const rgb = (h: string) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16))
export function mix(h: string, t: string, f: number) {
  const a = rgb(h)
  const b = rgb(t)
  return '#' + a.map((v, i) => Math.round(v + (b[i] - v) * f).toString(16).padStart(2, '0')).join('')
}
export const dark = (h: string, f: number) => mix(h, '#0b2540', f)
export const light = (h: string, f: number) => mix(h, '#ffffff', f)

interface LineOpts { anchor?: string; cls?: string; fill?: string; lh?: number; sizes?: number[]; fills?: string[]; weights?: number[] }
/** several lines of text, each its own tspan, starting at (x, y) */
export function lines(p: Element, x: number, y: number, arr: string[], size: number, o: LineOpts = {}) {
  const t = el(p, 'text', { x, y, 'text-anchor': o.anchor ?? 'middle', 'font-size': size, class: o.cls ?? '', fill: o.fill ?? INK })
  arr.forEach((s, i) => {
    const ts = el(t, 'tspan', { x, dy: i ? (o.sizes?.[i] ?? size) * (o.lh ?? 1.12) : 0 }, s)
    if (o.weights?.[i]) ts.setAttribute('font-weight', String(o.weights[i]))
    if (o.sizes?.[i]) ts.setAttribute('font-size', String(o.sizes[i]))
    if (o.fills?.[i]) ts.setAttribute('fill', o.fills[i])
  })
  return t
}

/** give text a paper-colour outline so lines never smear the words */
export function halo(t: SVGElement, w = 0.22) {
  t.setAttribute('paint-order', 'stroke')
  t.setAttribute('stroke', HALO)
  t.setAttribute('stroke-width', String(w))
  t.setAttribute('stroke-linejoin', 'round')
  return t
}

/** rounded orthogonal polyline as a path */
export function rpath(pts: Pt[], r = 0.45) {
  let d = `M${pts[0][0]} ${pts[0][1]}`
  for (let i = 1; i < pts.length - 1; i++) {
    const a = pts[i - 1]
    const b = pts[i]
    const c = pts[i + 1]
    const l1 = Math.hypot(b[0] - a[0], b[1] - a[1])
    const l2 = Math.hypot(c[0] - b[0], c[1] - b[1])
    const rr = Math.min(r, l1 / 2, l2 / 2)
    const p1 = [b[0] + ((a[0] - b[0]) / l1) * rr, b[1] + ((a[1] - b[1]) / l1) * rr]
    const p2 = [b[0] + ((c[0] - b[0]) / l2) * rr, b[1] + ((c[1] - b[1]) / l2) * rr]
    d += `L${p1[0]} ${p1[1]}Q${b[0]} ${b[1]} ${p2[0]} ${p2[1]}`
  }
  const e = pts[pts.length - 1]
  return d + `L${e[0]} ${e[1]}`
}

/** point and heading at fraction t of a polyline */
export function along(pts: Pt[], t: number) {
  const seg: number[] = []
  let L = 0
  for (let i = 1; i < pts.length; i++) {
    const l = Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1])
    seg.push(l)
    L += l
  }
  let d = L * t
  for (let i = 0; i < seg.length; i++) {
    if (d <= seg[i] || i === seg.length - 1) {
      const f = seg[i] ? d / seg[i] : 0
      const a = pts[i]
      const b = pts[i + 1]
      return { x: a[0] + (b[0] - a[0]) * f, y: a[1] + (b[1] - a[1]) * f }
    }
    d -= seg[i]
  }
  return { x: pts[0][0], y: pts[0][1] }
}

/** closest point on a polyline to (x, z) */
export function nearest(pts: Pt[], x: number, z: number): Pt {
  let best: Pt = pts[0]
  let bd = 1e9
  for (let i = 1; i < pts.length; i++) {
    const a = pts[i - 1]
    const b = pts[i]
    const dx = b[0] - a[0]
    const dz = b[1] - a[1]
    const L2 = dx * dx + dz * dz
    const t = L2 ? Math.max(0, Math.min(1, ((x - a[0]) * dx + (z - a[1]) * dz) / L2)) : 0
    const px = a[0] + dx * t
    const pz = a[1] + dz * t
    const d = Math.hypot(px - x, pz - z)
    if (d < bd) { bd = d; best = [px, pz] }
  }
  return best
}

interface BrickOpts { rx?: number; studs?: boolean; cols?: number; rows?: number }
/** a top-down LEGO brick: shadow wall, body, highlight, studs */
export function brick(p: Element, cx: number, cz: number, w: number, h: number, col: string, o: BrickOpts = {}) {
  const g = grp(p, 'brick')
  const x = cx - w / 2
  const z = cz - h / 2
  const rx = o.rx ?? 0.3
  el(g, 'rect', { x, y: z + 0.17, width: w, height: h, rx, fill: dark(col, 0.38) })
  el(g, 'rect', { x, y: z, width: w, height: h, rx, fill: col, stroke: INK, 'stroke-width': 0.1 })
  el(g, 'path', { d: `M${x + rx + 0.1} ${z + 0.14}H${x + w - rx - 0.1}`, stroke: '#fff', 'stroke-opacity': 0.55, 'stroke-width': 0.09, 'stroke-linecap': 'round' })
  if (o.studs !== false) {
    const cols = o.cols ?? Math.max(1, Math.round(w / 0.85))
    const rows = o.rows ?? Math.max(1, Math.round(h / 0.85))
    const sx = w / cols
    const sz = h / rows
    for (let i = 0; i < cols; i++) {
      for (let j = 0; j < rows; j++) {
        const cx0 = x + sx * (i + 0.5)
        const cz0 = z + sz * (j + 0.5)
        el(g, 'circle', { cx: cx0, cy: cz0 + 0.05, r: 0.2, fill: dark(col, 0.3) })
        el(g, 'circle', { cx: cx0, cy: cz0, r: 0.2, fill: light(col, 0.22), stroke: dark(col, 0.35), 'stroke-width': 0.045 })
        el(g, 'path', { d: `M${cx0 - 0.1} ${cz0 - 0.03}A.12 .12 0 0 1 ${cx0 + 0.02} ${cz0 - 0.12}`, stroke: '#fff', 'stroke-opacity': 0.7, 'stroke-width': 0.04, fill: 'none', 'stroke-linecap': 'round' })
      }
    }
  }
  return g
}

const S = `fill="none" stroke="${INK}" stroke-width=".085" stroke-linecap="round" stroke-linejoin="round"`
const GL = {
  plane: `<path ${S} d="M-.4 .04L.4 -.3L.12 .38L-.04 .1Z M-.04 .1L.4 -.3"/>`,
  bell: `<path ${S} d="M-.34 .24H.34M-.24 .24C-.24 -.22 .24 -.22 .24 .24M0 -.2V-.32"/><circle cx="0" cy="-.34" r=".05" fill="${INK}"/>`,
  tag: `<path ${S} d="M-.36 -.2H.08L.38 .06L.08 .32H-.36Z"/><circle cx="-.2" cy=".06" r=".06" fill="${INK}"/>`,
  phone: `<rect ${S} x="-.2" y="-.4" width=".4" height=".8" rx=".08"/><path ${S} d="M-.06 .28H.06"/>`,
  screen: `<rect ${S} x="-.4" y="-.3" width=".8" height=".52" rx=".06"/><path ${S} d="M-.16 .36H.16M-.2 .1V-.04M0 .1V-.14M.2 .1V-.1"/>`,
  book: `<path ${S} d="M-.4 -.26Q-.2 -.36 0 -.26V.3Q-.2 .2 -.4 .3Z M0 -.26Q.2 -.36 .4 -.26V.3Q.2 .2 0 .3Z"/>`,
  chip: `<rect ${S} x="-.22" y="-.22" width=".44" height=".44" rx=".05"/><path ${S} d="M-.1 -.4V-.22M.1 -.4V-.22M-.1 .22V.4M.1 .22V.4M-.4 -.1H-.22M-.4 .1H-.22M.22 -.1H.4M.22 .1H.4"/>`,
  pencil: `<path ${S} d="M-.32 .32L-.26 .1L.2 -.36L.38 -.18L-.08 .28Z M.1 -.26L.28 -.08"/>`,
  drawer: `<rect ${S} x="-.38" y="-.3" width=".76" height=".6" rx=".06"/><path ${S} d="M-.38 0H.38M-.1 .15H.1"/>`,
  bulb: `<circle ${S} cx="0" cy="-.1" r=".26"/><path ${S} d="M-.12 .26H.12M-.07 .36H.07"/>`,
  speaker: `<path ${S} d="M-.4 -.12H-.2L.04 -.32V.32L-.2 .12H-.4Z M.2 -.14Q.32 0 .2 .14 M.3 -.26Q.5 0 .3 .26"/>`,
  wave: `<path ${S} d="M-.4 0Q-.3 -.4 -.2 0T0 0T.2 0T.4 0"/>`,
}
export type GlyphName = keyof typeof GL

/** a small pictogram on a white round tile */
export function glyph(p: Element, name: GlyphName, x: number, z: number) {
  const g = el(p, 'g', { transform: `translate(${x} ${z})` })
  el(g, 'circle', { r: 0.52, fill: '#fff', stroke: INK, 'stroke-width': 0.08 })
  el(g, 'g').innerHTML = GL[name]
  return g
}

/** the "1x" part-count chip from a LEGO manual */
export function chip(p: Element, x: number, z: number, txt: string) {
  const g = grp(p, 'pc')
  const w = txt.length > 2 ? 1.2 : 1
  el(g, 'rect', { x: x - w / 2, y: z - 0.3, width: w, height: 0.6, rx: 0.3, fill: '#fff', stroke: INK, 'stroke-width': 0.08 })
  el(g, 'text', { x, y: z + 0.15, 'text-anchor': 'middle', 'font-size': 0.42, class: 'f' }, txt)
  return g
}

/** a numbered build bag: the zone's header, like the bags that come in the box */
export function bag(p: Element, x: number, z: number, n: number, col: string) {
  const g = grp(p, 'bag', { transform: `translate(${x} ${z})` })
  el(g, 'path', { d: 'M0 .4L.17 .12L.34 .4L.51 .12L.68 .4L.85 .12L1.02 .4L1.19 .12L1.36 .4L1.53 .12L1.7 .4V1.8Q1.7 2 1.5 2H.2Q0 2 0 1.8Z', fill: '#fff', stroke: INK, 'stroke-width': 0.1, 'stroke-linejoin': 'round' })
  el(g, 'path', { d: 'M.2 .75V1.6', stroke: col, 'stroke-opacity': 0.25, 'stroke-width': 0.12, 'stroke-linecap': 'round' })
  el(g, 'text', { x: 0.85, y: 1.5, 'text-anchor': 'middle', 'font-size': 1.1, class: 'f', fill: dark(col, 0.1) }, n)
  return g
}
