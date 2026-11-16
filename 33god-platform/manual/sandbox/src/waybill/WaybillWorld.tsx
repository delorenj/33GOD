// The 3D layer of the waybill player. A PURE function of the playhead: the driver below advances one
// number (wbClock.u, 0..1 through the current stop) and everything else reads it. No sim later().
import { useFrame } from '@react-three/fiber'
import { useMemo, useRef, useState, type ReactNode } from 'react'
import * as THREE from 'three'
import type { Vec3 } from '../content'
import { BAY_X, BAY_Z } from '../sim/layout'
import { Figure } from '../tour/TourWorld'
import { C } from '../world/Props'
import { Tag } from '../world/Tag'
import type { HeroForm, Stop } from './director'
import { placeName, spotOf, type Kiosk, type Placement } from './stations'
import { stopHold, useWb, wb, wbClock } from './state'
import { fmtMs } from './types'

const BELT_LOAD: Vec3 = [0, 1.25, 0.82]
const smooth = (x: number) => { const k = Math.max(0, Math.min(1, x)); return k * k * (3 - 2 * k) }
const lerp3 = (a: Vec3, b: Vec3, e: number): Vec3 => [a[0] + (b[0] - a[0]) * e, a[1] + (b[1] - a[1]) * e, a[2] + (b[2] - a[2]) * e]
const add = (a: Vec3, d: Vec3): Vec3 => [a[0] + d[0], a[1] + d[1], a[2] + d[2]]

