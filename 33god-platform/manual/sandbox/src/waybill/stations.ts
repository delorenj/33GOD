// Where each real component stands on the Factory floor.
// 1. The Atlas registry is the only table: every component's `factory:` block (station or near, plus aliases) and
//    the `factory_extras` in components.yaml are rendered into cast.generated.json by atlas.py. Nothing is kept here.
// 2. A component with a `station` IS that station. Every other component gets a KIOSK: a deterministic slot in an annex
//    row beside the station it is `near`, labelled with its REAL id. Adding a component never needs 3D work.
// 3. Keyed families stand by rule (resolve.ts): every Hermes desk `hermes-desk:<profile>` gets its own kiosk by the
//    crew hall; every tenant `tenant:<slug>` stands at the one tenant annex.
// 4. An id the cast does not know (a vendor CLI nobody listed, a new consumer name) still gets a kiosk, by kind.
import cast from '../cast.generated.json' with { type: 'json' }
import { VENDORS, type Vec3 } from '../content'
import { BAY_X, BAY_Z, CATALOGUER, CREW, READERS } from '../sim/layout'
import { setFor, type TourSet } from '../tour/sets'
import { familyOf } from './resolve'
import type { Component, Waybill } from './types'

// atlas.py reads this union to validate `station:` / `near:`: keep it one literal type.
export type SetId =
  | 'bays' | 'courier' | 'dock' | 'labeldesk' | 'belt' | 'archive' | 'rules' | 'control' | 'cataloguer' | 'clock' | 'crew'
  | 'entrance' | 'voxxy' | 'library' | 'staffing' | 'soundwing'

interface CastComponent { name: string; summary: string; domain: string; first_party: boolean; station: SetId | null; near: SetId | null; aliases: string[] }
interface CastExtra { name: string; station: SetId | null; near: SetId | null }
interface Cast {
  format: string; version: number; digest: string
  components: Record<string, CastComponent>
  aliases: Record<string, string>
  extras: Record<string, CastExtra>
}
const CAST = cast as unknown as Cast
if (CAST.format !== '33god.factory-cast' || CAST.version !== 1) throw new Error(`cast.generated.json: unknown format ${CAST.format} v${CAST.version}; run: python3 33god-platform/scripts/atlas.py render`)

export const CAST_DIGEST = CAST.digest

/** Where a component stands: its station, or the station its kiosk stands beside. `id` is the canonical id (a registry id,
 *  an extra, or a desk family member); `key` is the desk profile or tenant slug of a family member. */
export interface Stand { id: string; name: string; registry: boolean; station: SetId | null; near: SetId | null; key?: string }

const standCache = new Map<string, Stand | null>()
/** Resolve any id a waybill or an older table uses: a registry id, an alias, an `ext:` id, a registry extra, or a keyed
 *  family member (`hermes-desk:<profile>`, `tenant:<slug>`). */
export function standOf(id: string): Stand | null {
  if (standCache.has(id)) return standCache.get(id)!
  const direct = (k: string): Stand | null => {
    const c = CAST.components[k] ?? CAST.components[CAST.aliases[k]]
    if (c) { const rid = CAST.components[k] ? k : CAST.aliases[k]; return { id: rid, name: c.name, registry: true, station: c.station, near: c.near } }
    const eid = CAST.extras[k] ? k : CAST.extras[CAST.aliases[k]] ? CAST.aliases[k] : null
    const e = eid ? CAST.extras[eid] : null
    return e && eid ? { id: eid, name: e.name, registry: false, station: e.station, near: e.near } : null
  }
  const family = (k: string): Stand | null => {
    const f = familyOf(k)
    if (!f) return null
    if (f.kind === 'tenant') { const annex = f.annex ? direct(f.annex) : null; return annex ? { ...annex, key: f.key } : null }
    return { id: k, name: f.name, registry: false, station: null, near: (f.near as SetId | null) ?? null, key: f.key }
  }
  const s = direct(id) ?? (id.startsWith('ext:') ? direct(id.slice(4)) : direct(`ext:${id}`)) ?? family(id)
  standCache.set(id, s)
  return s
}

/** Id -> station / set, for every registry id, alias and extra the cast names. */
export const STATION_OF: Record<string, SetId> = {}
/** Id -> the station its kiosk stands beside, for every id that has no station of its own. */
export const NEAR: Record<string, SetId> = {}
for (const id of [...Object.keys(CAST.components), ...Object.keys(CAST.aliases), ...Object.keys(CAST.extras)]) {
  const s = standOf(id)
  if (s?.station) STATION_OF[id] = s.station
  else if (s?.near) NEAR[id] = s.near
}

