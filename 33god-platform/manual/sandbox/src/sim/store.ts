import { create } from 'zustand'
import type { BulbId, StationId, Vec3 } from '../content'

export type Kind = 'post' | 'env'

export interface Note {
  id: number
  kind: Kind
  headline: string
  from: string | null // the "from" corner; null when the note skipped the label desk
  noteId: string // never changes; the dedupe key
  barcode: string | null // one per conversation
  seq: number // belt number, stamped by the belt, per face (two streams, two counters)
  bornH: number // sim hour it was stuck on
  col: number
  viaDesk: boolean
  hatch: 'crew' | null // envelopes only; null = no hatch takes this kind
  heldBy: number | null // desk index holding a pinned envelope
  readBy: string[]
}

export interface Parcel { id: number; vendor: number; t0: number; backT0: number | null }
export type FlyerLook = 'post' | 'summary' | 'copy' | 'env' | 'scrap' | 'scrapEnv'
export interface Flyer { id: number; look: FlyerLook; from: Vec3; to: Vec3; t0: number; dur: number; arc: number }
export interface Puff { id: number; at: Vec3; text: string; t0: number; tone: 'ok' | 'warn' | 'info' }
export interface Desk { holding: number | null; startedAt: number; until: number }

export interface Stats { filed: number; dupes: number; control: number; rules: number; turnedBack: number; signed: number; handedBack: number; scraped: number }

interface State {
  notes: Note[]
  parcels: Parcel[]
  flyers: Flyer[]
  puffs: Puff[]
  desks: Desk[]
  stats: Stats
  lastRead: { archive: number | null; rules: number | null }
  clockRingAt: number
  dockPulseAt: number

  paused: boolean
  speed: number
  dockShut: boolean
  sources: boolean
  intro: boolean
  focus: { id: StationId | 'overview'; nonce: number } | null
  station: StationId | null
  bulb: BulbId | null
  inspect: number | null
  foundStations: StationId[]
  foundBulbs: BulbId[]
}

export const useWorld = create<State>(() => ({
  notes: [],
  parcels: [],
  flyers: [],
  puffs: [],
  desks: [{ holding: null, startedAt: 0, until: 0 }, { holding: null, startedAt: 0, until: 0 }],
  stats: { filed: 0, dupes: 0, control: 0, rules: 0, turnedBack: 0, signed: 0, handedBack: 0, scraped: 0 },
  lastRead: { archive: null, rules: null },
  clockRingAt: -99,
  dockPulseAt: -99,

  paused: false,
  speed: 1,
  dockShut: false,
  sources: false,
  intro: true,
  focus: null,
  station: null,
  bulb: null,
  inspect: null,
  foundStations: [],
  foundBulbs: [],
}))

// Mutable sim clock, read every frame without re-rendering React.
export const clock = { t: 0 }
export const HOURS_PER_SEC = 2 // at 1x, one real second is two warehouse hours
export const START_HOUR = 8
export const hoursNow = () => START_HOUR + clock.t * HOURS_PER_SEC

export const ui = {
  openStation(id: StationId) {
    useWorld.setState((s) => ({
      station: id,
      bulb: null,
      inspect: null,
      focus: { id, nonce: (s.focus?.nonce ?? 0) + 1 },
      foundStations: s.foundStations.includes(id) ? s.foundStations : [...s.foundStations, id],
    }))
  },
  openBulb(id: BulbId) {
    useWorld.setState((s) => ({
      bulb: id,
      foundBulbs: s.foundBulbs.includes(id) ? s.foundBulbs : [...s.foundBulbs, id],
    }))
  },
  overview() {
    useWorld.setState((s) => ({ station: null, inspect: null, focus: { id: 'overview', nonce: (s.focus?.nonce ?? 0) + 1 } }))
  },
}
