// The warehouse's rules, in one place. Every behaviour here is meant to match Bloodbank as it runs today
// (checked against code and the live broker on 2026-11-12):
// - post-its (events) stay on the front face until the 7-day scraper; readers come and tear off copies
// - envelopes (commands) stay on the back face until signed off, or the 1-day scraper
// - the crew hall's hatch keeps taking while its tray has room (drawn 4 desks + 4 tray; real 4 + 64)
// - a hand-back is rare (the hall could not start the job); after 5 tries the hall signs it off as failed
// - the clock posts tick post-its; its planner reads them and posts envelopes for the clock's own hands
// - the sound wing posts envelopes nobody is meant to take (trace records); they ride to the scraper
// - the archive turns away notes with label fields missing (today: every cataloguer summary)
// - a redelivery is the belt's doing: no signature within ~30 s and the note is offered again
// - the courier waits at the dock window for a briefing card and carries it back; a shut dock means it
//   turns round with the parcel; nothing queues at the door
import { VENDORS, type Vec3 } from '../content'
import { BELT, CATALOGUER, CLOCK, COLS, CREW, DOCK, HANDS, PLANNER, READERS, SOUND_OUTBOX, TRAY, notePos } from './layout'
import { HANDS_SLOT, TRAY_SLOT, clock, hoursNow, useWorld, type Flyer, type FlyerLook, type Hatch, type Note } from './store'

const WALK = 2.6 // sim seconds from bay to dock door
const OPEN = 0.7 // the clerk answers at the window
const STICK = 1.1 // post-it flight to the belt
const RETRY = 5 // a handed-back envelope is offered again after a short wait
const MAX_TRIES = 5 // the crew hall's batch hatch

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
const pick = <T,>(xs: T[]) => xs[Math.floor(Math.random() * xs.length)]
const hex = (n: number) => Array.from({ length: n }, () => Math.floor(Math.random() * 16).toString(16)).join('')
const newNoteId = () => `${hex(4)}-${hex(4)}`

const convs = VENDORS.map(() => ({ code: `conv-${hex(4).toUpperCase()}`, left: 3 + Math.floor(Math.random() * 5) }))

const set = useWorld.setState
const get = useWorld.getState

const SUBJECT: Record<string, string> = {
  'turn started': 'bloodbank.evt.conversation.turn.started',
  'session ended': 'bloodbank.evt.agent.session.ended',
  'summary written': 'bloodbank.evt.report.session.completed',
  'tick fired': 'bloodbank.evt.cron.tick.fired',
  'invocation completed': 'bloodbank.evt.agent.invocation.completed',
  'invocation failed': 'bloodbank.evt.agent.invocation.failed',
}
const ENV_SUBJECT: Record<'crew' | 'clock' | 'none', string> = {
  crew: 'bloodbank.cmd.agent.invocation.start',
  clock: 'bloodbank.cmd.cron.candybar.invoke',
  none: 'bloodbank.cmd.audio.task.start',
}

function fly(look: FlyerLook, from: Vec3, to: Vec3, dur: number, arc: number, hold = 0) {
  const f: Flyer = { id: nextId(), look, from, to, t0: clock.t, dur, arc, hold }
  set((s) => ({ flyers: [...s.flyers, f] }))
  later(dur + hold + 0.05, () => set((s) => ({ flyers: s.flyers.filter((x) => x.id !== f.id) })))
}

// Puffs live in sim time, so stretch them with the speed: at 16x they still read for ~2 real seconds.
function puff(at: Vec3, text: string, tone: 'ok' | 'warn' | 'info' = 'info') {
  const life = 2.2 * Math.max(1, get().speed)
  const p = { id: nextId(), at, text, t0: clock.t, life, tone }
  set((s) => ({ puffs: [...s.puffs, p] }))
  later(life, () => set((s) => ({ puffs: s.puffs.filter((x) => x.id !== p.id) })))
}

