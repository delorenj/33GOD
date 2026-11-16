// Where each real component stands on the Factory floor during a waybill.
// 1. A registry-id table maps known components to a station or a tour set (the canon cast table).
// 2. Every other component gets an auto-placed KIOSK: a deterministic slot in an annex row near the
//    station it is most related to, labelled with its REAL id. Adding a component never needs 3D work.
import { VENDORS, type Vec3 } from '../content'
import { BAY_X, BAY_Z, CATALOGUER, CREW, READERS } from '../sim/layout'
import { setFor, type TourSet } from '../tour/sets'
import type { Component, Waybill } from './types'

export type SetId =
  | 'bays' | 'courier' | 'dock' | 'labeldesk' | 'belt' | 'archive' | 'rules' | 'control' | 'cataloguer' | 'clock' | 'crew'
  | 'entrance' | 'voxxy' | 'library' | 'staffing' | 'soundwing'

/** Registry id -> station / set. Canon: manual/world/warehouse-bible.md section 4.1. */
export const STATION_OF: Record<string, SetId> = {
  'ext:claude-code': 'bays', 'ext:codex-cli': 'bays', 'ext:codex-desktop': 'bays', 'ext:codex-exec': 'bays',
  'claude-code': 'bays', 'codex': 'bays', 'codex-desktop': 'bays', 'ext:kimi': 'bays', 'ext:gemini': 'bays', 'ext:copilot': 'bays', 'ext:opencode': 'bays',
  'bb-hook': 'courier',
  'hook-hub': 'dock',
  'event-contract': 'labeldesk', 'naming-contract': 'labeldesk', 'holyfields': 'labeldesk',
  // the dock's poster: a publish passes the label desk on its way to the belt
  'agent-hooks': 'labeldesk',
  'bb-nats': 'belt', 'bloodbank': 'belt', 'nats': 'belt',
  'candystore': 'archive', 'candystore-daprd': 'archive',
  'holocene': 'control', 'holocene-api': 'control', 'team-dashboard': 'control', 'inbox-watcher': 'control',
  'enricher': 'cataloguer', 'enricher-daprd': 'cataloguer', 'turn-enricher': 'cataloguer',
  'n8n': 'rules', 'n8n-nodes-bloodbank': 'rules',
  'candybar': 'clock',
  'hermes-gw': 'crew', 'hermes-gateway': 'crew', 'hermes-bloodbank-plugin': 'crew',
  'hindsight': 'library',
  'aai-gateway': 'staffing', 'aai-llm-observability': 'staffing', 'automaticai-gateway': 'staffing',
  'agent-pad': 'entrance',
  'vox': 'voxxy', 'voxxy': 'voxxy',
  'wax': 'soundwing', 'heyma': 'soundwing', 'waxd': 'soundwing',
}

/** Components with no station of their own: which station their kiosk stands beside. */
const NEAR: Record<string, SetId> = {
  'asm': 'dock', 'redis': 'dock', 'skillex': 'dock', 'hook-hub-receipts': 'dock', 'crank': 'dock', 'crank-engine': 'dock',
  'ext:nanoleaf': 'bays', 'ext:orca': 'bays', 'ext:stream-deck': 'bays', 'ext:zellij': 'bays', 'zellij-notify': 'bays', 'asm-orcapaint': 'bays', 'asm-tabpaint': 'bays',
  'ntfy-router': 'control', 'deckard': 'control', 'ext:ntfy': 'control', 'monitoring': 'control',
  'artifact-sidecar': 'archive', 'vault-projector': 'archive', 'bb-dapr': 'archive', 'curator': 'archive',
  'cost-bridge': 'staffing', 'jev': 'staffing', 'ext:jev': 'staffing', 'jev-clairic-exporter': 'staffing',
  'agents-registry': 'crew', 'flume': 'crew', 'pjangler': 'crew',
  'transcribe': 'soundwing', 'vinyl': 'soundwing',
}
const NEAR_BY_KIND: Record<string, SetId> = {
  cli: 'bays', device: 'bays', external: 'bays', bus: 'belt', store: 'archive', memory: 'library', model: 'staffing', 'handler-host': 'dock',
}

/** Annex rows: where kiosks line up beside a station, on open floor (checked against the props). */
const ANNEX: Partial<Record<SetId, { start: Vec3; step: Vec3; row: Vec3; per: number }>> = {
  dock: { start: [-13.4, 0, -3.0], step: [1.55, 0, 0], row: [0, 0, -1.5], per: 5 },
  bays: { start: [-22.6, 0, 9.8], step: [0, 0, 1.7], row: [1.8, 0, 0], per: 3 },
  control: { start: [-0.6, 0, 9.8], step: [1.7, 0, 0.2], row: [0, 0, 1.7], per: 3 },
  belt: { start: [-1.9, 0, 5.7], step: [1.6, 0, 0.15], row: [0, 0, 1.5], per: 3 },
  archive: { start: [11.6, 0, 3.4], step: [0, 0, 1.55], row: [1.6, 0, 0], per: 4 },
  library: { start: [6.4, 0, 12.2], step: [0, 0, 1.45], row: [-1.6, 0, 0], per: 3 },
  staffing: { start: [12.4, 0, -1.9], step: [-1.55, 0, 0], row: [0, 0, 1.4], per: 3 },
  cataloguer: { start: [6.3, 0, 0.7], step: [0, 0, -1.45], row: [1.5, 0, 0], per: 2 },
  crew: { start: [4.2, 0, -11.6], step: [1.55, 0, 0], row: [0, 0, -1.4], per: 4 },
  clock: { start: [-3.6, 0, -10.2], step: [-1.55, 0, 0], row: [0, 0, -1.4], per: 4 },
  soundwing: { start: [17.2, 0, 2.6], step: [1.6, 0, 0], row: [0, 0, 1.5], per: 4 },
}

export interface Kiosk { id: string; name: string; at: Vec3; near: SetId }
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
  const id = typeof c === 'string' ? c : c.id
  return STATION_OF[id] ?? STATION_OF[id.replace(/^ext:/, '')] ?? null
}

/** Pure and deterministic: the same waybill always places the same kiosks in the same slots. */
export function place(wb: Pick<Waybill, 'components' | 'origin'>): Placement {
  const setOf: Record<string, string> = {}
  const byNear: Record<string, string[]> = {}
  for (const id of Object.keys(wb.components).sort()) {
    const st = stationOf(id)
    if (st) { setOf[id] = st; continue }
    const near = NEAR[id] ?? NEAR[id.replace(/^ext:/, '')] ?? NEAR_BY_KIND[wb.components[id].kind] ?? 'dock'
    ;(byNear[near] ??= []).push(id)
    setOf[id] = `kiosk:${id}`
  }
  const kiosks: Kiosk[] = []
  for (const [near, ids] of Object.entries(byNear)) {
    const a = ANNEX[near as SetId] ?? ANNEX.dock!
    ids.forEach((id, i) => {
      const col = i % a.per
      const row = Math.floor(i / a.per)
      const at: Vec3 = [a.start[0] + a.step[0] * col + a.row[0] * row, 0, a.start[2] + a.step[2] * col + a.row[2] * row]
      kiosks.push({ id, name: wb.components[id]?.name ?? id, at, near: near as SetId })
    })
  }
  return { setOf, kiosks, kioskById: Object.fromEntries(kiosks.map((k) => [k.id, k])), bay: bayFor(wb.origin.cli, wb.origin.surface) }
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
