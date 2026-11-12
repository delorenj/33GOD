import { Tag } from "./Tag"
import { useFrame, useThree, type ThreeEvent } from '@react-three/fiber'
import { useEffect, useRef, useState } from 'react'
import * as THREE from 'three'
import { BULBS, OVERVIEW, STATIONS, stationById, type Bulb } from '../content'
import { ui, useWorld } from '../sim/store'

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
      const s = hover ? 1.25 : 1
      g.current.scale.lerp(new THREE.Vector3(s, s, s), 0.15)
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
  return (
    <group>
      {STATIONS.map((s) => (
        <Tag key={s.id} position={s.label} z={[15, 5]}>
          <button
            className={`station-label ${s.bloodbank ? 'bb' : ''} ${current === s.id ? 'active' : ''}`}
            onClick={() => ui.openStation(s.id)}
          >
            <span className="sl-name">
              {found.includes(s.id) && <span className="sl-check">✓ </span>}
              {s.name}
            </span>
            <span className="sl-real">{s.real.split(':')[0]}</span>
            {s.bloodbank && <span className="sl-chip">Bloodbank</span>}
          </button>
        </Tag>
      ))}
    </group>
  )
}

const ease = (t: number) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2)

export function CameraRig() {
  const focus = useWorld((s) => s.focus)
  const { camera, controls } = useThree() as unknown as { camera: THREE.PerspectiveCamera; controls: { target: THREE.Vector3; update: () => void; addEventListener: (e: string, f: () => void) => void; removeEventListener: (e: string, f: () => void) => void } | null }
  const anim = useRef<{ t: number; fp: THREE.Vector3; ft: THREE.Vector3; tp: THREE.Vector3; tt: THREE.Vector3 } | null>(null)

  useEffect(() => {
    if (!focus || !controls) return
    const v = focus.id === 'overview' ? OVERVIEW : stationById[focus.id].view
    anim.current = {
      t: 0,
      fp: camera.position.clone(),
      ft: controls.target.clone(),
      tp: new THREE.Vector3(...v.pos),
      tt: new THREE.Vector3(...v.target),
    }
  }, [focus, controls, camera])

  useEffect(() => {
    if (!controls) return
    const cancel = () => { anim.current = null }
    controls.addEventListener('start', cancel)
    return () => controls.removeEventListener('start', cancel)
  }, [controls])

  useFrame((_, dt) => {
    const a = anim.current
    if (!a || !controls) return
    a.t = Math.min(1, a.t + dt / 1.6)
    const e = ease(a.t)
    camera.position.lerpVectors(a.fp, a.tp, e)
    controls.target.lerpVectors(a.ft, a.tt, e)
    controls.update()
    if (a.t >= 1) anim.current = null
  })
  return null
}