/** The one clock: advances the playhead, hands over to the next stop, keeps the recording-time cursor. */
function Driver() {
  useFrame((_, dt) => {
    const s = useWb.getState()
    const st = s.dir?.stops[s.stop]
    if (!s.dir || !st) return
    if (s.playing && st.kind !== 'end') {
      wbClock.u += (Math.min(dt, 0.1) * 1000 * s.rate) / stopHold(st)
      if (wbClock.u >= 1) {
        wbClock.u = 1
        if (s.stop < s.dir.stops.length - 1) wb.next()
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

// ---------- the hero object ----------

function HeroMesh({ form }: { form: HeroForm }) {
  switch (form) {
    case 'parcel': return <mesh castShadow><boxGeometry args={[0.5, 0.38, 0.44]} /><meshStandardMaterial color={C.parcel} roughness={0.9} /></mesh>
    case 'postit': return <mesh castShadow><boxGeometry args={[0.5, 0.5, 0.06]} /><meshStandardMaterial color={C.post} /></mesh>
    case 'envelope': return <mesh castShadow><boxGeometry args={[0.58, 0.4, 0.03]} /><meshStandardMaterial color="#D8B07A" /></mesh>
    case 'slip': return <mesh castShadow><boxGeometry args={[0.42, 0.26, 0.02]} /><meshStandardMaterial color="#F5F0E6" /></mesh>
    case 'card':
      return (
        <group>
          <mesh castShadow><boxGeometry args={[0.6, 0.4, 0.03]} /><meshStandardMaterial color="#FFFAF0" /></mesh>
          <mesh position={[0, 0.13, 0.02]}><boxGeometry args={[0.6, 0.08, 0.01]} /><meshStandardMaterial color="#2563EB" /></mesh>
        </group>
      )
    case 'phone':
      return (
        <group>
          <mesh castShadow><boxGeometry args={[0.3, 0.52, 0.05]} /><meshStandardMaterial color="#111827" roughness={0.4} /></mesh>
          <mesh position={[0, 0, 0.03]}><boxGeometry args={[0.25, 0.44, 0.005]} /><meshStandardMaterial color="#38BDF8" emissive="#38BDF8" emissiveIntensity={0.5} /></mesh>
        </group>
      )
    case 'toolbox':
      return (
        <group>
          <mesh castShadow><boxGeometry args={[0.56, 0.3, 0.36]} /><meshStandardMaterial color="#B91C1C" roughness={0.6} /></mesh>
          <mesh position={[0, 0.2, 0]}><boxGeometry args={[0.26, 0.06, 0.05]} /><meshStandardMaterial color="#374151" /></mesh>
        </group>
      )
    case 'lamp': return <mesh castShadow><sphereGeometry args={[0.2, 18, 14]} /><meshStandardMaterial color="#FBBF24" emissive="#F59E0B" emissiveIntensity={0.7} /></mesh>
    default: return null
  }
}

function Hero({ stop, prev, pl }: { stop: Stop; prev: Stop | null; pl: Placement }) {
  const g = useRef<THREE.Group>(null)
  const a = useRef<THREE.Group>(null)
  const b = useRef<THREE.Group>(null)
  const from = useMemo(() => (prev ? spotOf(prev.set, pl) : spotOf(stop.set, pl)), [prev, stop, pl])
  const to = useMemo(() => spotOf(stop.set, pl), [stop, pl])
  const same = !prev || prev.hero === stop.hero
  const full = stop.kind === 'courier' // the courier carries it the whole way
  useFrame(({ clock }) => {
    if (!g.current) return
    const e = prev ? smooth(wbClock.u / (full ? 1 : 0.35)) : 1
    const p = lerp3(from, to, e)
    const bob = e >= 1 ? Math.sin(clock.getElapsedTime() * 2.2) * 0.05 : 0
    g.current.position.set(p[0], p[1] + Math.sin(Math.PI * e) * (full ? 0.5 : 1.3) + bob, p[2])
    g.current.rotation.y = clock.getElapsedTime() * 0.6
    const k = same ? 1 : e
    if (b.current) b.current.scale.setScalar(Math.max(0.001, k))
    if (a.current) a.current.scale.setScalar(Math.max(0.001, same ? 0.001 : 1 - e))
  })
  if (stop.hero === 'none') return null
  return (
    <group ref={g}>
      <group ref={b}><HeroMesh form={stop.hero} /></group>
      {prev && !same && <group ref={a}><HeroMesh form={prev.hero} /></group>}
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
      <Tag position={[0, -0.42, 0.1]}>
        <Label real={c.handler} tone={broke || c.status === 'failed' || c.status === 'timeout' ? 'red' : c.status === 'skipped' ? 'dim' : undefined} place={c.status === 'skipped' ? `skipped${c.reason ? ': ' + c.reason : ''}` : fmtMs(c.t1 - c.t0)} />
      </Tag>
    </group>
  )
}

// ---------- fan-out: copies flying from the belt to each reader ----------

interface Target { component: string; set: string; observed: boolean; outcome: string; t: number | null; names: string[]; n: number }

function Copy({ tg, at, i, n, pl }: { tg: Target; at: Vec3; i: number; n: number; pl: Placement }) {
  const m = useRef<THREE.Mesh>(null)
  const start = 0.18 + (0.5 * i) / Math.max(1, n)
  const dur = 0.24
  const landed = useReached(start + dur * 0.9)
  void pl
  useFrame(() => {
    if (!m.current) return
    const e = smooth((wbClock.u - start) / dur)
    m.current.visible = wbClock.u >= start
    const p = lerp3(BELT_LOAD, at, e)
    m.current.position.set(p[0], p[1] + Math.sin(Math.PI * e) * 1.4, p[2])
    m.current.scale.setScalar(e >= 1 ? 0.8 : 1)
  })
  return (
    <>
      <mesh ref={m} castShadow visible={false}>
        <boxGeometry args={[0.36, 0.36, 0.04]} />
        <meshStandardMaterial color={C.post} transparent opacity={tg.observed ? 1 : 0.32} depthWrite={tg.observed} />
      </mesh>
      {landed && (
        <Tag position={add(at, [0, 0.62, 0])}>
          <Label real={tg.names.join(' · ')} tone={tg.observed ? undefined : 'dim'} place={`${tg.observed ? 'seen' : 'inferred'} · ${tg.outcome}${tg.t != null ? ' ' + fmtMs(tg.t) : ''}${tg.n > 1 ? ` ×${tg.n}` : ''}`} />
        </Tag>
      )}
    </>
  )
}

function FanOut({ stop, pl }: { stop: Stop; pl: Placement }) {
  const wbk = useWb((s) => s.waybill)!
  const targets = useMemo(() => {
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
  }, [stop, pl, wbk])
  // readers that share a spot fan out a little so their copies do not stack
  const seen = new Map<string, number>()
  return (
    <group>
      {targets.map((tg, i) => {
        const k = seen.get(tg.set) ?? 0
        seen.set(tg.set, k + 1)
        const at = add(spotOf(tg.set, pl), [k * 0.7, 0, k * 0.5])
        return <Copy key={tg.component} tg={tg} at={at} i={i} n={targets.length} pl={pl} />
      })}
      {(stop.fanout?.length ?? 0) === 1 && stop.fanout![0].seq !== null && (
        <Tag position={add(BELT_LOAD, [0, 0.9, 0])}>
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
    if (n.current) n.current.textContent = fmtMs(ms * Math.min(1, wbClock.u / 0.9))
  })
  return (
    <group position={at}>
      <mesh ref={r} rotation={[Math.PI / 2, 0, 0]}>
        <torusGeometry args={[0.7, 0.05, 8, 44, Math.PI * 1.55]} />
        <meshStandardMaterial color="#F59E0B" emissive="#F59E0B" emissiveIntensity={0.9} />
      </mesh>
      {ticking && (
        <Tag position={[0, 0.95, 0]}>
          <div className="wbtag amber"><b>waiting <span ref={n}>0 ms</span></b><i>the prompt is held here</i></div>
        </Tag>
      )}
    </group>
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
  return (
    <group position={[k.at[0], 0, k.at[2]]}>
      <mesh position={[0, 0.5, 0]} castShadow><boxGeometry args={[0.7, 1.0, 0.5]} /><meshStandardMaterial color={C.control} roughness={0.7} /></mesh>
      <mesh position={[0, 1.12, 0.05]} rotation={[-0.35, 0, 0]} castShadow><boxGeometry args={[0.74, 0.46, 0.06]} /><meshStandardMaterial color="#0F172A" roughness={0.4} /></mesh>
      <mesh position={[0, 1.38, 0.05]}><sphereGeometry args={[0.1, 14, 10]} /><meshStandardMaterial ref={lamp} color="#FBBF24" emissive="#F59E0B" emissiveIntensity={0.05} /></mesh>
      {(always || active) && <Tag position={[0, 1.9, 0]}><Label real={k.id} tone={active ? undefined : 'dim'} place={active ? undefined : 'kiosk'} /></Tag>}
    </group>
  )
}

// ---------- the layer ----------

function StopLayer({ stop, prev, pl }: { stop: Stop; prev: Stop | null; pl: Placement }) {
  const wbk = useWb((s) => s.waybill)!
  const bayAt: Vec3 = [BAY_X + 1.5, 2.55, BAY_Z[pl.bay] ?? 0]
  const heroAt = spotOf(stop.set, pl)
  // station tags: real names, grouped by where they stand
  const tags = useMemo(() => {
    const by = new Map<string, string[]>()
    for (const c of stop.components) {
      const s = pl.setOf[c]
      if (!s || s.startsWith('kiosk:')) continue
      ;(by.get(s) ?? by.set(s, []).get(s)!).push(wbk.components[c]?.name ?? c)
    }
    return [...by.entries()].slice(0, 6)
  }, [stop, pl, wbk])
  const cardSpans = new Set(stop.cards?.map((c) => c.span))
  const problems = stop.kind === 'end' ? [] : stop.problems.filter((p) => !cardSpans.has(p))
  const spanBy = useMemo(() => new Map(wbk.spans.map((s) => [s.id, s])), [wbk])
  return (
    <>
      <Hero stop={stop} prev={prev} pl={pl} />
      {stop.cards && <JobCards stop={stop} />}
      {stop.fanout && stop.fanout.some((f) => f.consumers.length) && stop.kind !== 'loop' && <FanOut stop={stop} pl={pl} />}
      {stop.kind === 'loop' && stop.fanout && stop.fanout.some((f) => f.consumers.length) && <FanOut stop={stop} pl={pl} />}
      {stop.waited && stop.waitedMs > 0 && (
        <>
          <WaitRing at={bayAt} ms={stop.waitedMs} ticking />
          {stop.set !== 'bays' && <WaitRing at={add(heroAt, [0, 0.8, 0])} ms={stop.waitedMs} ticking={false} />}
        </>
      )}
      {stop.kind === 'courier' && <Walker pl={pl} />}
      {tags.map(([set, names]) => (
        <Tag key={set} position={add(spotOf(set, pl), [0, set === 'bays' ? 1.4 : 0.95, 0])}>
          <Label real={names.join(' · ')} place={placeName(set, pl)} />
        </Tag>
      ))}
      {problems.map((p, i) => {
        const sp = spanBy.get(p.replace(/^evt:/, ''))
        const f = wbk.findings.find((x) => x.evidence.includes(p) || x.evidence.includes(p.replace(/^evt:/, '')))
        const comp = f?.component ?? sp?.component ?? stop.components[0]
        const at = add(spotOf(pl.setOf[comp] ?? stop.set, pl), [i * 0.8 - 0.4, 2.3, 1])
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
    const used = new Map<string, number>()
    const spot = (comp: string) => {
      const set = pl.setOf[comp] ?? 'dock'
      const k = used.get(set) ?? 0
      used.set(set, k + 1)
      return add(spotOf(set, pl), [k * 0.9, 1.4 + k * 0.5, 0.8])
    }
    w.findings.forEach((f, i) => out.push({ key: `f${i}`, at: spot(f.component), text: f.title.length > 42 ? f.title.slice(0, 40) + '…' : f.title, sub: f.severity, amber: f.severity !== 'broken' }))
    w.gaps.forEach((g, i) => out.push({ key: `g${i}`, at: spot(g.component), text: g.what.length > 42 ? g.what.slice(0, 40) + '…' : g.what, sub: 'gap', amber: true }))
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
