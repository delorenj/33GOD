import { stationById, type StationId, type Vec3 } from '../content'

// Where each tour stop is: where the newcomer stands (anchor) and where the camera looks from.
// Existing stations reuse the sandbox's floor plan; new sets are built in TourSets.tsx.
export interface TourSet { name: string; anchor: Vec3; view: { pos: Vec3; target: Vec3 }; built?: boolean; /** how far a phone backs the camera off (default 1.6) */ portraitK?: number }

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
  clock: [-3.8, 0, -6.6], // in front of the clock's face, clear of the planner's desk
  crew: [6.9, 0, -5.2],
}

// The sandbox's station views frame machinery; a tour stop frames people. These sets get a
// camera placed relative to the anchor (offset from it, looking just above the cast's heads).
const PEOPLE_FRAME: Partial<Record<StationId, { off: Vec3; look?: Vec3; portraitK?: number }>> = {
  dock: { off: [3.2, 4.4, 8.2] },
  labeldesk: { off: [2.6, 4.2, 8] },
  belt: { off: [-2.8, 4.6, 8.4] },
  cataloguer: { off: [1.4, 4.2, 8.4] },
  control: { off: [2.2, 3.6, 7.6], look: [0, 1.2, -1] },
  clock: { off: [7, 5.4, 1.8], look: [-1.2, 0.4, -0.2], portraitK: 1.1 }, // from the east, the clock behind the cast; further back is inside the crew hall
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
    const pf = PEOPLE_FRAME[st.id]
    if (pf) {
      const lk = pf.look ?? [0, 1.1, -1]
      return {
        name: st.name,
        anchor: a,
        portraitK: pf.portraitK,
        view: { pos: [a[0] + pf.off[0], a[1] + pf.off[1], a[2] + pf.off[2]], target: [a[0] + lk[0], a[1] + lk[1], a[2] + lk[2]] },
      }
    }
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
