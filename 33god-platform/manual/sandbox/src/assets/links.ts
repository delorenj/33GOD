// ?at=<component id>: fly to any Atlas component (its station, or its kiosk), not only to the eleven stations.
import { stationById, type StationId, type Vec3 } from '../content'
import { ui } from '../sim/store'
import { castPlacement, standOf, viewFor } from '../waybill/stations'
import { assetFor } from './registry'

/** A kiosk's camera, the same framing the waybill player uses for a kiosk stop. */
const kioskView = (a: Vec3) => ({ pos: [a[0] + 3.4, 3.9, a[2] + 6.6] as Vec3, target: [a[0] - 0.2, 1.1, a[2] - 0.4] as Vec3 })

/** Fly the camera to a component by registry id, alias or ext: id. Returns false when nothing on the floor answers to it. */
export function flyToComponent(id: string): boolean {
  const asset = assetFor(id)
  if (asset?.fixture && asset.anchor) { ui.fly(kioskView(asset.anchor.at)); return true }
  const s = standOf(id)
  if (!s) return false
  if (s.station) {
    if (s.station in stationById) ui.openStation(s.station as StationId) // a real station: its panel opens too
    else ui.fly(viewFor(s.station, castPlacement()).view)
    return true
  }
  const k = castPlacement().kioskById[s.id]
  if (!k) return false
  // a kiosk has no body on the ambient floor until its asset lands: show the station it stands beside, not an empty slot
  ui.fly(asset ? kioskView(k.at) : viewFor(k.near, castPlacement()).view)
  return true
}
