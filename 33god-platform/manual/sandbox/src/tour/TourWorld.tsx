import { RoundedBox } from '@react-three/drei'
import { useFrame } from '@react-three/fiber'
import { useMemo, useRef } from 'react'
import * as THREE from 'three'
import type { Vec3 } from '../content'
import { useWorld } from '../sim/store'
import { C } from '../world/Props'
import { Tag } from '../world/Tag'
import { CAST, TOUR, type Beat } from './script'
import { NEW_SETS, setFor } from './sets'

// ---------- people (faces are allowed on people, never on data) ----------

function Figure({ color, accent, height, speaking, isNew }: { color: string; accent: string; height: number; speaking: boolean; isNew?: boolean }) {
  const g = useRef<THREE.Group>(null)
  useFrame(({ clock }) => {
    if (!g.current) return
    const t = clock.getElapsedTime()
    g.current.position.y = speaking ? Math.abs(Math.sin(t * 7)) * 0.05 : 0
    g.current.rotation.z = speaking ? Math.sin(t * 3.5) * 0.04 : 0
  })
  const head = isNew ? 0.3 : 0.22
  return (
    <group ref={g} scale={[1, height, 1]}>
      <mesh position={[0, 0.55, 0]} castShadow>
        <capsuleGeometry args={[isNew ? 0.24 : 0.22, 0.55, 6, 14]} />
        <meshStandardMaterial color={color} roughness={0.7} />
      </mesh>
      <group position={[0, 1.18 + head - 0.19, 0]} scale={[1, 1 / height, 1]}>
        <mesh castShadow>
          <sphereGeometry args={[head, 24, 18]} />
          <meshStandardMaterial color={C.skin} roughness={0.8} />
        </mesh>
        {[-1, 1].map((s) => (
          <mesh key={s} position={[s * head * 0.36, head * 0.12, head * 0.9]}>
            <sphereGeometry args={[head * 0.11, 10, 8]} />
            <meshStandardMaterial color="#1B1B1B" />
          </mesh>
        ))}
        {/* hat or hair, in the character's accent */}
        <mesh position={[0, head * 0.72, 0]} castShadow>
          <cylinderGeometry args={[head * 0.75, head * 0.95, head * 0.45, 20]} />
          <meshStandardMaterial color={accent} roughness={0.6} />
        </mesh>
      </group>
      {isNew && (
        <mesh position={[0.12, 0.75, 0.23]}>
          <boxGeometry args={[0.16, 0.2, 0.02]} />
          <meshStandardMaterial color="#FFFFFF" />
        </mesh>
      )}
    </group>
  )
}

function HeroObject({ form }: { form: Beat['hero']['form'] }) {
  if (form === 'none') return null
  if (form === 'parcel')
    return (
      <RoundedBox args={[0.5, 0.38, 0.44]} radius={0.04} castShadow>
        <meshStandardMaterial color={C.parcel} roughness={0.9} />
      </RoundedBox>
    )
  if (form === 'postit')
    return (
      <mesh castShadow>
        <boxGeometry args={[0.5, 0.5, 0.06]} />
        <meshStandardMaterial color={C.post} />
      </mesh>
    )
  if (form === 'envelope' || form === 'slip')
    return (
      <mesh castShadow>
        <boxGeometry args={form === 'slip' ? [0.42, 0.26, 0.02] : [0.58, 0.4, 0.03]} />
        <meshStandardMaterial color={form === 'slip' ? '#F5F0E6' : '#D8B07A'} />
      </mesh>
    )
  // a recording: a small reel
  return (
    <group rotation={[Math.PI / 2, 0, 0]}>
      <mesh castShadow>
        <cylinderGeometry args={[0.24, 0.24, 0.08, 28]} />
        <meshStandardMaterial color="#111827" metalness={0.4} roughness={0.35} />
      </mesh>
      <mesh position={[0, 0.05, 0]}>
        <cylinderGeometry args={[0.08, 0.08, 0.02, 16]} />
        <meshStandardMaterial color="#F59E0B" />
      </mesh>
    </group>
  )
}

const tmp = new THREE.Vector3()