/** Where a kiosk stands when the cast does not know the component at all: by the kind of thing it is. */
const NEAR_BY_KIND: Record<string, SetId> = {
  cli: 'bays', device: 'bays', external: 'bays', bus: 'belt', store: 'archive', memory: 'library', model: 'staffing', 'handler-host': 'dock',
}

/** Annex rows: where kiosks line up beside a station, on open floor (src/sim/layout.ts and src/world/Props.tsx checked by tools/cast/selfcheck.ts). */
export const ANNEX: Partial<Record<SetId, { start: Vec3; step: Vec3; row: Vec3; per: number }>> = {
  dock: { start: [-13.4, 0, -3.0], step: [1.55, 0, 0], row: [0, 0, -1.5], per: 6 },
  bays: { start: [-22.6, 0, 9.8], step: [0, 0, 1.5], row: [1.8, 0, 0], per: 4 },
  control: { start: [-1.2, 0, 10.6], step: [1.7, 0, 0], row: [0, 0, 1.6], per: 3 },
  belt: { start: [-1.9, 0, 5.7], step: [1.6, 0, 0.15], row: [0, 0, 1.5], per: 3 },
  archive: { start: [11.6, 0, 3.4], step: [0, 0, 1.55], row: [1.6, 0, 0], per: 5 },
  library: { start: [6.4, 0, 12.2], step: [0, 0, 1.45], row: [-1.6, 0, 0], per: 5 },
  staffing: { start: [12.4, 0, -1.9], step: [-1.55, 0, 0], row: [0, 0, 1.4], per: 3 },
  cataloguer: { start: [6.3, 0, 0.7], step: [0, 0, -1.45], row: [1.5, 0, 0], per: 2 },
  crew: { start: [4.2, 0, -11.6], step: [1.55, 0, 0], row: [0, 0, -1.4], per: 6 },
  clock: { start: [-3.6, 0, -10.2], step: [-1.55, 0, 0], row: [0, 0, -1.4], per: 4 },
  soundwing: { start: [17.2, 0, 2.6], step: [1.6, 0, 0], row: [0, 0, 1.5], per: 4 },
  rules: { start: [-17.6, 0, -9.0], step: [1.5, 0, 0], row: [0, 0, -1.4], per: 6 },
  entrance: { start: [-11.0, 0, 10.4], step: [1.5, 0, 0], row: [0, 0, 1.5], per: 3 },
}

export interface Kiosk { id: string; name: string; at: Vec3; near: SetId; /** a registry component (not a vendor extra or an unknown id) */ registry?: boolean }
export interface Placement {
  /** component id -> station/set id, or 'kiosk:<component id>' */
  setOf: Record<string, string>
  kiosks: Kiosk[]
  kioskById: Record<string, Kiosk>
  bay: number
}

export function bayFor(cli: string, surface: string): number {
  const s = `${cli} ${surface}`.toLowerCase()
  const i = VENDORS.findIndex((v) => s.includes(v.name.toLowerCase()))
  return i >= 0 ? i : 0
}

export function stationOf(c: Component | string): SetId | null {
  return standOf(typeof c === 'string' ? c : c.id)?.station ?? null
}

/** Slot `i` of a station's annex. Rows run on past the end of the table, so a slot always exists. */
function slotAt(near: SetId, i: number): Vec3 {
  const a = ANNEX[near] ?? ANNEX.dock!
  const col = i % a.per
  const row = Math.floor(i / a.per)
  return [a.start[0] + a.step[0] * col + a.row[0] * row, 0, a.start[2] + a.step[2] * col + a.row[2] * row]
}

/** Every cast id that stands in a kiosk, in slot order: registry components (sorted), then extras (sorted), per station. */
const castSlots = (() => {
  const byNear: Partial<Record<SetId, string[]>> = {}
  const add = (id: string, near: SetId | null, station: SetId | null) => { if (!station && near) (byNear[near] ??= []).push(id) }
  for (const id of Object.keys(CAST.components).sort()) add(id, CAST.components[id].near, CAST.components[id].station)
  for (const id of Object.keys(CAST.extras).sort()) add(id, CAST.extras[id].near, CAST.extras[id].station)
  const slots = new Map<string, { near: SetId; index: number }>()
  const count: Partial<Record<SetId, number>> = {}
  for (const [near, ids] of Object.entries(byNear) as [SetId, string[]][]) {
    ids.forEach((id, index) => slots.set(id, { near, index }))
    count[near] = ids.length
  }
  return { slots, count }
})()

function kioskFor(id: string, name: string): Kiosk | null {
  const s = castSlots.slots.get(id)
  return s ? { id, name, at: slotAt(s.near, s.index), near: s.near, registry: !!CAST.components[id] } : null
}

