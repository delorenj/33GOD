import { DOMAINS, MAP_BOUNDS, domainById, type DomainId } from '../domains'
import { drawConn, type ConnEls } from './conn'
import { BAG, BRICKS, BUBBLES, BUS, CANDY, CLI_BAYS, CLI_NAMES, CONNS, GATE, JOURNEYS, bagAt, atOf, partById } from './graph'
import { paper, plate } from './paper'
import { INK, INK2, bag, brick, chip, dark, el, glyph, grp, halo, lines, nearest, type Pt } from './svg'

export type Sel = 'calm' | 'all' | 1 | 2 | 3
export interface L1Cb { zone(id: DomainId): void; part(id: string): void }
export interface L1 { apply(sel: Sel): void }

/** name big, job small, on the side that has room */
function label(p: Element, c: Pt, s: Pt, lab: string[], tag: string, side: 'b' | 't' | 'r', ns = 0.62) {
  const [x, z] = c
  const [w, h] = s
  const ts = 0.42
  const arr = [...lab, tag]
  const total = lab.length * ns * 1.1 + ts * 1.15
  let tx = x
  let tz: number
  let anchor = 'middle'
  if (side === 'b') tz = z + h / 2 + 0.2 + ns * 0.85
  else if (side === 't') tz = z - h / 2 - 0.2 - total + ns * 0.85
  else { tx = x + w / 2 + 0.35; tz = z - total / 2 + ns * 0.85; anchor = 'start' }
  const t = lines(p, tx, tz, arr, ns, { anchor, sizes: [...lab.map(() => ns), ts], fills: [...lab.map(() => INK), INK2], weights: lab.map(() => 700), lh: 1.1, cls: 'lab' })
  return halo(t)
}

const plain = (g: SVGElement, text: string) => { el(g, 'title', {}, text) }

/** white-on-colour text for words sitting on a brick */
function onBrick(p: Element, x: number, z: number, txt: string, size: number, col: string) {
  const t = el(p, 'text', { x, y: z, 'text-anchor': 'middle', 'font-size': size, fill: '#fff', stroke: dark(col, 0.5), 'stroke-width': size * 0.24, 'paint-order': 'stroke', 'stroke-linejoin': 'round', 'font-weight': 700 }, txt)
  return t
}

/** a plate that holds a few bricks: Candybar and hermes-gateway */
function submodel(p: Element, id: string, plateRect: number[], col: string, title: string, sub: string) {
  const g = grp(p, 'mp-part', { 'data-id': id })
  const [x0, z0, x1, z1] = plateRect
  el(g, 'rect', { x: x0, y: z0, width: x1 - x0, height: z1 - z0, rx: 0.4, fill: '#fff', 'fill-opacity': 0.8, stroke: dark(col, 0.2), 'stroke-width': 0.12 })
  chip(g, x0 + 0.65, z0 + 0.55, '1x')
  el(g, 'text', { x: x0 + 1.5, y: z0 + 0.85, 'font-size': 0.7, class: 'f' }, title)
  el(g, 'text', { x: x0 + 1.5, y: z0 + 1.45, 'font-size': 0.42, fill: INK2 }, sub)
  return g
}

