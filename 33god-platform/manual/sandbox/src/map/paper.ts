import { INK, el, grp } from './svg'

/** Blueprint paper, like the overworld page: pale blue sheet, 1 m and 5 m grid, a little grain, a double navy frame. */
export function paper(svg: SVGSVGElement, pre: string, frame: { x0: number; z0: number; x1: number; z1: number }) {
  const defs = el(svg, 'defs')
  defs.innerHTML = `<pattern id="${pre}-gs" width="1" height="1" patternUnits="userSpaceOnUse"><path d="M1 0H0V1" fill="none" stroke="#a9c6dc" stroke-width="0.022"/></pattern>
<pattern id="${pre}-gl" width="5" height="5" patternUnits="userSpaceOnUse"><path d="M5 0H0V5" fill="none" stroke="#8fb3cf" stroke-width="0.045"/></pattern>
<filter id="${pre}-grain"><feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" seed="4"/><feColorMatrix values="0 0 0 0 0.08  0 0 0 0 0.2  0 0 0 0 0.35  0 0 0 0.08 0"/></filter>`
  const g = grp(svg, 'mp-paper')
  const box = { x: frame.x0, y: frame.z0, width: frame.x1 - frame.x0, height: frame.z1 - frame.z0 }
  el(g, 'rect', { ...box, fill: '#d8e8f3' })
  el(g, 'rect', { ...box, fill: `url(#${pre}-gs)` })
  el(g, 'rect', { ...box, fill: `url(#${pre}-gl)` })
  el(g, 'rect', { ...box, filter: `url(#${pre}-grain)` })
  el(g, 'rect', { x: box.x, y: box.y, width: box.width, height: box.height, fill: 'none', stroke: INK, 'stroke-width': 0.12 })
  el(g, 'rect', { x: box.x + 0.22, y: box.y + 0.22, width: box.width - 0.44, height: box.height - 0.44, fill: 'none', stroke: INK, 'stroke-width': 0.04 })
  return g
}

/** a zone as a calm plate: a soft tint, a coloured edge and a dashed inner border (no studs: the bricks carry those) */
export function plate(p: Element, rect: [number, number, number, number], col: string, cls = 'mp-zone') {
  const [x0, z0, x1, z1] = rect
  const g = grp(p, cls)
  el(g, 'rect', { class: 'rbody', x: x0 + 0.2, y: z0 + 0.2, width: x1 - x0 - 0.4, height: z1 - z0 - 0.4, rx: 0.7, fill: col, 'fill-opacity': 0.13, stroke: col, 'stroke-width': 0.14 })
  el(g, 'rect', { x: x0 + 0.5, y: z0 + 0.5, width: x1 - x0 - 1, height: z1 - z0 - 1, rx: 0.45, fill: 'none', stroke: col, 'stroke-opacity': 0.5, 'stroke-width': 0.05, 'stroke-dasharray': '0.3 0.25' })
  return g
}

