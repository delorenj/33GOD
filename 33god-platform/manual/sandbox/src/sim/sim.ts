// The warehouse's rules, in one place. Every behaviour here is meant to match Bloodbank:
// - post-its (events) stay on the front face until the 7-day scraper; readers tear copies
// - envelopes (commands) stay on the back face until signed off, torn up, or the 1-day scraper
// - the hatch admits only as many envelopes as there are free desks
// - a shut dock means the courier turns round; nothing queues at the door
import { VENDORS, type Vec3 } from '../content'
import { BELT, CATALOGUER, CLOCK, COLS, CREW, DOCK, READERS, notePos } from './layout'
import { clock, hoursNow, useWorld, type Flyer, type FlyerLook, type Note } from './store'

const WALK = 2.6 // sim seconds from bay to dock door
const OPEN = 0.7 // clerk opens the parcel
const STICK = 1.1 // post-it flight to the belt

let uid = 1
const nextId = () => uid++
let frontSeq = 0
let backSeq = 0
let col = 0
let envCol = 0

interface Job { at: number; run: () => void }
const jobs: Job[] = []
const later = (delay: number, run: () => void) => {
  const at = clock.t + delay
  let i = jobs.length
  while (i > 0 && jobs[i - 1].at > at) i--
  jobs.splice(i, 0, { at, run })
}

const rand = (a: number, b: number) => a + Math.random() * (b - a)
const hex = (n: number) => Array.from({ length: n }, () => Math.floor(Math.random() * 16).toString(16)).join('')
const newNoteId = () => `${hex(4)}-${hex(4)}`

const convs = VENDORS.map(() => ({ code: `conv-${hex(4).toUpperCase()}`, left: 3 + Math.floor(Math.random() * 5) }))

const set = useWorld.setState
const get = useWorld.getState

function fly(look: FlyerLook, from: Vec3, to: Vec3, dur: number, arc: number) {
  const f: Flyer = { id: nextId(), look, from, to, t0: clock.t, dur, arc }
  set((s) => ({ flyers: [...s.flyers, f] }))
  later(dur + 0.05, () => set((s) => ({ flyers: s.flyers.filter((x) => x.id !== f.id) })))
}

function puff(at: Vec3, text: string, tone: 'ok' | 'warn' | 'info' = 'info') {
  const p = { id: nextId(), at, text, t0: clock.t, tone }
  set((s) => ({ puffs: [...s.puffs, p] }))
  later(2.2, () => set((s) => ({ puffs: s.puffs.filter((x) => x.id !== p.id) })))
}

const ageDays = (n: Note) => (hoursNow() - n.bornH) / 24
const posOf = (n: Note): Vec3 => notePos(n.kind, n.col, ageDays(n))
const findNote = (id: number) => get().notes.find((n) => n.id === id)

function patchNote(id: number, patch: (n: Note) => Partial<Note>) {
  set((s) => ({ notes: s.notes.map((n) => (n.id === id ? { ...n, ...patch(n) } : n)) }))
}

function stickPost(headline: string, from: string | null, barcode: string | null, viaDesk: boolean, start: Vec3, look: FlyerLook) {
  const c = col
  col = (col + 1) % COLS.length
  const target = notePos('post', c, 0)
  fly(look, start, target, STICK, 1.6)
  later(STICK, () => {
    frontSeq += 1
    const n: Note = {
      id: nextId(), kind: 'post', headline, from, noteId: newNoteId(), barcode,
      seq: frontSeq, bornH: hoursNow(), col: c, viaDesk, hatch: null, heldBy: null, readBy: [],
    }
    set((s) => ({ notes: [...s.notes, n] }))
    readersNotice(n)
  })
}

