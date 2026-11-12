import { RoundedBox } from "@react-three/drei"
import { Tag } from "./Tag"
import { useFrame } from '@react-three/fiber'
import { useRef } from 'react'
import * as THREE from 'three'
import { VENDORS } from '../content'
import { along, courierPath } from '../sim/layout'
import { clock, useWorld, type Flyer, type Parcel, type Puff } from '../sim/store'
import { C, Person } from './Props'

const WALK = 2.6

function Courier({ p }: { p: Parcel }) {
  const g = useRef<THREE.Group>(null)
  const path = courierPath(p.vendor)
  const v = VENDORS[p.vendor]
  useFrame(() => {
    if (!g.current) return
    const back = p.backT0 !== null
    const u = back ? 1 - (clock.t - (p.backT0 as number)) / WALK : (clock.t - p.t0) / WALK
    const a = along(path, u)
    const b = along(path, back ? u - 0.02 : u + 0.02)
    g.current.position.set(a[0], Math.abs(Math.sin(clock.t * 9)) * 0.06, a[2])
    g.current.rotation.y = Math.atan2(b[0] - a[0], b[2] - a[2])
  })
  return (
    <group ref={g}>
      <Person position={[0, 0, 0]} color={C.uniform} scale={0.8} />
      <CarriedItem p={p} color={v.color} />
      <Tag position={[0, 1.55, 0.3]} distanceFactor={16}>
        <div className="parcel-tag" style={{ borderColor: v.color }}>
          <b style={{ color: v.color }}>{v.name}</b> {v.word}
          {p.backT0 !== null && <span className="back">{p.reply ? ' ↩ briefing card' : ' ↩ door shut'}</span>}
        </div>
      </Tag>
    </group>
  )
}

/** Out: the parcel. Back from the window: a briefing card. Back from a shut door: the parcel, still in hand. */
function CarriedItem({ p, color }: { p: Parcel; color: string }) {
  const g = useRef<THREE.Group>(null)
  const card = useRef<THREE.Mesh>(null)
  useFrame(() => {
    const showCard = p.reply && p.backT0 !== null && clock.t >= p.backT0
    if (g.current) g.current.visible = !showCard
    if (card.current) card.current.visible = showCard
  })
  return (
    <>
      <group ref={g}>
        <RoundedBox args={[0.46, 0.36, 0.42]} radius={0.04} position={[0, 0.82, 0.32]} castShadow>
          <meshStandardMaterial color={C.parcel} roughness={0.9} />
        </RoundedBox>
        <mesh position={[0, 1.005, 0.32]}>
          <boxGeometry args={[0.47, 0.02, 0.1]} />
          <meshStandardMaterial color={color} />
        </mesh>
      </group>
      <mesh ref={card} position={[0.18, 0.9, 0.3]} rotation={[0, 0, -0.2]} visible={false}>
        <boxGeometry args={[0.32, 0.22, 0.015]} />
        <meshStandardMaterial color="#FFFFFF" emissive="#FFFFFF" emissiveIntensity={0.25} />
      </mesh>
    </>
  )
}

const LOOK: Record<Flyer['look'], { color: string; size: [number, number, number]; opacity: number }> = {
  post: { color: C.post, size: [0.52, 0.52, 0.07], opacity: 1 },
  summary: { color: C.post, size: [0.52, 0.52, 0.07], opacity: 1 },
  copy: { color: '#FFE58A', size: [0.42, 0.42, 0.01], opacity: 0.75 },
  env: { color: '#D8B07A', size: [0.58, 0.4, 0.03], opacity: 1 },
  scrap: { color: '#E6C34A', size: [0.5, 0.5, 0.02], opacity: 0.9 },
  scrapEnv: { color: '#B9A27E', size: [0.55, 0.38, 0.02], opacity: 0.9 },
}

function FlyerMesh({ f }: { f: Flyer }) {
  const m = useRef<THREE.Mesh>(null)
  const look = LOOK[f.look]
  useFrame(() => {
    if (!m.current) return
    const u = Math.min(1, Math.max(0, (clock.t - f.t0) / f.dur))
    const e = f.look.startsWith('scrap') ? u * u : 1 - Math.pow(1 - u, 2)
    m.current.position.set(
      f.from[0] + (f.to[0] - f.from[0]) * e,
      f.from[1] + (f.to[1] - f.from[1]) * e + Math.sin(Math.PI * u) * f.arc,
      f.from[2] + (f.to[2] - f.from[2]) * e,
    )
    if (f.look.startsWith('scrap')) m.current.rotation.set(u * 4, u * 2, u * 3)
    else if (f.look === 'copy') m.current.rotation.set(0, u * Math.PI * 2, Math.sin(u * 8) * 0.3)
    const mat = m.current.material as THREE.MeshStandardMaterial
    mat.opacity = look.opacity * (f.look === 'copy' ? 1 - Math.max(0, u - 0.8) * 5 : 1)
  })
  return (
    <mesh ref={m} castShadow={f.look !== 'copy'}>
      <boxGeometry args={look.size} />
      <meshStandardMaterial color={look.color} transparent opacity={look.opacity} roughness={0.85} />
    </mesh>
  )
}

function PuffTag({ p }: { p: Puff }) {
  const g = useRef<THREE.Group>(null)
  const el = useRef<HTMLDivElement>(null)
  useFrame(() => {
    const u = (clock.t - p.t0) / p.life
    if (g.current) g.current.position.set(p.at[0], p.at[1] + u * 1.2, p.at[2])
    if (el.current) el.current.style.opacity = String(Math.max(0, 1 - Math.max(0, u - 0.6) * 2.5))
  })
  return (
    <group ref={g} position={p.at}>
      <Tag distanceFactor={13}>
        <div ref={el} className={`puff puff-${p.tone}`}>{p.text}</div>
      </Tag>
    </group>
  )
}

export function Moving() {
  const parcels = useWorld((s) => s.parcels)
  const flyers = useWorld((s) => s.flyers)
  const puffs = useWorld((s) => s.puffs)
  return (
    <group>
      {parcels.map((p) => <Courier key={p.id} p={p} />)}
      {flyers.map((f) => <FlyerMesh key={f.id} f={f} />)}
      {puffs.map((p) => <PuffTag key={p.id} p={p} />)}
    </group>
  )
}
