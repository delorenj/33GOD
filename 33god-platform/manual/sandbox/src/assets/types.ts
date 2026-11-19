import type { AnimationAction, Object3D } from 'three'
import type { GLTF } from 'three-stdlib'
import type { AssetManifest } from './contract'
import type { VisitQueue } from './visits'

/** What a src/assets/<id>/Driver.tsx receives (contract section 5): it may replace the generic Accept -> Work -> Emit sequence. */
export interface AssetProps {
  id: string
  manifest: AssetManifest
  gltf: GLTF
  /** this body's own copy of the scene (the glb is shared, its clone is not) */
  scene: Object3D
  actions: Record<string, AnimationAction | null>
  sockets: { in: Object3D; hold: Object3D; out: Object3D }
  visits: VisitQueue
  /** the waybill playhead: u (0..1 through the current stop) and t (ms on the recording's axis) */
  playhead: { u: number; t: number }
}