// Readers come to the belt; the belt never delivers.
function readersNotice(n: Note) {
  const tear = (reader: 'archive' | 'control' | 'rules', delay: number, dupe = false) =>
    later(delay, () => {
      const live = findNote(n.id)
      if (!live) return
      fly('copy', posOf(live), READERS[reader], 0.9, 1.2)
      later(0.9, () => {
        if (reader === 'archive') {
          const already = get().notes.find((x) => x.id === n.id)?.readBy.includes('archive') || dupe
          if (already) {
            puff([READERS.archive[0], READERS.archive[1] + 1.6, READERS.archive[2]], `already filed ${n.noteId}`, 'warn')
            set((s) => ({ stats: { ...s.stats, dupes: s.stats.dupes + 1 } }))
            return
          }
          set((s) => ({ stats: { ...s.stats, filed: s.stats.filed + 1 }, lastRead: { ...s.lastRead, archive: n.id } }))
        } else if (reader === 'control') {
          set((s) => ({ stats: { ...s.stats, control: s.stats.control + 1 } }))
        } else {
          set((s) => ({ stats: { ...s.stats, rules: s.stats.rules + 1 }, lastRead: { ...s.lastRead, rules: n.id } }))
        }
        patchNote(n.id, (x) => ({ readBy: x.readBy.includes(reader) ? x.readBy : [...x.readBy, reader] }))
      })
    })

  tear('archive', rand(0.4, 1.3))
  if (Math.random() < 0.08) tear('archive', rand(3.5, 6), true) // a second copy turns up; the clerk files nothing
  tear('control', rand(1.8, 3.2)) // the window shows the floor a moment late
  if (n.headline === 'summary written') tear('rules', 1.0) // on the rules card's pick list
}

function stickEnvelope(headline: string, hatch: 'crew' | null) {
  const c = envCol
  envCol = (envCol + 1) % COLS.length
  const target = notePos('env', c, 0)
  fly('env', [CLOCK[0], 5.6, CLOCK[2] + 0.6], target, 1.3, 1.4)
  later(1.3, () => {
    backSeq += 1
    const n: Note = {
      id: nextId(), kind: 'env', headline, from: 'clock', noteId: newNoteId(), barcode: null,
      seq: backSeq, bornH: hoursNow(), col: c, viaDesk: true, hatch, heldBy: null, readBy: [],
    }
    set((s) => ({ notes: [...s.notes, n] }))
  })
}

// ---------- schedules ----------
let nextParcel = 0.3
let nextSummary = 6
let nextChore = 2
let nextBell = 24
let nextOrphan = 9

function spawnParcel() {
  const vendor = Math.floor(Math.random() * VENDORS.length)
  const p = { id: nextId(), vendor, t0: clock.t, backT0: null as number | null }
  set((s) => ({ parcels: [...s.parcels, p] }))
  later(WALK, () => {
    if (get().dockShut) {
      set((s) => ({
        parcels: s.parcels.map((x) => (x.id === p.id ? { ...x, backT0: clock.t } : x)),
        stats: { ...s.stats, turnedBack: s.stats.turnedBack + 1 },
      }))
      puff([DOCK.door[0] - 1, 2.4, 0], 'door shut, turning round', 'warn')
      later(WALK, () => set((s) => ({ parcels: s.parcels.filter((x) => x.id !== p.id) })))
      return
    }
    set((s) => ({ parcels: s.parcels.filter((x) => x.id !== p.id), dockPulseAt: clock.t }))
    const conv = convs[vendor]
    conv.left -= 1
    if (conv.left <= 0) { conv.code = `conv-${hex(4).toUpperCase()}`; conv.left = 3 + Math.floor(Math.random() * 5) }
    const barcode = conv.code
    later(OPEN, () => stickPost('turn started', VENDORS[vendor].name, barcode, true, DOCK.out, 'post'))
  })
}

const CHORES = ['start: daily report', 'start: board triage', 'start: journal', 'start: inbox sweep']

