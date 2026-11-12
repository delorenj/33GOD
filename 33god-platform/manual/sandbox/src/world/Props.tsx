import { Line, RoundedBox } from '@react-three/drei'
import { useFrame } from '@react-three/fiber'
import { useMemo, useRef } from 'react'
import * as THREE from 'three'
import { VENDORS, type Vec3 } from '../content'
import { BAY_X, BAY_Z, CATALOGUER, CLOCK, CREW, DOCK, HANDS, LABEL_DESK, PLANNER, READERS, TRAY, courierPath } from '../sim/layout'
import { TRAY_SLOT, clock, hoursNow, useWorld } from '../sim/store'
import { clockFace, floorSign } from './textures'

export const C = {
  floor: '#D9D1C1',
  wall: '#EFE6D4',
  trim: '#C9BBA2',
  dock: '#E8833A',
  steel: '#5B6573',
  wood: '#9A6A45',
  archive: '#7C4DBA',
  crew: '#2F7F7A',
  clock: '#B23A48',
  rules: '#6B7280',
  control: '#475569',
  uniform: '#1F3A5F',
  skin: '#E9C9A8',
  parcel: '#B5895A',
  post: '#FFD84D',
}

export function Person({ position, color = C.uniform, rotation = 0, scale = 1 }: { position: Vec3; color?: string; rotation?: number; scale?: number }) {
  return (
    <group position={position} rotation={[0, rotation, 0]} scale={scale}>
      <mesh position={[0, 0.55, 0]} castShadow>
        <capsuleGeometry args={[0.2, 0.55, 6, 12]} />
        <meshStandardMaterial color={color} roughness={0.7} />
      </mesh>
      <mesh position={[0, 1.18, 0]} castShadow>
        <sphereGeometry args={[0.19, 20, 16]} />
        <meshStandardMaterial color={C.skin} roughness={0.8} />
      </mesh>
    </group>
  )
}

function Floor() {
  const sign = useMemo(() => floorSign('MATERIAL HANDLING', 'its real name is Bloodbank'), [])
  return (
    <group>
      <mesh rotation={[-Math.PI / 2, 0, 0]} receiveShadow>
        <planeGeometry args={[90, 70]} />
        <meshStandardMaterial color={C.floor} roughness={0.95} />
      </mesh>
      {/* Bloodbank's department, painted on the floor: courier lanes, dock, label desk, belt */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[-6.4, 0.01, 0.9]} receiveShadow>
        <planeGeometry args={[19.6, 11]} />
        <meshStandardMaterial color="#3B82F6" transparent opacity={0.13} roughness={1} />
      </mesh>
      <Line
        points={[[-16.2, 0.02, -4.6], [3.4, 0.02, -4.6], [3.4, 0.02, 6.4], [-16.2, 0.02, 6.4], [-16.2, 0.02, -4.6]]}
        color="#2563EB" lineWidth={2.5} dashed dashSize={0.6} gapSize={0.35}
      />
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[-10.2, 0.02, 5.6]}>
        <planeGeometry args={[9, 1.4]} />
        <meshBasicMaterial map={sign} transparent depthWrite={false} />
      </mesh>
    </group>
  )
}

function Bays() {
  return (
    <group>
      <mesh position={[BAY_X - 2, 2.6, 0]} castShadow receiveShadow>
        <boxGeometry args={[0.6, 5.2, 21]} />
        <meshStandardMaterial color={C.wall} roughness={0.9} />
      </mesh>
      {BAY_Z.map((z, i) => (
        <group key={i} position={[BAY_X - 1.65, 0, z]}>
          <mesh position={[0, 1.4, 0]}>
            <boxGeometry args={[0.12, 2.8, 2.3]} />
            <meshStandardMaterial color={VENDORS[i].color} roughness={0.6} />
          </mesh>
          <mesh position={[0.07, 1.3, 0]}>
            <boxGeometry args={[0.04, 2.5, 2.0]} />
            <meshStandardMaterial color="#3A3A3A" roughness={1} />
          </mesh>
          {/* the vendor's stack of parcels, each packed its own way */}
          {[0, 1, 2].map((k) => (
            <RoundedBox key={k} args={[0.5, 0.42, 0.5]} radius={0.05} position={[0.9, 0.21 + (k === 2 ? 0.42 : 0), k === 1 ? 0.55 : 0]} castShadow>
              <meshStandardMaterial color={C.parcel} roughness={0.9} />
            </RoundedBox>
          ))}
          <Line points={courierPath(i).map((p) => [p[0], 0.025, p[2]] as Vec3)} color={VENDORS[i].color} lineWidth={2} dashed dashSize={0.3} gapSize={0.25} transparent opacity={0.7} />
        </group>
      ))}
    </group>
  )
}

