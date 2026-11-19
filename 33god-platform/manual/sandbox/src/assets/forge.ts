// The forge's browser hook (only with ?forge in the URL): window.__factoryForge drives one asset for
// deterministic screenshots. ready resolves once the framed asset's glb is loaded and a frame is drawn.
import type { ClipRole, VisitKind } from './contract'
import { FLAGS } from './flags'
import { assetFor } from './registry'
import { emitVisit } from './visits'

export interface BodyInfo { clips: string[]; sockets: string[]; tris: number }
/** What a mounted <AssetBody> lets the forge do to it. */
export interface BodyHandle {
  info: BodyInfo
  pose(clip: ClipRole, t: number): void
  release(): void
}

const bodies = new Map<string, Set<BodyHandle>>()
export function registerBody(id: string, h: BodyHandle): () => void {
  const set = bodies.get(id) ?? bodies.set(id, new Set()).get(id)!
  set.add(h)
  return () => { set.delete(h) }
}

/** ?at=<id>&forge: the asset alone on the turntable, when <id> names an asset on this floor. */
export const STAGE_ID: string | null = FLAGS.forge && FLAGS.at ? (assetFor(FLAGS.at)?.id ?? null) : null

let settle: { resolve: () => void; reject: (e: Error) => void } | null = null
const ready = new Promise<void>((resolve, reject) => { settle = { resolve, reject } })
ready.catch(() => {}) // a caller that never awaits it should not see an unhandled rejection

/** An asset's glb is in and a frame has been drawn with it (or, with no framed asset, the first frame of the floor). */
export function markReady(id: string | null) {
  if (!settle) return
  if (STAGE_ID ? id === STAGE_ID : id === null) { settle.resolve(); settle = null }
}
export function markFailed(id: string, why: string) {
  if (settle && id === STAGE_ID) { settle.reject(new Error(`asset ${id}: ${why}`)); settle = null }
}

const POSES: ClipRole[] = ['idle', 'accept', 'work', 'emit']

export interface FactoryForge {
  ready: Promise<void>
  visit(id: string, kind?: VisitKind): void
  pose(id: string, clip: ClipRole, t: number): void
  release(): void
  info(id: string): BodyInfo | null
}

export function installForge() {
  if (!FLAGS.forge) return
  if (FLAGS.at && !STAGE_ID) markFailedEarly(`no asset for "${FLAGS.at}" on this floor (src/assets/<id>/asset.json, or ?fixture for the test crate)`)
  const handles = (id: string) => [...(bodies.get(assetFor(id)?.id ?? id) ?? [])]
  const api: FactoryForge = {
    ready,
    visit(id, kind) {
      const a = assetFor(id)
      const rid = a?.id ?? id
      const k: VisitKind = kind ?? (a?.manifest.handles.find((h) => h !== 'any') as VisitKind | undefined) ?? 'post'
      if (!emitVisit(`id:${rid}`, { kind: k, source: 'forge', tag: 'forge visit' })) console.warn(`[factory] forge visit: no live asset for "${id}"`)
    },
    pose(id, clip, t) {
      if (!POSES.includes(clip)) throw new Error(`pose: clip must be one of ${POSES.join(', ')}`)
      for (const h of handles(id)) h.pose(clip, t)
    },
    release() { for (const set of bodies.values()) for (const h of set) h.release() },
    info(id) { return handles(id)[0]?.info ?? null },
  }
  ;(window as unknown as { __factoryForge: FactoryForge }).__factoryForge = api
}

function markFailedEarly(why: string) {
  if (settle) { settle.reject(new Error(why)); settle = null }
  console.warn(`[factory] forge: ${why}`)
}
