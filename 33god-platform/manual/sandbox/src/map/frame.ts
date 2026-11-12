import { MAP_BOUNDS } from '../domains'

// One frame shared by the top-down camera and the map overlay, so marks on the map sit on the things they name.
// Landscape: north (-z) is up. Portrait screens turn the floor a quarter so the long side runs down the phone:
// east (+x) is up and the front (+z) is to the right.

export const MAP_MARGIN = 1.6
export const mapPortrait = (w = innerWidth, h = innerHeight) => w / h < 0.9

/** world (x, z) to map/SVG coordinates */
export const toMap = (x: number, z: number, portrait: boolean): [number, number] => (portrait ? [z, -x] : [x, z])

/** a world rect [x0, z0, x1, z1] as an SVG box */
export function mapRect(r: readonly [number, number, number, number], portrait: boolean) {
  const [x0, z0, x1, z1] = r
  return portrait ? { x: z0, y: -x1, w: z1 - z0, h: x1 - x0 } : { x: x0, y: z0, w: x1 - x0, h: z1 - z0 }
}

export function mapViewBox(portrait: boolean) {
  const m = MAP_MARGIN
  const b = mapRect([MAP_BOUNDS.x0, MAP_BOUNDS.z0, MAP_BOUNDS.x1, MAP_BOUNDS.z1], portrait)
  return `${b.x - m} ${b.y - m} ${b.w + 2 * m} ${b.h + 2 * m}`
}