function Dock() {
  const shut = useWorld((s) => s.dockShut)
  const body = useRef<THREE.Group>(null)
  const shutter = useRef<THREE.Mesh>(null)
  useFrame((_, dt) => {
    const since = clock.t - useWorld.getState().dockPulseAt
    const k = since < 0.35 ? 1 + Math.sin((since / 0.35) * Math.PI) * 0.04 : 1
    body.current?.scale.set(k, k, k)
    if (shutter.current) {
      const target = shut ? 1 : 0.02
      shutter.current.scale.y += (target - shutter.current.scale.y) * Math.min(1, dt * 6)
      shutter.current.position.y = 2.3 - (shutter.current.scale.y * 2.2) / 2
    }
  })
  const [x, , z] = DOCK.center
  return (
    <group position={[x, 0, z]}>
      <group ref={body}>
        <RoundedBox args={[3.4, 2.8, 4.2]} radius={0.12} position={[0, 1.4, 0]} castShadow receiveShadow>
          <meshStandardMaterial color={C.dock} roughness={0.55} />
        </RoundedBox>
        <RoundedBox args={[3.7, 0.3, 4.5]} radius={0.08} position={[0, 2.95, 0]} castShadow>
          <meshStandardMaterial color="#C9692A" roughness={0.6} />
        </RoundedBox>
        {/* door in (parcels) on the left, slot out (post-its) on the right */}
        <mesh position={[-1.72, 1.15, 0]}>
          <boxGeometry args={[0.05, 2.2, 1.6]} />
          <meshStandardMaterial color="#2B2118" />
        </mesh>
        <mesh position={[1.72, 1.5, 0]}>
          <boxGeometry args={[0.05, 0.5, 0.9]} />
          <meshStandardMaterial color="#2B2118" />
        </mesh>
        {/* roof icons: a box goes in, a post-it comes out */}
        <RoundedBox args={[0.7, 0.55, 0.7]} radius={0.06} position={[-0.8, 3.4, 0]} castShadow>
          <meshStandardMaterial color={C.parcel} />
        </RoundedBox>
        <mesh position={[0.05, 3.4, 0]} rotation={[0, 0, -Math.PI / 2]}>
          <coneGeometry args={[0.18, 0.4, 3]} />
          <meshStandardMaterial color="#2B2118" />
        </mesh>
        <mesh position={[0.8, 3.45, 0]} rotation={[0, 0, 0.12]} castShadow>
          <boxGeometry args={[0.7, 0.7, 0.08]} />
          <meshStandardMaterial color={C.post} />
        </mesh>
      </group>
      <mesh ref={shutter} position={[-1.76, 1.2, 0]}>
        <boxGeometry args={[0.06, 2.2, 1.7]} />
        <meshStandardMaterial color="#8C939C" metalness={0.4} roughness={0.5} />
      </mesh>
    </group>
  )
}

