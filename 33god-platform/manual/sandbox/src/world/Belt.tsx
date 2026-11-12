import { Tag } from "./Tag"
import { useFrame, type ThreeEvent } from '@react-three/fiber'
import { useMemo, useRef, useState } from 'react'
import * as THREE from 'three'
import { BELT, BELT_TOP } from '../sim/layout'
import { notePos } from '../sim/layout'
import { hoursNow, useWorld, type Note } from '../sim/store'
import { C } from './Props'
import { envelopeFace, postItFace } from './textures'

const W = BELT.x1 - BELT.x0
const SLAT_GAP = 0.45

function Slats({ z, height }: { z: number; height: number }) {
  const ref = useRef<THREE.InstancedMesh>(null)
  const count = Math.ceil(height / SLAT_GAP) + 1
  const m = useMemo(() => new THREE.Matrix4(), [])
  useFrame(() => {
    if (!ref.current) return
    // the belt climbs at exactly the speed notes age: height is age
    const offset = ((hoursNow() / 24) * BELT.mPerDay) % SLAT_GAP
    for (let i = 0; i < count; i++) {
      const y = BELT.baseY - 0.3 + ((i * SLAT_GAP + offset) % (count * SLAT_GAP))
      m.makeTranslation(0, Math.min(y, BELT.baseY - 0.3 + height), z)
      ref.current.setMatrixAt(i, m)
    }
    ref.current.instanceMatrix.needsUpdate = true
  })
  return (
    <instancedMesh ref={ref} args={[undefined, undefined, count]}>
      <boxGeometry args={[W, 0.05, 0.03]} />
      <meshStandardMaterial color="#3D434D" roughness={0.9} />
    </instancedMesh>
  )
}

function Scraper({ y, z, label }: { y: number; z: number; label: string }) {
  const sign = z > 0 ? 1 : -1
  return (
    <group position={[0, y, z + sign * 0.12]}>
      <mesh castShadow>
        <boxGeometry args={[W + 0.5, 0.14, 0.18]} />
        <meshStandardMaterial color="#DC2626" roughness={0.4} />
      </mesh>
      {Array.from({ length: 12 }, (_, i) => (
        <mesh key={i} position={[BELT.x0 + 0.15 + i * (W / 11.6), -0.12, 0]} rotation={[Math.PI, 0, 0]}>
          <coneGeometry args={[0.05, 0.14, 4]} />
          <meshStandardMaterial color="#991B1B" />
        </mesh>
      ))}
      <Tag position={[sign > 0 ? W / 2 + 0.7 : -(W / 2 + 0.7), 0, 0]} distanceFactor={14}>
        <div className="tag tag-red">{label}</div>
      </Tag>
    </group>
  )
}

function Ruler() {
  const days = Array.from({ length: BELT.frontDays + 1 }, (_, d) => d)
  return (
    <group>
      {days.map((d) => (
        <group key={d} position={[BELT.x1 + 0.42, BELT.baseY + d * BELT.mPerDay, BELT.frontZ]}>
          <mesh>
            <boxGeometry args={[0.3, 0.03, 0.03]} />
            <meshStandardMaterial color="#1F2937" />
          </mesh>
          {d > 0 && d < BELT.frontDays && (
            <Tag position={[0.9, 0, 0]} distanceFactor={14}>
              <div className="tick">{d === 1 ? '1 day' : `${d} days`}</div>
            </Tag>
          )}
        </group>
      ))}
      {[0, 12].map((hr) => (
        <group key={hr} position={[BELT.x0 - 0.42, BELT.baseY + (hr / 24) * BELT.mPerDay, BELT.backZ]}>
          <mesh>
            <boxGeometry args={[0.3, 0.03, 0.03]} />
            <meshStandardMaterial color="#1F2937" />
          </mesh>
          {hr > 0 && (
            <Tag position={[-0.9, 0, 0]} distanceFactor={14}>
              <div className="tick">12 h</div>
            </Tag>
          )}
        </group>
      ))}
    </group>
  )
}

