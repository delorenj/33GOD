#!/usr/bin/env node
// Render narration lines through Voxxy (https://vox.delo.sh) into sandbox/public/voice/.
//
//   node tools/voice/render.mjs <items.json|-> [options]
//
// items.json is a JSON list of { id, role, text } (or { "items": [...] }). `role` is a key of voices.json "roles"
// (narrator | tips | floor) or a voice id (narrator-steady, ...), which is how auditions pick a specific variant.
//
// Output: <out>/<id>.<format> per item and <out>/manifest.json mapping id -> { file, hash, duration, ... }.
// Idempotent and resumable: an item whose hash (role + text + resolved voice config + output settings) matches the
// manifest and whose file exists is skipped. The manifest is rewritten atomically after every item, so an interrupted
// run loses at most the line in flight. Lines render serially (the service holds one GPU lock anyway).
//
// Options
//   --out DIR            output dir (default sandbox/public/voice)
//   --voices FILE        voice config (default tools/voice/voices.json)
//   --voice role=voice   override the voice a role resolves to, repeatable (--voice narrator=narrator-wry)
//   --format mp3|ogg|m4a|wav   override voices.json output.format
//   --only id,id         render just these ids
//   --force              re-render even when the hash matches
//   --prune              delete files + manifest entries that are not in this items list
//   --dry-run            list what would render and a time estimate; call nothing
//
// Env: VOX_URL (default from voices.json), VOX_API_KEY or VOX_API_KEY_OP (an op:// reference, read with `op read`).
// The service currently needs no key; nothing secret is ever written to a file.

import { createHash } from 'node:crypto'
import { spawn } from 'node:child_process'
import fs from 'node:fs/promises'
import path from 'node:path'
import process from 'node:process'
import { fileURLToPath } from 'node:url'

const HERE = path.dirname(fileURLToPath(import.meta.url))
const SANDBOX = path.resolve(HERE, '..', '..')
const REF_MAX_SECONDS = 15 // service cap for a per-request reference clip
const REF_MAX_BYTES = 2 * 1024 * 1024
const ID_RE = /^[A-Za-z0-9][A-Za-z0-9._-]*$/
const CHARS_PER_SECOND = 21 // measured synthesis speed on the 3090, used only for --dry-run estimates

// ---------------------------------------------------------------- args

function parseArgs(argv) {
  const a = { items: null, out: path.join(SANDBOX, 'public', 'voice'), voices: path.join(HERE, 'voices.json'),
    overrides: {}, format: null, only: null, force: false, prune: false, dryRun: false }
  for (let i = 0; i < argv.length; i++) {
    const t = argv[i]
    const val = () => { if (i + 1 >= argv.length) die(`${t} needs a value`); return argv[++i] }
    if (t === '--out') a.out = path.resolve(val())
    else if (t === '--voices') a.voices = path.resolve(val())
    else if (t === '--voice') {
      const [r, v] = val().split('=')
      if (!r || !v) die('--voice wants role=voice')
      a.overrides[r] = v
    } else if (t === '--format') a.format = val()
    else if (t === '--only') a.only = new Set(val().split(',').map((s) => s.trim()).filter(Boolean))
    else if (t === '--force') a.force = true
    else if (t === '--prune') a.prune = true
    else if (t === '--dry-run' || t === '--check') a.dryRun = true
    else if (t === '-h' || t === '--help') { console.log(usage()); process.exit(0) }
    else if (t.startsWith('--')) die(`unknown option ${t}`)
    else if (a.items === null) a.items = t
    else die(`unexpected argument ${t}`)
  }
  if (a.items === null) die('usage: render.mjs <items.json|-> [--out DIR] [--only id,id] [--force] [--prune] [--dry-run]')
  return a
}

function usage() {
  return 'Usage: node tools/voice/render.mjs <items.json|-> [--out DIR] [--voices FILE] [--voice role=voice] [--format mp3|ogg|m4a|wav] [--only id,id] [--force] [--prune] [--dry-run]\nSee the comment block at the top of this file.'
}

function die(msg) {
  console.error(`render: ${msg}`)
  process.exit(2)
}

// ---------------------------------------------------------------- helpers

const canon = (v) => JSON.stringify(sortKeys(v))
function sortKeys(v) {
  if (Array.isArray(v)) return v.map(sortKeys)
  if (v && typeof v === 'object') return Object.fromEntries(Object.keys(v).sort().map((k) => [k, sortKeys(v[k])]))
  return v
}
const sha = (s) => createHash('sha256').update(s).digest('hex')
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

