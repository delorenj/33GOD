import { domainById, type DomainId } from '../domains'
import { drawConn, obj, type ConnEls } from './conn'
import { L2_BUBBLES, L2_BUS, L2_EXITS, L2_EXIT_OF, L2_LINES, L2_PIPE, L2_PLATE } from './graph'
import { paper, plate } from './paper'
import { INK, INK2, bag, brick, chip, el, glyph, grp, halo, lines, nearest } from './svg'
import type { Sel } from './drawL1'

export interface L2Cb { zone(id: DomainId): void }
export interface L2 { apply(sel: Sel): void }

/** Page 2: Bloodbank up close. Same grammar as the whole map. Every line that leaves Bloodbank ends in a pill
 *  coloured for the zone on the other side, and the pill is a button that goes there. */
export function buildL2(svg: SVGSVGElement, cb: L2Cb): L2 {
  const BB = domainById.bloodbank.color
  paper(svg, 'l2', { x0: -3.7, z0: -2.7, x1: 37.7, z1: 20.2 })
  const plates = grp(svg, 'mp-plates')
  const lineL = grp(svg, 'mp-conns')
  const bricks = grp(svg, 'mp-bricks')
  const pills = grp(svg, 'mp-labels')
  const steps = grp(svg, 'mp-stepl')
  const ui = grp(svg, 'mp-ui')

  plate(plates, L2_PLATE, BB, 'mp-plate2')
  bag(ui, -3.1, -2.35, 2, BB)
  el(ui, 'text', { x: -0.9, y: -1.0, 'font-size': 1.25, class: 'f' }, 'Bloodbank')
  el(ui, 'text', { x: -0.85, y: -0.25, 'font-size': 0.5, fill: INK2 }, 'carries the news')
  el(ui, 'text', { x: -0.85, y: -2.0, 'font-size': 0.46, fill: INK2, 'font-weight': 700, 'letter-spacing': 0.05 }, 'UP CLOSE  ·  33GOD › BLOODBANK')

  // the pipeline row, inside the plate
  for (const q of L2_PIPE) {
    const g = grp(bricks, 'part')
    brick(g, q.x, q.z, q.w, q.h, BB)
    glyph(g, q.glyph, q.x, q.z + 0.02)
    chip(g, q.x - q.w / 2 + 0.1, q.side === 't' ? q.z + q.h / 2 + 0.05 : q.z - q.h / 2 - 0.05, '1x')
    const ns = 0.58
    const total = ns * 1.1 + 0.42 * 1.15
    const tz = q.side === 't' ? q.z - q.h / 2 - 0.2 - total + ns * 0.85 : q.z + q.h / 2 + 0.2 + ns * 0.85
    halo(lines(g, q.x, tz, [q.lab, q.tag], ns, { sizes: [ns, 0.42], fills: [INK, INK2], weights: [700], lh: 1.1 }))
  }

  // the big board: two faces, kept for different times
  {
    const { x, z, w, h } = L2_BUS
    const g = grp(bricks, 'part')
    el(g, 'rect', { x, y: z + 0.22, width: w, height: h, rx: 0.4, fill: '#7a1f27' })
    el(g, 'rect', { x, y: z, width: w, height: h / 2, rx: 0.4, fill: '#D6404B', stroke: INK, 'stroke-width': 0.1 })
    el(g, 'rect', { x, y: z + h / 2 - 0.4, width: w, height: h / 2 + 0.4, rx: 0.4, fill: '#F5C400', stroke: INK, 'stroke-width': 0.1 })
    el(g, 'rect', { x: x + 0.08, y: z + h / 2 - 0.3, width: w - 0.16, height: 0.6, fill: '#fff', stroke: INK, 'stroke-width': 0.07 })
    el(g, 'text', { x: x + w / 2, y: z + h / 2 + 0.19, 'text-anchor': 'middle', 'font-size': 0.52, class: 'f' }, 'Bloodbank bus  ·  NATS JetStream')
    el(g, 'text', { x: x + 0.5, y: z + 0.92, 'font-size': 0.5, fill: '#fff', stroke: '#7a1f27', 'stroke-width': 0.12, 'paint-order': 'stroke', 'font-weight': 700 }, 'BACK: envelopes (commands)  ·  kept 1 day')
    el(g, 'text', { x: x + 0.5, y: z + h - 0.35, 'font-size': 0.5, 'font-weight': 700 }, 'FRONT: post-its (events)  ·  kept 7 days')
    for (let i = 0; i < 4; i++) {
      obj(g, 'env', x + w - 4.2 + i, z + 0.5, 0.7)
      obj(g, 'postit', x + w - 4.2 + i, z + h - 0.55, 0.7)
    }
    chip(g, x - 0.05, z - 0.05, '1x')
  }

  // the lines, then a small white label pill on each
  const conns: ConnEls[] = L2_LINES.map((l) => drawConn(lineL, l.pts, l.k, { hl: 0.62, wScale: 1.2, round: 0.4, objAt: l.ot, objScale: 1.05 }))
  const labels = L2_LINES.map((l) => {
    if (!l.lab) return null
    const w = l.lab.length * 0.2 + 0.5
    const px = l.px ?? l.pts[0][0]
    const x0 = l.al === 'r' ? px + 0.35 - w : l.al === 'l' ? px - 0.35 : px - w / 2
    const g = grp(pills, 'pill', { transform: `translate(${x0} ${(l.pz ?? 0) - 0.31})` })
    el(g, 'rect', { width: w, height: 0.62, rx: 0.31, fill: '#fff', stroke: INK, 'stroke-width': 0.07 })
    el(g, 'text', { x: w / 2, y: 0.43, 'text-anchor': 'middle', 'font-size': 0.38, 'font-weight': 700 }, l.lab)
    return g
  })

  // zone-exit pills
  const exitG: Record<string, SVGGElement> = {}
  for (const e of L2_EXITS) {
    const zone = domainById[e.zone]
    const w = zone.name.length * 0.2 + 1.15
    const g = grp(pills, 'mp-pill', { transform: `translate(${e.x} ${e.z})` })
    exitG[e.id] = g
    el(g, 'rect', { x: -w / 2, y: -0.33, width: w, height: 0.66, rx: 0.33, fill: zone.color, stroke: '#fff', 'stroke-width': 0.06 })
    el(g, 'text', { x: -0.14, y: 0.12, 'text-anchor': 'middle', 'font-size': 0.34, class: 'f', fill: '#fff' }, zone.name)
    el(g, 'path', { d: `M${w / 2 - 0.55} -0.13L${w / 2 - 0.31} 0L${w / 2 - 0.55} 0.13`, fill: 'none', stroke: '#fff', 'stroke-width': 0.06, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' })
    const nm = e.name
    const ty = e.side === 't' ? -0.5 - (nm.length - 1) * 0.5 : 0.33 + 0.5
    halo(lines(g, 0, ty, nm, 0.41, { fills: [INK], lh: 1.15, weights: [700] }), 0.2)
    el(g, 'title', {}, `${e.name.join(' ')} lives in ${zone.name}. Click to go there.`)
    g.addEventListener('click', () => cb.zone(e.zone))
  }

  // build-1 step numbers
  const bubbles = L2_BUBBLES.map(([n, x, z, li]) => {
    const g = grp(steps, 'bub')
    const np = nearest(L2_LINES[li].pts, x, z)
    el(g, 'path', { d: `M${x} ${z}L${np[0]} ${np[1]}`, stroke: INK, 'stroke-width': 0.09, 'stroke-dasharray': '.12 .14', 'stroke-linecap': 'round' })
    el(g, 'circle', { cx: x, cy: z, r: 0.66, fill: '#fff', stroke: INK, 'stroke-width': 0.13 })
    el(g, 'text', { x, y: z + 0.3, 'text-anchor': 'middle', 'font-size': 0.9, class: 'f' }, n)
    return g
  })

  // the parts list for this page
  {
    const g = grp(ui, 'inv')
    el(g, 'rect', { x: -3.4, y: 15.3, width: 12.2, height: 4.4, rx: 0.5, fill: '#fff', 'fill-opacity': 0.88, stroke: INK, 'stroke-width': 0.1 })
    el(g, 'rect', { x: -3.4, y: 15.3, width: 12.2, height: 1, rx: 0.5, fill: INK })
    el(g, 'text', { x: 2.7, y: 16.0, 'text-anchor': 'middle', 'font-size': 0.5, fill: '#fff', class: 'f' }, 'PARTS FOR THIS PAGE')
    ;['bb-hook', 'hook-hub', 'naming contract', 'Bloodbank bus'].forEach((nm, i) => {
      const x = -3.0 + (i % 2) * 6.1
      const z = 17.4 + Math.floor(i / 2) * 1.55
      el(g, 'text', { x, y: z + 0.15, 'font-size': 0.5, class: 'f' }, '1x')
      brick(g, x + 1.6, z, 1.3, 0.8, BB, { cols: 2, rows: 1 })
      el(g, 'text', { x: x + 2.45, y: z + 0.15, 'font-size': 0.4, 'font-weight': 700 }, nm)
    })
  }
  el(ui, 'text', { x: 36.3, y: 19.7, 'text-anchor': 'end', 'font-size': 0.46, fill: INK2 }, 'Lines and bricks work just like the whole map. A coloured pill is another zone: click it to go there.')

  function apply(sel: Sel) {
    const n = typeof sel === 'number' ? sel : 0
    const litExit = new Set<string>()
    L2_LINES.forEach((l, i) => {
      const lit = !n || l.b.includes(n)
      const e = conns[i]
      e.g.style.opacity = lit ? '1' : '0.14'
      if (labels[i]) labels[i]!.style.opacity = lit ? '1' : '0.2'
      const big = n && lit ? 1.25 : 1
      e.halo.setAttribute('stroke-width', String(e.w * big + 0.34))
      e.ln.setAttribute('stroke-width', String(e.w * big))
      if (lit && L2_EXIT_OF[i]) litExit.add(L2_EXIT_OF[i])
      if (lit && n) lineL.appendChild(e.g)
    })
    for (const id in exitG) exitG[id].style.opacity = !n || litExit.has(id) ? '1' : '0.35'
    bubbles.forEach((b) => { b.style.display = n === 1 ? '' : 'none' })
  }
  apply('calm')
  return { apply }
}
