import { create } from 'zustand'
import type { ReactNode } from 'react'
import type { PropName } from '../assets/contract'

// Primitive props a loaded asset stands in for (asset.json `replaces`). Counted, so two owners can hide the
// same prop and it comes back only when both let go. A hidden prop keeps running (its hooks and state stay),
// so it is back the moment an asset unmounts or fails.
interface Hidden { count: Partial<Record<PropName, number>> }
export const useHidden = create<Hidden>(() => ({ count: {} }))

/** Hide these props until the returned function is called. */
export function hideProps(names: readonly PropName[]): () => void {
  if (!names.length) return () => {}
  const bump = (by: number) => useHidden.setState((s) => {
    const count = { ...s.count }
    for (const n of names) count[n] = Math.max(0, (count[n] ?? 0) + by)
    return { count }
  })
  bump(1)
  let done = false
  return () => { if (!done) { done = true; bump(-1) } }
}

// Which assets are standing on the floor right now (glb loaded, clips and sockets in), so a generic stand-in
// (the waybill's kiosk box) is drawn only until the real body is there.
export const useLive = create<{ ids: Record<string, number> }>(() => ({ ids: {} }))
export function markLive(id: string): () => void {
  const bump = (by: number) => useLive.setState((s) => ({ ids: { ...s.ids, [id]: Math.max(0, (s.ids[id] ?? 0) + by) } }))
  bump(1)
  let done = false
  return () => { if (!done) { done = true; bump(-1) } }
}

/** One primitive prop, hidden by name while an asset replaces it. */
export function Hideable({ name, children }: { name: PropName; children: ReactNode }) {
  const hidden = useHidden((s) => (s.count[name] ?? 0) > 0)
  return <group name={`prop:${name}`} visible={!hidden}>{children}</group>
}
