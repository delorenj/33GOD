// The Factory asset contract (forge/CONTRACT.md) as code: the manifest's shape and its checks. Pure, no imports,
// so the browser runtime (src/assets) and the node build (tools/assets/build.mjs) share one reading of it.

/** Primitive props in src/world/Props.tsx a station asset may hide (`replaces`). */
export const PROP_NAMES = ['Bays', 'Dock', 'LabelDesk', 'Archive', 'RulesCabinet', 'ControlRoom', 'Cataloguer', 'Clock', 'ClockCrew', 'CrewHall', 'ClipWires'] as const
export type PropName = (typeof PROP_NAMES)[number]

/** The station / set ids of src/waybill/stations.ts (SetId). */
export const SET_IDS = ['bays', 'courier', 'dock', 'labeldesk', 'belt', 'archive', 'rules', 'control', 'cataloguer', 'clock', 'crew', 'entrance', 'voxxy', 'library', 'staffing', 'soundwing'] as const
export type SetIdName = (typeof SET_IDS)[number]

/** The painted floor zone each set stands in (src/domains.ts): the colour a component's asset carries. */
export const SET_DOMAIN: Record<SetIdName, string> = {
  bays: 'agents', courier: 'bloodbank', dock: 'bloodbank', labeldesk: 'bloodbank', belt: 'bloodbank',
  archive: 'memory', cataloguer: 'memory', library: 'memory', rules: 'triggers', clock: 'triggers',
  control: 'holocene', entrance: 'holocene', crew: 'workers', staffing: 'workers', voxxy: 'voice', soundwing: 'voice',
}

export type VisitKind = 'parcel' | 'post' | 'env' | 'summary'
export const VISIT_KINDS: VisitKind[] = ['parcel', 'post', 'env', 'summary']
export type Handles = VisitKind | 'any'
export type ClipRole = 'idle' | 'accept' | 'work' | 'emit'
export const CLIP_ROLES: ClipRole[] = ['idle', 'accept', 'work', 'emit']
/** Clip length rules in seconds (contract section 4). */
export const CLIP_SECONDS: Record<ClipRole, [number, number]> = { idle: [2, 6], accept: [0.6, 1.5], work: [0.8, 3], emit: [0.5, 1.2] }
export const MAX_TRIS = 15000
export const MAX_GLB_KB = 600
/** A kiosk slot, metres x by z. */
export const KIOSK_SLOT: [number, number] = [1.4, 1.3]

export interface AssetManifest {
  format: '33god.factory-asset'
  version: 1
  id: string
  title: string
  placement: 'station' | 'kiosk'
  replaces: PropName[]
  footprint: [number, number]
  height: number
  scale: number
  rotationY: number
  handles: Handles[]
  clips: Record<ClipRole, string>
  sockets: { in: string; hold: string; out: string }
  budget: { tris: number; glbKB: number }
  forge?: { run: string; rounds: number; score: number }
}

export type Parsed = { ok: true; manifest: AssetManifest } | { ok: false; why: string[] }

const isObj = (v: unknown): v is Record<string, unknown> => typeof v === 'object' && v !== null && !Array.isArray(v)
const num = (v: unknown) => typeof v === 'number' && Number.isFinite(v)
const str = (v: unknown) => typeof v === 'string' && v.length > 0

/** Read an asset.json. `dirId` is the directory name it was found in: the id must match it exactly. */
export function parseManifest(raw: unknown, dirId: string): Parsed {
  const why: string[] = []
  if (!isObj(raw)) return { ok: false, why: ['not a JSON object'] }
  const r = raw
  if (r.format !== '33god.factory-asset') why.push(`format must be "33god.factory-asset" (got ${JSON.stringify(r.format)})`)
  if (r.version !== 1) why.push(`version must be 1 (got ${JSON.stringify(r.version)})`)
  if (r.id !== dirId) why.push(`id ${JSON.stringify(r.id)} must equal its directory name "${dirId}"`)
  if (!str(r.title)) why.push('title is required')
  if (r.placement !== 'station' && r.placement !== 'kiosk') why.push('placement must be "station" or "kiosk"')
  const replaces = r.replaces ?? []
  if (!Array.isArray(replaces) || !replaces.every((p) => (PROP_NAMES as readonly string[]).includes(p as string))) why.push(`replaces must list props from Props.tsx: ${PROP_NAMES.join(', ')}`)
  else if (r.placement === 'kiosk' && replaces.length) why.push('a kiosk asset replaces nothing')
  const fp = r.footprint
  if (!Array.isArray(fp) || fp.length !== 2 || !fp.every((n) => num(n) && (n as number) > 0)) why.push('footprint must be [x, z] metres > 0')
  if (!num(r.height) || (r.height as number) <= 0) why.push('height must be metres > 0')
  const scale = r.scale ?? 1
  if (!num(scale) || (scale as number) <= 0) why.push('scale must be > 0')
  const rotY = r.rotationY ?? 0
  if (!num(rotY)) why.push('rotationY must be a number (radians)')
  if (r.placement === 'kiosk' && Array.isArray(fp) && num(fp[0]) && num(fp[1]) && num(scale)) {
    const s = scale as number
    if ((fp[0] as number) * s > KIOSK_SLOT[0] + 1e-6 || (fp[1] as number) * s > KIOSK_SLOT[1] + 1e-6) why.push(`a kiosk footprint must fit the ${KIOSK_SLOT[0]} x ${KIOSK_SLOT[1]} slot`)
  }
  const handles = r.handles
  if (!Array.isArray(handles) || !handles.length || !handles.every((h) => h === 'any' || VISIT_KINDS.includes(h as VisitKind))) why.push('handles must list parcel / post / env / summary / any')
  const clips = r.clips
  if (!isObj(clips) || !CLIP_ROLES.every((k) => str(clips[k]))) why.push('clips must name idle, accept, work and emit')
  const sockets = r.sockets
  if (!isObj(sockets) || !['in', 'hold', 'out'].every((k) => str(sockets[k]))) why.push('sockets must name in, hold and out')
  const budget = r.budget
  if (!isObj(budget) || !num(budget.tris) || !num(budget.glbKB)) why.push('budget must give tris and glbKB')
  else {
    if ((budget.tris as number) > MAX_TRIS) why.push(`budget.tris is at most ${MAX_TRIS}`)
    if ((budget.glbKB as number) > MAX_GLB_KB) why.push(`budget.glbKB is at most ${MAX_GLB_KB}`)
  }
  if (r.forge !== undefined && !(isObj(r.forge) && str(r.forge.run) && num(r.forge.rounds) && num(r.forge.score))) why.push('forge, when present, must give run, rounds and score')
  if (why.length) return { ok: false, why }
  return {
    ok: true,
    manifest: {
      ...(r as unknown as AssetManifest),
      replaces: replaces as PropName[],
      scale: scale as number,
      rotationY: rotY as number,
    },
  }
}

/** Does this asset take this kind of visit? */
export const takes = (m: Pick<AssetManifest, 'handles'>, kind: VisitKind) => m.handles.includes('any') || m.handles.includes(kind)
