// <AssetBody>: one component's asset on the floor (contract section 5). It loads the generated glb, loops Idle,
// and plays each visit as Accept -> Work -> Emit with 0.15 s crossfades, the visiting item riding socket_in, then
// socket_hold, then leaving from socket_out and going back to the sim's own flow. A missing or broken glb renders
// nothing, so the primitive prop stays: a bad asset never takes the floor down.
// Loaded lazily (React.lazy in AssetLayer), so a floor with no assets never fetches the glTF loader.
import { useAnimations, useGLTF } from '@react-three/drei'
import { useFrame } from '@react-three/fiber'
import { Component, Suspense, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import * as THREE from 'three'
import { clone as cloneScene } from 'three/examples/jsm/utils/SkeletonUtils.js'
import type { Vec3 } from '../content'
import { useWorld } from '../sim/store'
import { useWb, wbClock } from '../waybill/state'
import { hideProps, markLive } from '../world/hidden'
import { ItemMesh, type ItemLook } from '../world/Moving'
import type { ClipRole } from './contract'
import { markFailed, markReady, registerBody } from './forge'
import type { AssetEntry } from './registry'
import type { AssetProps } from './types'
import { claimStation, useVisits, type Visit } from './visits'

export interface BodyProps {
  entry: AssetEntry
  at: Vec3
  rotY: number
  /** the ambient floor: play this station's sim traffic and hide the props the asset replaces */
  ambient?: boolean
  /** the forge's turntable: real time, no sim */
  stage?: boolean
  /** a DOM label (drei Html) placed above the model once it is in */
  label?: (height: number) => ReactNode
}

const FADE = 0.15
const warned = new Set<string>()
const warnOnce = (id: string, why: string) => {
  if (warned.has(id)) return
  warned.add(id)
  console.warn(`[factory] asset ${id}: ${why}; the primitive stays`)
}

// A cheap HEAD first: a glb that was never built (or failed its build) is the expected fallback, not an error.
const probes = new Map<string, Promise<string | null>>()
function probe(url: string): Promise<string | null> {
  let p = probes.get(url)
  if (!p) {
    p = fetch(url, { method: 'HEAD' })
      .then((r) => (!r.ok ? `HTTP ${r.status}` : /text\/html/.test(r.headers.get('content-type') ?? '') ? 'not built' : null))
      .catch((e) => `fetch failed: ${e}`)
    probes.set(url, p)
  }
  return p
}

class Boundary extends Component<{ id: string; children: ReactNode }, { failed: boolean }> {
  state = { failed: false }
  static getDerivedStateFromError() { return { failed: true } }
  componentDidCatch(e: unknown) {
    const why = e instanceof Error ? e.message : String(e)
    warnOnce(this.props.id, `glb failed to load (${why})`)
    markFailed(this.props.id, why)
  }
  render() { return this.state.failed ? null : this.props.children }
}

export default function AssetBody(props: BodyProps) {
  const { entry } = props
  const [ok, setOk] = useState(false)
  useEffect(() => {
    let live = true
    void probe(entry.url).then((why) => {
      if (!live) return
      if (why) { warnOnce(entry.id, `${entry.url} ${why}`); markFailed(entry.id, `${entry.url} ${why}`) }
      else setOk(true)
    })
    return () => { live = false }
  }, [entry])
  if (!ok) return null
  return (
    <Boundary id={entry.id}>
      <Suspense fallback={null}>
        <Loaded {...props} />
      </Suspense>
    </Boundary>
  )
}

/** How fast the clips run. Idle keeps real time (paused only with the sim); a visit's cycle runs on the sim's clock,
 *  so its hand-back stays in step with the floor at 4x and 16x. */
function scales(stage: boolean): { idle: number; cycle: number } {
  if (stage) return { idle: 1, cycle: 1 }
  const s = useWorld.getState()
  if (s.mode === 'waybill') { const w = useWb.getState(); return { idle: 1, cycle: w.playing ? Math.max(1, w.rate) : 1 } }
  if (s.intro) return { idle: 1, cycle: 1 }
  return s.paused ? { idle: 0, cycle: 0 } : { idle: 1, cycle: s.speed }
}

type Phase = 'idle' | 'accept' | 'work' | 'emit'
interface Seq { phase: Phase; t: number; visit: Visit | null; released: boolean; from: THREE.Vector3 | null; drift: { t: number; at: THREE.Vector3 } | null; pose: { role: ClipRole; t: number } | null }

const tmpV = new THREE.Vector3()
const tmpQ = new THREE.Quaternion()
const tmpQ2 = new THREE.Quaternion()
const FWD = new THREE.Vector3()

function Loaded({ entry, at, rotY, ambient = false, stage = false, label }: BodyProps) {
  const m = entry.manifest
  const gltf = useGLTF(entry.url, false, false)
  // the glb is cached and shared; each body animates its own copy
  const scene = useMemo(() => {
    const s = cloneScene(gltf.scene)
    s.traverse((o) => { if ((o as THREE.Mesh).isMesh) { o.castShadow = true; o.receiveShadow = true } })
    return s
  }, [gltf])
  const sockets = useMemo(() => {
    const get = (n: string) => scene.getObjectByName(n) ?? null
    const s = { in: get(m.sockets.in), hold: get(m.sockets.hold), out: get(m.sockets.out) }
    return s.in && s.hold && s.out ? (s as AssetProps['sockets']) : null
  }, [scene, m])
  const { actions, mixer } = useAnimations(gltf.animations, scene)
  const missing = useMemo(() => [
    ...(['idle', 'accept', 'work', 'emit'] as ClipRole[]).filter((r) => !gltf.animations.some((a) => a.name === m.clips[r])).map((r) => `clip ${m.clips[r]}`),
    ...(sockets ? [] : ['a socket node']),
  ], [gltf, m, sockets])
  const broken = missing.length > 0
  useEffect(() => { if (broken) { warnOnce(entry.id, `glb is missing ${missing.join(', ')}`); markFailed(entry.id, `missing ${missing.join(', ')}`) } }, [broken, missing, entry.id])

  const root = useRef<THREE.Group>(null)
  const item = useRef<THREE.Group>(null)
  const [look, setLook] = useState<ItemLook | null>(null)
  const lookRef = useRef<ItemLook | null>(null)
  const showLook = (l: ItemLook | null) => { if (lookRef.current !== l) { lookRef.current = l; setLook(l) } }
  const station = ambient ? entry.station : null
  const visits = useVisits(entry.id, { station, handles: m.handles })
  const seq = useRef<Seq>({ phase: 'idle', t: 0, visit: null, released: false, from: null, drift: null, pose: null })
  const current = useRef<THREE.AnimationAction | null>(null)
  const drawn = useRef(0)

  const act = useMemo(() => {
    if (broken) return null
    const a = (r: ClipRole) => actions[m.clips[r]] ?? null
    const out = { idle: a('idle'), accept: a('accept'), work: a('work'), emit: a('emit') }
    if (!out.idle || !out.accept || !out.work || !out.emit) return null
    for (const r of ['accept', 'emit'] as const) { out[r]!.setLoop(THREE.LoopOnce, 1); out[r]!.clampWhenFinished = true }
    out.work!.setLoop(THREE.LoopRepeat, Infinity)
    out.idle!.setLoop(THREE.LoopRepeat, Infinity)
    return out as Record<ClipRole, THREE.AnimationAction>
  }, [actions, m, broken])

  const play = (role: ClipRole, speed: number, fade: number) => {
    if (!act) return
    const next = act[role]
    const prev = current.current
    next.reset()
    next.setEffectiveTimeScale(speed)
    next.setEffectiveWeight(1)
    next.play()
    if (prev && prev !== next) prev.crossFadeTo(next, fade, false)
    current.current = next
  }

  // Idle from the first frame; hand back anything still queued when the body goes
  useEffect(() => {
    if (!act) return
    play('idle', 1, 0)
    return () => {
      const s = seq.current
      if (s.visit && !s.released) s.visit.release?.()
      s.visit = null
      current.current = null
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [act])

  // On the ambient floor the body plays its station's traffic and stands in for the props it replaces
  useEffect(() => {
    if (!act || !ambient) return
    const offs = [hideProps(m.replaces), markLive(entry.id)]
    if (station) offs.push(claimStation(station, m.handles))
    return () => offs.forEach((f) => f())
  }, [act, ambient, station, m, entry.id])

  // The forge's handle on this body
  useEffect(() => {
    if (!act || !sockets) return
    let tris = 0
    scene.traverse((o) => {
      const g = (o as THREE.Mesh).isMesh ? (o as THREE.Mesh).geometry : null
      if (g) tris += (g.index ? g.index.count : g.attributes.position.count) / 3
    })
    const sockNames: string[] = []
    scene.traverse((o) => { if (o.name.startsWith('socket_')) sockNames.push(o.name) })
    return registerBody(entry.id, {
      info: { clips: gltf.animations.map((a) => a.name), sockets: sockNames, tris: Math.round(tris) },
      pose(role, t) {
        const s = seq.current
        if (s.visit && !s.released) s.visit.release?.()
        Object.assign(s, { phase: 'idle', visit: null, released: false, drift: null, from: null, pose: { role, t } })
        mixer.stopAllAction()
        const a = act[role]
        a.reset()
        a.play()
        a.setEffectiveWeight(1)
        a.setEffectiveTimeScale(0)
        a.time = Math.max(0, Math.min(t, a.getClip().duration - 1e-4))
        current.current = a
        mixer.update(0)
        const kind = m.handles.find((h) => h !== 'any') ?? 'post'
        showLook(role === 'idle' ? null : kind === 'parcel' ? 'parcel' : kind === 'env' ? 'env' : kind === 'summary' ? 'summary' : 'post')
      },
      release() {
        const s = seq.current
        if (!s.pose) return
        s.pose = null
        mixer.stopAllAction()
        current.current = null
        play('idle', 1, 0)
        showLook(null)
      },
    })
  }, [act, sockets, scene, gltf, mixer, entry.id, m])

  useFrame((_, rawDt) => {
    if (!act || !sockets || !root.current || !item.current) return
    if (drawn.current < 2 && ++drawn.current === 2) markReady(entry.id)
    const dt = Math.min(rawDt, 0.1)
    const s = seq.current
    const sc = scales(stage)
    const it = item.current
    const parent = root.current
    const follow = (sock: THREE.Object3D, fromW?: THREE.Vector3 | null, k = 1) => {
      sock.getWorldPosition(tmpV)
      if (fromW && k < 1) tmpV.lerpVectors(fromW, tmpV, k)
      it.position.copy(parent.worldToLocal(tmpV))
      parent.getWorldQuaternion(tmpQ2).invert()
      it.quaternion.copy(tmpQ2.multiply(sock.getWorldQuaternion(tmpQ)))
      it.scale.setScalar(1)
      it.visible = true
    }

    if (s.pose) {
      const r = s.pose.role
      if (r === 'idle') it.visible = false
      else follow(r === 'accept' ? sockets.in : r === 'work' ? sockets.hold : sockets.out)
      return
    }
    if (entry.Driver) { it.visible = false; return }

    if (act.idle.isRunning()) act.idle.setEffectiveTimeScale(sc.idle)
    const waiting = visits.items.length
    const speed = (r: Phase) => sc.cycle * (r === 'work' ? 1 + 0.75 * Math.min(4, waiting) : 1 + 0.2 * Math.min(4, waiting))
    const dur = (r: ClipRole) => act[r].getClip().duration
    const fade = FADE / Math.max(1, sc.cycle)
    const begin = (r: Phase) => { s.phase = r; s.t = 0; play(r, speed(r), fade) }

    const next = () => {
      const v = visits.take()!
      Object.assign(s, { visit: v, released: false, drift: null, from: v.from ? new THREE.Vector3(...v.from) : null })
      showLook(v.look)
      begin('accept')
    }
    if (s.phase === 'idle' && waiting && sc.cycle > 0) next()
    if (s.phase !== 'idle') {
      const a = act[s.phase]
      a.setEffectiveTimeScale(speed(s.phase))
      s.t += dt * speed(s.phase)
      if (s.phase === 'accept' && s.t >= dur('accept')) begin('work')
      else if (s.phase === 'work' && s.t >= dur('work')) { showLook(s.visit?.out ?? null); begin('emit') }
      else if (s.phase === 'emit') {
        // the result leaves halfway through Emit; the rest of the clip settles back toward Idle
        if (!s.released && s.t >= dur('emit') * 0.5) {
          s.released = true
          sockets.out.getWorldPosition(tmpV)
          const v = s.visit
          if (v?.release) { v.release([tmpV.x, tmpV.y, tmpV.z]); showLook(null) }
          else s.drift = { t: 0, at: tmpV.clone() }
        }
        if (s.t >= dur('emit')) {
          s.visit = null
          if (visits.items.length) next()
          else { s.phase = 'idle'; play('idle', sc.idle, fade) }
        }
      }
    }

    // the item: caught at socket_in (eased in from where it really came from), held, sent out of socket_out
    if (s.drift) {
      s.drift.t += dt * Math.max(1, sc.cycle)
      const k = Math.min(1, s.drift.t / 0.5)
      FWD.set(0, 0.15, 0.45).applyQuaternion(parent.getWorldQuaternion(tmpQ))
      tmpV.copy(s.drift.at).addScaledVector(FWD, k)
      it.position.copy(parent.worldToLocal(tmpV))
      it.scale.setScalar(Math.max(0.001, 1 - k))
      if (k >= 1) { s.drift = null; it.visible = false; if (s.phase === 'idle') showLook(null) }
      return
    }
    if (s.phase === 'idle' || !s.visit || s.released) { it.visible = false; return }
    if (s.phase === 'accept') follow(sockets.in, s.from, Math.min(1, s.t / (dur('accept') * 0.35)))
    else follow(s.phase === 'work' ? sockets.hold : sockets.out)
  })

  if (broken) return null
  const props: AssetProps | null = act && sockets ? { id: entry.id, manifest: m, gltf, scene, actions, sockets, visits, playhead: wbClock } : null
  const Driver = entry.Driver
  return (
    <group ref={root} position={at} rotation={[0, rotY + m.rotationY, 0]}>
      <group scale={m.scale}>
        <primitive object={scene} />
      </group>
      <group ref={item} visible={false}>{look && <ItemMesh look={look} />}</group>
      {Driver && props && <Suspense fallback={null}><Driver {...props} /></Suspense>}
      {label?.(m.height * m.scale)}
    </group>
  )
}
