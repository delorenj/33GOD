/**
 * "Village" background music for the 33GOD Manual sandbox.
 *
 * Original composition, synthesised entirely with the Web Audio API (no assets, no deps).
 * G major, 84 bpm, 40 bars: A, A', B (flute + pad), C (celesta bridge), A'' + turnaround.
 *
 * Live use:      music.start() from a user gesture, music.stop(), music.toggle(), ...
 * Offline use:   const rig = createRig(offlineCtx, offlineCtx.destination)
 *                schedule(offlineCtx, rig, 0, 0, BARS * loops)
 */

// ---------------------------------------------------------------- composition

export const BPM = 84
export const BEATS_PER_BAR = 4
export const STEPS_PER_BAR = 8 // eighth notes
export const BARS = 40
const BEAT = 60 / BPM
const STEP = BEAT / 2
export const BAR_SECONDS = BEAT * BEATS_PER_BAR
export const LOOP_SECONDS = BAR_SECONDS * BARS
const LILT = 0.07 // odd eighths land this fraction of a step late (gentle swing)

type Section = {
  name: string
  from: number // first bar (0-based)
  bars: number
  lead: 'pizz' | 'flute' | 'celesta'
  arp: 'roll' | 'offbeat' | 'sparse'
  bass: 'half' | 'lilt'
  pad: number // 0..1
  sparkle: 'none' | 'twinkle' | 'double'
}

const SECTIONS: Section[] = [
  { name: 'A', from: 0, bars: 8, lead: 'pizz', arp: 'roll', bass: 'half', pad: 0, sparkle: 'none' },
  { name: "A'", from: 8, bars: 8, lead: 'pizz', arp: 'roll', bass: 'lilt', pad: 0, sparkle: 'twinkle' },
  { name: 'B', from: 16, bars: 8, lead: 'flute', arp: 'offbeat', bass: 'half', pad: 1, sparkle: 'twinkle' },
  { name: 'C', from: 24, bars: 8, lead: 'celesta', arp: 'sparse', bass: 'half', pad: 0.5, sparkle: 'none' },
  { name: "A''", from: 32, bars: 8, lead: 'pizz', arp: 'roll', bass: 'lilt', pad: 0, sparkle: 'double' },
]

/** One chord per bar, or two separated by "|" (first half / second half). */
const CHORDS: string[] = [
  // A
  'Gmaj7', 'Bm7', 'Cmaj7', 'Am7|D7', 'Gmaj7', 'Em7', 'Cmaj7', 'D7sus4|D7',
  // A'
  'Gmaj7', 'Bm7', 'Cmaj7', 'Am7|D7', 'Em7', 'Cmaj7', 'Am7|D7', 'Gmaj7',
  // B
  'Em7', 'Cmaj7', 'Am7', 'B7', 'Em7', 'Cmaj7', 'Am7', 'D7sus4|D7',
  // C
  'Cmaj7', 'Bm7', 'Am7', 'Gmaj7', 'Cmaj7', 'Em7', 'Am7', 'D7sus4|D7',
  // A''
  'Gmaj7', 'Bm7', 'Cmaj7', 'Am7|D7', 'Em7', 'Am7', 'Cmaj7', 'D7sus4|D7',
]