/** The newcomer: walks the rail between stops and carries the request in whatever form it has now. */
function Newcomer({ beat, speaking }: { beat: Beat; speaking: boolean }) {
  const g = useRef<THREE.Group>(null)
  const carry = beat.hero.at === beat.set
  const anchor = setFor(beat.set).anchor
  const cast = CAST.damian
  useFrame(({ camera, clock }, dt) => {
    if (!g.current) return
    tmp.set(anchor[0], anchor[1], anchor[2])
    const d = g.current.position.distanceTo(tmp)
    if (d > 0.02) {
      const step = Math.min(d, dt * Math.max(4, d * 1.4))
      const dir = tmp.clone().sub(g.current.position).normalize()
      g.current.position.addScaledVector(dir, step)
      g.current.rotation.y = Math.atan2(dir.x, dir.z)
      g.current.position.y = anchor[1] + Math.abs(Math.sin(clock.getElapsedTime() * 10)) * 0.08
    } else {
      const look = Math.atan2(camera.position.x - g.current.position.x, camera.position.z - g.current.position.z)
      g.current.rotation.y += (look - g.current.rotation.y) * 0.1
    }
  })
  return (
    <group ref={g} position={setFor(TOUR[0].set).anchor}>
      <Figure color={cast?.color ?? '#F97316'} accent={cast?.accent ?? '#FDE68A'} height={cast?.height ?? 0.85} speaking={speaking} isNew />
      {carry && (
        <group position={[0, 0.62, 0.46]}>
          <HeroObject form={beat.hero.form} />
        </group>
      )}
      <Tag position={[0, 2.1, 0]}>
        <div className={`tour-name ${speaking ? 'on' : ''}`} style={{ borderColor: cast?.color }}>{cast?.name ?? 'Damian'}</div>
      </Tag>
    </group>
  )
}

const SPOTS: Vec3[] = [[1.5, 0, -0.5], [-1.5, 0, -0.5], [2.6, 0, -1.4], [-2.6, 0, -1.4], [0.2, 0, -2.2]]

function Speaker({ who, at, speaking }: { who: string; at: Vec3; speaking: boolean }) {
  const g = useRef<THREE.Group>(null)
  const c = CAST[who]
  useFrame(({ camera }) => {
    if (!g.current) return
    const look = Math.atan2(camera.position.x - at[0], camera.position.z - at[2])
    g.current.rotation.y += (look - g.current.rotation.y) * 0.08
  })
  if (!c) return null
  return (
    <group position={at}>
      <group ref={g}>
        <Figure color={c.color} accent={c.accent} height={c.height} speaking={speaking} />
      </group>
      <Tag position={[0, 2.2 * Math.max(0.9, c.height), 0]}>
        <div className={`tour-name ${speaking ? 'on' : ''}`} style={{ borderColor: c.color }}>
          {c.name}
          <span>{c.role}</span>
        </div>
      </Tag>
    </group>
  )
}

/** A marker over the request when it is somewhere other than in the newcomer's hands. */
function HeroElsewhere({ beat }: { beat: Beat }) {
  const g = useRef<THREE.Group>(null)
  const at = setFor(beat.hero.at).anchor
  useFrame(({ clock }) => {
    if (!g.current) return
    g.current.position.y = at[1] + 2.4 + Math.sin(clock.getElapsedTime() * 2.2) * 0.12
    g.current.rotation.y = clock.getElapsedTime() * 0.8
  })
  if (beat.hero.at === beat.set || beat.hero.form === 'none') return null
  return (
    <group ref={g} position={[at[0], at[1] + 2.4, at[2]]}>
      <HeroObject form={beat.hero.form} />
      <mesh position={[0, -0.55, 0]} rotation={[Math.PI, 0, 0]}>
        <coneGeometry args={[0.14, 0.3, 4]} />
        <meshStandardMaterial color="#F59E0B" emissive="#F59E0B" emissiveIntensity={0.6} />
      </mesh>
    </group>
  )
}

export function TourCast() {
  const mode = useWorld((s) => s.mode)
  const bi = useWorld((s) => s.beat)
  const li = useWorld((s) => s.line)
  const beat = TOUR[Math.min(bi, TOUR.length - 1)]
  const others = useMemo(() => Array.from(new Set(beat.lines.map((l) => l.who))).filter((w) => w !== 'damian' && CAST[w]), [beat])
  if (mode !== 'tour' || !beat) return null
  const anchor = setFor(beat.set).anchor
  const speakingWho = beat.lines[Math.min(li, beat.lines.length - 1)]?.who
  return (
    <group>
      <Newcomer beat={beat} speaking={speakingWho === 'damian'} />
      {others.map((w, i) => {
        const s = SPOTS[i % SPOTS.length]
        return <Speaker key={`${beat.id}-${w}`} who={w} at={[anchor[0] + s[0], anchor[1] + s[1], anchor[2] + s[2]]} speaking={speakingWho === w} />
      })}
      <HeroElsewhere beat={beat} />
    </group>
  )
}

// ---------- the new sets: places the sandbox floor did not have yet ----------

function Entrance() {
  const s = NEW_SETS.entrance.anchor
  return (
    <group position={[s[0], 0, s[2] - 2]}>
      {[-2.2, 2.2].map((x) => (
        <mesh key={x} position={[x, 2, 0]} castShadow>
          <boxGeometry args={[0.5, 4, 0.5]} />
          <meshStandardMaterial color={C.trim} />
        </mesh>
      ))}
      <mesh position={[0, 4.2, 0]} castShadow>
        <boxGeometry args={[5, 0.6, 0.6]} />
        <meshStandardMaterial color={C.dock} />
      </mesh>
      <mesh position={[0, 0.011, 1.8]} rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[3.2, 4]} />
        <meshStandardMaterial color="#B45309" roughness={1} />
      </mesh>
    </group>
  )
}