function NoteMesh({ note }: { note: Note }) {
  const group = useRef<THREE.Group>(null)
  const inspecting = useWorld((s) => s.inspect === note.id)
  const [hover, setHover] = useState(false)
  const isPost = note.kind === 'post'
  const tex = useMemo(
    () => (isPost ? postItFace(note.headline, note.from) : envelopeFace(note.headline, note.hatch === null)),
    [isPost, note.headline, note.from, note.hatch],
  )
  const tilt = useMemo(() => ((note.id * 7919) % 100) / 100 - 0.5, [note.id])
  useFrame(() => {
    if (!group.current) return
    const p = notePos(note.kind, note.col, (hoursNow() - note.bornH) / 24)
    group.current.position.set(p[0], p[1], p[2])
    const s = inspecting ? 1.35 : hover ? 1.15 : 1
    group.current.scale.lerp(new THREE.Vector3(s, s, s), 0.2)
  })
  const onClick = (e: ThreeEvent<MouseEvent>) => {
    if (e.delta > 6) return
    e.stopPropagation()
    useWorld.setState({ inspect: note.id, bulb: null })
  }
  const w = isPost ? 0.52 : 0.58
  const h = isPost ? 0.52 : 0.4
  return (
    <group
      ref={group}
      rotation={[0, isPost ? 0 : Math.PI, tilt * 0.12]}
      onClick={onClick}
      onPointerOver={(e) => { e.stopPropagation(); setHover(true); document.body.style.cursor = 'pointer' }}
      onPointerOut={() => { setHover(false); document.body.style.cursor = '' }}
    >
      {/* a pad of identical sheets: tearing one off leaves the note on the belt */}
      <mesh position={[0, 0, isPost ? 0.035 : 0.02]} castShadow>
        <boxGeometry args={[w, h, isPost ? 0.07 : 0.03]} />
        <meshStandardMaterial color={isPost ? '#F2C93B' : note.hatch === null ? '#A8A399' : '#C79A62'} roughness={0.9} />
      </mesh>
      <mesh position={[0, 0, isPost ? 0.072 : 0.037]}>
        <planeGeometry args={[w, h]} />
        <meshStandardMaterial map={tex} roughness={0.85} emissive={inspecting ? '#FFFFFF' : '#000000'} emissiveIntensity={inspecting ? 0.15 : 0} />
      </mesh>
      {note.heldBy !== null && (
        <group position={[0.2, 0.14, 0.06]}>
          <mesh>
            <sphereGeometry args={[0.06, 12, 12]} />
            <meshStandardMaterial color={C.crew} />
          </mesh>
          <Tag position={[0.05, 0.16, 0]} distanceFactor={10}>
            <div className="tag tag-teal">desk {note.heldBy + 1}</div>
          </Tag>
        </group>
      )}
    </group>
  )
}

function Clip({ which, color, label }: { which: 'archive' | 'rules'; color: string; label: string }) {
  const ref = useRef<THREE.Group>(null)
  useFrame(() => {
    const s = useWorld.getState()
    const id = s.lastRead[which]
    const n = id !== null ? s.notes.find((x) => x.id === id) : undefined
    if (!ref.current) return
    ref.current.visible = !!n
    if (n) {
      const p = notePos('post', 0, (hoursNow() - n.bornH) / 24)
      ref.current.position.y += (p[1] - ref.current.position.y) * 0.2
    }
  })
  return (
    <group ref={ref} position={[BELT.x0 - 0.3, BELT.baseY, BELT.frontZ + (which === 'archive' ? 0.1 : 0.22)]}>
      <mesh castShadow>
        <boxGeometry args={[0.22, 0.12, 0.08]} />
        <meshStandardMaterial color={color} metalness={0.3} roughness={0.4} />
      </mesh>
      <Tag position={[-0.55, which === 'archive' ? 0.05 : -0.18, 0]} distanceFactor={10}>
        <div className="tick">{label}</div>
      </Tag>
    </group>
  )
}

export function Belt() {
  const notes = useWorld((s) => s.notes)
  const shaftH = BELT_TOP + 1.4
  return (
    <group>
      {/* frame */}
      {[BELT.x0 - 0.2, BELT.x1 + 0.2].map((x) => (
        <mesh key={x} position={[x, shaftH / 2, 0]} castShadow receiveShadow>
          <boxGeometry args={[0.22, shaftH, 1.5]} />
          <meshStandardMaterial color={C.steel} metalness={0.5} roughness={0.45} />
        </mesh>
      ))}
      {[0.35, shaftH - 0.2].map((y) => (
        <mesh key={y} position={[0, y, 0]} rotation={[0, 0, Math.PI / 2]} castShadow>
          <cylinderGeometry args={[0.6, 0.6, W, 32]} />
          <meshStandardMaterial color="#4B5563" metalness={0.6} roughness={0.35} />
        </mesh>
      ))}
      {/* the two faces: post-its on the front, envelopes on the back */}
      <mesh position={[0, shaftH / 2, BELT.frontZ - 0.03]} receiveShadow>
        <boxGeometry args={[W, shaftH - 0.4, 0.04]} />
        <meshStandardMaterial color="#2B2F36" roughness={0.95} />
      </mesh>
      <mesh position={[0, shaftH / 2, BELT.backZ + 0.03]} receiveShadow>
        <boxGeometry args={[W, shaftH - 0.4, 0.04]} />
        <meshStandardMaterial color="#33302B" roughness={0.95} />
      </mesh>
      <Slats z={BELT.frontZ - 0.005} height={shaftH - 0.6} />
      <Slats z={BELT.backZ + 0.005} height={shaftH - 0.6} />
      {/* glass shaft */}
      <mesh position={[0, shaftH / 2, 0]}>
        <boxGeometry args={[W + 0.9, shaftH + 0.2, 2.1]} />
        <meshStandardMaterial color="#CFE8FF" transparent opacity={0.07} depthWrite={false} roughness={0.1} />
      </mesh>
      <Scraper y={BELT_TOP} z={BELT.frontZ} label="7-day scraper" />
      <Scraper y={BELT.baseY + BELT.backDays * BELT.mPerDay} z={BELT.backZ} label="1-day scraper" />
      <Ruler />
      <Clip which="archive" color={C.archive} label="archive's clip" />
      <Clip which="rules" color={C.rules} label="rules card's clip" />
      {notes.map((n) => (
        <NoteMesh key={n.id} note={n} />
      ))}
    </group>
  )
}
