// Asset discovery (contract section 5): every src/assets/<id>/asset.json is read at build time, checked against
// the contract and the Atlas cast, and becomes one entry. A bad manifest logs one console.warn and is ignored, so
// a broken asset can never take the floor down. Driver.tsx files load lazily, only when their asset mounts.
import { lazy, type ComponentType, type LazyExoticComponent } from 'react'
import { standOf, type SetId, type Stand } from '../waybill/stations'
import { STATION_BODY, FIXTURE_SLOT, type Anchor } from './anchors'
import { parseManifest, type AssetManifest } from './contract'
import { FIXTURE_ID, FLAGS } from './flags'
import type { AssetProps } from './types'

export interface AssetEntry {
  id: string
  manifest: AssetManifest
  /** the generated glb, public/assets/<id>/model.glb */
  url: string
  stand: Stand | null
  /** a station asset's station (null for a kiosk) */
  station: SetId | null
  /** a station asset's anchor; a kiosk's comes from the cast placement */
  anchor: Anchor | null
  Driver: LazyExoticComponent<ComponentType<AssetProps>> | null
  fixture: boolean
}

const manifests = import.meta.glob<unknown>('./*/asset.json', { eager: true, import: 'default' })
const drivers = import.meta.glob<{ default: ComponentType<AssetProps> }>('./*/Driver.tsx')
const fixtureManifest = import.meta.glob<unknown>('../../forge/fixture/asset.json', { eager: true, import: 'default' })

const urlOf = (id: string) => `${import.meta.env.BASE_URL}assets/${id}/model.glb`
const warn = (dir: string, why: string) => console.warn(`[factory] src/assets/${dir}/asset.json ignored: ${why}`)

function discover(): AssetEntry[] {
  const out: AssetEntry[] = []
  const stationTaken = new Map<SetId, string>()
  for (const path of Object.keys(manifests).sort()) {
    const dir = path.split('/')[1]
    const parsed = parseManifest(manifests[path], dir)
    if (!parsed.ok) { warn(dir, parsed.why.join('; ')); continue }
    const m = parsed.manifest
    const stand = standOf(m.id)
    if (!stand?.registry || stand.id !== m.id) { warn(dir, `"${m.id}" is not an Atlas registry id (components/<id>.yaml)`); continue }
    if (m.placement === 'station' && !stand.station) { warn(dir, `placement "station", but the Atlas gives ${m.id} no station (it stands near ${stand.near})`); continue }
    if (m.placement === 'kiosk' && stand.station) { warn(dir, `placement "kiosk", but the Atlas says ${m.id} is the ${stand.station} station`); continue }
    const station = m.placement === 'station' ? stand.station : null
    if (station) {
      const other = stationTaken.get(station)
      if (other) { warn(dir, `the ${station} station already has a body (${other})`); continue }
      stationTaken.set(station, m.id)
    }
    const drv = drivers[`./${dir}/Driver.tsx`]
    out.push({
      id: m.id, manifest: m, url: urlOf(m.id), stand, station,
      anchor: station ? STATION_BODY[station] : null,
      Driver: drv ? lazy(drv) : null,
      fixture: false,
    })
  }
  // the pipeline's test crate: a kiosk for a fake id, only with ?fixture (dev or forge)
  if (FLAGS.fixture) {
    const raw = Object.values(fixtureManifest)[0]
    const parsed = parseManifest(raw, FIXTURE_ID)
    if (parsed.ok) out.push({ id: FIXTURE_ID, manifest: parsed.manifest, url: urlOf(FIXTURE_ID), stand: null, station: null, anchor: { at: FIXTURE_SLOT, rotY: 0 }, Driver: null, fixture: true })
    else console.warn(`[factory] forge/fixture/asset.json ignored: ${parsed.why.join('; ')}`)
  }
  return out
}

export const ASSETS: AssetEntry[] = discover()
const byId = new Map(ASSETS.map((a) => [a.id, a]))

/** The asset for any id a waybill or a link uses (a registry id, an alias, an ext: id), if one is on the floor. */
export function assetFor(id: string): AssetEntry | undefined {
  return byId.get(id) ?? byId.get(standOf(id)?.id ?? '')
}
