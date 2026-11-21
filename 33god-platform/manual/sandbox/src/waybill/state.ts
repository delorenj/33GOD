// Player state. A SECOND small zustand store (the sandbox store only learns `mode: 'waybill'`), plus a
// mutable per-frame progress value read by the 3D layer and the waterfall without re-rendering React.
import { create } from 'zustand'
import { isPortrait, type Vec3 } from '../content'
import { ui, useWorld } from '../sim/store'
import type { VisitKind } from '../assets/contract'
import { assetFor } from '../assets/registry'
import { emitVisit } from '../assets/visits'
import { direct, type Direction, type Stop } from './director'
import { fanoutView, pairView, spotOf, viewFor } from './stations'
import type { Waybill } from './types'

export type LoadState = { state: 'idle' } | { state: 'loading'; source: string } | { state: 'error'; message: string; source: string; retry?: string }

interface Wb {
  waybill: Waybill | null
  dir: Direction | null
  warnings: string[]
  source: string
  stop: number
  playing: boolean
  rate: number
  /** selected span id or 'evt:<id>' (the inspector) */
  sel: string | null
  ended: boolean
  picker: boolean
  load: LoadState
  prevPaused: boolean
  /** waterfall zoom: fit the whole run, fit the current stop, or log-compress */
  zoom: 'fit' | 'stop' | 'log'
  /** the browser refused to start the narration without a gesture: playback paused, the HUD asks for one tap */
  needsTap: boolean
}

export const useWb = create<Wb>(() => ({
  waybill: null, dir: null, warnings: [], source: '', stop: 0, playing: true, rate: 1, sel: null, ended: false,
  picker: false, load: { state: 'idle' }, prevPaused: false, zoom: 'stop', needsTap: false,
}))

/** Progress through the current stop, 0..1. Written by the driver, read every frame. */
export const wbClock = { u: 0, /** the playhead on the recording's own ms axis */ t: 0 }

/** How long a stop is held on screen at 1x, in ms. Display time, not recorded time. */
export function stopHold(s: Stop): number {
  if (s.kind === 'end') return 0
  const real = Math.max(0, s.t1 - s.t0)
  let ms = 2800 + Math.min(2600, real * 0.35)
  ms += (s.cards?.length ?? 0) * 320
  // readers are grouped by component, so a post-it with 30 inferred readers still holds for a few seconds, not a minute
  // a failure stop can carry dozens of kept notes; only the first few readers fly, so only they add time
  ms += Math.min(s.readers ? s.readers.length : s.fanout?.length ?? 0, s.chapter ? 6 : 99) * 380
  ms += Math.min(8, s.tools?.reduce((n, t) => n + t.count, 0) ?? 0) * 450
  return Math.min(11000, ms)
}

/** Where the camera looks for a stop (the belt's fan-out is framed around its readers). */
export function cameraFor(stop: Stop, dir: Direction): { pos: Vec3; target: Vec3 } {
  const pl = dir.placement
  let base = viewFor(stop.set, pl)
  let view = base.view
  let k = isPortrait() ? (base.portraitK ?? 1.6) : 1
  const consumers = stop.fanout?.flatMap((f) => f.consumers) ?? []
  if (consumers.length && (stop.kind === 'belt' || stop.kind === 'reader')) {
    const fan = fanoutView([...new Set(consumers.map((c) => dir.placement.setOf[c.component] ?? 'dock'))].map((s) => spotOf(s, pl)))
    view = fan
    k = isPortrait() ? 1.25 : 1
  }
  // a stop that travels (the briefing card) frames both ends of the trip, the dock and the bay
  if (stop.travel) { view = pairView([spotOf(stop.travel.from, pl), spotOf(stop.travel.to, pl)]); k = isPortrait() ? 1.2 : 1 }
  let pos = view.pos.map((p, j) => view.target[j] + (p - view.target[j]) * k) as Vec3
  let target = view.target
  // a phone's stop card covers the lower third: slide the whole view down so the hero sits in the upper part
  if (isPortrait()) { pos = [pos[0], pos[1] - 1.4, pos[2]]; target = [target[0], target[1] - 1.4, target[2]] }
  return { pos, target }
}

const KIND_OF: Partial<Record<Stop['hero'], VisitKind>> = { parcel: 'parcel', postit: 'post', envelope: 'env', card: 'env', slip: 'summary' }

/** The playhead enters a stop: every component of it that has an asset gets a visit (a station asset by its station,
 *  a kiosk asset by its id). The readers a post-it fans out to are not visited, only the component the stop is about. */