let castPlaced: Placement | null = null
/** The permanent floor: every registry component that has no station gets its kiosk, in the same slot every time.
 *  Vendor extras get theirs too (registry: false). The ambient floor stands asset-bearing kiosks from this. */
export function castPlacement(): Placement {
  if (castPlaced) return castPlaced
  const kiosks: Kiosk[] = []
  const setOf: Record<string, string> = {}
  for (const id of [...Object.keys(CAST.components), ...Object.keys(CAST.extras)].sort()) {
    const s = standOf(id)!
    if (s.station) { setOf[id] = s.station; continue }
    const k = kioskFor(id, s.name)
    if (k) { kiosks.push(k); setOf[id] = `kiosk:${id}` }
  }
  for (const [alias, id] of Object.entries(CAST.aliases)) setOf[alias] = setOf[id]
  const kioskById: Record<string, Kiosk> = Object.fromEntries(kiosks.map((k) => [k.id, k]))
  for (const [alias, id] of Object.entries(CAST.aliases)) if (kioskById[id]) kioskById[alias] = kioskById[id]
  castPlaced = { setOf, kiosks, kioskById, bay: 0 }
  return castPlaced
}

/** Pure and deterministic: the same waybill always places the same kiosks in the same slots.
 *  A cast component keeps its permanent slot (the one castPlacement() uses); only ids the cast does not know
 *  are appended after the cast's slots in the annex they belong to. */
export function place(wb: Pick<Waybill, 'components' | 'origin'>): Placement {
  const setOf: Record<string, string> = {}
  const unknown: Record<string, string[]> = {}
  const kiosks: Kiosk[] = []
  const seen = new Set<string>()
  for (const id of Object.keys(wb.components).sort()) {
    const s = standOf(id)
    if (s?.station) { setOf[id] = s.station; continue }
    // a tenant shares the annex's kiosk, so the kiosk keeps the annex's own name, not the first tenant's
    const k = s && kioskFor(s.id, (s.key && s.id !== id ? s.name : null) ?? wb.components[s.id]?.name ?? wb.components[id]?.name ?? s.name)
    if (k) {
      setOf[id] = `kiosk:${k.id}`
      if (!seen.has(k.id)) { seen.add(k.id); kiosks.push(k) }
      continue
    }
    // a desk family member has no permanent slot but knows its station; anything else stands by kind
    const near = s?.near ?? NEAR_BY_KIND[wb.components[id].kind] ?? 'dock'
    ;(unknown[near] ??= []).push(id)
    setOf[id] = `kiosk:${id}`
  }
  for (const [near, ids] of Object.entries(unknown) as [SetId, string[]][]) {
    ids.forEach((id, i) => kiosks.push({ id, name: wb.components[id]?.name ?? id, at: slotAt(near, (castSlots.count[near] ?? 0) + i), near, registry: false }))
  }
  const kioskById: Record<string, Kiosk> = Object.fromEntries(kiosks.map((k) => [k.id, k]))
  // a waybill's alias (hermes-gateway) answers to the same kiosk as the registry id (hermes-gw)
  for (const [id, set] of Object.entries(setOf)) if (set.startsWith('kiosk:') && !kioskById[id]) kioskById[id] = kioskById[set.slice(6)]
  return { setOf, kiosks, kioskById, bay: bayFor(wb.origin.cli, wb.origin.surface) }
}

/** The point on a station where the hero object rests and fan-out copies land. */
export function spotOf(set: string, pl: Placement): Vec3 {
  if (set.startsWith('kiosk:')) {
    const k = pl.kioskById[set.slice(6)]
    return k ? [k.at[0], 1.75, k.at[2]] : [0, 1.5, 6]
  }
  switch (set) {
    case 'bays': return [BAY_X + 1.5, 1.35, BAY_Z[pl.bay] ?? 0]
    case 'courier': return [-16.2, 1.25, 1.4]
    case 'dock': return [-12.1, 1.55, 0.9]
    case 'labeldesk': return [-9.5, 1.45, 3.55]
    case 'belt': return [0, 1.25, 0.82]
    case 'archive': return [READERS.archive[0] - 1.5, 1.5, READERS.archive[2] + 0.7]
    case 'control': return [READERS.control[0], READERS.control[1] + 0.3, READERS.control[2]]
    case 'cataloguer': return [CATALOGUER[0], 1.3, CATALOGUER[2] + 0.6]
    case 'rules': return [READERS.rules[0], 1.6, READERS.rules[2] + 0.8]
    case 'clock': return [-5.4, 1.4, -5.2]
    case 'crew': return [CREW.tray[0], 1.7, CREW.tray[2]]
    case 'library': return [11.2, 1.5, 11.7]
    case 'staffing': return [13, 1.55, -5.5]
    case 'entrance': return [-14.5, 1.4, 11.2]
    case 'voxxy': return [17.4, 1.4, -9.4]
    case 'soundwing': return [20.6, 1.4, -4]
  }
  const a = setFor(set).anchor
  return [a[0], 1.4, a[2]]
}

