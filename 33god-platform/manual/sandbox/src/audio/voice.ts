// Narration player: one voice at a time, global mute, no-ops when audio is missing.
//
// Audio is rendered offline by tools/voice/render.mjs into public/voice/ (gitignored) together with
// manifest.json: { [id]: { file, hash, duration } }. Both are fetched relative to the page, so this works
// under the /sandbox/ base in dev and in the built site. Nothing here ever throws or rejects: a missing
// manifest, a missing file, a blocked autoplay or a muted state all resolve `say()` to `false`.
//
//   voice.say('intro-1')           // stops whatever is speaking, plays this line; resolves true if it played to the end
//   voice.stop()
//   voice.setMuted(true) / voice.toggleMute() / voice.muted
//   voice.onSpeaking((on) => ...)  // true when a line starts sounding, false when it ends or is cut off (duck the music)
//   voice.onMuted((muted) => ...)  // for the HUD toggle
//
// The mute flag persists in localStorage under `manual.voice` as {"muted": boolean}. Every storage access is guarded.

export interface VoiceEntry { file: string; hash: string; duration: number }
type Manifest = Record<string, VoiceEntry>

const STORAGE_KEY = 'manual.voice'
const MANIFEST_URL = 'voice/manifest.json'
const MANIFEST_RETRY_MS = 5000

// ---- persisted mute ---------------------------------------------------------------------------------------------

function readMuted(): boolean {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    if (raw === null) return false
    if (/^(1|true|muted|off)$/i.test(raw.trim())) return true
    const v: unknown = JSON.parse(raw)
    return typeof v === 'object' && v !== null && (v as { muted?: unknown }).muted === true
  } catch {
    return false
  }
}

function writeMuted(muted: boolean): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify({ muted }))
  } catch {
    /* private window, blocked storage, quota: the toggle still works for this session */
  }
}

// ---- state ------------------------------------------------------------------------------------------------------

let muted = readMuted()
let speaking = false
let manifest: Manifest | null = null
let manifestLoad: Promise<Manifest | null> | null = null
let manifestFailedAt = 0
let audio: HTMLAudioElement | null = null
let current: { token: number; finish: (completed: boolean) => void } | null = null
let token = 0

const speakingListeners = new Set<(speaking: boolean) => void>()
const mutedListeners = new Set<(muted: boolean) => void>()

function emit<T>(listeners: Set<(v: T) => void>, value: T): void {
  for (const cb of [...listeners]) {
    try { cb(value) } catch { /* a bad subscriber must not break playback */ }
  }
}

function setSpeaking(next: boolean): void {
  if (speaking === next) return
  speaking = next
  emit(speakingListeners, next)
}

// ---- manifest ---------------------------------------------------------------------------------------------------

function isManifest(v: unknown): v is Manifest {
  return typeof v === 'object' && v !== null && !Array.isArray(v)
}

function loadManifest(): Promise<Manifest | null> {
  if (manifest) return Promise.resolve(manifest)
  if (manifestLoad) return manifestLoad
  if (manifestFailedAt && Date.now() - manifestFailedAt < MANIFEST_RETRY_MS) return Promise.resolve(null)
  manifestLoad = (async () => {
    try {
      const res = await fetch(MANIFEST_URL, { cache: 'no-cache' })
      if (!res.ok) throw new Error(`manifest ${res.status}`)
      // The Vite dev server answers a missing file with index.html and a 200; JSON.parse rejects that.
      const json: unknown = JSON.parse(await res.text())
      if (!isManifest(json)) throw new Error('manifest is not an object')
      manifest = json
      manifestFailedAt = 0
      return manifest
    } catch {
      manifestFailedAt = Date.now()
      return null
    } finally {
      manifestLoad = null
    }
  })()
  return manifestLoad
}

function entryFor(m: Manifest, id: string): VoiceEntry | null {
  const e = Object.prototype.hasOwnProperty.call(m, id) ? m[id] : undefined
  return e && typeof e.file === 'string' ? e : null
}

// ---- playback ---------------------------------------------------------------------------------------------------

function getAudio(): HTMLAudioElement | null {
  if (audio) return audio
  try {
    audio = new Audio()
    audio.preload = 'auto'
    return audio
  } catch {
    return null
  }
}

function endCurrent(completed: boolean): void {
  const c = current
  current = null
  setSpeaking(false)
  c?.finish(completed)
}

async function say(id: string): Promise<boolean> {
  if (muted) return false
  const my = ++token
  // A new line always cuts off the old one, even if this one turns out to be missing.
  if (current) endCurrent(false)
  const el = getAudio()
  if (el) el.pause()

  const m = await loadManifest()
  if (my !== token || muted || !m || !el) return false // superseded, muted meanwhile, or nothing to play
  const entry = entryFor(m, id)
  if (!entry) return false

  return new Promise<boolean>((resolve) => {
    let settled = false
    const cleanup = () => {
      el.removeEventListener('ended', onEnded)
      el.removeEventListener('error', onError)
      el.removeEventListener('playing', onPlaying)
    }
    const finish = (completed: boolean) => {
      if (settled) return
      settled = true
      cleanup()
      resolve(completed)
    }
    const onEnded = () => { if (current?.token === my) endCurrent(true) }
    const onError = () => { if (current?.token === my) endCurrent(false) }
    const onPlaying = () => { if (current?.token === my) setSpeaking(true) }

    current = { token: my, finish }
    el.addEventListener('ended', onEnded)
    el.addEventListener('error', onError)
    el.addEventListener('playing', onPlaying)
    try {
      // The hash busts the browser cache when a line is re-rendered under the same id.
      el.src = `voice/${encodeURIComponent(entry.file)}?v=${encodeURIComponent(entry.hash ?? '')}`
      const p = el.play()
      if (p && typeof p.catch === 'function') {
        p.catch(() => { if (current?.token === my) endCurrent(false) }) // autoplay blocked, file missing, decode error
      }
    } catch {
      if (current?.token === my) endCurrent(false)
    }
  })
}

function stop(): void {
  token++ // also cancels a say() still waiting on the manifest
  if (audio) {
    try { audio.pause() } catch { /* ignore */ }
  }
  if (current) endCurrent(false)
  else setSpeaking(false)
}

function setMuted(next: boolean): void {
  if (muted === next) return
  muted = next
  writeMuted(next)
  if (next) stop()
  emit(mutedListeners, next)
}

export const voice = {
  say,
  stop,
  setMuted,
  toggleMute(): boolean { setMuted(!muted); return muted },
  get muted(): boolean { return muted },
  get speaking(): boolean { return speaking },
  /** Seconds a line runs, or null when the manifest or the id is missing. Useful for timing a beat. */
  async duration(id: string): Promise<number | null> {
    const m = await loadManifest()
    const e = m ? entryFor(m, id) : null
    return e && Number.isFinite(e.duration) ? e.duration : null
  },
  /** Subscribe to speaking on/off. Returns the unsubscribe function. Does not fire on subscribe; read `voice.speaking`. */
  onSpeaking(cb: (speaking: boolean) => void): () => void {
    speakingListeners.add(cb)
    return () => { speakingListeners.delete(cb) }
  },
  /** Subscribe to mute changes. Returns the unsubscribe function. */
  onMuted(cb: (muted: boolean) => void): () => void {
    mutedListeners.add(cb)
    return () => { mutedListeners.delete(cb) }
  },
}

export default voice