function visitStop(stop: Stop, dir: Direction) {
  const kind = KIND_OF[stop.hero] ?? 'post'
  const readers = new Set((stop.fanout?.flatMap((f) => f.consumers.map((c) => c.component)) ?? []).filter((c) => dir.placement.setOf[c] !== stop.set))
  const seen = new Set<string>()
  for (const c of stop.components) {
    if (readers.has(c)) continue
    const a = assetFor(c)
    if (!a) continue
    const key = a.station ? `station:${a.station}` : `id:${a.id}`
    if (seen.has(key)) continue
    seen.add(key)
    emitVisit(key, { kind, source: 'waybill', stop: stop.id, tag: stop.title })
  }
}

function fly(stop: Stop, dir: Direction) {
  const v = cameraFor(stop, dir)
  useWorld.setState((s) => ({ focus: { id: 'custom', nonce: (s.focus?.nonce ?? 0) + 1, view: v } }))
}

export const wb = {
  /** Start playing a parsed waybill (from the picker, a drop or ?waybill=). */
  play(w: Waybill, source: string, warnings: string[] = [], startStop = 0) {
    const dir = direct(w)
    const was = useWorld.getState()
    const first = Math.max(0, Math.min(dir.stops.length - 1, startStop))
    wbClock.u = 0
    wbClock.t = dir.stops[first]?.t0 ?? 0
    useWb.setState({
      // the axis follows the active stop (padded), so every stop's bars are readable; 'log' and 'linear' stay as overviews
      // a query's lanes are bucketed over the whole window: fit it
      zoom: dir.query ? 'fit' : 'stop',
      waybill: w, dir, warnings, source, stop: first, playing: true, sel: null, ended: false, picker: false, load: { state: 'idle' }, needsTap: false,
      prevPaused: was.mode === 'waybill' ? useWb.getState().prevPaused : was.paused,
    })
    useWorld.setState({ mode: 'waybill', intro: false, paused: true, station: null, inspect: null, bulb: null, mapOpen: false })
    document.body.classList.add('waybill-on')
    if (dir.stops[first]) { fly(dir.stops[first], dir); visitStop(dir.stops[first], dir) }
  },
  go(i: number) {
    const { dir } = useWb.getState()
    if (!dir) return
    const k = Math.max(0, Math.min(dir.stops.length - 1, i))
    wbClock.u = 0
    wbClock.t = dir.stops[k].t0
    useWb.setState({ stop: k, ended: dir.stops[k].kind === 'end', sel: null })
    fly(dir.stops[k], dir)
    visitStop(dir.stops[k], dir)
  },
  next() { const s = useWb.getState(); if (s.dir && s.stop < s.dir.stops.length - 1) wb.go(s.stop + 1); else useWb.setState({ playing: false }) },
  prev() { const s = useWb.getState(); if (s.stop > 0) wb.go(s.stop - 1) },
  toggle() {
    const s = useWb.getState()
    if (!s.dir) return
    if (s.playing) return useWb.setState({ playing: false })
    if (s.dir.stops[s.stop].kind === 'end') return wb.go(0), useWb.setState({ playing: true })
    useWb.setState({ playing: true })
  },
  replay() { wb.go(0); useWb.setState({ playing: true, ended: false }) },
  setRate(r: number) { useWb.setState({ rate: r }) },
  select(id: string | null) { useWb.setState({ sel: id }) },
  /** Jump to the stop that owns a span or event id, and open the inspector on it. */
  jump(id: string) {
    const { dir } = useWb.getState()
    if (!dir) return
    const i = id.startsWith('evt:') ? dir.stopOfEvent[id.slice(4)] : dir.stopOfSpan[id]
    if (i === undefined) return useWb.setState({ sel: id })
    wb.go(i)
    useWb.setState({ sel: id, playing: false })
  },
  openPicker(open = true) { useWb.setState({ picker: open }) },
  setLoad(load: LoadState) { useWb.setState({ load }) },
  /** Leave the mode: back to the sandbox floor, paused state restored. */
  leave() {
    const { prevPaused } = useWb.getState()
    useWb.setState({ playing: false, ended: false, sel: null })
    useWorld.setState({ mode: 'sandbox', paused: prevPaused })
    document.body.classList.remove('waybill-on')
    ui.overview()
  },
  /** The end card's "Explore the floor": leave, but keep the sim paused off so it comes back alive. */
  explore() { useWb.setState({ prevPaused: false }); wb.leave() },
}
