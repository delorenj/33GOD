// candybar's Driver (contract section 5). The clock gets two different `post` visits from the floor, and the generic
// Accept -> Work -> Emit cannot tell them apart:
//   - `tick fired` is the heartbeat's own tick (heartbeat/publisher.py): play Strike (the hammer rings the bell, the
//     cuckoo doors open) and hand the post-it to the floor from socket_tick, on the perch.
//   - anything else (the planner's `chore due` copy, a waybill copy) is the dispatcher (dispatcher/worker.py): play
//     Accept -> Work -> Emit, catching the copy at socket_in and sending the envelope out of socket_out.
// It also turns the face's hands from the floor's own clock, as the primitive Clock did. AssetBody hides its own
// item and plays nothing once a Driver exists (it keeps the forge's poses), so this file does all of it.
import { useFrame } from '@react-three/fiber'
import { useEffect, useMemo, useRef, useState } from 'react'
import * as THREE from 'three'
import { hoursNow, useWorld } from '../../sim/store'
import { useWb } from '../../waybill/state'
import { ItemMesh, type ItemLook } from '../../world/Moving'
import { STAGE_ID } from '../forge'
import type { AssetProps } from '../types'
import type { Visit } from '../visits'

const FADE = 0.15
const TICK_RELEASE = 1.4 // seconds into Strike: the post-it has stood on the perch for half a second
const TICK_SHOW = 0.5   // seconds into Strike: the doors are open, the tick shows in the doorway
const INK_AT = 1.0      // seconds into Work: the ram is down on the copy
// Work variant per visit: which runner kind's card comes due, in the chart's (the registry's) proportions
const WORK_CYCLE = ['Work_S', 'Work', 'Work_S', 'Work_H', 'Work_S', 'Work', 'Work_S', 'Work_N', 'Work_S', 'Work'] as const
// half thickness of each look the dispatcher can hold (Moving.tsx sizes), for the ink mark's faces
const HALF: Record<string, number> = { copy: 0.005, post: 0.035, env: 0.015, summary: 0.035 }
type Phase = 'idle' | 'strike' | 'accept' | 'work' | 'emit'
// works: every Work variant once (to fade out); cycle: the variant per visit, in WORK_CYCLE order
type Acts = Record<Phase, THREE.AnimationAction> & { works: THREE.AnimationAction[]; cycle: THREE.AnimationAction[] }
interface Seq { phase: Phase; t: number; visit: Visit | null; released: boolean; from: THREE.Vector3 | null; drift: { t: number; at: THREE.Vector3 } | null }

/** The sim's clock for a visit's cycle (AssetBody's own rule): real time on the forge's stage (where the sim stays
 *  paused), in waybill and in the intro; otherwise paused with the sim and at its speed. */
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

