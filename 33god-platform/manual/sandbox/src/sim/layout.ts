import type { Vec3 } from '../content'

// Floor plan, in metres. Flow runs left to right: vendors -> courier -> dock -> belt -> readers.
// Envelopes live on the back (-z) side: clock -> belt back -> crew hall.

export const BELT = {
  x0: -2.1, x1: 2.1,
  frontZ: 0.68, backZ: -0.68,
  baseY: 0.9,
  mPerDay: 1.8,
  frontDays: 7, backDays: 1,
}
export const BELT_TOP = BELT.baseY + BELT.frontDays * BELT.mPerDay
export const COLS = [-1.72, -1.03, -0.34, 0.34, 1.03, 1.72]

export const BAY_X = -24
export const BAY_Z = [-7.5, -4.5, -1.5, 1.5, 4.5, 7.5]

export const DOCK = { center: [-9.5, 0, 0] as Vec3, door: [-11.5, 0, 0] as Vec3, out: [-7.6, 1.5, 0] as Vec3 }
export const LABEL_DESK: Vec3 = [-9.5, 0, 3]

export const READERS = {
  archive: [8, 1.4, 5] as Vec3,
  control: [-5, 4.6, 11.5] as Vec3, // Holocene, up front, its window facing the belt
  rules: [-14, 1.3, -7] as Vec3, // n8n, in the Triggers zone
}
export const CATALOGUER: Vec3 = [4.6, 0, 2]
export const CLOCK: Vec3 = [-6, 0, -6]
// the clock's planner reads tick post-its; its hands (the executor) take the clock's own envelopes
export const PLANNER: Vec3 = [-4.4, 0, -4.6]
export const HANDS: Vec3 = [-8.8, 0, -5.6]
// the crew hall: drawn with 4 desks and a tray of 4; the real batch hatch runs 4 and holds 64 more
export const CREW = {
  center: [7, 0, -7.5] as Vec3,
  desks: [[4.9, 1.05, -7.2], [6.3, 1.05, -7.2], [7.7, 1.05, -7.2], [9.1, 1.05, -7.2]] as Vec3[],
  tray: [4.2, 1.1, -4.9] as Vec3,
}
export const TRAY = 4
// where the sound wing's outbox sticks its no-hatch envelopes from
export const SOUND_OUTBOX: Vec3 = [15.5, 3, -3.2]

export function courierPath(vendor: number): Vec3[] {
  const z = BAY_Z[vendor]
  return [
    [BAY_X + 1.2, 0, z],
    [-18, 0, z],
    [-14.5, 0, z * 0.25],
    [DOCK.door[0] - 0.4, 0, 0],
  ]
}

export function along(path: Vec3[], u: number): Vec3 {
  const segs: number[] = []
  let total = 0
  for (let i = 1; i < path.length; i++) {
    const d = Math.hypot(path[i][0] - path[i - 1][0], path[i][2] - path[i - 1][2])
    segs.push(d)
    total += d
  }
  let dist = Math.max(0, Math.min(1, u)) * total
  for (let i = 0; i < segs.length; i++) {
    if (dist <= segs[i] || i === segs.length - 1) {
      const k = segs[i] === 0 ? 0 : Math.min(1, dist / segs[i])
      const a = path[i], b = path[i + 1]
      return [a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k, a[2] + (b[2] - a[2]) * k]
    }
    dist -= segs[i]
  }
  return path[path.length - 1]
}

export function notePos(kind: 'post' | 'env', col: number, ageDays: number): Vec3 {
  return [COLS[col], BELT.baseY + ageDays * BELT.mPerDay, kind === 'post' ? BELT.frontZ : BELT.backZ]
}