/** Lead lines, "note:eighths" tokens, every bar sums to 8 eighths. "r" is a rest. */
const MELODY: string[] = [
  // A: question (1-4) and answer (5-8)
  'B4:1 D5:2 G5:1 F#5:2 D5:2',
  'D5:1 F#5:1 A5:2 G5:1 F#5:1 D5:2',
  'E5:2 G5:1 B5:2 A5:1 G5:2',
  'A5:2 E5:2 F#5:1 A5:1 C6:2',
  'B5:3 A5:1 G5:2 D5:2',
  'E5:2 G5:2 B5:1 A5:1 G5:2',
  'A5:1 G5:1 E5:2 G5:2 E5:1 D5:1',
  'G5:2 E5:1 D5:1 C5:2 A4:2',
  // A': higher, more ornamented
  'D6:2 B5:1 G5:1 A5:2 B5:2',
  'B5:2 A5:1 F#5:1 A5:2 D5:2',
  'E5:1 G5:1 B5:2 C6:2 B5:1 G5:1',
  'A5:2 G5:1 E5:1 F#5:2 A5:2',
  'G5:2 B5:1 D6:1 E6:2 D6:2',
  'C6:2 B5:1 G5:1 E5:2 G5:2',
  'A5:1 G5:1 E5:2 F#5:1 A5:1 C6:2',
  'B5:2 A5:1 G5:1 D5:2 r:2',
  // B: flute, long breaths
  'G5:4 B5:2 A5:2',
  'G5:3 E5:1 G5:2 C6:2',
  'B5:2 A5:2 E5:4',
  'F#5:3 D#5:1 B4:2 D#5:2',
  'E5:2 G5:2 B5:2 E6:2',
  'D6:3 B5:1 G5:4',
  'E6:2 C6:2 A5:4',
  'B5:2 A5:2 F#5:2 A5:1 C6:1',
  // C: celesta bridge
  'E6:2 r:2 G6:2 E6:2',
  'D6:2 F#6:2 r:1 D6:1 B5:2',
  'C6:2 E6:2 A5:2 r:2',
  'B5:2 D6:2 G6:4',
  'G6:1 E6:1 C6:2 E6:2 G6:2',
  'G6:2 E6:2 B5:2 D6:2',
  'E6:2 D6:1 C6:1 A5:4',
  'D6:2 C6:1 A5:1 F#5:2 A5:2',
  // A'': question again (33-36), new answer (37-40) that peaks then turns around
  'B4:1 D5:2 G5:1 F#5:2 D5:2',
  'D5:1 F#5:1 A5:2 G5:1 F#5:1 D5:2',
  'E5:2 G5:1 B5:2 A5:1 G5:2',
  'A5:2 E5:2 F#5:1 A5:1 C6:2',
  'E5:1 G5:1 B5:2 D6:2 B5:1 G5:1',
  'C6:2 A5:1 E5:1 A5:2 C6:2',
  'E6:3 D6:1 C6:2 B5:2',
  'A5:2 G5:2 F#5:2 D5:2',
]

// ---------------------------------------------------------------- theory

const NOTE_PC: Record<string, number> = { C: 0, D: 2, E: 4, F: 5, G: 7, A: 9, B: 11 }
const QUALITY: Record<string, number[]> = {
  '': [0, 4, 7],
  m: [0, 3, 7],
  maj7: [0, 4, 7, 11],
  m7: [0, 3, 7, 10],
  '7': [0, 4, 7, 10],
  '7sus4': [0, 5, 7, 10],
}

