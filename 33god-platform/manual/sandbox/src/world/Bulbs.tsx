import { Tag } from "./Tag"
import { useFrame, type ThreeEvent } from '@react-three/fiber'
import { useRef, useState } from 'react'
import * as THREE from 'three'
import { BULBS, STATIONS, type Bulb } from '../content'
import { domainById } from '../domains'
import { ui, useWorld } from '../sim/store'

const ONE = new THREE.Vector3(1, 1, 1)
const BIG = new THREE.Vector3(1.25, 1.25, 1.25)

function LightBulb({ b, index }: { b: Bulb; index: number }) {
  const g = useRef<THREE.Group>(null)
  const glass = useRef<THREE.MeshStandardMaterial>(null)
  const [hover, setHover] = useState(false)
  const found = useWorld((s) => s.foundBulbs.includes(b.id))
  useFrame(({ clock: c }) => {
    const t = c.getElapsedTime() + index * 0.9
    if (g.current) {
      g.current.position.y = b.at[1] + Math.sin(t * 2) * 0.12
      g.current.rotation.y = t * 0.6
      g.current.scale.lerp(hover ? BIG : ONE, 0.15)
    }
    if (glass.current) glass.current.emissiveIntensity = (found ? 1.2 : 2.4) + Math.sin(t * 3) * (found ? 0.2 : 0.8) + (hover ? 1.5 : 0)
  })
  const onClick = (e: ThreeEvent<MouseEvent>) => {
    if (e.delta > 6) return
    e.stopPropagation()
    ui.openBulb(b.id)
  }
  return (
    <group
      ref={g}
      position={b.at}
      onClick={onClick}
      onPointerOver={(e) => { e.stopPropagation(); setHover(true); document.body.style.cursor = 'pointer' }}
      onPointerOut={() => { setHover(false); document.body.style.cursor = '' }}
    >
      <mesh position={[0, 0.12, 0]}>
        <sphereGeometry args={[0.24, 32, 24]} />
        <meshStandardMaterial ref={glass} color="#FFF4C2" emissive="#FFC93C" emissiveIntensity={2} toneMapped={false} transparent opacity={0.95} />
      </mesh>
      <mesh position={[0, -0.17, 0]}>
        <cylinderGeometry args={[0.11, 0.09, 0.2, 16]} />
        <meshStandardMaterial color="#9CA3AF" metalness={0.8} roughness={0.3} />
      </mesh>
      {/* a generous invisible hit area so the bulb is easy to tap on a phone */}
      <mesh visible={false}>
        <sphereGeometry args={[0.55, 8, 8]} />
      </mesh>
      {hover && (
        <Tag position={[0, 0.65, 0]}>
          <div className="tag tag-bulb">{b.title}</div>
        </Tag>
      )}
    </group>
  )
}

export function Bulbs() {
  return <group>{BULBS.map((b, i) => <LightBulb key={b.id} b={b} index={i} />)}</group>
}

export function StationLabels() {
  const found = useWorld((s) => s.foundStations)
  const current = useWorld((s) => s.station)
  const mode = useWorld((s) => s.mode)
  const intro = useWorld((s) => s.intro)
  const mapOpen = useWorld((s) => s.mapOpen)
  if (mode === 'tour' || intro || mapOpen) return null
  // labels speak in real 33GOD names; the warehouse words are painted on signs in the world
  return (
    <group>
      {STATIONS.map((s) => {
        const d = domainById[s.domain]
        return (
          <Tag key={s.id} position={s.label} z={[15, 5]}>
            <button
              className={`station-label ${current === s.id ? 'active' : ''}`}
              style={{ borderColor: d.color }}
              onClick={() => ui.openStation(s.id)}
            >
              <span className="sl-name">
                {found.includes(s.id) && <span className="sl-check" style={{ color: d.color }}>✓ </span>}
                {s.name}
              </span>
              <span className="sl-chip" style={{ background: d.color }}>{d.name}</span>
            </button>
          </Tag>
        )
      })}
    </group>
  )
}