const ageDays = (n: Note) => (hoursNow() - n.bornH) / 24
const posOf = (n: Note): Vec3 => notePos(n.kind, n.col, ageDays(n))
const findNote = (id: number) => get().notes.find((n) => n.id === id)
const bump = (k: keyof ReturnType<typeof get>['stats'], by = 1) => set((s) => ({ stats: { ...s.stats, [k]: s.stats[k] + by } }))

function patchNote(id: number, patch: (n: Note) => Partial<Note>) {
  set((s) => ({ notes: s.notes.map((n) => (n.id === id ? { ...n, ...patch(n) } : n)) }))
}

function stickPost(headline: string, from: string | null, barcode: string | null, viaDesk: boolean, start: Vec3, look: FlyerLook = 'post') {
  const c = col
  col = (col + 1) % COLS.length
  fly(look, start, notePos('post', c, 0), STICK, 1.6)
  later(STICK, () => {
    frontSeq += 1
    const n: Note = {
      id: nextId(), kind: 'post', headline, from, noteId: newNoteId(), barcode, subject: SUBJECT[headline] ?? 'bloodbank.evt',
      seq: frontSeq, bornH: hoursNow(), col: c, viaDesk, hatch: null, heldBy: null, tries: 0, retryAt: 0, readBy: [],
    }
    set((s) => ({ notes: [...s.notes, n] }))
    readersNotice(n)
  })
}

function stickEnvelope(headline: string, hatch: Hatch, from: string, origin: Vec3) {
  const c = envCol
  envCol = (envCol + 1) % COLS.length
  fly('env', origin, notePos('env', c, 0), 1.3, 1.4)
  later(1.3, () => {
    backSeq += 1
    const n: Note = {
      id: nextId(), kind: 'env', headline, from, noteId: newNoteId(), barcode: null, subject: ENV_SUBJECT[hatch ?? 'none'],
      seq: backSeq, bornH: hoursNow(), col: c, viaDesk: true, hatch, heldBy: null, tries: 0, retryAt: 0, readBy: [],
    }
    set((s) => ({ notes: [...s.notes, n] }))
  })
}

const markRead = (id: number, reader: string) => patchNote(id, (x) => ({ readBy: x.readBy.includes(reader) ? x.readBy : [...x.readBy, reader] }))

// Readers come to the belt and tear off copies. The original stays.
function readersNotice(n: Note) {
  const tear = (to: Vec3, delay: number, then: (live: Note) => void) =>
    later(delay, () => {
      const live = findNote(n.id)
      if (!live) return
      fly('copy', posOf(live), to, 0.9, 1.2)
      later(0.9, () => then(live))
    })
  const above = (p: Vec3, dy = 1.6): Vec3 => [p[0], p[1] + dy, p[2]]

  // the archive files every note it can; a note with label fields missing goes in the rejects drawer
  tear(READERS.archive, rand(0.4, 1.3), (live) => {
    if (!live.viaDesk) {
      puff(above(READERS.archive), 'rejects drawer: label fields missing', 'warn')
      bump('rejected')
      markRead(n.id, 'archive-rejected')
      return
    }
    bump('filed')
    set((s) => ({ lastRead: { ...s.lastRead, archive: n.id } }))
    markRead(n.id, 'archive')
  })
  // now and then the archive's signature is late, so the belt offers the same note again (~30 s ackWait)
  if (n.viaDesk && Math.random() < 0.08) {
    tear(READERS.archive, rand(7, 9), () => {
      puff(above(READERS.archive), `offered again: ${n.noteId} already filed`, 'info')
      bump('dupes')
    })
  }
  // the control room sees everything, a moment late
  tear(READERS.control, rand(1.8, 3.2), () => { bump('control'); markRead(n.id, 'control') })
  // the rule card's pick list: finished jobs only
  if (n.headline === 'invocation completed') {
    tear(READERS.rules, 1.0, () => {
      bump('rules')
      set((s) => ({ lastRead: { ...s.lastRead, rules: n.id } }))
      markRead(n.id, 'rules')
    })
  }
  // the cataloguer acts on "session ended": it asks the archive for the history, then its runner sticks a summary
  if (n.headline === 'session ended') {
    tear([CATALOGUER[0], 1.2, CATALOGUER[2]], 0.6, () => {
      markRead(n.id, 'cataloguer')
      later(2.6, () => stickPost('summary written', null, null, false, [CATALOGUER[0] - 1.1, 1.3, CATALOGUER[2] - 0.2], 'summary'))
    })
  }
  // the clock's planner reads every tick and, when a chore is due, sticks an envelope for the clock's own hands
  if (n.headline === 'tick fired') {
    tear([PLANNER[0], 1.2, PLANNER[2]], 0.5, () => {
      markRead(n.id, 'planner')
      if (Math.random() < 0.55) {
        bump('chores')
        stickEnvelope(pick(CLOCK_CHORES), 'clock', 'clock', [PLANNER[0], 1.6, PLANNER[2]])
      }
    })
  }
}

