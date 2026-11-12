import { useFrame, useThree } from '@react-three/fiber'
import { useEffect, useRef } from 'react'
import * as THREE from 'three'
import { overview, stationById, type Vec3 } from '../content'
import { MAP_BOUNDS } from '../domains'
import { MAP_MARGIN, mapPortrait } from '../map/frame'
import { useWorld } from '../sim/store'

// One camera, two ways of looking:
// - free: the warehouse in perspective (fov 42), orbit to look around
// - top: straight down with a very narrow lens from far away, so it reads as orthographic, the whole floor fitted
// Every move between them is a dolly-zoom in "frame space": the target, the view direction, the height of
// the frame at the target and the lens are tweened separately, so nothing jumps when the lens changes.

export const BASE_FOV = 42
const TOP_FOV = 5

interface Pose { target: THREE.Vector3; dir: THREE.Vector3; h: number; fov: number }
type Controls = {
  target: THREE.Vector3
  update: () => void
  addEventListener: (e: string, f: () => void) => void
  removeEventListener: (e: string, f: () => void) => void
}

const rad = (deg: number) => (deg * Math.PI) / 180
const frameH = (dist: number, fov: number) => 2 * dist * Math.tan(rad(fov) / 2)
const distFor = (h: number, fov: number) => h / (2 * Math.tan(rad(fov) / 2))

function poseFromView(v: { pos: Vec3; target: Vec3 }, fov = BASE_FOV): Pose {
  const target = new THREE.Vector3(...v.target)
  const d = new THREE.Vector3(...v.pos).sub(target)
  return { target, dir: d.clone().normalize(), h: frameH(d.length(), fov), fov }
}

/** The whole zoned floor, fitted to the screen. MapOverlay draws in the same frame (map/frame.ts), so they line up. */
export function topPose(w: number, h: number): Pose {
  const portrait = mapPortrait(w, h)
  const W = MAP_BOUNDS.x1 - MAP_BOUNDS.x0 + 2 * MAP_MARGIN
  const D = MAP_BOUNDS.z1 - MAP_BOUNDS.z0 + 2 * MAP_MARGIN
  return {
    target: new THREE.Vector3((MAP_BOUNDS.x0 + MAP_BOUNDS.x1) / 2, 0, (MAP_BOUNDS.z0 + MAP_BOUNDS.z1) / 2),
    // a hair off vertical sets which way is up on screen: north (-z) in landscape, east (+x) in portrait
    dir: (portrait ? new THREE.Vector3(-1e-4, 1, 0) : new THREE.Vector3(0, 1, 1e-4)).normalize(),
    h: portrait ? Math.max(W, D / (w / h)) : Math.max(D, W / (w / h)),
    fov: TOP_FOV,
  }
}

/** A perspective view that looks at a ground point from the front, close enough to read the props. */
export function viewAt(p: THREE.Vector3 | Vec3, frame = 16): { pos: Vec3; target: Vec3 } {
  const [x, , z] = Array.isArray(p) ? p : [p.x, p.y, p.z]
  const dir = new THREE.Vector3(0.35, 0.62, 1).normalize()
  const d = distFor(frame, BASE_FOV)
  return { pos: [x + dir.x * d, 1 + dir.y * d, z + dir.z * d], target: [x, 1, z] }
}

const ease = (t: number) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2)
const lerpLog = (a: number, b: number, t: number) => Math.exp(Math.log(a) + (Math.log(b) - Math.log(a)) * t)

