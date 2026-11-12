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
  rules: [-13, 0, -5.4],
  control: [-5, 3.5, 12.2], // on Holocene's mezzanine
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

// The tour's own sets. Views are relative to the anchor, so a set can move with its domain.
const rel = (name: string, anchor: Vec3, off: Vec3, look: Vec3): TourSet => ({
  name, anchor, built: true,
  view: { pos: [anchor[0] + off[0], anchor[1] + off[1], anchor[2] + off[2]], target: [anchor[0] + look[0], anchor[1] + look[1], anchor[2] + look[2]] },
})
const NEW: Record<string, TourSet> = {
  entrance: rel('The entrance', [-14.5, 0, 12.5], [5, 3.4, 7], [0, 1.4, -0.5]), // Holocene: the Agent Pad
  voxxy: rel('The voice booth', [15.4, 0, -8.6], [-4.7, 4.6, 7.9], [1.3, 1.4, -1.6]), // Voice
  library: rel('The lessons library', [11.5, 0, 13], [5.6, 4.4, 7.2], [-1.4, 1.5, -2]), // Memory: Hindsight
  staffing: rel('The staffing desk', [11.4, 0, -4.6], [5.9, 4.2, 6.7], [1.4, 1.3, -1.8]), // Workers: AutomaticAI gateway
  soundwing: rel('The sound wing', [18.6, 0, -1.8], [5.9, 5, 7.3], [1.9, 1.4, -2.2]), // Voice: wax
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
        name: st.place,
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
      name: st.place,
      anchor: a,
      view: { pos: [tx + (px - tx) * k, ty + (py - ty) * k, tz + (pz - tz) * k], target: [(tx + a[0]) / 2, Math.max(1.2, (ty + a[1] + 1) / 2), (tz + a[2]) / 2] },
    }
  }
  return { name: id, anchor: [0, 0, 6], view: { pos: [8, 6, 16], target: [0, 1.5, 6] } }
}

export const NEW_SETS = NEW