// voices.json "lexicon": { word: respelling } for words the voices mangle ("idempotent" -> "eye-dem-poh-tent").
// Applied to what is SENT to the service (and hashed); the items list and the manifest keep the original copy.
function applyLexicon(lexicon, text) {
  let out = text
  for (const [word, say] of Object.entries(lexicon ?? {})) {
    out = out.replace(new RegExp(`\\b${word.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'gi'), say)
  }
  return out
}

async function exists(p) { try { await fs.access(p); return true } catch { return false } }

async function writeAtomic(file, data) {
  const tmp = `${file}.${process.pid}.part`
  await fs.writeFile(tmp, data)
  await fs.rename(tmp, file)
}

function run(cmd, args, { input, capture = 'stdout' } = {}) {
  return new Promise((resolve, reject) => {
    const p = spawn(cmd, args, { stdio: ['pipe', 'pipe', 'pipe'] })
    const out = []
    const err = []
    p.stdout.on('data', (d) => out.push(d))
    p.stderr.on('data', (d) => err.push(d))
    p.on('error', reject)
    p.on('close', (code) => {
      const so = Buffer.concat(out)
      const se = Buffer.concat(err).toString()
      if (code === 0 || capture === 'stderr-ok') resolve({ stdout: so, stderr: se, code })
      else reject(new Error(`${cmd} exited ${code}: ${se.split('\n').slice(-6).join('\n')}`))
    })
    p.stdin.on('error', () => {}) // ffmpeg may close stdin early on error; the exit code reports it
    p.stdin.end(input)
  })
}

function wavSeconds(buf) {
  // 44-byte-header PCM WAV from the service; parse fmt + data chunks to be safe.
  if (buf.length < 44 || buf.toString('ascii', 0, 4) !== 'RIFF') throw new Error('response is not a WAV')
  let pos = 12
  let byteRate = 0
  while (pos + 8 <= buf.length) {
    const id = buf.toString('ascii', pos, pos + 4)
    const size = buf.readUInt32LE(pos + 4)
    if (id === 'fmt ') byteRate = buf.readUInt32LE(pos + 16)
    if (id === 'data') return byteRate ? Math.min(size, buf.length - pos - 8) / byteRate : 0
    pos += 8 + size + (size % 2)
  }
  throw new Error('WAV has no data chunk')
}

// ---------------------------------------------------------------- Voxxy client

let apiKeyPromise = null
function apiKey() {
  if (!apiKeyPromise) {
    apiKeyPromise = (async () => {
      if (process.env.VOX_API_KEY) return process.env.VOX_API_KEY
      const ref = process.env.VOX_API_KEY_OP
      if (ref) return (await run('op', ['read', ref])).stdout.toString().trim()
      return null
    })()
  }
  return apiKeyPromise
}

async function synthesize(cfg, body) {
  const base = (process.env.VOX_URL || cfg.service.url).replace(/\/+$/, '')
  const headers = { 'content-type': 'application/json' }
  const key = await apiKey()
  if (key) headers['x-api-key'] = key
  const payload = { engines: cfg.service.engines, ...body }
  let lastErr
  for (let attempt = 1; attempt <= (cfg.service.retries ?? 3); attempt++) {
    try {
      const res = await fetch(`${base}/synthesize`, {
        method: 'POST', headers, body: JSON.stringify(payload), signal: AbortSignal.timeout(cfg.service.timeoutMs ?? 180000),
      })
      if (!res.ok) {
        const detail = (await res.text()).slice(0, 300)
        const e = new Error(`vox ${res.status}: ${detail}`)
        e.retry = res.status >= 500 || res.status === 429
        throw e
      }
      const engine = res.headers.get('x-vox-engine')
      if (cfg.service.engines && !cfg.service.engines.includes(engine)) throw new Error(`engine ${engine} answered, not one of ${cfg.service.engines}; refusing a stranger's voice`)
      return { wav: Buffer.from(await res.arrayBuffer()), engine, source: res.headers.get('x-vox-voice-source') }
    } catch (e) {
      lastErr = e
      if (e.retry === false || (e.message.startsWith('vox 4') && e.retry !== true)) break
      if (attempt < (cfg.service.retries ?? 3)) await sleep(1500 * attempt)
    }
  }
  throw lastErr
}

// ---------------------------------------------------------------- stage 1: design the reference clip

const refJobs = new Map()
function ensureRef(cfg, name, voice) {
  if (!refJobs.has(name)) refJobs.set(name, makeRef(cfg, name, voice))
  return refJobs.get(name)
}

async function makeRef(cfg, name, voice) {
  const d = voice.design
  const key = sha(canon({ d, engines: cfg.service.engines })).slice(0, 12)
  const dir = path.join(HERE, '.cache', 'refs')
  const file = path.join(dir, `${name}-${key}.wav`)
  let wav
  if (await exists(file)) wav = await fs.readFile(file)
  else {
    console.log(`  designing ${name} (seed ${d.seed}): ${d.description}`)
    const r = await synthesize(cfg, { text: `(${d.description})${d.text}`, seed: d.seed, cfg: d.cfg, steps: d.steps })
    wav = r.wav
    await fs.mkdir(dir, { recursive: true })
    await writeAtomic(file, wav)
  }
  const seconds = wavSeconds(wav)
  if (seconds > REF_MAX_SECONDS || wav.length > REF_MAX_BYTES)
    throw new Error(`reference for ${name} is ${seconds.toFixed(1)} s / ${wav.length} B, over the service cap (${REF_MAX_SECONDS} s / 2 MiB). Shorten design.text, then delete ${file}`)
  return { b64: wav.toString('base64'), seconds }
}

// ---------------------------------------------------------------- stage 2: a line

async function renderLine(cfg, name, voice, text) {
  const ref = await ensureRef(cfg, name, voice)
  const s = voice.synth ?? {}
  const body = { cfg: s.cfg, steps: s.steps, seed: s.seed, normalize: s.normalize ?? false, reference_audio_b64: ref.b64 }
  if ((voice.mode ?? 'clone') === 'clone') {
    body.text = text
    body.prompt_text = voice.design.text // continuation cloning: biggest consistency lever
  } else {
    body.text = `(${voice.style ?? voice.design.description})${text}`
  }
  for (const k of Object.keys(body)) if (body[k] === undefined) delete body[k]
  const r = await synthesize(cfg, body)
  if (r.source && r.source !== 'reference') throw new Error(`service answered with voice source "${r.source}", not the reference clip`)
  return r.wav
}

// ---------------------------------------------------------------- encode

const FORMATS = {
  mp3: { muxer: 'mp3', codec: ['-c:a', 'libmp3lame', '-q:a', '4', '-ac', '1', '-ar', '44100'] },
  ogg: { muxer: 'ogg', codec: ['-c:a', 'libopus', '-b:a', '56k', '-ac', '1'] },
  m4a: { muxer: 'ipod', codec: ['-c:a', 'aac', '-b:a', '72k', '-ac', '1', '-movflags', '+faststart'] },
  wav: { muxer: 'wav', codec: ['-c:a', 'pcm_s16le', '-ac', '1'] },
}

const TRIM = 'silenceremove=start_periods=1:start_threshold=-48dB:start_silence=0.06,areverse,silenceremove=start_periods=1:start_threshold=-48dB:start_silence=0.12,areverse'

async function ff(args, input) {
  return run('ffmpeg', ['-hide_banner', '-nostdin', '-loglevel', 'info', ...args], { input, capture: 'stderr-ok' })
}

async function measureLoudness(wav, pre) {
  const filter = `${pre}loudnorm=I=-18:TP=-2:LRA=11:print_format=json`
  const r = await ff(['-f', 'wav', '-i', 'pipe:0', '-af', filter, '-f', 'null', '-'], wav)
  const m = r.stderr.match(/\{[\s\S]*"target_offset"[\s\S]*?\}/)
  if (!m) return null
  const j = JSON.parse(m[0])
  const i = parseFloat(j.input_i)
  return Number.isFinite(i) ? j : null
}

async function encode(cfg, fmtName, wav, outFile, voice) {
  const fmt = FORMATS[fmtName]
  const out = cfg.output ?? {}
  const pre = out.trimSilence === false ? '' : `${TRIM},`
  const gain = voice.gainDb ?? 0
  let filter = pre.replace(/,$/, '')
  const target = out.loudnessLufs
  if (typeof target === 'number') {
    const m = await measureLoudness(wav, pre)
    if (m) {
      const ln = `loudnorm=I=${target + gain}:TP=-2:LRA=11:measured_I=${m.input_i}:measured_TP=${m.input_tp}:measured_LRA=${m.input_lra}:measured_thresh=${m.input_thresh}:offset=${m.target_offset}:linear=true`
      filter = filter ? `${filter},${ln}` : ln
    } else if (gain) filter = `${filter ? `${filter},` : ''}volume=${gain}dB`
  } else if (gain) filter = `${filter ? `${filter},` : ''}volume=${gain}dB`
  const tmp = `${outFile}.${process.pid}.part`
  const args = ['-y', '-f', 'wav', '-i', 'pipe:0']
  if (filter) args.push('-af', filter)
  args.push(...fmt.codec, '-f', fmt.muxer, tmp)
  await ff(args, wav)
  await fs.rename(tmp, outFile)
  const probe = await run('ffprobe', ['-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', outFile])
  return Math.round(parseFloat(probe.stdout.toString().trim()) * 1000) / 1000
}

// ---------------------------------------------------------------- main

async function main() {
  const args = parseArgs(process.argv.slice(2))
  const cfg = JSON.parse(await fs.readFile(args.voices, 'utf8'))
  const fmtName = args.format ?? cfg.output?.format ?? 'mp3'
  if (!FORMATS[fmtName]) die(`unknown format ${fmtName} (${Object.keys(FORMATS).join(', ')})`)

  const raw = args.items === '-' ? await new Promise((res) => { let s = ''; process.stdin.on('data', (d) => (s += d)); process.stdin.on('end', () => res(s)) }) : await fs.readFile(args.items, 'utf8')
  let items = JSON.parse(raw)
  if (!Array.isArray(items)) items = items.items
  if (!Array.isArray(items)) die('items.json must be a list of { id, role, text }')

  const roles = { ...cfg.roles, ...args.overrides }
  const seen = new Set()
  const jobs = []
  for (const [n, it] of items.entries()) {
    const where = `item ${n} (${it?.id ?? '?'})`
    if (!it || typeof it.id !== 'string' || !ID_RE.test(it.id)) die(`${where}: id must match ${ID_RE}`)
    if (seen.has(it.id)) die(`${where}: duplicate id`)
    seen.add(it.id)
    if (typeof it.text !== 'string' || !it.text.trim()) die(`${where}: empty text`)
    const name = roles[it.role] ?? (cfg.voices[it.role] ? it.role : null)
    if (!name || !cfg.voices[name]) die(`${where}: role "${it.role}" is not a role (${Object.keys(roles)}) or a voice (${Object.keys(cfg.voices)})`)
    const voice = cfg.voices[name]
    if (it.text.trimStart().startsWith('(')) console.warn(`  warning: ${it.id} starts with "(", VoxCPM reads a leading parenthesis as a style description`)
    const spoken = applyLexicon(cfg.lexicon, it.text) // hash the spoken text: a lexicon edit re-renders only the lines it touches
    const hash = sha(canon({ v: 1, role: it.role, text: spoken, voice: name, cfgv: voice, format: fmtName, enc: [FORMATS[fmtName].codec, TRIM], out: cfg.output, engines: cfg.service.engines })).slice(0, 16)
    jobs.push({ id: it.id, role: it.role, text: it.text, spoken, name, voice, hash })
  }

  const manifestFile = path.join(args.out, 'manifest.json')
  let manifest = {}
  try { manifest = JSON.parse(await fs.readFile(manifestFile, 'utf8')) } catch {}

  const todo = []
  for (const j of jobs) {
    if (args.only && !args.only.has(j.id)) continue
    const e = manifest[j.id]
    const fresh = !args.force && e && e.hash === j.hash && (await exists(path.join(args.out, e.file)))
    if (!fresh) todo.push(j)
  }
  const skipped = jobs.length - todo.length
  const chars = todo.reduce((s, j) => s + j.text.length, 0)
  console.log(`${jobs.length} items, ${skipped} up to date, ${todo.length} to render (${chars} chars, about ${Math.ceil(chars / CHARS_PER_SECOND / 60)} min) -> ${args.out} [${fmtName}]`)
  if (args.dryRun) { for (const j of todo) console.log(`  would render ${j.id} [${j.name}] ${j.text.length} chars`); return }

  await fs.mkdir(args.out, { recursive: true })
  for (const f of await fs.readdir(args.out)) if (f.endsWith('.part')) await fs.rm(path.join(args.out, f), { force: true }) // debris of a killed run
  let failed = 0
  let done = 0
  for (const j of todo) {
    const t0 = Date.now()
    try {
      const wav = await renderLine(cfg, j.name, j.voice, j.spoken)
      const file = `${j.id}.${fmtName}`
      const duration = await encode(cfg, fmtName, wav, path.join(args.out, file), j.voice)
      manifest[j.id] = { file, hash: j.hash, duration, role: j.role, voice: j.name }
      await writeAtomic(manifestFile, JSON.stringify(manifest, null, 2) + '\n')
      done++
      console.log(`[${done + failed}/${todo.length}] ${j.id} [${j.name}] ${duration.toFixed(2)} s in ${((Date.now() - t0) / 1000).toFixed(1)} s`)
    } catch (e) {
      failed++
      console.error(`[${done + failed}/${todo.length}] ${j.id} FAILED: ${e.message}`)
    }
  }

  if (args.prune) {
    const keep = new Set(jobs.map((j) => j.id))
    for (const id of Object.keys(manifest)) {
      if (keep.has(id)) continue
      await fs.rm(path.join(args.out, manifest[id].file), { force: true })
      delete manifest[id]
      console.log(`pruned ${id}`)
    }
    await writeAtomic(manifestFile, JSON.stringify(manifest, null, 2) + '\n')
  }
  console.log(`done: ${done} rendered, ${skipped} cached, ${failed} failed`)
  if (failed) process.exit(1)
}

main().catch((e) => { console.error(`render: ${e.stack || e.message}`); process.exit(1) })
