// turn-enricher's Driver (contract section 5). The cataloguer station has two members in the cast, and the floor sends
// both of them `post` visits on `station:cataloguer`:
//   - the Candystore enricher's (`enricher`): the sim's `session ended` copy (sim.ts), or a waybill visit tagged for
//     the enricher. This asset draws that desk as the primitive did and never moves it: the copy glides onto the ochre
//     desk's blotter and stays there; after the sim's own 2.6 s the summary is handed back to the floor from the green
//     runner, and the copy goes.
//   - everything else is the turn-enricher (main.py): Accept -> Work -> Emit. Work is one of the two turns the waybills
//     recorded (Work: codex `ls`, one artifact; Work_B: claude README, four artifacts), picked to match a waybill's own
//     turn when it has one, else alternating. The new post-it lies on the pad from the moment the pen starts, and each
//     fact shows on it as the pen finishes that line: the action, then one tick per artifact.
// main.py handles one turn at a time and never hurries, so the cycle runs at the floor's speed, not the queue's.
// AssetBody hides its own item and plays nothing once a Driver exists (it keeps the forge's poses), so this file does
// all of it.
import { useFrame } from '@react-three/fiber'
import { useEffect, useMemo, useRef, useState } from 'react'
import * as THREE from 'three'
import { useWorld } from '../../sim/store'
import { useWb } from '../../waybill/state'
import { ItemMesh, type ItemLook } from '../../world/Moving'
import { STAGE_ID } from '../forge'
import type { AssetProps } from '../types'
import type { Visit } from '../visits'

const FADE = 0.15
const SIDE_GLIDE = 0.5   // seconds: the enricher's copy glides from where its flight ended onto the ochre desk
const SIDE_HOLD = 2.6    // seconds: the sim's own hand-off delay for the summary (sim.ts handOff 2.6)
const COPY_GONE = 0.35   // seconds into Emit: the read copy has faded on the lectern
const PEN_DOWN = 1.98    // seconds into Work: the pen reaches the pad; the new post-it is its top sheet from here
const LINE_1 = 2.13      // seconds into Work: the first line (the action) is written
const LINE_2 = 2.3       // seconds into Work: the second line (the artifacts) is written
// what each baked Work writes, from the waybills it was baked from
const WORKS = [
  { clip: 'Work', action: 0.1, artifacts: 1 },     // codex-ls: action "ls", artifacts ["ls"]
  { clip: 'Work_B', action: 0.34, artifacts: 4 },  // claude-readme: "receives CloudEvents from Dapr pub/sub", 4 artifacts
] as const
// half thickness of each look (Moving.tsx sizes); the sockets are sized for a post-it (0.035)
const HALF: Record<string, number> = { post: 0.035, summary: 0.035, copy: 0.005, env: 0.015, parcel: 0.035 }
type Phase = 'idle' | 'accept' | 'work' | 'emit'
interface Seq { phase: Phase; t: number; visit: Visit | null; released: boolean; from: THREE.Vector3 | null; drift: { t: number; at: THREE.Vector3 } | null; w: number }
interface Side { visit: Visit; t: number; from: THREE.Vector3 | null }

/** A visit for the station's other member, the Candystore enricher (not this component). */
function forEnricher(v: Visit): boolean {
  const tag = (v.tag ?? '').toLowerCase()
  if (tag === 'session ended') return true
  return v.source === 'waybill' && /\benricher\b/.test(tag) && !/turn[- ]enricher/.test(tag)
}

/** The baked Work that matches the loaded waybill's own annotated turn (its artifact count), if it has one. */
function workForWaybill(): number | null {
  const wb = useWb.getState().waybill
  const span = wb?.spans.find((s) => s.component === 'turn-enricher' && typeof s.attrs?.artifacts === 'number')
  if (!span) return null
  const n = span.attrs!.artifacts as number
  let best = 0
  WORKS.forEach((w, i) => { if (Math.abs(w.artifacts - n) < Math.abs(WORKS[best].artifacts - n)) best = i })
  return best
}