function LabelDesk() {
  return (
    <group position={LABEL_DESK}>
      <RoundedBox args={[2.2, 0.9, 1.1]} radius={0.06} position={[0, 0.45, 0]} castShadow receiveShadow>
        <meshStandardMaterial color={C.wood} roughness={0.8} />
      </RoundedBox>
      <mesh position={[-0.55, 1.0, 0]} castShadow>
        <boxGeometry args={[0.7, 0.2, 0.5]} />
        <meshStandardMaterial color="#1E3A8A" />
      </mesh>
      {[0, 1, 2].map((i) => (
        <mesh key={i} position={[0.25 + i * 0.36, 0.95 + i * 0.01, 0.05]} castShadow>
          <boxGeometry args={[0.3, 0.1, 0.3]} />
          <meshStandardMaterial color={i === 1 ? '#FDE68A' : C.post} />
        </mesh>
      ))}
      <Person position={[0, 0, -0.9]} color="#1E3A8A" />
    </group>
  )
}

function Archive() {
  const [x, , z] = READERS.archive
  return (
    <group position={[x, 0, z]}>
      {[-1.3, 0, 1.3].map((dx, r) => (
        <group key={r} position={[dx, 0, 0]}>
          {[0.6, 1.4, 2.2].map((y, k) => (
            <group key={k}>
              <mesh position={[0, y, 0]} castShadow receiveShadow>
                <boxGeometry args={[1.1, 0.06, 0.8]} />
                <meshStandardMaterial color={C.wood} />
              </mesh>
              {[-0.32, 0, 0.32].map((bx, b) => (
                <mesh key={b} position={[bx, y + 0.2, 0]} castShadow>
                  <boxGeometry args={[0.26, 0.34, 0.6]} />
                  <meshStandardMaterial color={(r + k + b) % 3 === 0 ? C.archive : '#E9DCC3'} />
                </mesh>
              ))}
            </group>
          ))}
          {[-0.52, 0.52].map((px) => (
            <mesh key={px} position={[px, 1.3, 0]} castShadow>
              <boxGeometry args={[0.06, 2.6, 0.8]} />
              <meshStandardMaterial color={C.steel} />
            </mesh>
          ))}
        </group>
      ))}
      <Person position={[-2.4, 0, 0.6]} color={C.archive} rotation={-0.8} />
    </group>
  )
}

function RulesCabinet() {
  const [x, , z] = READERS.rules
  return (
    <group position={[x, 0, z]}>
      <RoundedBox args={[1.4, 2.2, 0.9]} radius={0.06} position={[0, 1.1, 0]} castShadow receiveShadow>
        <meshStandardMaterial color={C.rules} roughness={0.5} metalness={0.2} />
      </RoundedBox>
      {[0.5, 1.1, 1.7].map((y) => (
        <mesh key={y} position={[0, y, 0.46]}>
          <boxGeometry args={[1.1, 0.42, 0.04]} />
          <meshStandardMaterial color="#9CA3AF" />
        </mesh>
      ))}
    </group>
  )
}

function ControlRoom() {
  const [x, , z] = READERS.control
  return (
    <group position={[x, 0, z]}>
      <mesh position={[0.5, 3.4, 0]} castShadow receiveShadow>
        <boxGeometry args={[4, 0.2, 3.2]} />
        <meshStandardMaterial color={C.control} />
      </mesh>
      {[[-1.3, -1.4], [2.3, -1.4], [-1.3, 1.4], [2.3, 1.4]].map(([px, pz], i) => (
        <mesh key={i} position={[px, 1.7, pz]} castShadow>
          <boxGeometry args={[0.16, 3.4, 0.16]} />
          <meshStandardMaterial color={C.steel} />
        </mesh>
      ))}
      {/* the visitor's window, facing the belt */}
      <mesh position={[-1.45, 4.3, 0]}>
        <boxGeometry args={[0.05, 1.5, 3.0]} />
        <meshStandardMaterial color="#A5D8FF" transparent opacity={0.25} />
      </mesh>
      {[-0.7, 0.4].map((dz) => (
        <mesh key={dz} position={[0.9, 4.15, dz]} rotation={[0, -Math.PI / 2, 0]}>
          <boxGeometry args={[0.9, 0.55, 0.06]} />
          <meshStandardMaterial color="#0B1220" emissive="#38BDF8" emissiveIntensity={0.9} />
        </mesh>
      ))}
      <Person position={[0.2, 3.5, 0]} color={C.control} rotation={-Math.PI / 2} />
      {/* its own notebook */}
      <mesh position={[-0.6, 3.56, 1.0]} rotation={[-Math.PI / 2, 0, 0.3]}>
        <boxGeometry args={[0.4, 0.5, 0.05]} />
        <meshStandardMaterial color="#F43F5E" />
      </mesh>
      {/* stairs */}
      {Array.from({ length: 8 }, (_, i) => (
        <mesh key={i} position={[3.1, 0.2 + i * 0.42, 1.2 - i * 0.32]} castShadow receiveShadow>
          <boxGeometry args={[0.9, 0.12, 0.34]} />
          <meshStandardMaterial color={C.steel} />
        </mesh>
      ))}
    </group>
  )
}

