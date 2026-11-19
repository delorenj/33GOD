// Where a station's body stands: the floor point and facing of the primitive it replaces (src/world/Props.tsx,
// src/tour/TourWorld.tsx for the tour's own sets). An asset's front (+Z in the model) turns to `rotY`, then its
// own asset.json `rotationY` is added. Kiosks face +Z, like the generic kiosk box.
import type { Vec3 } from '../content'
import { BAY_X, CATALOGUER, CLOCK, CREW, DOCK, LABEL_DESK, READERS } from '../sim/layout'
import { setFor } from '../tour/sets'
import type { SetId } from '../waybill/stations'

export interface Anchor { at: Vec3; rotY: number }
const floor = (p: Vec3): Vec3 => [p[0], 0, p[2]]

export const STATION_BODY: Record<SetId, Anchor> = {
  bays: { at: [BAY_X - 1.2, 0, 0], rotY: Math.PI / 2 }, // the bays open east, onto the floor
  courier: { at: [-16.4, 0, 6.4], rotY: 0 }, // beside the courier's sign, clear of the six walking paths
  dock: { at: floor(DOCK.center), rotY: -Math.PI / 2 }, // the door (parcels in) faces west, the slot (post-its out) east
  labeldesk: { at: floor(LABEL_DESK), rotY: 0 },
  belt: { at: [0, 0, 0], rotY: 0 }, // post-its on the front (+z) face, envelopes on the back
  archive: { at: floor(READERS.archive), rotY: 0 },
  rules: { at: floor(READERS.rules), rotY: 0 },
  control: { at: floor(READERS.control), rotY: Math.PI }, // Holocene's window faces the belt (north)
  cataloguer: { at: floor(CATALOGUER), rotY: 0 },
  clock: { at: floor(CLOCK), rotY: Math.PI / 4 }, // the face looks south-east, down the floor
  crew: { at: floor(CREW.center), rotY: 0 }, // the hall is open to the south
  entrance: { at: floor(setFor('entrance').anchor), rotY: 0 },
  voxxy: { at: floor(setFor('voxxy').anchor), rotY: 0 },
  library: { at: floor(setFor('library').anchor), rotY: 0 },
  staffing: { at: floor(setFor('staffing').anchor), rotY: 0 },
  soundwing: { at: floor(setFor('soundwing').anchor), rotY: 0 },
}

/** Where the test fixture stands on the floor (dev / forge only): open floor south of the belt, clear of every annex row. */
export const FIXTURE_SLOT: Vec3 = [-4.8, 0, 7.9]