// ---------- schedules ----------
let nextParcel = 0.3
let nextTick = 1.5
let nextJob = 2
let nextBatch = 22
let nextAudio = 4

function spawnParcel() {
  const vendor = Math.floor(Math.random() * VENDORS.length)
  const p = { id: nextId(), vendor, t0: clock.t, backT0: null as number | null, reply: false }
  set((s) => ({ parcels: [...s.parcels, p] }))
  const remove = (after: number) => later(after, () => set((s) => ({ parcels: s.parcels.filter((x) => x.id !== p.id) })))
  later(WALK, () => {
    if (get().dockShut) {
      set((s) => ({ parcels: s.parcels.map((x) => (x.id === p.id ? { ...x, backT0: clock.t } : x)) }))
      bump('turnedBack')
      puff([DOCK.door[0] - 1, 2.4, 0], 'door shut, turning round', 'warn')
      remove(WALK)
      return
    }
    // hand over the parcel, wait at the window for the clerk's answer, walk the briefing card back
    set((s) => ({ parcels: s.parcels.map((x) => (x.id === p.id ? { ...x, backT0: clock.t + OPEN, reply: true } : x)), dockPulseAt: clock.t }))
    remove(OPEN + WALK)
    const conv = convs[vendor]
    const barcode = conv.code
    // a separate clerk at the back writes the post-it; the courier does not wait for that
    later(OPEN, () => stickPost('turn started', VENDORS[vendor].name, barcode, true, DOCK.out))
    conv.left -= 1
    if (conv.left <= 0) {
      later(OPEN + 0.7, () => stickPost('session ended', VENDORS[vendor].name, barcode, true, DOCK.out))
      conv.code = `conv-${hex(4).toUpperCase()}`
      conv.left = 3 + Math.floor(Math.random() * 5)
    }
  })
}

const CLOCK_CHORES = ['start: daily report', 'start: disk sweep', 'start: journal']
const CREW_JOBS = ['start: board triage', 'start: inbox sweep', 'start: code review', 'start: release notes']
const RULES_OUT: Vec3 = [READERS.rules[0], 3.2, READERS.rules[2]]

const crewDone = (i: number) => set((st) => ({ desks: st.desks.map((x, j) => (j === i ? { holding: null, startedAt: 0, until: 0 } : x)) }))

