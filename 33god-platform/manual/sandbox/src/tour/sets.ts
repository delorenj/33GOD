import { stationById, type StationId, type Vec3 } from '../content'

// Where each tour stop is: where the newcomer stands (anchor) and where the camera looks from.
// Existing stations reuse the sandbox's floor plan; new sets are built in TourSets.tsx.
export interface TourSet { name: string; anchor: Vec3; view: { pos: Vec3; target: Vec3 }; built?: boolean }

const ANCHORS: Record<StationId, Vec3> = {
  bays: [-20.5, 0, 2.2],
  courier: [-16, 0, 3.4],
  dock: [-12.6, 0, 2.8],
  labeldesk: [-7.9, 0, 4.4],
  belt: [-3.3, 0, 2.6],
  archive: [5.8, 0, 6.8],
  rules: [4, 0, 10],
  control: [9.4, 3.5, 1.6],
  cataloguer: [3.4, 0, 3.4],
  clock: [-4.2, 0, -4.4],
  crew: [6.9, 0, -5.2],
}

const NEW: Record<string, TourSet> = {
  entrance: { name: 'The entrance', anchor: [-19.5, 0, 14.5], view: { pos: [-14.5, 3.4, 21.5], target: [-19.5, 1.4, 14] }, built: true },
  voxxy: { name: 'The voice booth', anchor: [15.2, 0, -9.4], view: { pos: [10.5, 4.6, -1.5], target: [16.5, 1.4, -11] }, built: true },
  library: { name: 'The lessons library', anchor: [-12.6, 0, -8], view: { pos: [-7, 4.4, -0.8], target: [-14, 1.5, -10] }, built: true },
  staffing: { name: 'The staffing desk', anchor: [11.6, 0, 13.8], view: { pos: [17.5, 4.2, 20.5], target: [13, 1.3, 12] }, built: true },
  soundwing: { name: 'The sound wing', anchor: [18.6, 0, -1.8], view: { pos: [24.5, 5, 5.5], target: [20.5, 1.4, -4] }, built: true },
}

export function setFor(id: string): TourSet {
  if (id in NEW) return NEW[id]
  const st = stationById[id as StationId]
  if (st) {
    const a = ANCHORS[st.id]
    // pull the station's camera in a little so the people are in frame
    const [px, py, pz] = st.view.pos
    const [tx, ty, tz] = st.view.target
    const k = 0.78
    return {
      name: st.name,
      anchor: a,
      view: { pos: [tx + (px - tx) * k, ty + (py - ty) * k, tz + (pz - tz) * k], target: [(tx + a[0]) / 2, Math.max(1.2, (ty + a[1] + 1) / 2), (tz + a[2]) / 2] },
    }
  }
  return { name: id, anchor: [0, 0, 6], view: { pos: [8, 6, 16], target: [0, 1.5, 6] } }
}

export const NEW_SETS = NEW
