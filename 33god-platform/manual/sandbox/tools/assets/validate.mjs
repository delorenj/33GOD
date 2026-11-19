// Reads a .glb's JSON chunk and checks it against its asset.json (contract sections 3 and 4): triangle count,
// file size, the four named clips (and their lengths), the three socket nodes, image textures.
// Usage: node tools/assets/validate.mjs <model.glb> <asset.json>   (exit 1 when the asset fails)
import { readFileSync, statSync } from 'node:fs'
import { CLIP_ROLES, CLIP_SECONDS, MAX_GLB_KB, MAX_TRIS } from '../../src/assets/contract.ts'

/** The glTF JSON of a binary glTF (throws on a malformed file). */
export function glbJson(buf) {
  if (buf.length < 20 || buf.readUInt32LE(0) !== 0x46546c67) throw new Error('not a glb (bad magic)')
  if (buf.readUInt32LE(4) !== 2) throw new Error(`glTF version ${buf.readUInt32LE(4)}, expected 2`)
  const len = buf.readUInt32LE(12)
  if (buf.readUInt32LE(16) !== 0x4e4f534a) throw new Error('first chunk is not JSON')
  return JSON.parse(buf.subarray(20, 20 + len).toString('utf8'))
}

/** Triangles drawn: every mesh primitive, once per node that uses the mesh. */
export function triangles(gltf) {
  const uses = new Map()
  for (const n of gltf.nodes ?? []) if (n.mesh !== undefined) uses.set(n.mesh, (uses.get(n.mesh) ?? 0) + 1)
  let tris = 0
  ;(gltf.meshes ?? []).forEach((m, i) => {
    for (const p of m.primitives ?? []) {
      const mode = p.mode ?? 4
      const count = p.indices !== undefined ? gltf.accessors[p.indices].count : gltf.accessors[p.attributes.POSITION].count
      const t = mode === 4 ? count / 3 : mode === 5 || mode === 6 ? Math.max(0, count - 2) : 0
      tris += t * (uses.get(i) ?? 0)
    }
  })
  return Math.round(tris)
}

/** Each animation's length in seconds (the longest sampler input). */
export function clipLengths(gltf) {
  const out = {}
  for (const a of gltf.animations ?? []) {
    let t0 = Infinity, t1 = -Infinity
    for (const s of a.samplers ?? []) {
      const acc = gltf.accessors[s.input]
      if (acc?.min) t0 = Math.min(t0, acc.min[0])
      if (acc?.max) t1 = Math.max(t1, acc.max[0])
    }
    out[a.name ?? ''] = Number.isFinite(t1) ? +(t1 - Math.min(0, t0)).toFixed(3) : 0
  }
  return out
}

export function validate(glbPath, manifest) {
  const errors = [], warnings = []
  const buf = readFileSync(glbPath)
  const kb = +(statSync(glbPath).size / 1024).toFixed(1)
  let gltf
  try { gltf = glbJson(buf) } catch (e) { return { ok: false, errors: [String(e.message ?? e)], warnings, kb, tris: 0, clips: {}, sockets: [] } }
  const tris = triangles(gltf)
  const clips = clipLengths(gltf)
  const names = new Set((gltf.nodes ?? []).map((n) => n.name))
  const sockets = [...names].filter((n) => typeof n === 'string' && n.startsWith('socket_'))
  const triCap = Math.min(MAX_TRIS, manifest.budget?.tris ?? MAX_TRIS)
  const kbCap = Math.min(MAX_GLB_KB, manifest.budget?.glbKB ?? MAX_GLB_KB)
  if (tris > triCap) errors.push(`${tris} triangles, over the budget of ${triCap}`)
  if (kb > kbCap) errors.push(`${kb} KB, over the budget of ${kbCap} KB`)
  for (const role of CLIP_ROLES) {
    const name = manifest.clips?.[role]
    if (!(name in clips)) { errors.push(`missing clip "${name}" (${role})`); continue }
    const [lo, hi] = CLIP_SECONDS[role]
    const d = clips[name]
    if (d < lo - 0.05 || d > hi + 0.05) errors.push(`clip "${name}" runs ${d} s; ${role} must run ${lo}-${hi} s`)
  }
  for (const [k, name] of Object.entries(manifest.sockets ?? {})) if (!names.has(name)) errors.push(`missing socket node "${name}" (${k})`)
  const images = gltf.images ?? []
  if (images.length > 1) errors.push(`${images.length} images; at most one baked AO map is allowed`)
  else if (images.length === 1) warnings.push('one image (must be a baked AO map of at most 512 px)')
  const extra = Object.keys(clips).filter((c) => !Object.values(manifest.clips ?? {}).includes(c))
  if (extra.length) warnings.push(`extra clips the runtime ignores: ${extra.join(', ')}`)
  return { ok: errors.length === 0, errors, warnings, kb, tris, clips, sockets }
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const [glb, man] = process.argv.slice(2)
  if (!glb || !man) { console.error('usage: node tools/assets/validate.mjs <model.glb> <asset.json>'); process.exit(2) }
  const r = validate(glb, JSON.parse(readFileSync(man, 'utf8')))
  console.log(JSON.stringify(r, null, 2))
  process.exit(r.ok ? 0 : 1)
}
