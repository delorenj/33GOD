// Visits: the traffic that passes through a component's asset. Three sources feed one bus:
// - the ambient sim (src/sim/sim.ts): an item reaching a station, addressed `station:<set>`;
// - waybill playback (src/waybill): the playhead reaching a stop at a component, `id:<registry id>` for a kiosk,
//   `station:<set>` for a component that is a station;
// - the forge hook (window.__factoryForge.visit), `id:<registry id>`.
// useVisits(id) merges what reaches one asset into a small queue its <AssetBody> (or its Driver) plays.
import { useEffect, useMemo } from 'react'
import type { Vec3 } from '../content'
import type { ItemLook } from '../world/Moving'
import type { Handles, VisitKind } from './contract'

export type { ItemLook }
export const MAX_WAITING = 4

export interface Visit {
  seq: number
  kind: VisitKind
  /** what arrives, drawn in the floor's own look */
  look: ItemLook
  /** what leaves from socket_out (the dock takes a parcel and sends a post-it) */
  out: ItemLook
  source: 'sim' | 'waybill' | 'forge'
  /** world point the item comes from (where the sim's flight ended), so the catch is continuous */
  from?: Vec3
  /** hand the result back to the sim's flow, from socket_out's world position; called with no point, the sim
   *  carries on from its own point at its own time (an overflowing queue, an unmounted body) */
  release?: (from?: Vec3) => void
  /** a word on what happened ('filed', 'rejected', 'duplicate', a stop title), for a Driver */
  tag?: string
  /** a waybill visit's stop id */
  stop?: string
}

export type VisitInput = Omit<Visit, 'seq' | 'look' | 'out'> & { look?: ItemLook; out?: ItemLook }

const LOOK_OF: Record<VisitKind, ItemLook> = { parcel: 'parcel', post: 'post', env: 'env', summary: 'summary' }
type Listener = (v: Visit) => void
const listeners = new Map<string, Set<Listener>>()
const takers = new Map<string, Handles[][]>()
let seq = 1

/** Send a visit to `id:<registry id>` or `station:<set>`. Returns false when no live asset listens. */
export function emitVisit(key: string, v: VisitInput): boolean {
  const ls = listeners.get(key)
  if (!ls?.size) return false
  const look = v.look ?? LOOK_OF[v.kind]
  const visit: Visit = { ...v, seq: seq++, look, out: v.out ?? look }
  // one release per visit, however many listeners there are
  if (v.release) {
    let done = false
    visit.release = (from) => { if (!done) { done = true; v.release!(from) } }
  }
  for (const l of ls) l(visit)
  return true
}

export function onVisit(key: string, fn: Listener): () => void {
  const set = listeners.get(key) ?? listeners.set(key, new Set()).get(key)!
  set.add(fn)
  return () => { set.delete(fn) }
}

/** A loaded station asset says it plays this station's traffic (the kinds in its `handles`). */
export function claimStation(station: string, handles: Handles[]): () => void {
  const list = takers.get(station) ?? takers.set(station, []).get(station)!
  list.push(handles)
  return () => { const i = list.indexOf(handles); if (i >= 0) list.splice(i, 1) }
}

/** Does a live asset at this station take this kind of item? The sim asks before it hands anything over. */
export function takerFor(station: string, kind: VisitKind): boolean {
  return !!takers.get(station)?.some((h) => h.includes('any') || h.includes(kind))
}

/** The visits waiting at one asset, oldest first. Mutable on purpose: the body reads it every frame. */
export interface VisitQueue {
  readonly id: string
  items: Visit[]
  take(): Visit | undefined
  /** drop everything waiting, handing each item back to the sim untouched */
  flush(): void
}

/** Every visit that reaches this asset: its own id, and its station's traffic when it is a station.
 *  `handles` filters by kind. At most MAX_WAITING wait; an overflowing visit is handed straight back. */
export function useVisits(id: string, opts: { station?: string | null; handles?: Handles[] } = {}): VisitQueue {
  const { station = null, handles } = opts
  const q = useMemo<VisitQueue>(() => {
    const queue: VisitQueue = {
      id,
      items: [],
      take: () => queue.items.shift(),
      flush: () => { const xs = queue.items.splice(0); for (const v of xs) v.release?.() },
    }
    return queue
  }, [id])
  const hkey = handles?.join(',') ?? 'any'
  useEffect(() => {
    const ok = (v: Visit) => !handles || handles.includes('any') || handles.includes(v.kind)
    const push = (v: Visit) => {
      if (!ok(v)) return v.release?.()
      if (q.items.length >= MAX_WAITING) return v.release?.()
      q.items.push(v)
    }
    const offs = [onVisit(`id:${id}`, push)]
    if (station) offs.push(onVisit(`station:${station}`, push))
    return () => { offs.forEach((f) => f()); q.flush() }
    // handles is compared by its joined key
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q, id, station, hkey])
  return q
}
