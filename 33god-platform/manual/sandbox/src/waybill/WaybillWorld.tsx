// The 3D layer of the waybill player. A PURE function of the playhead: the driver below advances one
// number (wbClock.u, 0..1 through the current stop) and everything else reads it. No sim later().
import { useFrame } from '@react-three/fiber'
import { Suspense, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import * as THREE from 'three'
import { isPortrait, type Vec3 } from '../content'
import { BAY_X, BAY_Z } from '../sim/layout'
import { AssetBody } from '../assets/AssetLayer'
import { assetFor } from '../assets/registry'
import { emitVisit } from '../assets/visits'
import { Figure } from '../tour/TourWorld'
import { useLive } from '../world/hidden'
import { C } from '../world/Props'
import { Tag } from '../world/Tag'
import type { HeroForm, Stop } from './director'
import { placeName, spotOf, type Kiosk, type Placement } from './stations'
import { narr } from './narrator'
import { stopHold, useWb, wb, wbClock } from './state'
import { fmtMs, fmtRel, fmtT, type Waybill } from './types'

const BELT_LOAD: Vec3 = [0, 1.25, 0.82]
const smooth = (x: number) => { const k = Math.max(0, Math.min(1, x)); return k * k * (3 - 2 * k) }
const lerp3 = (a: Vec3, b: Vec3, e: number): Vec3 => [a[0] + (b[0] - a[0]) * e, a[1] + (b[1] - a[1]) * e, a[2] + (b[2] - a[2]) * e]
const add = (a: Vec3, d: Vec3): Vec3 => [a[0] + d[0], a[1] + d[1], a[2] + d[2]]

/** The one clock: advances the playhead, hands over to the next stop, keeps the recording-time cursor.
 *  A narrated stop is held at least as long as its line runs, and never left while the narrator is still talking. */
function Driver() {
  useFrame((_, dt) => {
    const s = useWb.getState()
    const st = s.dir?.stops[s.stop]
    if (!s.dir || !st) return
    if (s.playing && st.kind !== 'end') {
      wbClock.u += (Math.min(dt, 0.1) * 1000 * s.rate) / Math.max(stopHold(st), narr.holdMs * s.rate)
      if (wbClock.u >= 1) {
        wbClock.u = 1
        if (narr.done && s.stop < s.dir.stops.length - 1) wb.next()
      }
    }
    wbClock.t = st.t0 + wbClock.u * (st.t1 - st.t0)
  })
  return null
}

/** Flips to true once the stop's progress passes `at`. Re-renders only at the crossing. */
function useReached(at: number): boolean {
  const [on, setOn] = useState(wbClock.u >= at)
  useFrame(() => { const r = wbClock.u >= at; if (r !== on) setOn(r) })
  return on
}

function Label({ real, place, tone, children }: { real: string; place?: string; tone?: 'red' | 'amber' | 'dim' | 'blue'; children?: ReactNode }) {
  return (
    <div className={`wbtag ${tone ?? ''}`}>
      <b>{real}</b>
      {place && <i>{place}</i>}
      {children}
    </div>
  )
}

/** The hero's own line under a station tag: what the thing is and its size or time. */
function HeroLine({ h }: { h: NonNullable<Stop['heroLabel']> }) {
  return <div className="wbhero"><b>{h.real}</b>{h.sub && <span>{h.sub}</span>}</div>
}

/** 'collected at +4.1 s', or '2.21 s before Enter' when it happened before the prompt. */
const atWords = (verb: string, t: number | null | undefined) => (t == null ? verb : t < 0 ? `${verb} ${fmtRel(t)}` : `${verb} at ${fmtT(t)}`)

// ---------- the hero object ----------

function HeroMesh({ form }: { form: HeroForm }) {
  switch (form) {
    case 'parcel': return <mesh castShadow><boxGeometry args={[0.5, 0.38, 0.44]} /><meshStandardMaterial color={C.parcel} roughness={0.9} /></mesh>
    case 'postit': return <mesh castShadow><boxGeometry args={[0.5, 0.5, 0.06]} /><meshStandardMaterial color={C.post} /></mesh>
    case 'envelope': return <mesh castShadow><boxGeometry args={[0.58, 0.4, 0.03]} /><meshStandardMaterial color="#D8B07A" /></mesh>
    case 'slip': return <mesh castShadow><boxGeometry args={[0.42, 0.26, 0.02]} /><meshStandardMaterial color="#F5F0E6" /></mesh>
    case 'card':
      // a big envelope with a bold accent outline: it has to read from across the floor
      return (
        <group scale={1.9}>
          <mesh castShadow position={[0, 0, -0.025]}><boxGeometry args={[0.74, 0.52, 0.03]} /><meshStandardMaterial color="#2563EB" emissive="#2563EB" emissiveIntensity={0.35} /></mesh>
          <mesh castShadow><boxGeometry args={[0.66, 0.44, 0.04]} /><meshStandardMaterial color="#FFFAF0" /></mesh>
          <mesh position={[0, 0.14, 0.03]}><boxGeometry args={[0.66, 0.1, 0.01]} /><meshStandardMaterial color="#2563EB" /></mesh>
          {[-0.04, -0.12].map((y, i) => <mesh key={i} position={[-0.05 - i * 0.04, y, 0.03]}><boxGeometry args={[0.46 - i * 0.1, 0.03, 0.01]} /><meshStandardMaterial color="#9CA3AF" /></mesh>)}
        </group>
      )
    case 'phone':
      return (
        <group scale={1.9}>
          <mesh castShadow><boxGeometry args={[0.3, 0.52, 0.05]} /><meshStandardMaterial color="#111827" roughness={0.4} /></mesh>
          <mesh position={[0, 0, 0.03]}><boxGeometry args={[0.25, 0.44, 0.005]} /><meshStandardMaterial color="#38BDF8" emissive="#38BDF8" emissiveIntensity={0.5} /></mesh>
        </group>
      )
    case 'toolbox':
      return (
        <group scale={1.6}>
          <mesh castShadow><boxGeometry args={[0.56, 0.3, 0.36]} /><meshStandardMaterial color="#B91C1C" roughness={0.6} /></mesh>
          <mesh position={[0, 0.2, 0]}><boxGeometry args={[0.26, 0.06, 0.05]} /><meshStandardMaterial color="#374151" /></mesh>
        </group>
      )
    case 'lamp': return <mesh castShadow><sphereGeometry args={[0.2, 18, 14]} /><meshStandardMaterial color="#FBBF24" emissive="#F59E0B" emissiveIntensity={0.7} /></mesh>
    default: return null
  }
}

const FLAT = new Set<HeroForm>(['card', 'postit', 'envelope', 'slip'])

function Hero({ stop, prev, pl }: { stop: Stop; prev: Stop | null; pl: Placement }) {
  const g = useRef<THREE.Group>(null)
  const a = useRef<THREE.Group>(null)
  const b = useRef<THREE.Group>(null)
  // a stop that travels (the briefing card: dock to bay) carries its hero the whole way and does not morph from the last stop
  const travel = stop.travel
  const pv = travel ? null : prev
  const from = useMemo(() => (travel ? spotOf(travel.from, pl) : pv ? spotOf(pv.set, pl) : spotOf(stop.set, pl)), [pv, travel, stop, pl])
  const to = useMemo(() => spotOf(travel ? travel.to : stop.set, pl), [travel, stop, pl])
  const same = !pv || pv.hero === stop.hero
  const full = stop.kind === 'courier' || !!travel // the courier and the card go the whole way
  useFrame(({ clock }) => {
    if (!g.current) return
    const e = travel ? smooth(wbClock.u / 0.9) : pv ? smooth(wbClock.u / (full ? 1 : 0.35)) : 1
    const p = lerp3(from, to, e)
    const bob = e >= 1 ? Math.sin(clock.getElapsedTime() * 2.2) * 0.05 : 0
    g.current.position.set(p[0], p[1] + Math.sin(Math.PI * e) * (full ? 0.5 : 1.3) + bob, p[2])
    // a flat card or post-it sways instead of spinning, so it is never seen edge-on
    g.current.rotation.y = FLAT.has(stop.hero) ? Math.sin(clock.getElapsedTime() * 0.9) * 0.4 : clock.getElapsedTime() * 0.6
    const k = same ? 1 : e
    if (b.current) b.current.scale.setScalar(Math.max(0.001, k))
    if (a.current) a.current.scale.setScalar(Math.max(0.001, same ? 0.001 : 1 - e))
  })
  if (stop.hero === 'none') return null
  return (
    <group ref={g}>
      <group ref={b}>
        <HeroMesh form={stop.hero} />
        {travel && stop.heroLabel && <Tag position={[0, 1.15, 0]}><div className="wbtag blue"><HeroLine h={stop.heroLabel} /></div></Tag>}
      </group>
      {pv && !same && <group ref={a}><HeroMesh form={pv.hero} /></group>}
    </group>
  )
}

// ---------- the dock's job cards ----------

const OUTCOME_COLOR = { ok: '#16A34A', skipped: '#9CA3AF', failed: '#DC2626', timeout: '#DC2626', dropped: '#DC2626', pending: '#F59E0B', unknown: '#9CA3AF' } as const

function JobCards({ stop }: { stop: Stop }) {
  const cards = stop.cards ?? []
  const sync = cards.filter((c) => c.mode === 'sync')
  const async = cards.filter((c) => c.mode === 'async')
  const place = (mode: 'sync' | 'async', i: number): Vec3 => [-13.5 + i * 1.25, mode === 'sync' ? 2.3 : 3.5, 1.7]
  return (
    <group>
      {sync.map((c, i) => <Card key={c.span} c={c} at={place('sync', i)} />)}
      {async.map((c, i) => <Card key={c.span} c={c} at={place('async', i)} />)}
      <Tag position={[-14.9, 2.3, 1.7]}><div className="wbtag dim"><b>window</b><i>sync, one by one</i></div></Tag>
      {async.length > 0 && <Tag position={[-14.9, 3.5, 1.7]}><div className="wbtag dim"><b>back room</b><i>async, all at once</i></div></Tag>}
    </group>
  )
}

function Card({ c, at }: { c: NonNullable<Stop['cards']>[number]; at: Vec3 }) {
  const m = useRef<THREE.MeshStandardMaterial>(null)
  const g = useRef<THREE.Group>(null)
  const broke = c.status === 'skipped' && !!c.reason && /missing|fail|error|timeout|denied/i.test(c.reason)
  const color = broke ? OUTCOME_COLOR.failed : (OUTCOME_COLOR[c.status] ?? '#9CA3AF')
  useFrame(({ clock }) => {
    if (!m.current || !g.current) return
    const t = wbClock.t
    const live = t >= c.t0 && t <= c.t1
    const done = t > c.t1
    const lit = live || done
    m.current.emissiveIntensity = live ? 0.7 + Math.sin(clock.getElapsedTime() * 9) * 0.25 : done ? 0.18 : 0
    m.current.opacity = lit ? 1 : 0.4
    g.current.position.y = at[1] + (live ? 0.12 : 0)
  })
  return (
    <group ref={g} position={at}>
      <mesh castShadow>
        <boxGeometry args={[0.86, 0.5, 0.05]} />
        <meshStandardMaterial ref={m} color={color} emissive={color} emissiveIntensity={0} transparent opacity={0.4} roughness={0.7} />
      </mesh>
      {(!isPortrait() || broke || c.status === 'failed' || c.status === 'timeout') && <Tag position={[0, -0.42, 0.1]}>
        <Label real={c.handler} tone={broke || c.status === 'failed' || c.status === 'timeout' ? 'red' : c.status === 'skipped' ? 'dim' : undefined} place={c.status === 'skipped' ? `skipped${c.reason ? ': ' + c.reason : ''}` : fmtMs(c.t1 - c.t0)} />
      </Tag>}
    </group>
  )
}

// ---------- fan-out: copies flying from the belt to each reader ----------

interface Target { component: string; set: string; observed: boolean; outcome: string; t: number | null; names: string[]; n: number }

/** The readers a stop's post-its fly to: one per component, the seen ones first, at most nine. */
function fanTargets(stop: Stop, pl: Placement, wbk: Waybill): Target[] {
  const by = new Map<string, Target>()
  for (const f of stop.fanout ?? []) {
    for (const c of f.consumers) {
      const key = c.component
      const t = by.get(key) ?? { component: key, set: pl.setOf[key] ?? 'dock', observed: false, outcome: c.outcome, t: c.t ?? null, names: [wbk.components[key]?.name ?? key], n: 0 }
      t.n++
      if (c.evidence === 'observed') { t.observed = true; t.outcome = c.outcome; t.t = c.t ?? t.t }
      by.set(key, t)
    }
  }
  // readers that were seen come first, so the nine that fit are the ones that matter
  return [...by.values()].sort((a, b) => Number(b.observed) - Number(a.observed)).slice(0, 9)
}

const TRAIL = 5

/** One copy of the post-it flying to a reader: big enough to follow (about 1 unit), with a fading trail behind it. */
function Copy({ tg, at, i, n, label }: { tg: Target; at: Vec3; i: number; n: number; label: boolean }) {
  const m = useRef<THREE.Mesh>(null)
  const trail = useRef<(THREE.Mesh | null)[]>([])
  const start = 0.18 + (0.5 * i) / Math.max(1, n)
  const dur = 0.24
  const landed = useReached(start + dur * 0.9)
  // a copy that really reached its reader (seen, not inferred) is a visit at that reader's asset
  const sent = useRef(false)
  useEffect(() => {
    if (!landed) { sent.current = false; return }
    if (sent.current || !tg.observed) return
    sent.current = true
    const a = assetFor(tg.component)
    if (a) emitVisit(a.station ? `station:${a.station}` : `id:${a.id}`, { kind: 'post', look: 'copy', source: 'waybill', from: at, tag: tg.names.join(' · ') })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [landed])
  useFrame(() => {
    if (!m.current) return
    const place = (mesh: THREE.Mesh, e: number, k: number) => {
      const p = lerp3(BELT_LOAD, at, e)
      mesh.position.set(p[0], p[1] + Math.sin(Math.PI * e) * 1.8, p[2])
      mesh.scale.setScalar(k)
    }
    const e = smooth((wbClock.u - start) / dur)
    m.current.visible = wbClock.u >= start
    place(m.current, e, e >= 1 ? 0.85 : 1)
    trail.current.forEach((t, j) => {
      if (!t) return
      const et = smooth((wbClock.u - start - (j + 1) * 0.012) / dur)
      t.visible = wbClock.u >= start + (j + 1) * 0.012 && et < 1 && et > 0
      place(t, et, 0.85 - j * 0.12)
    })
  })
  const col = tg.observed ? C.post : '#E7DDB8'
  return (
    <>
      <mesh ref={m} castShadow visible={false}>
        <boxGeometry args={[1, 1, 0.07]} />
        <meshStandardMaterial color={col} emissive={col} emissiveIntensity={tg.observed ? 0.25 : 0} transparent opacity={tg.observed ? 1 : 0.4} depthWrite={tg.observed} />
      </mesh>
      {Array.from({ length: TRAIL }, (_, j) => (
        <mesh key={j} ref={(el) => { trail.current[j] = el }} visible={false}>
          <boxGeometry args={[1, 1, 0.04]} />
          <meshStandardMaterial color={col} transparent opacity={(tg.observed ? 0.32 : 0.14) * (1 - j / TRAIL)} depthWrite={false} />
        </mesh>
      ))}
      {landed && label && (
        <Tag position={add(at, [0, 0.95, 0])}>
          <Label real={tg.names.join(' · ')} tone={tg.observed ? undefined : 'dim'} place={`${tg.observed ? 'seen' : 'inferred'} · ${atWords(tg.outcome, tg.t)}${tg.n > 1 ? ` ×${tg.n}` : ''}`} />
        </Tag>
      )}
    </>
  )
}

function FanOut({ stop, pl }: { stop: Stop; pl: Placement }) {
  const wbk = useWb((s) => s.waybill)!
  const targets = useMemo(() => fanTargets(stop, pl, wbk), [stop, pl, wbk])
  const phone = isPortrait()
  // readers that share a spot fan out a little so their copies do not stack
  const seen = new Map<string, number>()
  return (
    <group>
      {targets.map((tg, i) => {
        const k = seen.get(tg.set) ?? 0
        seen.set(tg.set, k + 1)
        const at = add(spotOf(tg.set, pl), [k * 1.1, 0, k * 0.8])
        return <Copy key={tg.component} tg={tg} at={at} i={i} n={targets.length} label={!phone || i < 2} />
      })}
      {(stop.fanout?.length ?? 0) === 1 && stop.fanout![0].seq !== null && (
        <Tag position={add(BELT_LOAD, [0, 1.2, 0])}>
          <div className="wbtag blue"><b>belt #{stop.fanout![0].seq}</b><i>seq</i></div>
        </Tag>
      )}
    </group>
  )
}

// ---------- waiting, failures, kiosks ----------

function WaitRing({ at, ms, ticking }: { at: Vec3; ms: number; ticking: boolean }) {
  const r = useRef<THREE.Mesh>(null)
  const n = useRef<HTMLSpanElement>(null)
  useFrame(({ clock }) => {
    if (r.current) r.current.rotation.z = -clock.getElapsedTime() * 2.4
    // the count only runs while the stop plays; paused (or stepped to), it shows the number the caption states
    if (n.current) n.current.textContent = fmtMs(useWb.getState().playing ? ms * Math.min(1, wbClock.u / 0.9) : ms)
  })
  return (
    <group position={at}>
      <mesh ref={r} rotation={[Math.PI / 2, 0, 0]}>
        <torusGeometry args={[0.7, 0.05, 8, 44, Math.PI * 1.55]} />
        <meshStandardMaterial color="#F59E0B" emissive="#F59E0B" emissiveIntensity={0.9} />
      </mesh>
      {ticking && (
        <Tag position={[0, 0.95, 0]}>
          <div className="wbtag amber"><b>waiting <span ref={n}>{fmtMs(ms)}</span></b><i>the prompt is held here</i></div>
        </Tag>
      )}
    </group>
  )
}

/** Three dots orbiting the hero: the model is thinking. */
function Thinking({ at }: { at: Vec3 }) {
  const g = useRef<THREE.Group>(null)
  useFrame(({ clock }) => { if (g.current) g.current.rotation.y = clock.getElapsedTime() * 3.2 })
  return (
    <group position={add(at, [0, 0.1, 0])}>
      <group ref={g}>
        {[0, 1, 2].map((i) => (
          <mesh key={i} position={[Math.cos((i * Math.PI * 2) / 3) * 0.75, 0.55 + i * 0.06, Math.sin((i * Math.PI * 2) / 3) * 0.75]}>
            <sphereGeometry args={[0.13, 14, 10]} />
            <meshStandardMaterial color="#38BDF8" emissive="#38BDF8" emissiveIntensity={0.9} />
          </mesh>
        ))}
      </group>
    </group>
  )
}

const HELPER_COLORS = ['#2563EB', '#16A34A', '#D97706', '#9333EA', '#DC2626', '#0891B2', '#CA8A04', '#DB2777']

/** One figure per subagent, popping in one after another in front of the launching tool's bay. */
function Helpers({ stop, pl }: { stop: Stop; pl: Placement }) {
  const n = Math.min(stop.helpers ?? 1, 8)
  const at = spotOf(stop.set, pl)
  return (
    <group>
      {Array.from({ length: n }, (_, i) => <Helper key={i} i={i} n={n} at={[at[0] + 2.2 + (i % 4) * 0.9, 0, at[2] + 0.2 + Math.floor(i / 4) * 0.8]} />)}
      {(stop.helpers ?? 1) > n && <Tag position={add(at, [3.2, 1.7, 1.2])}><div className="wbtag dim"><b>+{(stop.helpers ?? 1) - n} more</b></div></Tag>}
    </group>
  )
}

function Helper({ i, n, at }: { i: number; n: number; at: Vec3 }) {
  const g = useRef<THREE.Group>(null)
  useFrame(() => { if (g.current) g.current.scale.setScalar(Math.max(0.001, smooth((wbClock.u * 1.6 - (0.5 * i) / Math.max(1, n)) / 0.2))) })
  return <group ref={g} position={at}><Figure color={HELPER_COLORS[i % HELPER_COLORS.length]} accent="#F5F0E6" height={0.9} speaking /></group>
}

/** Names the tool call running right now ('Bash · 12 of 34'), stepping with the playhead. */
function ToolTicker({ stop, at }: { stop: Stop; at: Vec3 }) {
  const el = useRef<HTMLSpanElement>(null)
  const sub = useRef<HTMLElement>(null)
  const runs = stop.toolRuns ?? []
  useFrame(() => {
    if (!el.current || !runs.length) return
    const t = wbClock.t
    let k = -1
    for (let i = 0; i < runs.length; i++) if (runs[i].t0 <= t) k = i
    const r = runs[Math.max(0, k)]
    el.current.textContent = `${r.name} · ${Math.max(0, k) + 1} of ${runs.length}`
    if (sub.current) sub.current.textContent = k >= 0 && t <= r.t1 ? `running, ${fmtMs(r.t1 - r.t0)}` : k < 0 ? 'about to start' : 'done, the model reads the result'
  })
  if (!runs.length) return null
  return (
    <Tag position={add(at, [0, -0.75, 0])}>
      <div className="wbtag amber"><b><span ref={el} /></b><i ref={sub} /></div>
    </Tag>
  )
}

function Marker({ at, text, sub, amber, info }: { at: Vec3; text: string; sub?: string; amber?: boolean; info?: boolean }) {
  const m = useRef<THREE.Mesh>(null)
  useFrame(({ clock }) => { if (m.current) { m.current.rotation.y = clock.getElapsedTime() * 1.6; m.current.position.y = Math.sin(clock.getElapsedTime() * 3) * 0.08 } })
  const col = info ? '#2563EB' : amber ? '#F59E0B' : '#DC2626'
  return (
    <group position={at}>
      <mesh ref={m}>
        <octahedronGeometry args={[0.24]} />
        <meshStandardMaterial color={col} emissive={col} emissiveIntensity={0.8} />
      </mesh>
      <Tag position={[0, 0.55, 0]}><Label real={text} tone={info ? 'blue' : amber ? 'amber' : 'red'} place={sub} /></Tag>
    </group>
  )
}

function KioskProp({ k, active, always }: { k: Kiosk; active: boolean; always: boolean }) {
  const lamp = useRef<THREE.MeshStandardMaterial>(null)
  useFrame(({ clock }) => { if (lamp.current) lamp.current.emissiveIntensity = active ? 1.1 + Math.sin(clock.getElapsedTime() * 6) * 0.35 : 0.05 })
  // a kiosk with its own asset (src/assets/<id>) is drawn by that body instead of the generic box, once the body is in
  const asset = assetFor(k.id)
  const own = asset && !asset.station ? asset : null
  const live = useLive((s) => !!own && (s.ids[own.id] ?? 0) > 0)
  const height = own ? own.manifest.height * own.manifest.scale : 1.4
  return (
    <group position={[k.at[0], 0, k.at[2]]}>
      {own && <Suspense fallback={null}><AssetBody entry={own} at={[0, 0, 0]} rotY={own.anchor?.rotY ?? 0} ambient /></Suspense>}
      {!live && (
        <>
          <mesh position={[0, 0.5, 0]} castShadow><boxGeometry args={[0.7, 1.0, 0.5]} /><meshStandardMaterial color={C.control} roughness={0.7} /></mesh>
          <mesh position={[0, 1.12, 0.05]} rotation={[-0.35, 0, 0]} castShadow><boxGeometry args={[0.74, 0.46, 0.06]} /><meshStandardMaterial color="#0F172A" roughness={0.4} /></mesh>
          <mesh position={[0, 1.38, 0.05]}><sphereGeometry args={[0.1, 14, 10]} /><meshStandardMaterial ref={lamp} color="#FBBF24" emissive="#F59E0B" emissiveIntensity={0.05} /></mesh>
        </>
      )}
      {(always || active) && <Tag position={[0, live ? height + 0.45 : 1.9, 0]}><Label real={k.id} tone={active ? undefined : 'dim'} place={active ? undefined : 'kiosk'} /></Tag>}
    </group>
  )
}

// ---------- the layer ----------

function StopLayer({ stop, prev, pl }: { stop: Stop; prev: Stop | null; pl: Placement }) {
  const wbk = useWb((s) => s.waybill)!
  const phone = isPortrait()
  const bayAt: Vec3 = [BAY_X + 1.5, 2.55, BAY_Z[pl.bay] ?? 0]
  const heroSet = stop.travel ? stop.travel.to : stop.set
  const heroAt = spotOf(heroSet, pl)
  const hero = stop.hero === 'none' ? undefined : stop.heroLabel ?? { real: stop.title.length > 34 ? stop.title.slice(0, 32) + '…' : stop.title }
  // a post-it copy lands at its reader and names it there: that reader's station tag would be a second label on the same spot
  const fanSets = useMemo(() => new Set(stop.kind === 'end' ? [] : fanTargets(stop, pl, wbk).map((t) => t.set)), [stop, pl, wbk])
  // station tags: one per station, one name per tag (the others become '+n'), the hero's line merged into its own station's tag
  const tags = useMemo(() => {
    const by = new Map<string, string[]>()
    for (const c of stop.components) {
      const s = pl.setOf[c]
      if (!s || s.startsWith('kiosk:')) continue
      const name = wbk.components[c]?.name ?? c
      const list = by.get(s) ?? by.set(s, []).get(s)!
      if (!list.includes(name)) list.push(name)
    }
    if (stop.travel) { for (const e of [stop.travel.from, stop.travel.to]) if (!by.has(e)) by.set(e, []) }
    else if (hero && !by.has(stop.set)) by.set(stop.set, [])
    const all = [...by.entries()].filter(([set]) => !fanSets.has(set) || set === heroSet)
    // the hero's own station first, then the rest; a phone shows the hero plus one
    all.sort(([a], [b]) => Number(b === heroSet) - Number(a === heroSet))
    return all.slice(0, phone ? 2 : 6)
  }, [stop, pl, wbk, fanSets, hero, heroSet, phone])
  const cardSpans = new Set(stop.cards?.map((c) => c.span))
  const problems = stop.kind === 'end' ? [] : stop.problems.filter((p) => !cardSpans.has(p))
  const spanBy = useMemo(() => new Map(wbk.spans.map((s) => [s.id, s])), [wbk])
  return (
    <>
      <Hero stop={stop} prev={prev} pl={pl} />
      {stop.cards && <JobCards stop={stop} />}
      {stop.fanout && stop.fanout.some((f) => f.consumers.length) && <FanOut stop={stop} pl={pl} />}
      {stop.waited && stop.waitedMs > 0 && (
        <>
          <WaitRing at={bayAt} ms={stop.waitedMs} ticking />
          {stop.set !== 'bays' && <WaitRing at={add(heroAt, [0, 0.8, 0])} ms={stop.waitedMs} ticking={false} />}
        </>
      )}
      {stop.kind === 'courier' && <Walker pl={pl} />}
      {stop.kind === 'llm' && <Thinking at={heroAt} />}
      {stop.kind === 'crew' && <Helpers stop={stop} pl={pl} />}
      {(stop.kind === 'loop' || stop.kind === 'crew') && <ToolTicker stop={stop} at={heroAt} />}
      {tags.map(([set, names]) => {
        const here = hero && !stop.travel && set === heroSet
        const place = placeName(set, pl) + (names.length > 1 ? ` · +${names.length - 1} more` : '')
        return (
          <Tag key={set} position={add(spotOf(set, pl), [0, set === 'bays' ? 1.4 : here && stop.hero !== 'postit' && stop.hero !== 'slip' ? 1.55 : 0.95, 0])}>
            {names.length ? <Label real={names[0]} place={place}>{here && <HeroLine h={hero} />}</Label> : here ? <Label real={hero.real} place={hero.sub ?? placeName(set, pl)} /> : <Label real={placeName(set, pl)} tone="dim" />}
          </Tag>
        )
      })}
      {problems.map((p, i) => {
        const sp = spanBy.get(p.replace(/^evt:/, ''))
        const f = wbk.findings.find((x) => x.evidence.includes(p) || x.evidence.includes(p.replace(/^evt:/, '')))
        const comp = f?.component ?? sp?.component ?? stop.components[0]
        const at = add(spotOf(pl.setOf[comp] ?? stop.set, pl), [i * 0.8 - 0.4, 2.3 + i * 0.5, 1])
        const text = f ? (f.title.length > 44 ? f.title.slice(0, 42) + '…' : f.title) : (sp?.name ?? 'problem')
        return <Marker key={p} at={at} text={text} sub={f ? f.severity : sp ? (sp.reason ?? sp.status) : undefined} info={f?.severity === 'info'} amber={f?.severity === 'warn'} />
      })}
      {stop.kind === 'end' && <EndMarkers pl={pl} />}
    </>
  )
}

function Walker({ pl }: { pl: Placement }) {
  const g = useRef<THREE.Group>(null)
  const a = spotOf('bays', pl), b = spotOf('courier', pl)
  useFrame(() => { if (g.current) { const p = lerp3(a, b, smooth(wbClock.u)); g.current.position.set(p[0] + 0.7, 0, p[2] + 0.5) } })
  return <group ref={g}><Figure color="#2563EB" accent="#DBEAFE" height={0.9} speaking={false} /></group>
}

function EndMarkers({ pl }: { pl: Placement }) {
  const w = useWb((s) => s.waybill)!
  const rows = useMemo(() => {
    const out: { key: string; at: Vec3; text: string; sub: string; amber: boolean }[] = []
    // a ladder: each tag stays over its own station but sits one rung higher than the one before, so none overprints another
    const spot = (comp: string) => {
      const set = pl.setOf[comp] ?? 'dock'
      return add(spotOf(set, pl), [0, 1.2 + out.length * 2.5, 0.8])
    }
    // broken first, then warnings, then notes; the long tail stays in the card
    const order = { broken: 0, warn: 1, info: 2 } as const
    const finds = [...w.findings].sort((a, b) => order[a.severity] - order[b.severity]).filter((f) => f.severity !== 'info').slice(0, 3)
    finds.forEach((f, i) => out.push({ key: `f${i}`, at: spot(f.component), text: f.title.length > 42 ? f.title.slice(0, 40) + '…' : f.title, sub: f.severity, amber: f.severity !== 'broken' }))
    // at most three gap tags in 3D, spread over three different stations when they can be; the end card lists the rest
    const stations = new Set<string>()
    const spread = w.gaps.filter((g) => { const st = pl.setOf[g.component] ?? 'dock'; if (stations.has(st)) return false; stations.add(st); return true })
    const gaps = [...spread, ...w.gaps.filter((g) => !spread.includes(g))].slice(0, 3)
    gaps.forEach((g, i) => out.push({ key: `g${i}`, at: spot(g.component), text: g.what.length > 42 ? g.what.slice(0, 40) + '…' : g.what, sub: w.gaps.length > 3 && i === 2 ? `gap · +${w.gaps.length - 3} more in the card` : 'gap', amber: true }))
    return out
  }, [w, pl])
  return <>{rows.map((r) => <Marker key={r.key} at={r.at} text={r.text} sub={r.sub} amber={r.amber} />)}</>
}

export function WaybillWorld() {
  const dir = useWb((s) => s.dir)
  const si = useWb((s) => s.stop)
  if (!dir) return null
  const stop = dir.stops[si]
  const prev = si > 0 ? dir.stops[si - 1] : null
  const pl = dir.placement
  const always = pl.kiosks.length <= 12
  return (
    <>
      <Driver />
      {pl.kiosks.map((k) => <KioskProp key={k.id} k={k} always={always} active={!!stop && stop.components.some((c) => pl.setOf[c] === `kiosk:${k.id}`)} />)}
      {stop && <StopLayer key={stop.id} stop={stop} prev={prev} pl={pl} />}
    </>
  )
}
