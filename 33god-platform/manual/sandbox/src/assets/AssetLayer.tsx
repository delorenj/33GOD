// Every discovered asset, standing on the ambient floor: station assets at their station's anchor (hiding the
// primitive they replace), kiosk assets in their permanent annex slot from the Atlas cast. During waybill playback
// a kiosk the waybill places is drawn by WaybillWorld instead, so it is never on the floor twice.
import { useFrame, useThree } from '@react-three/fiber'
import { Suspense, lazy, useMemo, useRef } from 'react'
import * as THREE from 'three'
import type { Vec3 } from '../content'
import { useWorld } from '../sim/store'
import { useWb } from '../waybill/state'
import { castPlacement } from '../waybill/stations'
import { Tag } from '../world/Tag'
import { STAGE_ID, markReady } from './forge'
import { FLAGS } from './flags'
import { ASSETS, assetFor, type AssetEntry } from './registry'

export const AssetBody = lazy(() => import('./AssetBody'))

/** A kiosk asset's floor point: its permanent annex slot (the fixture has its own test slot). */
export function kioskAt(a: AssetEntry): Vec3 | null {
  if (a.anchor) return a.anchor.at
  return castPlacement().kioskById[a.id]?.at ?? null
}

function KioskLabel({ a, h }: { a: AssetEntry; h: number }) {
  return (
    <Tag position={[0, h + 0.45, 0]} distanceFactor={14}>
      <div className="wbtag dim"><b>{a.id}</b><i>{a.stand?.name && a.stand.name !== a.id ? a.stand.name : 'kiosk'}</i></div>
    </Tag>
  )
}

export function AssetLayer() {
  const wbKiosks = useWb((s) => s.dir?.placement.kiosks)
  const wbMode = useWorld((s) => s.mode === 'waybill')
  const skip = useMemo(() => new Set(wbMode ? (wbKiosks ?? []).map((k) => assetFor(k.id)?.id).filter(Boolean) : []), [wbMode, wbKiosks])
  if (!ASSETS.length) return null
  return (
    <Suspense fallback={null}>
      {ASSETS.map((a) => {
        if (a.station && a.anchor) return <AssetBody key={a.id} entry={a} at={a.anchor.at} rotY={a.anchor.rotY} ambient />
        if (skip.has(a.id)) return null
        const at = kioskAt(a)
        if (!at) return null
        return <AssetBody key={a.id} entry={a} at={at} rotY={a.anchor?.rotY ?? 0} ambient label={wbMode ? undefined : (h) => <KioskLabel a={a} h={h} />} />
      })}
    </Suspense>
  )
}

/** The forge's stage (?at=<id>&forge): the asset alone on a neutral floor disc, on a slow turntable. */
export function ForgeStage() {
  const a = STAGE_ID ? assetFor(STAGE_ID) : undefined
  const m = a?.manifest
  const r = m ? Math.max(m.footprint[0], m.footprint[1], m.height) * m.scale : 2
  return (
    <group>
      <directionalLight position={[r * 3, r * 5, r * 4]} intensity={1.7} castShadow shadow-mapSize={[2048, 2048]} shadow-camera-left={-r * 2} shadow-camera-right={r * 2} shadow-camera-top={r * 2} shadow-camera-bottom={-r * 2} shadow-bias={-0.0004} />
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.001, 0]} receiveShadow>
        <circleGeometry args={[Math.max(3, r * 2.4), 96]} />
        <meshStandardMaterial color="#D9D1C1" roughness={0.95} />
      </mesh>
      {a && <Suspense fallback={null}><AssetBody entry={a} at={[0, 0, 0]} rotY={0} stage /></Suspense>}
      <Turntable r={r} h={m ? m.height * m.scale : 1} />
    </group>
  )
}

/** The forge camera: looks at the asset from the front-right, a little above, turning slowly (or held at &angle=). */
function Turntable({ r, h }: { r: number; h: number }) {
  const { camera } = useThree()
  const t = useRef(0)
  const target = useMemo(() => new THREE.Vector3(0, h * 0.45, 0), [h])
  useFrame((_, dt) => {
    if (FLAGS.spin) t.current += Math.min(dt, 0.1)
    const cam = camera as THREE.PerspectiveCamera
    // fit a sphere round the asset into the frame, then stand back a little
    const fit = (r * 0.75) / Math.sin(THREE.MathUtils.degToRad(cam.fov / 2)) * 1.15
    const ang = THREE.MathUtils.degToRad(FLAGS.angle + 30) + (t.current * Math.PI * 2) / 24
    cam.position.set(Math.sin(ang) * fit * 0.94, target.y + fit * 0.34, Math.cos(ang) * fit * 0.94)
    cam.lookAt(target)
  })
  return null
}

/** With ?forge and no framed asset, ready resolves on the first drawn frame of the floor. */
export function FrameProbe() {
  const n = useRef(0)
  useFrame(() => { if (n.current < 2 && ++n.current === 2) markReady(null) })
  return null
}
