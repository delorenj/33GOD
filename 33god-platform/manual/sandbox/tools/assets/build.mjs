// mise run assets: build every stale Factory asset glb (contract section 2).
// For each src/assets/<id>/build.py (and the forge's test fixture), when public/assets/<id>/model.glb is missing
// or older than its build.py / asset.json / the harness, run Blender headless through blender_run.py, validate the
// glb against asset.json, and only then put it in place. A failed asset loses its glb (the floor falls back to
// the primitive) and the build carries on. Assets build one at a time: Blender is heavy.
//
// node tools/assets/build.mjs [--force] [--only id,id] [--strict] [--json] [--no-fixture]
import { spawnSync } from 'node:child_process'
import { copyFileSync, existsSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, rmSync, statSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { SET_DOMAIN, parseManifest } from '../../src/assets/contract.ts'
import { validate } from './validate.mjs'

const HERE = dirname(fileURLToPath(import.meta.url))
const ROOT = resolve(HERE, '../..')
const SRC = join(ROOT, 'src/assets')
const OUT = join(ROOT, 'public/assets')
const FIXTURE = join(ROOT, 'forge/fixture')
const HARNESS = [join(HERE, 'blender_run.py'), join(HERE, 'factory.py')]

const args = process.argv.slice(2)
const flag = (f) => args.includes(f)
const only = (() => { const i = args.indexOf('--only'); return i >= 0 ? new Set(args[i + 1].split(',')) : null })()
const json = flag('--json')
const log = (...m) => { if (!json) console.log(...m) }
const warn = (...m) => console.warn('assets:', ...m)

function findBlender() {
  const cands = [process.env.BLENDER, join(process.env.HOME ?? '', '.local/bin/blender')].filter(Boolean)
  for (const c of cands) if (existsSync(c)) return c
  const w = spawnSync('sh', ['-c', 'command -v blender'], { encoding: 'utf8' })
  return w.status === 0 ? w.stdout.trim() : null
}

/** The floor palette (`export const C = {...}` in Props.tsx) and the domain colours (domains.ts), read as text. */
function palette() {
  const props = readFileSync(join(ROOT, 'src/world/Props.tsx'), 'utf8')
  const block = props.match(/export const C = \{([\s\S]*?)\n\}/)?.[1] ?? ''
  const C = Object.fromEntries([...block.matchAll(/(\w+):\s*'(#[0-9A-Fa-f]{6})'/g)].map((m) => [m[1], m[2]]))
  const doms = readFileSync(join(ROOT, 'src/domains.ts'), 'utf8')
  const domains = Object.fromEntries([...doms.matchAll(/\{ id: '(\w+)',[^}]*?color: '(#[0-9A-Fa-f]{6})'/g)].map((m) => [m[1], m[2]]))
  return { C, domains }
}

function readCast() {
  const p = join(ROOT, 'src/cast.generated.json')
  if (!existsSync(p)) return null
  try { return JSON.parse(readFileSync(p, 'utf8')) } catch (e) { warn(`cast.generated.json unreadable: ${e.message}`); return null }
}

function sources() {
  const out = []
  if (existsSync(SRC)) {
    for (const d of readdirSync(SRC, { withFileTypes: true })) {
      if (!d.isDirectory()) continue
      const dir = join(SRC, d.name)
      if (!existsSync(join(dir, 'asset.json'))) continue
      out.push({ id: d.name, dir, fixture: false })
    }
  }
  if (!flag('--no-fixture') && existsSync(join(FIXTURE, 'asset.json'))) out.push({ id: 'fixture', dir: FIXTURE, fixture: true })
  return out.sort((a, b) => a.id.localeCompare(b.id))
}

const mtime = (p) => (existsSync(p) ? statSync(p).mtimeMs : 0)

function main() {
  const all = sources()
  const results = []
  // prune glbs whose source is gone, so a deleted asset does not linger in the deploy
  if (existsSync(OUT)) {
    const ids = new Set(all.map((s) => s.id))
    for (const d of readdirSync(OUT, { withFileTypes: true })) if (d.isDirectory() && !ids.has(d.name)) { rmSync(join(OUT, d.name), { recursive: true, force: true }); log(`assets: pruned public/assets/${d.name} (no source)`) }
  }
  const todo = all.filter((s) => !only || only.has(s.id))
  if (!todo.length) { log('assets: nothing to build'); if (json) console.log(JSON.stringify(results)); return 0 }
  const { C, domains } = palette()
  const cast = readCast()
  if (!cast) warn('src/cast.generated.json not found: asset ids are not checked against the registry and domain colours fall back to Bloodbank blue')
  const blender = findBlender()

  for (const s of todo) {
    const r = { id: s.id, status: 'fresh', errors: [], warnings: [] }
    results.push(r)
    const glb = join(OUT, s.id, 'model.glb')
    const buildPy = join(s.dir, 'build.py')
    const manPath = join(s.dir, 'asset.json')
    const fail = (why) => {
      r.status = 'failed'
      r.errors.push(...[].concat(why))
      if (existsSync(glb)) rmSync(glb) // the floor falls back to the primitive rather than show a stale or broken body
      warn(`${s.id}: FAILED, skipped (${r.errors.join('; ')})`)
    }
    let raw
    try { raw = JSON.parse(readFileSync(manPath, 'utf8')) } catch (e) { fail(`asset.json: ${e.message}`); continue }
    const parsed = parseManifest(raw, s.id)
    if (!parsed.ok) { fail(parsed.why.map((w) => `asset.json: ${w}`)); continue }
    const m = parsed.manifest
    if (!existsSync(buildPy)) { fail('build.py is missing'); continue }
    const comp = cast?.components?.[s.id]
    if (cast && !comp && !s.fixture) { fail(`"${s.id}" is not an Atlas registry id (components/<id>.yaml)`); continue }
    if (!s.fixture && !existsSync(join(s.dir, 'NOTES.md'))) r.warnings.push('NOTES.md is missing (required by the contract)')
    const stale = flag('--force') || mtime(glb) < Math.max(mtime(buildPy), mtime(manPath), ...HARNESS.map(mtime))
    if (!stale) { log(`assets: ${s.id} up to date`); continue }
    if (!blender) { fail('Blender not found (set BLENDER or install ~/.local/bin/blender)'); continue }

    const set = comp?.station ?? comp?.near ?? null
    const domain = (set && SET_DOMAIN[set]) || 'bloodbank'
    const tmp = mkdtempSync(join(tmpdir(), `factory-asset-${s.id}-`))
    const out = join(tmp, 'model.glb')
    const ctx = join(tmp, 'ctx.json')
    writeFileSync(ctx, JSON.stringify({ id: s.id, build_py: buildPy, out, manifest: m, palette: C, domains, domain, domain_color: domains[domain] }))
    log(`assets: building ${s.id} (${m.placement}${set ? ` at ${set}` : ''}, domain ${domain})`)
    const t0 = Date.now()
    const run = spawnSync(blender, ['-b', '--factory-startup', '--python-exit-code', '1', '-P', HARNESS[0], '--', '--ctx', ctx], { encoding: 'utf8', timeout: 300_000, maxBuffer: 64 << 20 })
    r.seconds = +((Date.now() - t0) / 1000).toFixed(1)
    if (run.status !== 0 || !existsSync(out)) {
      const tail = `${run.stdout ?? ''}\n${run.stderr ?? ''}`.trim().split('\n').slice(-25).join('\n')
      if (!json) console.error(tail)
      fail(run.error ? `blender: ${run.error.message}` : `blender exited ${run.status}`)
      rmSync(tmp, { recursive: true, force: true })
      continue
    }
    const v = validate(out, m)
    Object.assign(r, { tris: v.tris, kb: v.kb, clips: v.clips, sockets: v.sockets })
    r.warnings.push(...v.warnings)
    if (!v.ok) { fail(v.errors); rmSync(tmp, { recursive: true, force: true }); continue }
    mkdirSync(dirname(glb), { recursive: true })
    copyFileSync(out, glb)
    rmSync(tmp, { recursive: true, force: true })
    r.status = 'built'
    log(`assets: ${s.id} built in ${r.seconds} s: ${v.tris} tris, ${v.kb} KB, clips ${Object.entries(v.clips).map(([k, d]) => `${k} ${d}s`).join(', ')}`)
    for (const w of r.warnings) warn(`${s.id}: ${w}`)
  }
  const failed = results.filter((r) => r.status === 'failed')
  log(`assets: ${results.filter((r) => r.status === 'built').length} built, ${results.filter((r) => r.status === 'fresh').length} up to date, ${failed.length} failed`)
  if (json) console.log(JSON.stringify(results, null, 2))
  return flag('--strict') && failed.length ? 1 : 0
}

process.exit(main())
