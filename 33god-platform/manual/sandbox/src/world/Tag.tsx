import { Html } from '@react-three/drei'
import { useFrame } from '@react-three/fiber'
import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import * as THREE from 'three'
import type { Vec3 } from '../content'
import { BELT_TOP } from '../sim/layout'

// DOM labels are never hidden by 3D geometry, so a label on the far side of the belt would float
// through it. The belt is the one big occluder on this floor; hide any label it stands in front of.
const BELT_BOX = new THREE.Box3(new THREE.Vector3(-2.35, 0, -0.6), new THREE.Vector3(2.35, BELT_TOP + 1.3, 0.6))
const ray = new THREE.Ray()
const hit = new THREE.Vector3()
const world = new THREE.Vector3()
let tagSeq = 0

export function behindBelt(camera: THREE.Camera, p: THREE.Vector3) {
  ray.origin.copy(camera.position)
  ray.direction.copy(p).sub(camera.position)
  const len = ray.direction.length()
  ray.direction.normalize()
  if (!ray.intersectBox(BELT_BOX, hit)) return false
  return hit.distanceTo(camera.position) < len - 0.05
}

export function Tag({ position = [0, 0, 0], children, distanceFactor, z = [10, 0] }: { position?: Vec3; children: ReactNode; distanceFactor?: number; z?: [number, number] }) {
  const g = useRef<THREE.Group>(null)
  const el = useRef<HTMLDivElement>(null)
  const pos = useMemo(() => position, [position])
  // mount the DOM label one frame late, so the anchor's world matrix is current for the first belt test
  const [on, setOn] = useState(false)
  useEffect(() => {
    const id = requestAnimationFrame(() => setOn(true))
    return () => cancelAnimationFrame(id)
  }, [])
  // re-test every third frame, staggered across tags: ~60 labels, one ray test each
  const slot = useRef(tagSeq++ % 3)
  const frame = useRef(0)
  useFrame(({ camera }) => {
    if (!g.current || !el.current) return
    if ((frame.current++ + slot.current) % 3 !== 0 && el.current.style.visibility) return
    g.current.getWorldPosition(world)
    const hidden = behindBelt(camera, world)
    el.current.style.visibility = hidden ? 'hidden' : 'visible'
  })
  return (
    <group ref={g} position={pos}>
      {on && (
        <Html center distanceFactor={distanceFactor} zIndexRange={z}>
          <div ref={el}>{children}</div>
        </Html>
      )}
    </group>
  )
}