function Cataloguer() {
  return (
    <group position={CATALOGUER}>
      <RoundedBox args={[1.5, 0.85, 0.9]} radius={0.05} position={[0, 0.43, 0]} castShadow receiveShadow>
        <meshStandardMaterial color="#A16207" />
      </RoundedBox>
      <Person position={[0.2, 0, 0.8]} color="#A16207" rotation={Math.PI} />
      {/* the runner: a helper bolted to the cataloguer's room */}
      <Person position={[-1.1, 0, -0.2]} color="#65A30D" scale={0.85} />
    </group>
  )
}

function Clock() {
  const hour = useRef<THREE.Group>(null)
  const minute = useRef<THREE.Group>(null)
  const bell = useRef<THREE.Group>(null)
  const face = useMemo(() => clockFace(), [])
  useFrame(() => {
    const h = hoursNow()
    if (hour.current) hour.current.rotation.z = -((h % 12) / 12) * Math.PI * 2
    if (minute.current) minute.current.rotation.z = -(h % 1) * Math.PI * 2
    const since = clock.t - useWorld.getState().clockRingAt
    if (bell.current) bell.current.rotation.z = since < 1.2 ? Math.sin(since * 22) * 0.35 * (1 - since / 1.2) : 0
  })
  return (
    <group position={CLOCK} rotation={[0, Math.PI / 4, 0]}>
      <RoundedBox args={[1.6, 5.2, 1.6]} radius={0.1} position={[0, 2.6, 0]} castShadow receiveShadow>
        <meshStandardMaterial color={C.clock} roughness={0.6} />
      </RoundedBox>
      <group position={[0, 4.3, 0.82]}>
        <mesh>
          <circleGeometry args={[0.7, 48]} />
          <meshStandardMaterial map={face} />
        </mesh>
        <group ref={hour} position={[0, 0, 0.02]}>
          <mesh position={[0, 0.2, 0]}>
            <boxGeometry args={[0.07, 0.4, 0.02]} />
            <meshStandardMaterial color="#2a2418" />
          </mesh>
        </group>
        <group ref={minute} position={[0, 0, 0.03]}>
          <mesh position={[0, 0.28, 0]}>
            <boxGeometry args={[0.04, 0.56, 0.02]} />
            <meshStandardMaterial color="#2a2418" />
          </mesh>
        </group>
      </group>
      <group ref={bell} position={[0, 5.9, 0]}>
        <mesh position={[0, -0.25, 0]} castShadow>
          <cylinderGeometry args={[0.18, 0.45, 0.6, 24, 1, true]} />
          <meshStandardMaterial color="#D4A017" metalness={0.7} roughness={0.3} side={THREE.DoubleSide} />
        </mesh>
      </group>
    </group>
  )
}