function VoiceBooth() {
  const [x, , z] = NEW_SETS.voxxy.anchor
  return (
    <group position={[x + 2, 0, z - 2.4]}>
      <RoundedBox args={[3.4, 2.8, 2.6]} radius={0.1} position={[0, 1.4, 0]} castShadow receiveShadow>
        <meshStandardMaterial color="#312E81" roughness={0.9} />
      </RoundedBox>
      <mesh position={[0, 1.6, 1.31]}>
        <boxGeometry args={[1.8, 1, 0.04]} />
        <meshStandardMaterial color="#A5D8FF" transparent opacity={0.45} />
      </mesh>
      <mesh position={[0, 2.95, 0.8]}>
        <boxGeometry args={[1.4, 0.3, 0.1]} />
        <meshStandardMaterial color="#DC2626" emissive="#DC2626" emissiveIntensity={1.2} toneMapped={false} />
      </mesh>
      <group position={[-2.2, 0, 1.2]}>
        <mesh position={[0, 0.8, 0]}>
          <cylinderGeometry args={[0.03, 0.03, 1.6, 8]} />
          <meshStandardMaterial color="#111827" />
        </mesh>
        <mesh position={[0, 1.65, 0]}>
          <capsuleGeometry args={[0.09, 0.16, 4, 10]} />
          <meshStandardMaterial color="#9CA3AF" metalness={0.7} roughness={0.3} />
        </mesh>
      </group>
    </group>
  )
}

function Library() {
  const [x, , z] = NEW_SETS.library.anchor
  return (
    <group position={[x - 1.6, 0, z - 2]}>
      {[-1.4, 0, 1.4].map((dx) => (
        <group key={dx} position={[dx, 0, 0]}>
          <mesh position={[0, 1.3, 0]} castShadow receiveShadow>
            <boxGeometry args={[1.2, 2.6, 0.5]} />
            <meshStandardMaterial color={C.wood} />
          </mesh>
          {[0.5, 1.1, 1.7, 2.3].map((y) => (
            <mesh key={y} position={[0, y, 0.2]}>
              <boxGeometry args={[1.05, 0.4, 0.15]} />
              <meshStandardMaterial color={['#B91C1C', '#1D4ED8', '#047857', '#7C3AED'][Math.round(y * 3) % 4]} />
            </mesh>
          ))}
        </group>
      ))}
      <mesh position={[2.4, 0.9, 0.6]} castShadow>
        <boxGeometry args={[0.4, 0.25, 0.3]} />
        <meshStandardMaterial color="#111827" />
      </mesh>
    </group>
  )
}

function StaffingDesk() {
  const [x, , z] = NEW_SETS.staffing.anchor
  return (
    <group position={[x + 1.6, 0, z - 1.6]}>
      <RoundedBox args={[2.4, 1, 1]} radius={0.06} position={[0, 0.5, 0]} castShadow receiveShadow>
        <meshStandardMaterial color="#0F766E" />
      </RoundedBox>
      {[0, 1, 2].map((i) => (
        <mesh key={i} position={[-0.8 + i * 0.8, 1.9, -0.6]} castShadow>
          <boxGeometry args={[0.6, 0.4, 0.06]} />
          <meshStandardMaterial color={['#F59E0B', '#8B5CF6', '#10B981'][i]} />
        </mesh>
      ))}
    </group>
  )
}

function SoundWing() {
  const [x, , z] = NEW_SETS.soundwing.anchor
  return (
    <group position={[x + 2, 0, z - 2.2]}>
      {Array.from({ length: 9 }, (_, i) => (
        <mesh key={i} position={[-2 + i * 0.5, 1.3, 0]} castShadow>
          <boxGeometry args={[0.05, 2.6, 0.05]} />
          <meshStandardMaterial color="#6B7280" metalness={0.6} roughness={0.4} />
        </mesh>
      ))}
      <mesh position={[0, 2.62, 0]}>
        <boxGeometry args={[4.2, 0.08, 0.08]} />
        <meshStandardMaterial color="#6B7280" />
      </mesh>
      {[-1, 0, 1].map((i) => (
        <mesh key={i} position={[i * 1.2, 0.6, -1]} castShadow>
          <boxGeometry args={[0.8, 1.2, 0.6]} />
          <meshStandardMaterial color="#1F2937" />
        </mesh>
      ))}
    </group>
  )
}

/** New sets are always on the floor once built, so the sandbox can visit them too. */
export function TourSets() {
  const used = useMemo(() => new Set(TOUR.flatMap((b) => [b.set, b.hero.at])), [])
  return (
    <group>
      {used.has('entrance') && <Entrance />}
      {used.has('voxxy') && <VoiceBooth />}
      {used.has('library') && <Library />}
      {used.has('staffing') && <StaffingDesk />}
      {used.has('soundwing') && <SoundWing />}
    </group>
  )
}