export function buildL1(svg: SVGSVGElement, cb: L1Cb): L1 {
  const B = MAP_BOUNDS
  paper(svg, 'l1', { x0: B.x0 - 0.5, z0: B.z0 - 0.5, x1: B.x1 + 0.5, z1: B.z1 + 0.5 })
  const plates = grp(svg, 'mp-plates')
  const lineL = grp(svg, 'mp-conns')
  const bricks = grp(svg, 'mp-bricks')
  const steps = grp(svg, 'mp-stepl')

  // ---- zones: one calm plate and one numbered bag each. Click = open that zone ----
  for (const d of DOMAINS) {
    const g = plate(plates, d.rect, d.color)
    g.setAttribute('data-zone', d.id)
    const [hx, hz] = bagAt(d.id)
    bag(g, hx, hz, BAG[d.id], d.color)
    el(g, 'text', { x: hx + 2.05, y: hz + 1.05, 'font-size': 0.8, class: 'f' }, d.name)
    el(g, 'text', { x: hx + 2.05, y: hz + 1.7, 'font-size': 0.46, fill: INK2 }, d.says)
    plain(g, `${d.name}: ${d.says}`)
    g.addEventListener('click', () => cb.zone(d.id))
  }

  const partG: Record<string, SVGGElement> = {}
  const mk = (id: string) => {
    const g = grp(bricks, 'mp-part', { 'data-id': id })
    partG[id] = g
    g.addEventListener('click', () => cb.part(id))
    plain(g, `${partById[id].name}: ${partById[id].plain}`)
    return g
  }

  // ---- single bricks, each on its PARTS.at ----
  for (const q of BRICKS) {
    const [cx, cz] = atOf(q.id)
    const col = domainById[partById[q.id].domain].color
    const g = mk(q.id)
    brick(g, cx, cz, q.s[0], q.s[1], col)
    glyph(g, q.glyph, cx, cz + 0.02)
    chip(g, q.side === 't' ? cx + q.s[0] / 2 - 0.1 : cx - q.s[0] / 2 + 0.1, q.side === 't' ? cz + q.s[1] / 2 + 0.05 : cz - q.s[1] / 2 - 0.05, '1x')
    label(g, [cx, cz], q.s, q.lab, q.tag, q.side)
  }

  // ---- Agent CLIs: six bays are one part ("6x") ----
  {
    const [x, z] = atOf('clis')
    const g = mk('clis')
    const col = domainById.agents.color
    CLI_NAMES.forEach((nm, i) => {
      brick(g, x, z + CLI_BAYS[i], 4.6, 1.7, col, { cols: 5, rows: 1 })
      onBrick(g, x, z + CLI_BAYS[i] + 0.5, nm, 0.62, col)
    })
    el(g, 'path', { d: `M${x + 2.25} ${z - 7.5}H${x + 2.8}V${z + 7.5}H${x + 2.25}`, fill: 'none', stroke: INK, 'stroke-width': 0.12, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' })
    chip(g, x - 1.85, z - 9.85, '6x')
    el(g, 'text', { x: x - 1.15, y: z - 9.62, 'font-size': 0.62, fill: INK, 'font-weight': 700 }, 'Agent CLIs')
    el(g, 'text', { x: x - 2.35, y: z - 8.88, 'font-size': 0.4, fill: INK2 }, 'each has a bb-hook inside')
  }

  // ---- Candybar: the one clock, three parts on one plate ----
  {
    const g = submodel(bricks, 'candybar', CANDY.plate, domainById.triggers.color, 'Candybar', 'the only clock')
    partG.candybar = g
    g.addEventListener('click', () => cb.part('candybar'))
    plain(g, `${partById.candybar.name}: ${partById.candybar.plain}`)
    const col = domainById.triggers.color
    for (const [k, nm] of [['clock', 'clock'], ['exec', 'executor'], ['disp', 'dispatcher']] as const) {
      const [cx, cz, w, h] = CANDY[k]
      brick(g, cx, cz, w, h, col, { cols: Math.round(w / 0.9), rows: 1 })
      onBrick(g, cx, cz + 0.45, nm, 0.5, col)
    }
  }

  // ---- hermes-gateway: the crew hall with two hatches ----
  {
    const g = submodel(bricks, 'gateway', GATE.plate, domainById.workers.color, 'hermes-gateway', 'the crew hall')
    partG.gateway = g
    g.addEventListener('click', () => cb.part('gateway'))
    plain(g, `${partById.gateway.name}: ${partById.gateway.plain}`)
    const col = domainById.workers.color
    for (const [k, nm, sub] of [['batch', 'batch hatch', '4 desks + a tray'], ['express', 'express hatch', 'a person is waiting']] as const) {
      const [cx, cz, w, h] = GATE[k]
      brick(g, cx, cz, w, h, col, { cols: Math.round(w / 0.9), rows: 1 })
      onBrick(g, cx, cz + 0.5, nm, 0.44, col)
      el(g, 'text', { x: cx, y: cz + h / 2 + 0.5, 'text-anchor': 'middle', 'font-size': 0.38, fill: INK2 }, sub)
    }
  }

  // ---- the Bloodbank bus: a two-faced board. North half = BACK (envelopes), south half = FRONT (post-its) ----
  {
    const [bx, bz] = atOf('bus')
    const g = mk('bus')
    const [w, h] = BUS.s
    const x = bx - w / 2
    const z = bz - h / 2
    el(g, 'rect', { x, y: z + 0.2, width: w, height: h, rx: 0.35, fill: '#7a1f27' })
    el(g, 'rect', { x, y: z, width: w, height: h / 2 + 0.1, rx: 0.35, fill: '#D6404B', stroke: INK, 'stroke-width': 0.1 })
    el(g, 'rect', { x, y: bz - 0.1, width: w, height: h / 2 + 0.1, rx: 0.35, fill: '#F5C400', stroke: INK, 'stroke-width': 0.1 })
    el(g, 'rect', { x: x + 0.05, y: bz - 0.2, width: w - 0.1, height: 0.4, fill: '#fff', stroke: INK, 'stroke-width': 0.06 })
    el(g, 'text', { x: bx, y: bz + 0.17, 'text-anchor': 'middle', 'font-size': 0.5, class: 'f' }, 'Bloodbank bus')
    el(g, 'text', { x: bx, y: bz - 0.5, 'text-anchor': 'middle', 'font-size': 0.4, fill: '#fff', stroke: '#7a1f27', 'stroke-width': 0.1, 'paint-order': 'stroke', 'font-weight': 700 }, 'envelopes')
    el(g, 'text', { x: bx, y: bz + 0.76, 'text-anchor': 'middle', 'font-size': 0.4, fill: INK, 'font-weight': 700 }, 'post-its')
    chip(g, x - 0.05, z - 0.05, '1x')
  }

  // ---- a button to open Bloodbank up close (page 2) ----
  {
    const g = grp(steps, 'mp-zoom', { transform: 'translate(-18.9 5.55)' })
    el(g, 'rect', { width: 6, height: 1.15, rx: 0.575, fill: '#FFD43B', stroke: INK, 'stroke-width': 0.1 })
    el(g, 'circle', { cx: 0.62, cy: 0.575, r: 0.3, fill: '#fff', stroke: INK, 'stroke-width': 0.08 })
    el(g, 'path', { d: 'M.84 .8L1.12 1.05', stroke: INK, 'stroke-width': 0.1, 'stroke-linecap': 'round' })
    el(g, 'text', { x: 1.5, y: 0.76, 'font-size': 0.42, 'font-weight': 700 }, 'zoom in: Bloodbank')
    plain(g, 'Open Bloodbank up close')
    g.addEventListener('click', () => cb.zone('bloodbank'))
  }

  // ---- the lines ----
  const conns: ConnEls[] = CONNS.map((c) => drawConn(lineL, c.r, c.k, { objAt: c.lt }))
  const stepLayer = grp(steps, 'mp-bubbles')

  function apply(sel: Sel) {
    const act = typeof sel === 'number' ? JOURNEYS[sel - 1] : null
    const on = new Set<number>()
    const used = new Set<string>()
    if (act) {
      act.steps.forEach((s) => s.forEach((ci) => on.add(ci)))
      act.extra.forEach((ci) => on.add(ci))
      on.forEach((ci) => { used.add(CONNS[ci].f); used.add(CONNS[ci].t) })
    }
    CONNS.forEach((_, i) => {
      const e = conns[i]
      const lit = act ? on.has(i) : sel === 'all'
      // calm: every line is there, quiet. A build: its lines shout, the rest almost vanish.
      e.g.style.opacity = act ? (lit ? '1' : '0.12') : sel === 'all' ? '1' : '0.32'
      const big = act && lit ? 1.3 : sel === 'calm' ? 0.85 : 1
      e.halo.setAttribute('stroke-width', String(e.w * big + 0.34))
      e.ln.setAttribute('stroke-width', String(e.w * big))
      e.g.querySelectorAll<SVGElement>('.obj').forEach((o) => { o.style.display = sel === 'calm' || (act && !lit) ? 'none' : '' })
      if (lit) lineL.appendChild(e.g)
    })
    for (const id of [...BRICKS.map((b) => b.id), 'clis', 'candybar', 'gateway', 'bus']) {
      partG[id].style.opacity = !act || used.has(id) || id === 'bus' ? '1' : '0.5'
    }
    stepLayer.replaceChildren()
    if (!act) return
    if (sel === 2) {
      // build 2 rides the express hatch: a person is waiting there, and an agent picks the job up
      const [hx, hz, hw, hh] = GATE.express
      el(stepLayer, 'rect', { x: hx - hw / 2 - 0.2, y: hz - hh / 2 - 0.2, width: hw + 0.4, height: hh + 0.4, rx: 0.45, fill: 'none', stroke: '#FFB400', 'stroke-width': 0.16, 'stroke-dasharray': '.5 .25' })
      const hg = grp(stepLayer, 'holly', { transform: `translate(${hx} ${hz - 0.32})` })
      el(hg, 'rect', { x: -0.85, y: -0.27, width: 1.7, height: 0.54, rx: 0.27, fill: '#FFD43B', stroke: INK, 'stroke-width': 0.07 })
      el(hg, 'circle', { cx: -0.5, cy: 0, r: 0.17, fill: '#fff', stroke: INK, 'stroke-width': 0.05 })
      el(hg, 'text', { x: 0.18, y: 0.14, 'text-anchor': 'middle', 'font-size': 0.4, 'font-weight': 700 }, 'Holly')
    }
    // big step numbers, each tied to its line by a thin dotted leader
    act.steps.forEach((st, si) => st.forEach((ci) => {
      const m = conns[ci].mid
      const bp = BUBBLES[ci] ?? [m.x, m.y - 1.2]
      const g = grp(stepLayer, 'bub')
      const np = nearest(CONNS[ci].r, bp[0], bp[1])
      el(g, 'path', { d: `M${bp[0]} ${bp[1]}L${np[0]} ${np[1]}`, stroke: INK, 'stroke-width': 0.09, 'stroke-dasharray': '.12 .14', 'stroke-linecap': 'round' })
      el(g, 'circle', { cx: bp[0], cy: bp[1], r: 0.72, fill: '#fff', stroke: INK, 'stroke-width': 0.14 })
      el(g, 'text', { x: bp[0], y: bp[1] + 0.32, 'text-anchor': 'middle', 'font-size': 0.98, class: 'f' }, si + 1)
    }))
  }
  apply('calm')
  return { apply }
}