export default function CandybarDriver({ id, scene, actions, sockets, visits }: AssetProps) {
  const item = useRef<THREE.Group>(null)
  const [look, setLook] = useState<ItemLook | null>(null)
  const lookRef = useRef<ItemLook | null>(null)
  const showLook = (l: ItemLook | null) => { if (lookRef.current !== l) { lookRef.current = l; setLook(l) } }
  const seq = useRef<Seq>({ phase: 'idle', t: 0, visit: null, released: false, from: null, drift: null })
  const current = useRef<THREE.AnimationAction | null>(null)
  const ink = useRef<THREE.Group>(null)
  const workN = useRef(0)
  const pendPh = useRef(0)
  const froze = useRef(false)

  const parts = useMemo(() => ({
    hour: scene.getObjectByName('hand_hour') ?? null,
    minute: scene.getObjectByName('hand_minute') ?? null,
    tick: scene.getObjectByName('socket_tick') ?? null,
    pend: scene.getObjectByName('pendulum') ?? null,
  }), [scene])

  const act = useMemo<Acts | null>(() => {
    const a = (n: string) => actions[n] ?? null
    const o = { idle: a('Idle'), strike: a('Strike'), accept: a('Accept'), work: a('Work'), emit: a('Emit') }
    if (!o.idle || !o.strike || !o.accept || !o.work || !o.emit) return null
    for (const r of ['strike', 'accept', 'emit'] as const) { o[r]!.setLoop(THREE.LoopOnce, 1); o[r]!.clampWhenFinished = true }
    const works = WORK_CYCLE.map((n) => a(n) ?? o.work!)
    for (const w of works) w.setLoop(THREE.LoopRepeat, Infinity)
    return { ...(o as Record<Phase, THREE.AnimationAction>), works: [...new Set(works)], cycle: works } as Acts
  }, [actions])

  const play = (next: THREE.AnimationAction, speed: number, fade: number) => {
    if (!act) return
    // fade out whatever runs, including the Idle AssetBody started
    for (const a of [act.idle, act.strike, act.accept, act.emit, ...act.works]) if (a !== next && a.isScheduled()) a.fadeOut(fade)
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
  }, [])

  useFrame((_, rawDt) => {
    // the face shows the floor's time (two warehouse hours per real second at 1x); 8:00 on the forge's stage
    const h = hoursNow()
    if (parts.hour) parts.hour.rotation.set(0, 0, -((h % 12) / 12) * Math.PI * 2)
    if (parts.minute) parts.minute.rotation.set(0, 0, -(h % 1) * Math.PI * 2)

    const it = item.current
    const parent = it?.parent
    const dt = Math.min(rawDt, 0.1)
    const cycle = cycleSpeed(id)
    // the pendulum swings on the floor's own time in every clip (2 s period), so no clip change ever snaps it
    pendPh.current = (pendPh.current + dt * (cycle > 0 ? 1 : 0)) % 2
    if (parts.pend) parts.pend.rotation.set(0, 0, 0.22 * Math.sin(Math.PI * pendPh.current))
    if (!act || !it || !parent || !parts.tick) return
    const s = seq.current

    // the forge posed the body (it stops every action): drop the cycle and leave the pose alone
    if (s.phase !== 'idle' && current.current && !current.current.isScheduled()) {
      if (s.visit && !s.released) s.visit.release?.()
      Object.assign(s, { phase: 'idle', visit: null, released: false, drift: null, from: null })
      current.current = null
      it.visible = false
      showLook(null)
      return
    }

    // AssetBody returns before it sets Idle's time scale when a Driver exists: Idle pauses with the sim here.
    // isRunning() is false once the time scale is 0, so remember who froze it (a forge pose also stops it at 0)
    if (act.idle.isScheduled()) {
      if (cycle === 0 && act.idle.isRunning()) { act.idle.setEffectiveTimeScale(0); froze.current = true }
      else if (cycle > 0 && froze.current) { act.idle.setEffectiveTimeScale(1); froze.current = false }
    }
    const waiting = visits.items.length
    const speed = (r: Phase) => cycle * (r === 'work' ? 1 + 0.75 * Math.min(4, waiting) : 1 + 0.2 * Math.min(4, waiting))
    const dur = (r: Phase) => act[r].getClip().duration
    const fade = FADE / Math.max(1, cycle)
    const begin = (r: Phase) => {
      // each visit's Work is the variant for the runner kind of the card that comes due
      if (r === 'work') act.work = act.cycle[workN.current++ % WORK_CYCLE.length]
      s.phase = r; s.t = 0; play(act[r], speed(r), fade)
    }
    const follow = (sock: THREE.Object3D, fromW?: THREE.Vector3 | null, k = 1) => {
      sock.getWorldPosition(tmpV)
      if (fromW && k < 1) tmpV.lerpVectors(fromW, tmpV, k)
      it.position.copy(parent.worldToLocal(tmpV))
      parent.getWorldQuaternion(tmpQ2).invert()
      it.quaternion.copy(tmpQ2.multiply(sock.getWorldQuaternion(tmpQ)))
      it.scale.setScalar(1)
      it.visible = true
    }
    const letGo = (sock: THREE.Object3D) => {
      s.released = true
      sock.getWorldPosition(tmpV)
      const v = s.visit
      if (v?.release) { v.release([tmpV.x, tmpV.y, tmpV.z]); showLook(null) }
      else s.drift = { t: 0, at: tmpV.clone() }
    }
    const next = () => {
      // the heartbeat does not wait on the dispatcher: a queued tick goes first
      const ti = visits.items.findIndex((q) => q.tag === 'tick fired')
      if (ti > 0) visits.items.unshift(...visits.items.splice(ti, 1))
      const v = visits.take()!
      Object.assign(s, { visit: v, released: false, drift: null, from: v.from ? new THREE.Vector3(...v.from) : null })
      if (v.tag === 'tick fired') { showLook(v.out); begin('strike') }
      else { showLook(v.look); begin('accept') }
    }

    if (s.phase === 'idle' && waiting && cycle > 0) next()
    if (s.phase !== 'idle') {
      act[s.phase].setEffectiveTimeScale(speed(s.phase))
      s.t += dt * speed(s.phase)
      const done = () => {
        s.visit = null
        if (visits.items.length) next()
        else { s.phase = 'idle'; play(act.idle, 1, fade) }
      }
      if (s.phase === 'strike') {
        if (!s.released && s.t >= TICK_RELEASE) letGo(parts.tick)
        if (s.t >= dur('strike')) done()
      } else if (s.phase === 'accept' && s.t >= dur('accept')) begin('work')
      else if (s.phase === 'work' && s.t >= dur('work')) { showLook(s.visit?.out ?? null); begin('emit') }
      else if (s.phase === 'emit') {
        if (!s.released && s.t >= dur('emit') * 0.5) letGo(sockets.out)
        if (s.t >= dur('emit')) done()
      }
    }

    // the ram's mark on the copy, carried with it down the chute
    if (ink.current) {
      const inked = (s.phase === 'work' && s.t >= INK_AT) || s.phase === 'emit'
      ink.current.visible = inked && !!s.visit && !s.released
      const h = (HALF[lookRef.current ?? ''] ?? 0.02) + 0.003
      ink.current.children[0]?.position.set(0, 0, h)
      ink.current.children[1]?.position.set(0, 0, -h)
    }

    // the item: a released one with nowhere to go drifts off and shrinks; otherwise it rides its socket
    if (s.drift) {
      s.drift.t += dt * Math.max(1, cycle)
      const k = Math.min(1, s.drift.t / 0.5)
      FWD.set(0, 0.15, 0.45).applyQuaternion(parent.getWorldQuaternion(tmpQ))
      tmpV.copy(s.drift.at).addScaledVector(FWD, k)
      it.position.copy(parent.worldToLocal(tmpV))
      it.scale.setScalar(Math.max(0.001, 1 - k))
      if (k >= 1) { s.drift = null; it.visible = false; if (s.phase === 'idle') showLook(null) }
      return
    }
    if (s.phase === 'idle' || !s.visit || s.released) { it.visible = false; return }
    if (s.phase === 'strike') {
      // the tick is written inside the tower: it shows once the doors open
      if (s.t < TICK_SHOW) { it.visible = false; return }
      follow(parts.tick)
    } else if (s.phase === 'accept') follow(sockets.in, s.from, Math.min(1, s.t / (dur('accept') * 0.35)))
    else follow(s.phase === 'work' ? sockets.hold : sockets.out)
  })

  return (
    <group ref={item} visible={false}>
      {look && <ItemMesh look={look} />}
      <group ref={ink} visible={false}>
        {[0, 1].map((k) => (
          <mesh key={k}><boxGeometry args={[0.22, 0.12, 0.004]} /><meshStandardMaterial color="#8E1F2E" roughness={0.7} /></mesh>
        ))}
      </group>
    </group>
  )
}