export function step(realDt: number) {
  const s = get()
  if (s.paused || s.intro) return
  const dt = Math.min(realDt, 0.1) * s.speed
  clock.t += dt
  const t = clock.t

  while (jobs.length && jobs[0].at <= t) jobs.shift()!.run()

  if (t >= nextParcel) { spawnParcel(); nextParcel = t + rand(1.1, 2.1) }
  if (t >= nextSummary) {
    stickPost('summary written', null, null, false, [CATALOGUER[0], 1.3, CATALOGUER[2]], 'summary')
    nextSummary = t + rand(9, 13)
  }
  if (t >= nextChore) {
    set({ clockRingAt: t })
    stickEnvelope(CHORES[Math.floor(Math.random() * CHORES.length)], 'crew')
    nextChore = t + rand(4.5, 7)
  }
  if (t >= nextBell) {
    // the hour bell: a burst of chores, more than the desks can take at once
    set({ clockRingAt: t })
    for (let i = 0; i < 4; i++) later(i * 0.35, () => stickEnvelope(CHORES[i % CHORES.length], 'crew'))
    nextBell = t + rand(26, 34)
  }
  if (t >= nextOrphan) {
    stickEnvelope('start: audio task', null) // no hatch takes this kind
    nextOrphan = t + rand(12, 18)
  }

  // the hatch: one envelope per free desk, oldest first; it stays pinned on the belt
  const desks = get().desks
  desks.forEach((d, i) => {
    if (d.holding !== null) return
    const candidates = get().notes.filter((n) => n.kind === 'env' && n.hatch === 'crew' && n.heldBy === null)
    if (!candidates.length) return
    const pick = candidates.reduce((a, b) => (a.bornH <= b.bornH ? a : b))
    const work = rand(3.5, 6.5)
    patchNote(pick.id, () => ({ heldBy: i }))
    set((st) => ({ desks: st.desks.map((x, j) => (j === i ? { holding: pick.id, startedAt: t, until: t + work } : x)) }))
    fly('env', posOf(pick), CREW.desks[i], 0.8, 0.8)
  })
  get().desks.forEach((d, i) => {
    if (d.holding === null || t < d.until) return
    const id = d.holding
    const at: Vec3 = [CREW.desks[i][0], 2.6, CREW.desks[i][2]]
    set((st) => ({ desks: st.desks.map((x, j) => (j === i ? { holding: null, startedAt: 0, until: 0 } : x)) }))
    if (!findNote(id)) return
    if (Math.random() < 0.1) {
      patchNote(id, () => ({ heldBy: null }))
      set((st) => ({ stats: { ...st.stats, handedBack: st.stats.handedBack + 1 } }))
      puff(at, 'handed back, try again', 'warn')
    } else {
      set((st) => ({ notes: st.notes.filter((n) => n.id !== id), stats: { ...st.stats, signed: st.stats.signed + 1 } }))
      puff(at, 'signed off', 'ok')
    }
  })

  // the scrapers: whatever reaches the bar goes, read or not
  const h = hoursNow()
  const expired = get().notes.filter((n) => (h - n.bornH) / 24 >= (n.kind === 'post' ? BELT.frontDays : BELT.backDays))
  if (expired.length) {
    expired.forEach((n) => {
      const p = posOf(n)
      fly(n.kind === 'post' ? 'scrap' : 'scrapEnv', p, [p[0] + rand(-0.6, 0.6), 0.03, p[2] + (n.kind === 'post' ? 1.6 : -1.6)], 1.3, 0.4)
      if (n.heldBy !== null) {
        const di = n.heldBy
        set((st) => ({ desks: st.desks.map((x, j) => (j === di ? { holding: null, startedAt: 0, until: 0 } : x)) }))
      }
    })
    const gone = new Set(expired.map((n) => n.id))
    set((st) => ({
      notes: st.notes.filter((n) => !gone.has(n.id)),
      stats: { ...st.stats, scraped: st.stats.scraped + expired.length },
      inspect: st.inspect !== null && gone.has(st.inspect) ? null : st.inspect,
    }))
  }
}

// Warm the belt so the first look is not an empty wall: pre-age some notes.
export function seed() {
  const h = hoursNow()
  for (let i = 0; i < 46; i++) {
    const age = (i / 46) * 6.8 + Math.random() * 0.1
    const summary = i % 8 === 3
    const v = Math.floor(Math.random() * VENDORS.length)
    frontSeq += 1
    useWorld.setState((s) => ({
      notes: [...s.notes, {
        id: nextId(), kind: 'post', headline: summary ? 'summary written' : 'turn started',
        from: summary ? null : VENDORS[v].name, noteId: newNoteId(), barcode: summary ? null : convs[v].code,
        seq: frontSeq, bornH: h - age * 24, col: i % COLS.length, viaDesk: !summary, hatch: null, heldBy: null,
        readBy: ['archive', 'control', ...(summary ? ['rules'] : [])],
      }],
    }))
  }
  for (let i = 0; i < 5; i++) {
    backSeq += 1
    const orphan = i === 1 || i === 4
    useWorld.setState((s) => ({
      notes: [...s.notes, {
        id: nextId(), kind: 'env', headline: orphan ? 'start: audio task' : CHORES[i % CHORES.length], from: 'clock',
        noteId: newNoteId(), barcode: null, seq: backSeq, bornH: h - (orphan ? 14 + i * 2 : 2 + i) , col: i % COLS.length,
        viaDesk: true, hatch: orphan ? null : 'crew', heldBy: null, readBy: [],
      }],
    }))
  }
  const fn = useWorld.getState().notes.filter((n) => n.kind === 'post')
  useWorld.setState({ lastRead: { archive: fn[fn.length - 1]?.id ?? null, rules: fn.filter((n) => n.headline === 'summary written').pop()?.id ?? null } })
}