const SET_NAMES: Record<SetId, string> = {
  bays: 'the vendor bays', courier: 'the courier', dock: 'the receiving dock', labeldesk: 'the label desk', belt: 'the belt',
  archive: 'the archive', rules: 'the rules cabinet', control: 'the control room', cataloguer: 'the cataloguer', clock: 'the clock',
  crew: 'the crew hall', entrance: 'the entrance', voxxy: 'the voice booth', library: 'the lessons library', staffing: 'the staffing desk', soundwing: 'the sound wing',
}

/** The warehouse word for where a component stands (shown small, beside its real id). */
export function placeName(set: string, pl: Placement): string {
  if (set.startsWith('kiosk:')) {
    const k = pl.kioskById[set.slice(6)]
    return k ? `a kiosk by ${SET_NAMES[k.near]}` : 'a kiosk'
  }
  return SET_NAMES[set as SetId] ?? set
}

/** A camera stop, in the same shape the tour uses (TourSet), so the same fly() logic drives it. */
export function viewFor(set: string, pl: Placement): TourSet {
  if (set.startsWith('kiosk:')) {
    const k = pl.kioskById[set.slice(6)]
    const a: Vec3 = k ? k.at : [0, 0, 6]
    return { name: k?.name ?? set, anchor: a, portraitK: 1.5, view: { pos: [a[0] + 3.4, 3.9, a[2] + 6.6], target: [a[0] - 0.2, 1.1, a[2] - 0.4] } }
  }
  if (set === 'bays') {
    const z = BAY_Z[pl.bay] ?? 0
    return { name: 'Vendor bays', anchor: [BAY_X + 2.2, 0, z], portraitK: 1.5, view: { pos: [BAY_X + 13.2, 5.8, z + 11.6], target: [BAY_X + 3.9, 1.3, z + 3.4] } } // aimed a little nearer the camera: the bottom panel covers the lower screen
  }
  // the belt in waybill mode frames the fan-out: the loading point and the readers in front of it
  if (set === 'belt') return { name: 'The belt', anchor: [0, 0, 1], portraitK: 1.35, view: { pos: [6.5, 9.5, 23.5], target: [0.4, 2.6, 4.6] } }
  // the staffing desk from the south: the tour's view looks west across the Crew Hall block; this one looks at the desk itself
  if (set === 'staffing') return { name: 'The staffing desk', anchor: [11.4, 0, -4.6], portraitK: 1.35, view: { pos: [15.6, 3.7, 3.1], target: [12.6, 1.5, -5.4] } }
  if (set === 'overview') return { name: 'The floor', anchor: [0, 0, 0], portraitK: 1, view: { pos: [24, 21, 33], target: [-3, 2, 1] } }
  return setFor(set)
}

/** Fan-out view: wide enough to see the belt and every reader a copy flies to. */
export function fanoutView(targets: Vec3[]): { pos: Vec3; target: Vec3 } {
  const pts: Vec3[] = [[0, 1.2, 0.8], ...targets]
  const xs = pts.map((p) => p[0]), zs = pts.map((p) => p[2])
  const cx = (Math.min(...xs) + Math.max(...xs)) / 2
  const cz = (Math.min(...zs) + Math.max(...zs)) / 2
  const span = Math.max(Math.max(...xs) - Math.min(...xs), (Math.max(...zs) - Math.min(...zs)) * 1.3, 10)
  const d = span * 1.05 + 6
  return { pos: [cx + d * 0.3, d * 0.55 + 3, cz + d * 0.92], target: [cx, 1.6, cz] }
}

/** Frame two or more spots (the briefing card's dock and bay) from the south-east, close enough to read them both. */
export function pairView(points: Vec3[]): { pos: Vec3; target: Vec3 } {
  const xs = points.map((p) => p[0]), zs = points.map((p) => p[2])
  const cx = (Math.min(...xs) + Math.max(...xs)) / 2
  const cz = (Math.min(...zs) + Math.max(...zs)) / 2
  const span = Math.max(Math.max(...xs) - Math.min(...xs), (Math.max(...zs) - Math.min(...zs)) * 1.3, 6)
  const d = span * 1.2 + 7
  // the bottom panel covers the lower part of the screen: aim a little nearer the camera so the action sits higher
  const nudge = 3.2
  return { pos: [cx + d * 0.15, d * 0.45 + 2.2, cz + d * 0.95 + nudge], target: [cx, 1.3, cz + nudge] }
}