function pitchClass(name: string): number {
  const m = /^([A-G])(#|b)?$/.exec(name)
  if (!m) throw new Error(`bad pitch class ${name}`)
  return (NOTE_PC[m[1]] + (m[2] === '#' ? 1 : m[2] === 'b' ? -1 : 0) + 12) % 12
}

/** "F#5" -> MIDI number (C-1 = 0). */
function midiOf(name: string): number {
  const m = /^([A-G][#b]?)(-?\d)$/.exec(name)
  if (!m) throw new Error(`bad note ${name}`)
  return pitchClass(m[1]) + (Number(m[2]) + 1) * 12
}

const hz = (midi: number) => 440 * 2 ** ((midi - 69) / 12)

type Chord = { root: number; tones: number[] } // root = pitch class, tones = semitones above it

function parseChord(sym: string): Chord {
  const m = /^([A-G][#b]?)(.*)$/.exec(sym)
  if (!m || !(m[2] in QUALITY)) throw new Error(`bad chord ${sym}`)
  return { root: pitchClass(m[1]), tones: QUALITY[m[2]] }
}

type Note = { step: number; len: number; midi: number }

function parseBar(src: string): Note[] {
  const out: Note[] = []
  let step = 0
  for (const tok of src.split(/\s+/)) {
    const [n, d] = tok.split(':')
    const len = Number(d ?? 1)
    if (n !== 'r') out.push({ step, len, midi: midiOf(n) })
    step += len
  }
  if (step !== STEPS_PER_BAR) throw new Error(`bar "${src}" has ${step} eighths`)
  return out
}

const BAR_CHORDS: Chord[][] = CHORDS.map(c => c.split('|').map(parseChord))
const BAR_MELODY: Note[][] = MELODY.map(parseBar)
if (BAR_CHORDS.length !== BARS || BAR_MELODY.length !== BARS) throw new Error('composition is not BARS long')

const chordAt = (bar: number, step: number): Chord => {
  const cs = BAR_CHORDS[bar]
  return cs.length === 1 || step < 4 ? cs[0] : cs[1]
}

/** i-th arpeggio tone above `base`, wrapping into higher octaves for chords of any size. */
const arpTone = (c: Chord, base: number, i: number) => base + c.tones[i % c.tones.length] + 12 * Math.floor(i / c.tones.length)

/** Chord root as a MIDI note, folded into [lo, lo + 12). */
const rootIn = (c: Chord, lo: number) => lo + ((c.root - lo) % 12 + 12) % 12

const ARP_PATTERNS: Record<Section['arp'], (number | null)[][]> = {
  // every eighth; two shapes alternate bar by bar
  roll: [
    [0, 2, 1, 3, 2, 3, 1, 2],
    [0, 1, 2, 4, 3, 2, 1, 2],
  ],
  // chord plucks on the "ands"
  offbeat: [[null, 2, null, 1, null, 3, null, 1]],
  // a few soft notes per bar, leaves room for the celesta
  sparse: [[0, null, 2, null, 1, null, 3, null]],
}
const ARP_ACCENT = [0.5, 0.34, 0.42, 0.34, 0.46, 0.34, 0.42, 0.36]

// [step, semitones above chord root, length in eighths, velocity]
const BASS_PATTERNS: Record<Section['bass'], number[][]> = {
  half: [[0, 0, 3, 1], [4, 7, 3, 0.74]],
  lilt: [[0, 0, 2, 1], [3, 7, 1, 0.62], [4, 12, 2, 0.82], [6, 7, 1, 0.6]],
}

const sectionOf = (bar: number) => SECTIONS.find(s => bar >= s.from && bar < s.from + s.bars)!

// ---------------------------------------------------------------- synthesis

/** Small deterministic PRNG so offline renders are reproducible. */
function mulberry32(seed: number) {
  let a = seed >>> 0
  return () => {
    a = (a + 0x6d2b79f5) >>> 0
    let t = a
    t = Math.imul(t ^ (t >>> 15), t | 1)
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61)
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

const bufferCache = new WeakMap<BaseAudioContext, Map<string, AudioBuffer>>()
function cached(ctx: BaseAudioContext, key: string, make: () => AudioBuffer): AudioBuffer {
  let m = bufferCache.get(ctx)
  if (!m) bufferCache.set(ctx, (m = new Map()))
  let b = m.get(key)
  if (!b) m.set(key, (b = make()))
  return b
}

type PluckKind = 'lead' | 'arp'
const PLUCK: Record<PluckKind, { secs: number; t60: number; smooth: number; burst: number; pos: number; body: number }> = {
  // t60: seconds to -60 dB at the fundamental. smooth: loop low-pass (0.5 = classic KS, lower = brighter).
  lead: { secs: 1.5, t60: 0.85, smooth: 0.42, burst: 0.5, pos: 0.17, body: 0.22 },
  arp: { secs: 1.1, t60: 0.55, smooth: 0.5, burst: 0.38, pos: 0.3, body: 0.12 },
}

/** Karplus-Strong pluck with a fractional-delay loop, so every pitch is in tune, plus a short soft "body" thump. */
function pluckBuffer(ctx: BaseAudioContext, kind: PluckKind, midi: number): AudioBuffer {
  return cached(ctx, `${kind}${midi}`, () => {
    const sr = ctx.sampleRate
    const f = hz(midi)
    const p = PLUCK[kind]
    const n = Math.ceil(sr * p.secs)
    const buf = ctx.createBuffer(1, n, sr)
    const y = buf.getChannelData(0)
    const L = sr / f - p.smooth
    const Li = Math.floor(L)
    const fr = L - Li
    const g = 10 ** (-3 / (p.t60 * f)) // loss per period
    const m = Li + 2
    const rng = mulberry32(midi * 7919 + (kind === 'lead' ? 1 : 2))
    const e = new Float32Array(m)
    let lp = 0
    let mean = 0
    for (let i = 0; i < m; i++) {
      lp += (rng() * 2 - 1 - lp) * p.burst
      e[i] = lp
      mean += lp
    }
    mean /= m
    const pk = Math.max(1, Math.round(m * p.pos)) // pluck position comb
    for (let i = 0; i < m; i++) y[i] = e[i] - mean - (i >= pk ? (e[i - pk] - mean) * 0.85 : 0)
    const d = (i: number) => y[i - Li] * (1 - fr) + y[i - Li - 1] * fr
    let prev = d(m - 1)
    for (let i = m; i < n; i++) {
      const cur = d(i)
      y[i] = g * ((1 - p.smooth) * cur + p.smooth * prev)
      prev = cur
    }
    const w = (2 * Math.PI * f) / sr
    let peak = 0
    for (let i = 0; i < n; i++) {
      y[i] += p.body * Math.sin(w * i) * Math.exp(-i / (sr * 0.07))
      peak = Math.max(peak, Math.abs(y[i]))
    }
    const fade = Math.floor(sr * 0.05)
    const k = 0.9 / (peak || 1)
    const attack = Math.floor(sr * 0.0012) // ~1 ms, only to avoid a click on the first sample
    for (let i = 0; i < n; i++) y[i] *= k * (i > n - fade ? (n - i) / fade : 1) * (i < attack ? i / attack : 1)
    return buf
  })
}

function noiseBuffer(ctx: BaseAudioContext): AudioBuffer {
  return cached(ctx, 'noise', () => {
    const n = ctx.sampleRate * 2
    const b = ctx.createBuffer(1, n, ctx.sampleRate)
    const d = b.getChannelData(0)
    const rng = mulberry32(4242)
    for (let i = 0; i < n; i++) d[i] = rng() * 2 - 1
    return b
  })
}

/** Short, warm room: ~1.4 s, getting darker as it decays, with a few early reflections. */
function impulse(ctx: BaseAudioContext): AudioBuffer {
  return cached(ctx, 'impulse', () => {
    const sr = ctx.sampleRate
    const secs = 1.7
    const rt60 = 1.4
    const n = Math.floor(sr * secs)
    const buf = ctx.createBuffer(2, n, sr)
    const early = [
      [0.017, 0.5, 0.031, 0.32, 0.053, 0.2],
      [0.023, 0.45, 0.037, 0.3, 0.059, 0.22],
    ]
    for (let ch = 0; ch < 2; ch++) {
      const d = buf.getChannelData(ch)
      const rng = mulberry32(900 + ch)
      let lp = 0
      const pre = Math.floor(sr * 0.012)
      for (let i = pre; i < n; i++) {
        const t = i / sr
        const a = 0.6 - 0.47 * (t / secs) // low-pass coefficient falls with time
        lp += (rng() * 2 - 1 - lp) * a
        d[i] = lp * Math.exp((-6.9 * t) / rt60) * Math.min(1, (i - pre) / (sr * 0.02))
      }
      for (let k = 0; k < early[ch].length; k += 2) d[Math.floor(sr * early[ch][k])] += early[ch][k + 1] * (ch ? -1 : 1)
    }
    return buf
  })
}

// ---------------------------------------------------------------- rig (mixer + effects)

type BusName = 'lead' | 'arp' | 'bass' | 'celesta' | 'flute' | 'pad'
//                         gain  pan    reverb send
const BUS: Record<BusName, [number, number, number]> = {
  lead: [0.5, 0.08, 0.3],
  arp: [0.35, -0.22, 0.3],
  bass: [0.15, 0, 0.04],
  celesta: [0.18, 0.3, 0.55],
  flute: [0.033, 0.12, 0.45],
  pad: [0.03, 0, 0.5],
}

export type Rig = { buses: Record<BusName, GainNode>; out: AudioNode; nodes: AudioNode[] }

/** Builds the instrument buses, reverb, tone shaping and glue compressor, wired into `destination`. */
export function createRig(ctx: BaseAudioContext, destination: AudioNode): Rig {
  const nodes: AudioNode[] = []
  const add = <T extends AudioNode>(n: T) => (nodes.push(n), n)
  const mix = add(ctx.createGain())
  const reverb = add(ctx.createConvolver())
  reverb.buffer = impulse(ctx)
  const wet = add(ctx.createGain())
  wet.gain.value = 0.6
  reverb.connect(wet).connect(mix)

  const comp = add(ctx.createDynamicsCompressor())
  comp.threshold.value = -20
  comp.knee.value = 16
  comp.ratio.value = 2.5
  comp.attack.value = 0.012
  comp.release.value = 0.3
  const lowpass = add(ctx.createBiquadFilter()) // dark-ish, 16-bit sampler flavour
  lowpass.type = 'lowpass'
  lowpass.frequency.value = 7800
  lowpass.Q.value = 0.5
  const highpass = add(ctx.createBiquadFilter())
  highpass.type = 'highpass'
  highpass.frequency.value = 55
  highpass.Q.value = 0.5
  mix.connect(comp).connect(lowpass).connect(highpass).connect(destination)

  const buses = {} as Record<BusName, GainNode>
  for (const name of Object.keys(BUS) as BusName[]) {
    const [gain, pan, send] = BUS[name]
    const bus = add(ctx.createGain())
    bus.gain.value = gain
    const panner = add(ctx.createStereoPanner())
    panner.pan.value = pan
    const s = add(ctx.createGain())
    s.gain.value = send
    bus.connect(panner).connect(mix)
    bus.connect(s).connect(reverb)
    buses[name] = bus
  }
  return { buses, out: highpass, nodes }
}

/** Disconnect everything so notes that were queued but not yet heard go nowhere. */
export function disposeRig(rig: Rig) {
  for (const n of rig.nodes) {
    try {
      n.disconnect()
    } catch {
      /* already disconnected */
    }
  }
}

// ---------------------------------------------------------------- voices

function pluck(ctx: BaseAudioContext, bus: AudioNode, kind: PluckKind, midi: number, t: number, vel: number) {
  const src = ctx.createBufferSource()
  src.buffer = pluckBuffer(ctx, kind, midi)
  const g = ctx.createGain()
  g.gain.value = vel
  src.connect(g).connect(bus)
  src.start(t)
}

function bassNote(ctx: BaseAudioContext, bus: AudioNode, midi: number, t: number, vel: number) {
  const f = hz(midi)
  const tri = ctx.createOscillator()
  tri.type = 'triangle'
  tri.frequency.value = f
  const saw = ctx.createOscillator()
  saw.type = 'sawtooth'
  saw.frequency.value = f
  const sawGain = ctx.createGain()
  sawGain.gain.value = 0.09
  const lp = ctx.createBiquadFilter()
  lp.type = 'lowpass'
  lp.Q.value = 0.8
  lp.frequency.setValueAtTime(1000, t)
  lp.frequency.exponentialRampToValueAtTime(240, t + 0.3)
  const env = ctx.createGain()
  env.gain.setValueAtTime(0, t)
  env.gain.linearRampToValueAtTime(vel, t + 0.006)
  env.gain.setTargetAtTime(0, t + 0.012, 0.15)
  tri.connect(lp)
  saw.connect(sawGain).connect(lp)
  lp.connect(env).connect(bus)
  for (const o of [tri, saw]) {
    o.start(t)
    o.stop(t + 1.3)
  }
}

function celestaNote(ctx: BaseAudioContext, bus: AudioNode, midi: number, t: number, vel: number) {
  const f = hz(midi)
  for (const [ratio, amp, tau] of [[1, 1, 0.32], [2, 0.16, 0.2], [4.01, 0.1, 0.07]] as const) {
    if (f * ratio > 9000) continue
    const o = ctx.createOscillator()
    o.type = 'sine'
    o.frequency.value = f * ratio
    const env = ctx.createGain()
    env.gain.setValueAtTime(0, t)
    env.gain.linearRampToValueAtTime(vel * amp, t + 0.003)
    env.gain.setTargetAtTime(0, t + 0.006, tau)
    o.connect(env).connect(bus)
    o.start(t)
    o.stop(t + 2.4)
  }
}

function fluteNote(ctx: BaseAudioContext, bus: AudioNode, midi: number, t: number, dur: number, vel: number) {
  const f = hz(midi)
  const end = t + Math.max(0.12, dur)
  const env = ctx.createGain()
  env.gain.setValueAtTime(0, t)
  env.gain.linearRampToValueAtTime(vel, t + 0.07)
  env.gain.setValueAtTime(vel * 0.92, end - 0.02)
  env.gain.setTargetAtTime(0, end, 0.07)
  env.connect(bus)
  const vib = ctx.createOscillator()
  vib.frequency.value = 5.1
  const vibDepth = ctx.createGain()
  vibDepth.gain.setValueAtTime(0, t)
  vibDepth.gain.linearRampToValueAtTime(7, t + 0.45) // cents
  vib.connect(vibDepth)
  const oscs: OscillatorNode[] = [vib]
  for (const [type, amp] of [['sine', 1], ['triangle', 0.3]] as const) {
    const o = ctx.createOscillator()
    o.type = type
    o.frequency.value = f
    vibDepth.connect(o.detune)
    const a = ctx.createGain()
    a.gain.value = amp
    o.connect(a).connect(env)
    oscs.push(o)
  }
  // breath
  const nz = ctx.createBufferSource()
  nz.buffer = noiseBuffer(ctx)
  nz.loop = true
  const bp = ctx.createBiquadFilter()
  bp.type = 'bandpass'
  bp.frequency.value = Math.min(6000, f * 2)
  bp.Q.value = 1.4
  const bg = ctx.createGain()
  bg.gain.setValueAtTime(0, t)
  bg.gain.linearRampToValueAtTime(0.1, t + 0.03)
  bg.gain.setTargetAtTime(0.025, t + 0.04, 0.08)
  nz.connect(bp).connect(bg).connect(env)
  nz.start(t)
  nz.stop(end + 0.6)
  for (const o of oscs) {
    o.start(t)
    o.stop(end + 0.6)
  }
}

function padChord(ctx: BaseAudioContext, bus: AudioNode, c: Chord, t: number, dur: number, level: number) {
  const base = rootIn(c, 55)
  const lp = ctx.createBiquadFilter()
  lp.type = 'lowpass'
  lp.frequency.value = 1100
  lp.Q.value = 0.4
  const env = ctx.createGain()
  const end = t + dur
  env.gain.setValueAtTime(0, t)
  env.gain.linearRampToValueAtTime(level, t + 0.8)
  env.gain.setValueAtTime(level, end - 0.1)
  env.gain.setTargetAtTime(0, end, 0.4)
  lp.connect(env).connect(bus)
  for (const semi of c.tones.slice(0, 4)) {
    for (const cents of [-6, 6]) {
      const o = ctx.createOscillator()
      o.type = cents < 0 ? 'triangle' : 'sine'
      o.frequency.value = hz(base + semi)
      o.detune.value = cents
      const a = ctx.createGain()
      a.gain.value = 0.3
      o.connect(a).connect(lp)
      o.start(t)
      o.stop(end + 2.5)
    }
  }
}

// ---------------------------------------------------------------- scheduling

const CELESTA_LEAD = 0.5 // celesta is quiet by nature; this lifts it when it carries the tune

function scheduleBar(ctx: BaseAudioContext, rig: Rig, t0: number, absBar: number) {
  const bar = ((absBar % BARS) + BARS) % BARS
  const sec = sectionOf(bar)
  const barInSection = bar - sec.from
  const rng = mulberry32(Math.imul(absBar + 1, 2654435761) >>> 0)
  const jit = (amt: number) => 1 + (rng() - 0.5) * amt
  const at = (step: number) => t0 + step * STEP + (step % 2 ? LILT * STEP : 0)
  const metric = (s: number) => (s % 4 === 0 ? 1 : s % 2 === 0 ? 0.85 : 0.72)
  const b = rig.buses

  for (const n of BAR_MELODY[bar]) {
    const t = at(n.step)
    const v = metric(n.step) * jit(0.12)
    if (sec.lead === 'pizz') {
      pluck(ctx, b.lead, 'lead', n.midi, t, v)
      if (sec.sparkle === 'double' && n.len >= 2 && n.midi + 12 <= 96) celestaNote(ctx, b.celesta, n.midi + 12, t + 0.012, 0.5 * v)
    } else if (sec.lead === 'flute') {
      fluteNote(ctx, b.flute, n.midi, t, n.len * STEP * 1.03, v)
      if (barInSection >= 4) pluck(ctx, b.lead, 'lead', n.midi, t, 0.4 * v) // pizz joins the flute for the second half
    } else {
      celestaNote(ctx, b.celesta, n.midi, t, CELESTA_LEAD * v)
    }
  }

  const arpScale = { roll: 1, offbeat: 1.1, sparse: 0.95 }[sec.arp]
  const pats = ARP_PATTERNS[sec.arp]
  const pat = pats[bar % pats.length]
  for (let step = 0; step < STEPS_PER_BAR; step++) {
    const idx = pat[step]
    if (idx == null) continue
    const c = chordAt(bar, step)
    pluck(ctx, b.arp, 'arp', arpTone(c, rootIn(c, 48), idx), at(step), ARP_ACCENT[step] * arpScale * jit(0.2))
  }

  for (const [step, semi, , vel] of BASS_PATTERNS[sec.bass]) {
    bassNote(ctx, b.bass, rootIn(chordAt(bar, step), 36) + semi, at(step), vel * jit(0.1))
  }

  if (sec.pad > 0) {
    const cs = BAR_CHORDS[bar]
    cs.forEach((c, i) => padChord(ctx, b.pad, c, t0 + i * 4 * STEP, (cs.length === 1 ? 8 : 4) * STEP + 0.5, 0.5 * sec.pad))
  }

  if (sec.sparkle === 'twinkle' && bar % 2 === 1) {
    ;[5, 7].forEach((step, k) => {
      const c = chordAt(bar, step)
      let m = rootIn(c, 84) + c.tones[(bar + 2 * k) % c.tones.length]
      while (m > 96) m -= 12
      celestaNote(ctx, b.celesta, m, at(step), 0.55 * jit(0.2))
    })
  }
}

/**
 * Schedule `bars` bars starting with composition bar `fromBar` (it wraps, so the loop is endless)
 * so that bar `fromBar` begins at `startTime` on the context clock. Works on any BaseAudioContext.
 */
export function schedule(ctx: BaseAudioContext, rig: Rig, startTime: number, fromBar: number, bars: number) {
  for (let i = 0; i < bars; i++) scheduleBar(ctx, rig, startTime + i * BAR_SECONDS, fromBar + i)
}

export const DEFAULT_VOLUME = 0.7
const LEVEL = 1.5
/** Slider position (0..1) to linear gain; squared so the slider feels even. */
export const levelFor = (v: number) => LEVEL * Math.min(1, Math.max(0, v)) ** 2

/** One-call offline helper: master gain, rig and `loops` full loops from t = 0. */
export function renderLoops(ctx: BaseAudioContext, destination: AudioNode, loops = 1, volume = DEFAULT_VOLUME): Rig {
  const out = ctx.createGain()
  out.gain.value = levelFor(volume)
  out.connect(destination)
  const rig = createRig(ctx, out)
  schedule(ctx, rig, 0, 0, BARS * loops)
  return rig
}

// ---------------------------------------------------------------- live engine

const KEY = 'manual.music'
const FADE_IN = 2
const FADE_OUT = 1
const DUCK_GAIN = 10 ** (-10 / 20)
const LOOKAHEAD = 8 // seconds scheduled ahead; generous so a throttled background timer still keeps up
const TICK_MS = 400

type Session = { rig: Rig; fade: GainNode; timer: ReturnType<typeof setInterval>; nextTime: number; nextBar: number }

let ctx: AudioContext | null = null
let vol: GainNode | null = null
let duckNode: GainNode | null = null
let session: Session | null = null
let starting: Promise<void> | null = null
let isOn = false
let volume = DEFAULT_VOLUME
let ducked = false
let resumeBar = 0
let hooked = false
const listeners = new Set<() => void>()

const notify = () => listeners.forEach(l => l())

function readPref(): boolean {
  try {
    return window.localStorage.getItem(KEY) === '1'
  } catch {
    return false
  }
}

function writePref(on: boolean) {
  try {
    window.localStorage.setItem(KEY, on ? '1' : '0')
  } catch {
    /* storage unavailable: preference just doesn't persist */
  }
}

function ensureContext(): AudioContext | null {
  if (ctx) return ctx
  const Ctor: typeof AudioContext | undefined =
    typeof window === 'undefined' ? undefined : window.AudioContext ?? (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext
  if (!Ctor) return null
  ctx = new Ctor({ latencyHint: 'playback' })
  const limiter = ctx.createDynamicsCompressor() // safety net so volume = 1 can never clip
  limiter.threshold.value = -3
  limiter.knee.value = 0
  limiter.ratio.value = 20
  limiter.attack.value = 0.002
  limiter.release.value = 0.15
  limiter.connect(ctx.destination)
  duckNode = ctx.createGain()
  duckNode.gain.value = ducked ? DUCK_GAIN : 1
  duckNode.connect(limiter)
  vol = ctx.createGain()
  vol.gain.value = levelFor(volume)
  vol.connect(duckNode)
  if (!hooked && typeof document !== 'undefined') {
    hooked = true
    document.addEventListener('visibilitychange', () => {
      if (isOn && ctx && ctx.state !== 'running') ctx.resume().catch(() => {})
    })
  }
  return ctx
}

function tick(s: Session, c: AudioContext) {
  const now = c.currentTime
  while (s.nextTime < now + LOOKAHEAD) {
    if (s.nextTime < now - 0.05) {
      // fell behind (timer throttled or context suspended): skip whole bars rather than clump notes into the past
      const skip = Math.ceil((now - s.nextTime) / BAR_SECONDS)
      s.nextTime += skip * BAR_SECONDS
      s.nextBar += skip
      continue
    }
    schedule(c, s.rig, s.nextTime, s.nextBar, 1)
    s.nextTime += BAR_SECONDS
    s.nextBar += 1
  }
}

async function start(): Promise<void> {
  if (isOn) return
  if (starting) return starting
  starting = (async () => {
    const c = ensureContext()
    if (!c || !vol) return
    try {
      await c.resume()
    } catch {
      /* blocked: no gesture */
    }
    if (c.state !== 'running') return
    const fade = c.createGain()
    const now = c.currentTime
    fade.gain.setValueAtTime(0, now)
    fade.gain.linearRampToValueAtTime(1, now + FADE_IN)
    fade.connect(vol)
    const s: Session = { rig: createRig(c, fade), fade, timer: 0 as never, nextTime: now + 0.15, nextBar: resumeBar }
    tick(s, c)
    s.timer = setInterval(() => tick(s, c), TICK_MS)
    session = s
    isOn = true
    writePref(true)
    notify()
  })().finally(() => {
    starting = null
  })
  return starting
}

function stop(): void {
  if (!isOn || !session || !ctx) return
  const s = session
  const c = ctx
  isOn = false
  session = null
  writePref(false)
  clearInterval(s.timer)
  const now = c.currentTime
  resumeBar = (((s.nextBar - Math.max(0, Math.ceil((s.nextTime - now) / BAR_SECONDS))) % BARS) + BARS) % BARS
  s.fade.gain.cancelScheduledValues(now)
  s.fade.gain.setValueAtTime(s.fade.gain.value, now)
  s.fade.gain.linearRampToValueAtTime(0, now + FADE_OUT)
  setTimeout(() => {
    disposeRig(s.rig)
    s.fade.disconnect()
    if (!session) c.suspend().catch(() => {})
  }, (FADE_OUT + 0.15) * 1000)
  notify()
}

async function toggle(): Promise<boolean> {
  if (isOn) stop()
  else await start()
  return isOn
}

function setVolume(v: number) {
  volume = Math.min(1, Math.max(0, Number.isFinite(v) ? v : DEFAULT_VOLUME))
  if (vol && ctx) vol.gain.setTargetAtTime(levelFor(volume), ctx.currentTime, 0.04)
}

/** Lower the music about 10 dB (smoothly) while a narration voice speaks. */
function duck(on: boolean) {
  ducked = on
  if (duckNode && ctx) {
    const g = duckNode.gain
    g.cancelScheduledValues(ctx.currentTime)
    g.setTargetAtTime(on ? DUCK_GAIN : 1, ctx.currentTime, on ? 0.12 : 0.45)
  }
}

export interface MusicApi {
  /** Must be called from a user gesture (autoplay policy). Resolves once playing, or without playing if the browser refused. */
  start(): Promise<void>
  /** Fades out over ~1 s. */
  stop(): void
  toggle(): Promise<boolean>
  readonly on: boolean
  /** v: 0..1 (default 0.7). */
  setVolume(v: number): void
  duck(on: boolean): void
  /** Saved preference (localStorage "manual.music"); true means the HUD should start music on the first click. Defaults to false. */
  wanted(): boolean
  /** For useSyncExternalStore: called whenever `on` changes. */
  subscribe(listener: () => void): () => void
}

export const music: MusicApi = {
  start,
  stop,
  toggle,
  get on() {
    return isOn
  },
  setVolume,
  duck,
  wanted: readPref,
  subscribe(listener) {
    listeners.add(listener)
    return () => void listeners.delete(listener)
  },
}