export function step(realDt: number) {
  const s = get()
  if (s.paused || s.intro) return
  const dt = Math.min(realDt, 0.1) * s.speed
  clock.t += dt
  const t = clock.t

  while (jobs.length && jobs[0].at <= t) jobs.shift()!.run()

  if (t >= nextParcel) { spawnParcel(); nextParcel = t + rand(1.1, 2.1) }
  if (t >= nextTick) {
    // drawn far less often than the real one-a-minute tick
    set({ clockRingAt: t })
    bump('ticks')
    stickPost('tick fired', 'clock', null, true, [CLOCK[0], 5.6, CLOCK[2] + 0.6])
    nextTick = t + rand(5, 7)
  }
  if (t >= nextJob) {
    stickEnvelope(pick(CREW_JOBS), 'crew', 'rules cabinet', RULES_OUT)
    nextJob = t + rand(4.5, 7)
  }
  if (t >= nextBatch) {
    // a batch handed on all at once: more than the desks and the tray can hold
    for (let i = 0; i < 10; i++) later(i * 0.25, () => stickEnvelope(CREW_JOBS[i % CREW_JOBS.length], 'crew', 'rules cabinet', RULES_OUT))
    nextBatch = t + rand(28, 36)
  }
  if (t >= nextAudio) {
    stickEnvelope('start: audio task', null, 'sound wing', SOUND_OUTBOX) // a trace record: nobody is meant to take it
    nextAudio = t + rand(3, 5)
  }

  // the crew hall's hatch: keeps taking, oldest first, while desks + tray have room; taken envelopes stay pinned
  {
    const notes = get().notes
    let pinned = notes.filter((n) => n.hatch === 'crew' && n.heldBy !== null).length
    const waiting = notes.filter((n) => n.hatch === 'crew' && n.heldBy === null && n.retryAt <= t).sort((a, b) => a.bornH - b.bornH)
    for (const n of waiting) {
      if (pinned >= CREW.desks.length + TRAY) break
      pinned++
      patchNote(n.id, (x) => ({ heldBy: TRAY_SLOT, tries: x.tries + 1 }))
      fly('env', posOf(n), CREW.tray, 0.8, 0.8)
    }
  }
  // a free desk takes the oldest envelope in the tray
  get().desks.forEach((d, i) => {
    if (d.holding !== null) return
    const inTray = get().notes.filter((n) => n.hatch === 'crew' && n.heldBy === TRAY_SLOT)
    if (!inTray.length) return
    const next = inTray.reduce((a, b) => (a.bornH <= b.bornH ? a : b))
    patchNote(next.id, () => ({ heldBy: i }))
    set((st) => ({ desks: st.desks.map((x, j) => (j === i ? { holding: next.id, startedAt: t, until: t + rand(3.5, 6.5) } : x)) }))
    fly('env', CREW.tray, CREW.desks[i], 0.6, 0.5)
  })
  get().desks.forEach((d, i) => {
    if (d.holding === null || t < d.until) return
    const id = d.holding
    const at: Vec3 = [CREW.desks[i][0], 2.6, CREW.desks[i][2]]
    const hallFront: Vec3 = [CREW.center[0], 1.6, CREW.center[2] + 2]
    crewDone(i)
    const n = findNote(id)
    if (!n) return
    if (Math.random() < 0.03) {
      // the hall could not start the job (closing mid-shift): hand it back, or give up after the last try
      if (n.tries >= MAX_TRIES) {
        set((st) => ({ notes: st.notes.filter((x) => x.id !== id) }))
        bump('failed'); bump('signed')
        puff(at, 'out of tries: signed off as failed', 'warn')
        stickPost('invocation failed', 'crew hall', null, true, hallFront)
      } else {
        patchNote(id, () => ({ heldBy: null, retryAt: t + RETRY }))
        bump('handedBack')
        puff(at, 'handed back: “try again in a bit”', 'info')
      }
    } else {
      set((st) => ({ notes: st.notes.filter((x) => x.id !== id) }))
      bump('signed')
      puff(at, 'signed off', 'info')
      stickPost('invocation completed', 'crew hall', null, true, hallFront)
    }
  })

  // the clock's hands: one at a time, never gives up; signs off when finished (or when it skips a run)
  {
    const hands = get().hands
    if (hands.holding === null) {
      const due = get().notes.filter((n) => n.hatch === 'clock' && n.heldBy === null)
      if (due.length) {
        const next = due.reduce((a, b) => (a.bornH <= b.bornH ? a : b))
        patchNote(next.id, (x) => ({ heldBy: HANDS_SLOT, tries: x.tries + 1 }))
        set({ hands: { holding: next.id, startedAt: t, until: t + rand(2, 4) } })
        fly('env', posOf(next), [HANDS[0], 1.1, HANDS[2]], 0.9, 0.9)
      }
    } else if (t >= hands.until) {
      const id = hands.holding
      set((st) => ({ hands: { holding: null, startedAt: 0, until: 0 }, notes: st.notes.filter((x) => x.id !== id) }))
      puff([HANDS[0], 2.4, HANDS[2]], 'signed off', 'info')
    }
  }

  // the scrapers: whatever reaches the bar is scraped, read or not
  const h = hoursNow()
  const expired = get().notes.filter((n) => (h - n.bornH) / 24 >= (n.kind === 'post' ? BELT.frontDays : BELT.backDays))
  if (expired.length) {
    expired.forEach((n) => {
      const p = posOf(n)
      // scraped paper flutters down like a leaf (about 2.4 m/s), lands flat on the floor, lies there a moment, fades
      const fall = Math.max(1.8, p[1] / 2.4)
      fly(n.kind === 'post' ? 'scrap' : 'scrapEnv', p, [p[0] + rand(-0.9, 0.9), 0.016, p[2] + (n.kind === 'post' ? 1 : -1) * rand(1.4, 2.6)], fall, 0, 3.5)
      if (n.heldBy !== null && n.heldBy >= 0) crewDone(n.heldBy)
      if (n.heldBy === HANDS_SLOT) set({ hands: { holding: null, startedAt: 0, until: 0 } })
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
  const front: Note[] = []
  for (let i = 0; i < 46; i++) {
    const age = (i / 46) * 6.8 + Math.random() * 0.1
    const v = Math.floor(Math.random() * VENDORS.length)
    const kind = i % 9 === 3 ? 'summary written' : i % 7 === 5 ? 'invocation completed' : i % 6 === 1 ? 'tick fired' : i % 11 === 8 ? 'session ended' : 'turn started'
    const vendorish = kind === 'turn started' || kind === 'session ended'
    const viaDesk = kind !== 'summary written'
    frontSeq += 1
    front.push({
      id: nextId(), kind: 'post', headline: kind, subject: SUBJECT[kind],
      from: vendorish ? VENDORS[v].name : kind === 'tick fired' ? 'clock' : kind === 'invocation completed' ? 'crew hall' : null,
      noteId: newNoteId(), barcode: vendorish ? convs[v].code : null,
      seq: frontSeq, bornH: h - age * 24, col: i % COLS.length, viaDesk, hatch: null, heldBy: null, tries: 0, retryAt: 0,
      readBy: ['control', viaDesk ? 'archive' : 'archive-rejected', ...(kind === 'invocation completed' ? ['rules'] : []), ...(kind === 'tick fired' ? ['planner'] : []), ...(kind === 'session ended' ? ['cataloguer'] : [])],
    })
  }
  const back: Note[] = []
  // on the real belt almost everything left standing at the back is grey: taken envelopes are gone in minutes
  const ages = [20, 16, 12, 9, 6, 3]
  ages.forEach((ageH, i) => {
    backSeq += 1
    back.push({
      id: nextId(), kind: 'env', headline: 'start: audio task', subject: ENV_SUBJECT.none, from: 'sound wing',
      noteId: newNoteId(), barcode: null, seq: backSeq, bornH: h - ageH, col: i % COLS.length,
      viaDesk: true, hatch: null, heldBy: null, tries: 0, retryAt: 0, readBy: [],
    })
  })
  useWorld.setState((s) => ({ notes: [...s.notes, ...front, ...back] }))
  envCol = ages.length % COLS.length
  useWorld.setState({
    lastRead: {
      archive: front.filter((n) => n.viaDesk).pop()?.id ?? null,
      rules: front.filter((n) => n.headline === 'invocation completed').pop()?.id ?? null,
    },
  })
}