export function CameraRig() {
  const focus = useWorld((s) => s.focus)
  const { camera, controls, size } = useThree() as unknown as { camera: THREE.PerspectiveCamera; controls: Controls | null; size: { width: number; height: number } }
  const anim = useRef<{ t: number; dur: number; from: Pose; to: Pose; top: boolean; openMap: boolean } | null>(null)

  useEffect(() => {
    if (!focus || !controls) return
    const top = focus.id === 'top'
    const to = top
      ? topPose(size.width, size.height)
      : poseFromView(focus.view ?? (focus.id === 'overview' || focus.id === 'custom' ? overview() : stationById[focus.id as keyof typeof stationById].view))
    const d = camera.position.clone().sub(controls.target)
    const from: Pose = { target: controls.target.clone(), dir: d.clone().normalize(), h: frameH(d.length(), camera.fov), fov: camera.fov }
    // leaving the top view: hand the mouse back to orbiting as soon as the camera starts to tilt
    if (!top) useWorld.setState({ cam: 'free' })
    anim.current = { t: 0, dur: top ? 1.25 : 1.5, from, to, top, openMap: !!focus.openMap }
    // focus.nonce is the trigger; size is read once per move
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [focus, controls, camera])

  // when a side panel is open, shift the frame so the station sits in the uncovered part of the screen
  const panelOpen = useWorld((s) => s.station !== null || s.inspect !== null)
  useEffect(() => {
    const { width: w, height: h } = size
    if (!panelOpen) camera.clearViewOffset()
    else if (w <= 720) camera.setViewOffset(w, h, 0, h * 0.2, w, h)
    else camera.setViewOffset(w, h, 100, 0, w, h)
    return () => camera.clearViewOffset()
  }, [panelOpen, size, camera])

  // the top view stays fitted when the window changes shape
  useEffect(() => {
    if (useWorld.getState().cam !== 'top' || anim.current || !controls) return
    const p = topPose(size.width, size.height)
    camera.fov = p.fov
    camera.updateProjectionMatrix()
    camera.position.copy(p.target).addScaledVector(p.dir, distFor(p.h, p.fov))
    controls.target.copy(p.target)
    controls.update()
  }, [size, camera, controls])

  useEffect(() => {
    if (!controls) return
    const cancel = () => { anim.current = null }
    controls.addEventListener('start', cancel)
    return () => controls.removeEventListener('start', cancel)
  }, [controls])

  useFrame((_, dt) => {
    const a = anim.current
    if (!a || !controls) return
    a.t = Math.min(1, a.t + dt / a.dur)
    const e = ease(a.t)
    const target = a.from.target.clone().lerp(a.to.target, e)
    const dir = a.from.dir.clone().lerp(a.to.dir, e).normalize()
    const h = lerpLog(a.from.h, a.to.h, e)
    const fov = lerpLog(a.from.fov, a.to.fov, e)
    camera.fov = fov
    camera.updateProjectionMatrix()
    camera.position.copy(target).addScaledVector(dir, distFor(h, fov))
    controls.target.copy(target)
    controls.update()
    if (a.t >= 1) {
      anim.current = null
      if (a.top) useWorld.setState({ cam: 'top', mapOpen: a.openMap })
    }
  })
  return null
}

/**
 * The mouse wheel no longer nudges the zoom. Scroll up: rise to the top-down view of the whole floor.
 * Scroll down: drop toward whatever is under the cursor (from the top view, or a step closer from anywhere).
 */
export function WheelNav() {
  const { gl, camera, controls } = useThree() as unknown as { gl: THREE.WebGLRenderer; camera: THREE.PerspectiveCamera; controls: Controls | null }
  useEffect(() => {
    const el = gl.domElement
    let acc = 0
    let lock = 0
    const ray = new THREE.Raycaster()
    const ground = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0)
    const groundUnder = (e: WheelEvent) => {
      const r = el.getBoundingClientRect()
      ray.setFromCamera(new THREE.Vector2(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1), camera)
      const p = new THREE.Vector3()
      if (!ray.ray.intersectPlane(ground, p)) return null
      p.x = THREE.MathUtils.clamp(p.x, MAP_BOUNDS.x0, MAP_BOUNDS.x1)
      p.z = THREE.MathUtils.clamp(p.z, MAP_BOUNDS.z0, MAP_BOUNDS.z1)
      return p
    }
    const onWheel = (e: WheelEvent) => {
      e.preventDefault()
      const s = useWorld.getState()
      if (s.intro || s.mode === 'tour') return
      const now = performance.now()
      if (now < lock) return
      acc += e.deltaY
      if (Math.abs(acc) < 40) return // a trackpad sends many tiny deltas: wait for a deliberate flick
      const up = acc < 0
      acc = 0
      lock = now + 900
      if (up) {
        if (s.cam !== 'top') useWorld.setState((st) => ({ station: null, inspect: null, focus: { id: 'top', nonce: (st.focus?.nonce ?? 0) + 1 } }))
        return
      }
      const p = groundUnder(e)
      if (!p) return
      if (s.cam === 'top') {
        useWorld.setState((st) => ({ mapOpen: false, focus: { id: 'custom', nonce: (st.focus?.nonce ?? 0) + 1, view: viewAt(p, 18) } }))
      } else if (controls) {
        // a step closer, drifting toward the cursor
        const t = controls.target.clone().lerp(p.setY(controls.target.y), 0.35)
        const d = camera.position.clone().sub(controls.target)
        const dist = Math.max(5, d.length() * 0.62)
        const pos = t.clone().addScaledVector(d.normalize(), dist)
        useWorld.setState((st) => ({ focus: { id: 'custom', nonce: (st.focus?.nonce ?? 0) + 1, view: { pos: [pos.x, pos.y, pos.z], target: [t.x, t.y, t.z] } } }))
      }
    }
    el.addEventListener('wheel', onWheel, { passive: false })
    return () => el.removeEventListener('wheel', onWheel)
  }, [gl, camera, controls])
  return null
}

/** Fog is tuned for the floor at eye level; push it back when the camera rises so the top view stays clear. */
export function FogFollow() {
  const { scene, camera, controls } = useThree() as unknown as { scene: THREE.Scene; camera: THREE.Camera; controls: Controls | null }
  useFrame(() => {
    const fog = scene.fog as THREE.Fog | null
    if (!fog || !controls) return
    const d = camera.position.distanceTo(controls.target)
    fog.near = Math.max(55, d + 20)
    fog.far = fog.near + 70
  })
  return null
}