/** AssetBody's clock rule: real time on the forge's stage, in waybill and the intro; else paused with the sim. */
function cycleSpeed(id: string): number {
  if (STAGE_ID === id) return 1
  const s = useWorld.getState()
  if (s.mode === 'waybill') { const w = useWb.getState(); return w.playing ? Math.max(1, w.rate) : 1 }
  if (s.intro) return 1
  return s.paused ? 0 : s.speed
}

const tmpV = new THREE.Vector3()
const tmpQ = new THREE.Quaternion()
const tmpQ2 = new THREE.Quaternion()
const FWD = new THREE.Vector3()
const NRM = new THREE.Vector3()

export default function TurnEnricherDriver({ id, scene, actions, sockets, visits }: AssetProps) {
  const item = useRef<THREE.Group>(null)      // the copy being read (in, hold, fading in Emit)
  const outItem = useRef<THREE.Group>(null)   // the new `turn annotated` post-it (end of Work, Emit)
  const sideItem = useRef<THREE.Group>(null)  // the enricher's copy, on the ochre desk
  const facts = useRef<THREE.Group>(null)
  const [look, setLook] = useState<ItemLook | null>(null)
  const [outLook, setOutLook] = useState<ItemLook | null>(null)
  const lookRef = useRef<ItemLook | null>(null)
  const outRef = useRef<ItemLook | null>(null)
  const showLook = (l: ItemLook | null) => { if (lookRef.current !== l) { lookRef.current = l; setLook(l) } }
  const showOut = (l: ItemLook | null) => { if (outRef.current !== l) { outRef.current = l; setOutLook(l) } }
  const seq = useRef<Seq>({ phase: 'idle', t: 0, visit: null, released: false, from: null, drift: null, w: 0 })
  const side = useRef<Side[]>([])
  const current = useRef<THREE.AnimationAction | null>(null)
  const workN = useRef(0)
  const froze = useRef(false)

  const parts = useMemo(() => ({
    enrTray: scene.getObjectByName('socket_enricher') ?? null,
    runner: scene.getObjectByName('socket_runner') ?? null,
  }), [scene])

  const act = useMemo(() => {
    const a = (n: string) => actions[n] ?? null
    const idle = a('Idle'), accept = a('Accept'), emit = a('Emit')
    const works = WORKS.map((w) => a(w.clip) ?? a('Work'))
    if (!idle || !accept || !emit || works.some((w) => !w)) return null
    const ws = works as THREE.AnimationAction[]
    for (const x of [accept, emit, ...ws]) { x.setLoop(THREE.LoopOnce, 1); x.clampWhenFinished = true }
    return { idle, accept, emit, works: ws }
  }, [actions])

  const play = (next: THREE.AnimationAction, speed: number, fade: number) => {
    if (!act) return
    for (const x of new Set([act.idle, act.accept, act.emit, ...act.works])) if (x !== next && x.isScheduled()) x.fadeOut(fade)
    froze.current = false
    next.reset()
    next.setEffectiveTimeScale(speed)
    next.setEffectiveWeight(1)
    next.fadeIn(fade)
    next.play()
    current.current = next
  }

  // hand back whatever is held when the body goes
  useEffect(() => () => {
    const s = seq.current
    if (s.visit && !s.released) s.visit.release?.()
    s.visit = null
    for (const x of side.current.splice(0)) x.visit.release?.()
  }, [])

  useFrame((_, rawDt) => {
    const it = item.current
    const out = outItem.current
    const sd = sideItem.current
    const parent = it?.parent
    if (!act || !it || !out || !sd || !parent) return
    const dt = Math.min(rawDt, 0.1)
    const cycle = cycleSpeed(id)
    const s = seq.current

    /** put g on a socket; a thinner item than a post-it sinks onto the surface the socket rests on */
    const place = (g: THREE.Object3D, sock: THREE.Object3D, l: ItemLook | null, fromW?: THREE.Vector3 | null, k = 1) => {
      sock.getWorldPosition(tmpV)
      if (fromW && k < 1) tmpV.lerpVectors(fromW, tmpV, k)
      parent.getWorldQuaternion(tmpQ2).invert()
      g.quaternion.copy(tmpQ2.multiply(sock.getWorldQuaternion(tmpQ)))
      g.position.copy(parent.worldToLocal(tmpV))
      const sink = 0.035 - (HALF[l ?? 'post'] ?? 0.035)
      if (sink > 0) {
        NRM.set(0, 0, 1).applyQuaternion(g.quaternion)
        if (NRM.y < 0) NRM.negate()
        if (NRM.y > 0.3) g.position.addScaledVector(NRM, -sink)
      }
      g.visible = true
    }

    // the Candystore enricher's traffic: pulled out of the queue, never played through this desk's clips
    for (let i = visits.items.length - 1; i >= 0; i--) {
      const v = visits.items[i]
      if (!forEnricher(v)) continue
      visits.items.splice(i, 1)
      side.current.push({ visit: v, t: 0, from: v.from ? new THREE.Vector3(...v.from) : null })
    }
    for (const x of side.current) x.t += dt * cycle
    const first = side.current[0]
    if (first && parts.enrTray) {
      const k = Math.min(1, first.t / SIDE_GLIDE)
      place(sd, parts.enrTray, 'copy', first.from, k * (2 - k))
    } else sd.visible = false
    for (let i = side.current.length - 1; i >= 0; i--) {
      const x = side.current[i]
      if (x.t < SIDE_HOLD && parts.runner) continue
      side.current.splice(i, 1)
      if (parts.runner) { parts.runner.getWorldPosition(tmpV); x.visit.release?.([tmpV.x, tmpV.y, tmpV.z]) }
      else x.visit.release?.()
    }

    // the forge posed the body (it stops every action): drop the cycle and leave the pose alone
    if (s.phase !== 'idle' && current.current && !current.current.isScheduled()) {
      if (s.visit && !s.released) s.visit.release?.()
      Object.assign(s, { phase: 'idle', visit: null, released: false, drift: null, from: null })
      current.current = null
      it.visible = false
      out.visible = false
      showLook(null)
      showOut(null)
      return
    }

    // AssetBody returns before it sets Idle's time scale when a Driver exists: Idle pauses with the sim here.
    // isRunning() is false once the time scale is 0, so remember who froze it (a forge pose also stops it at 0)
    if (act.idle.isScheduled()) {
      if (cycle === 0 && act.idle.isRunning()) { act.idle.setEffectiveTimeScale(0); froze.current = true }
      else if (cycle > 0 && froze.current) { act.idle.setEffectiveTimeScale(1); froze.current = false }
    }
    const clipOf = (r: Phase) => (r === 'work' ? act.works[s.w] : r === 'idle' ? act.idle : act[r])
    const dur = (r: Phase) => clipOf(r).getClip().duration
    const fade = FADE / Math.max(1, cycle)
    const begin = (r: Phase) => { s.phase = r; s.t = 0; play(clipOf(r), cycle, fade) }
    const next = () => {
      const v = visits.take()!
      const wb = v.source === 'waybill' ? workForWaybill() : null
      const w = wb ?? workN.current++ % WORKS.length
      Object.assign(s, { visit: v, released: false, drift: null, from: v.from ? new THREE.Vector3(...v.from) : null, w })
      showLook(v.look)
      showOut(null)
      begin('accept')
    }

    if (s.phase === 'idle' && visits.items.length && cycle > 0) next()
    if (s.phase !== 'idle') {
      clipOf(s.phase).setEffectiveTimeScale(cycle)
      s.t += dt * cycle
      if (s.phase === 'accept' && s.t >= dur('accept')) begin('work')
      else if (s.phase === 'work' && s.t >= dur('work')) begin('emit')
      else if (s.phase === 'emit') {
        if (!s.released && s.t >= dur('emit') * 0.5) {
          s.released = true
          sockets.out.getWorldPosition(tmpV)
          const v = s.visit
          if (v?.release) { v.release([tmpV.x, tmpV.y, tmpV.z]); showOut(null) }
          else s.drift = { t: 0, at: tmpV.clone() }
        }
        if (s.t >= dur('emit')) {
          s.visit = null
          if (visits.items.length) next()
          else { s.phase = 'idle'; play(act.idle, 1, fade); showLook(null) }
        }
      }
    }

    // the copy: caught in the tray, read on the lectern, faded once the post-it is written
    if (s.phase === 'idle' || !s.visit) it.visible = false
    else if (s.phase === 'accept') {
      const k = Math.min(1, s.t / (dur('accept') * 0.35))
      place(it, sockets.in, lookRef.current, s.from, k * (2 - k))
      it.scale.setScalar(1)
    } else if (s.phase === 'work') { place(it, sockets.hold, lookRef.current); it.scale.setScalar(1) }
    else {
      const k = Math.min(1, s.t / COPY_GONE)
      place(it, sockets.hold, lookRef.current)
      it.scale.setScalar(Math.max(0.001, 1 - k))
      if (k >= 1) it.visible = false
    }

    // the new post-it: the pad's top sheet once the pen comes down, then it rides socket_out until the floor takes it
    const writing = s.phase === 'work' && s.t >= PEN_DOWN
    if ((writing || s.phase === 'emit') && s.visit && !s.released && !outRef.current) showOut(s.visit.out ?? 'post')
    if (s.drift) {
      s.drift.t += dt * Math.max(1, cycle)
      const k = Math.min(1, s.drift.t / 0.5)
      FWD.set(0, 0.15, 0.45).applyQuaternion(parent.getWorldQuaternion(tmpQ))
      tmpV.copy(s.drift.at).addScaledVector(FWD, k)
      out.position.copy(parent.worldToLocal(tmpV))
      out.scale.setScalar(Math.max(0.001, 1 - k))
      if (k >= 1) { s.drift = null; out.visible = false; showOut(null) }
    } else if ((writing || s.phase === 'emit') && s.visit && !s.released) { place(out, sockets.out, outRef.current); out.scale.setScalar(1) }
    else out.visible = false

    // the facts the pen wrote, on both faces: the action (a stroke as long as the phrase), one tick per artifact
    const f = facts.current
    if (f) {
      const spec = WORKS[s.w]
      const t = s.phase === 'emit' ? 99 : s.phase === 'work' ? s.t : -1
      const h = (HALF[outRef.current ?? ''] ?? 0.035) + 0.003
      f.children.forEach((m, i) => {
        const back = i % 2 === 1
        const z = back ? -h : h
        if (i < 2) {
          m.visible = t >= LINE_1
          m.scale.set(spec.action / 0.1, 1, 1)
          m.position.set(-0.17 + spec.action / 2, 0.1, z)
        } else {
          const k = (i - 2) >> 1
          m.visible = t >= LINE_2 && k < spec.artifacts
          m.position.set(-0.15 + k * 0.1, -0.07, z)
        }
      })
    }
  })

  return (
    <>
      <group ref={item} visible={false}>{look && <ItemMesh look={look} />}</group>
      <group ref={outItem} visible={false}>
        {outLook && <ItemMesh look={outLook} />}
        <group ref={facts}>
          {Array.from({ length: 10 }, (_, i) => (
            <mesh key={i}>
              <boxGeometry args={i < 2 ? [0.1, 0.06, 0.004] : [0.07, 0.07, 0.004]} />
              <meshStandardMaterial color={i < 2 ? '#2A2418' : '#55347F'} roughness={0.8} />
            </mesh>
          ))}
        </group>
      </group>
      <group ref={sideItem} visible={false}><ItemMesh look="copy" /></group>
    </>
  )
}