function CrewHall() {
  const desks = useWorld((s) => s.desks)
  const inTray = useWorld((s) => s.notes.filter((n) => n.hatch === 'crew' && n.heldBy === TRAY_SLOT).length)
  const [x, , z] = CREW.center
  return (
    <group>
      <group position={[x, 0, z]}>
        <mesh position={[0, 1.6, -1.6]} castShadow receiveShadow>
          <boxGeometry args={[6.8, 3.2, 0.25]} />
          <meshStandardMaterial color={C.crew} />
        </mesh>
        {[-3.4, 3.4].map((sx) => (
          <mesh key={sx} position={[sx, 1.6, 0]} castShadow receiveShadow>
            <boxGeometry args={[0.25, 3.2, 3.4]} />
            <meshStandardMaterial color={C.crew} />
          </mesh>
        ))}
      </group>
      {CREW.desks.map((d, i) => (
        <group key={i} position={[d[0], 0, d[2]]}>
          <RoundedBox args={[1.15, 0.9, 0.9]} radius={0.05} position={[0, 0.45, 0]} castShadow receiveShadow>
            <meshStandardMaterial color={C.wood} />
          </RoundedBox>
          <Person position={[0, 0, -0.8]} color={C.crew} />
          {desks[i]?.holding != null && (
            <mesh position={[0, 0.93, 0.05]} rotation={[-Math.PI / 2, 0, 0]}>
              <planeGeometry args={[0.55, 0.38]} />
              <meshStandardMaterial color="#D8B07A" />
            </mesh>
          )}
        </group>
      ))}
      {/* the tray by the hatch: envelopes taken, waiting for a desk (drawn 4 slots; the real tray holds 64) */}
      <group position={[CREW.tray[0], 0, CREW.tray[2]]}>
        <mesh position={[0, 0.5, 0]} castShadow receiveShadow>
          <boxGeometry args={[1.2, 1, 0.8]} />
          <meshStandardMaterial color={C.steel} />
        </mesh>
        {Array.from({ length: TRAY }, (_, i) => (
          <mesh key={i} position={[0, 1.02 + i * 0.06, 0]} visible={i < inTray}>
            <boxGeometry args={[0.6, 0.04, 0.42]} />
            <meshStandardMaterial color="#D8B07A" />
          </mesh>
        ))}
      </group>
    </group>
  )
}

/** The clock's planner reads tick post-its; its hands take the clock's own envelopes. */
function ClockCrew() {
  const busy = useWorld((s) => s.hands.holding !== null)
  return (
    <group>
      <group position={PLANNER}>
        <RoundedBox args={[1.1, 0.8, 0.7]} radius={0.04} position={[0, 0.4, 0]} castShadow receiveShadow>
          <meshStandardMaterial color={C.clock} />
        </RoundedBox>
        <Person position={[0, 0, -0.65]} color={C.clock} scale={0.9} />
      </group>
      <group position={HANDS}>
        <RoundedBox args={[1.2, 0.85, 0.8]} radius={0.04} position={[0, 0.43, 0]} castShadow receiveShadow>
          <meshStandardMaterial color={C.wood} />
        </RoundedBox>
        <Person position={[0, 0, -0.7]} color={C.clock} />
        {busy && (
          <mesh position={[0, 0.88, 0.05]} rotation={[-Math.PI / 2, 0, 0]}>
            <planeGeometry args={[0.55, 0.38]} />
            <meshStandardMaterial color="#D8B07A" />
          </mesh>
        )}
      </group>
    </group>
  )
}

/** Wires from each durable reader to its clip on the belt rail: the clip lives on the belt, not in the reader's hand. */
function ClipWires() {
  return (
    <group>
      <Line points={[[READERS.archive[0] - 1.6, 2.6, READERS.archive[2]], [4, 4, 3], [-2.35, 2.2, 0.9]]} color={C.archive} lineWidth={1.2} transparent opacity={0.35} />
      <Line points={[[READERS.rules[0], 2.2, READERS.rules[2]], [2, 3.5, 5], [-2.35, 2.2, 0.9]]} color={C.rules} lineWidth={1.2} transparent opacity={0.35} />
    </group>
  )
}

export function Props() {
  return (
    <group>
      <Floor />
      <Bays />
      <Dock />
      <LabelDesk />
      <Archive />
      <RulesCabinet />
      <ControlRoom />
      <Cataloguer />
      <Clock />
      <CrewHall />
      <ClockCrew />
      <ClipWires />
    </group>
  )
}
