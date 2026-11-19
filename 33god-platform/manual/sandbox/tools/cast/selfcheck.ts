// Self-check for the Factory cast (src/cast.generated.json, rendered by atlas.py) and the floor it places.
//   node --import ./tools/waybill/register.mjs --experimental-strip-types tools/cast/selfcheck.ts
import { existsSync, readFileSync, readdirSync } from 'node:fs'
import { gunzipSync } from 'node:zlib'
import { ANNEX, CAST_DIGEST, STATION_OF, castPlacement, place, standOf, stationOf, type SetId } from '../../src/waybill/stations'
import { parseWaybill } from '../../src/waybill/types'
import { courierPath } from '../../src/sim/layout'

let failed = 0
const ok = (cond: boolean, msg: string) => { console.log(`${cond ? 'ok  ' : 'FAIL'} ${msg}`); if (!cond) failed++ }

const REGISTRY = '../../../../components'
const registryIds = readdirSync(new URL(`${REGISTRY}/`, import.meta.url)).filter((f) => f.endsWith('.yaml')).map((f) => f.slice(0, -5)).sort()
ok(registryIds.length > 0, `registry read (${registryIds.length} components)`)

// 1. every registry component is placed: a station or a kiosk, never neither
const cast = castPlacement()
const unplaced = registryIds.filter((id) => !standOf(id) || (!stationOf(id) && !cast.kioskById[id]))
ok(unplaced.length === 0, `every registry component stands somewhere${unplaced.length ? ' (missing: ' + unplaced.join(', ') + ')' : ''}`)
ok(JSON.stringify(castPlacement()) === JSON.stringify(castPlacement()), 'castPlacement() is deterministic')
ok(typeof CAST_DIGEST === 'string' && CAST_DIGEST.length === 64, 'cast carries its digest')

// 2. every id a waybill can emit resolves through the cast (registry id, alias or extra), never by the by-kind fallback
const EMITTED = [
  // waybill/waybill/collectors/*.py and assemble.py: registry ids
  'aai-gateway', 'aai-llm-observability', 'agent-hooks', 'agent-pad', 'artifact-sidecar', 'artifact-vault-projector', 'asm', 'bb-dapr', 'bb-hook', 'bb-nats',
  'candybar', 'candystore', 'cost-bridge', 'curator', 'deckard', 'enricher', 'farm-command-bridge', 'hermes-bloodbank-plugin', 'hermes-gw', 'hindsight',
  'holocene', 'hook-hub', 'jev-litellm', 'milkshake', 'n8n', 'ntfy-router', 'pilot', 'redis', 'target-watch', 'turn-enricher',
  // ids that are not registry components: vendor CLIs, devices, and the recorder's own meta ids
  'ext:claude-code', 'ext:codex-cli', 'ext:codex-exec', 'ext:codex-desktop', 'ext:nanoleaf', 'ext:orca', 'ext:codex-mcp-helper-reaper', 'ext:hook-command', 'ext:unknown',
  'unknown', 'waybill',
]
const lost = EMITTED.filter((id) => !standOf(id))
ok(lost.length === 0, `every id a waybill can emit resolves${lost.length ? ' (lost: ' + lost.join(', ') + ')' : ''}`)
const SAMPLES = new URL('../../public/waybills/', import.meta.url)
for (const f of readdirSync(SAMPLES).filter((n) => n.endsWith('.json') && n !== 'index.json' || n.endsWith('.json.gz'))) {
  const raw = readFileSync(new URL(f, SAMPLES))
  const r = parseWaybill(raw[0] === 0x1f && raw[1] === 0x8b ? gunzipSync(raw).toString('utf8') : raw.toString('utf8'))
  if (!r.ok) { ok(false, `${f} parses`); continue }
  const miss = Object.keys(r.waybill.components).filter((id) => !standOf(id))
  ok(miss.length === 0, `${f}: every component is in the cast${miss.length ? ' (missing: ' + miss.join(', ') + ')' : ''}`)
}
ok(stationOf('hermes-gateway') === 'crew' && stationOf('hermes-gw') === 'crew', 'an alias resolves to its component\'s station')
ok(stationOf('claude-code') === 'bays' && stationOf('ext:claude-code') === 'bays', 'vendor CLIs stand at the bays, with or without the ext: prefix')
ok(stationOf('ext:hook-hub') === 'dock', 'an ext: prefix on a registry id still resolves')
ok(Object.keys(STATION_OF).length > 0, 'STATION_OF is built from the cast')

// 3. a waybill's kiosk is the same component in the same slot as the permanent floor
const demo = { origin: { cli: 'claude', surface: 'claude-code' }, components: Object.fromEntries(['hermes-gateway', 'asm', 'redis', 'ext:nanoleaf', 'ext:gemini', 'weird-new-consumer'].map((id) => [id, { id, name: id, kind: id === 'weird-new-consumer' ? 'service' : 'cli', registry: false }])) } as Parameters<typeof place>[0]
const pl = place(demo)
ok(JSON.stringify(place(demo)) === JSON.stringify(pl), 'place() is deterministic')
ok(pl.kioskById.asm.at.join() === cast.kioskById.asm.at.join() && pl.kioskById.redis.at.join() === cast.kioskById.redis.at.join(), 'a waybill kiosk keeps its permanent slot')
ok(pl.setOf['hermes-gateway'] === 'crew' && pl.setOf['ext:gemini'] === 'bays', 'waybill ids resolve to stations through the cast')
ok(pl.kioskById['weird-new-consumer'] !== undefined && !pl.kiosks.some((k) => k.id !== 'weird-new-consumer' && k.at.join() === pl.kioskById['weird-new-consumer'].at.join()), 'an id the cast does not know gets its own free slot')

// 4. geometry: every kiosk slot is inside its annex table, on open floor, clear of props and other slots (slot 1.4 x 1.3 m)
type Box = [number, number, number, number] // x0, z0, x1, z1
const PROPS: Record<string, Box> = {
  bays: [-26.6, -10.8, -23.7, 10.8], dock: [-11.45, -2.3, -7.55, 2.3], labeldesk: [-10.8, 1.9, -8.2, 3.7], belt: [-2.8, -1.3, 2.8, 1.3],
  archive: [5.1, 4.2, 10.0, 6.1], rules: [-14.9, -7.6, -13.1, -6.3], control: [-6.6, 9.8, -3.4, 15.3], cataloguer: [3.1, 1.3, 5.6, 3.3],
  clock: [-7.4, -7.4, -4.7, -4.7], planner: [-5.2, -5.9, -3.6, -3.8], hands: [-9.7, -6.9, -7.9, -4.7], crew: [3.3, -9.6, 10.8, -4.2],
  library: [7.6, 10.5, 12.9, 12.1], staffing: [11.5, -7.2, 14.5, -5.4], entranceFrame: [-17.0, 10.1, -11.9, 10.9], entranceMat: [-16.3, 10.2, -12.7, 14.4],
  voiceBooth: [15.0, -12.5, 19.3, -9.4], soundWing: [18.3, -5.5, 22.9, -3.7],
}
const slotBox = (at: [number, number, number]): Box => [at[0] - 0.7, at[2] - 0.65, at[0] + 0.7, at[2] + 0.65]
const overlap = (a: Box, b: Box) => a[0] < b[2] && a[2] > b[0] && a[1] < b[3] && a[3] > b[1]
const nearPath = (b: Box) => {
  for (let v = 0; v < 6; v++) {
    const p = courierPath(v)
    for (let i = 1; i < p.length; i++) {
      const n = Math.ceil(Math.hypot(p[i][0] - p[i - 1][0], p[i][2] - p[i - 1][2]) / 0.1)
      for (let k = 0; k <= n; k++) {
        const x = p[i - 1][0] + ((p[i][0] - p[i - 1][0]) * k) / n, z = p[i - 1][2] + ((p[i][2] - p[i - 1][2]) * k) / n
        if (x > b[0] - 0.35 && x < b[2] + 0.35 && z > b[1] - 0.35 && z < b[3] + 0.35) return true
      }
    }
  }
  return false
}
const noAnnex = cast.kiosks.filter((k) => !ANNEX[k.near])
ok(noAnnex.length === 0, `every kiosk's station has an annex row${noAnnex.length ? ' (' + noAnnex.map((k) => k.id).join(', ') + ')' : ''}`)
const bad: string[] = []
for (const k of cast.kiosks) {
  const b = slotBox(k.at)
  const hit = Object.entries(PROPS).filter(([, p]) => overlap(b, p)).map(([n]) => n)
  if (nearPath(b)) hit.push('courier path')
  if (Math.abs(k.at[0]) > 43 || Math.abs(k.at[2]) > 33) hit.push('off the floor')
  if (hit.length) bad.push(`${k.id} at ${k.at[0].toFixed(1)},${k.at[2].toFixed(1)} hits ${hit.join(', ')}`)
}
ok(bad.length === 0, `no kiosk slot collides with a prop, the courier lanes or the floor edge${bad.length ? '\n  ' + bad.join('\n  ') : ''}`)
const clash: string[] = []
cast.kiosks.forEach((a, i) => cast.kiosks.slice(i + 1).forEach((b) => { if (overlap(slotBox(a.at), slotBox(b.at))) clash.push(`${a.id} / ${b.id}`) }))
ok(clash.length === 0, `no two kiosk slots overlap${clash.length ? ' (' + clash.join(', ') + ')' : ''}`)
const perSet: Record<string, number> = {}
for (const k of cast.kiosks) perSet[k.near] = (perSet[k.near] ?? 0) + 1
console.log('kiosks per station:', Object.entries(perSet).sort().map(([s, n]) => `${s} ${n}`).join(', '))
const sets = new Set<SetId>(Object.values(STATION_OF))
console.log('stations with a component of their own:', [...sets].sort().join(', '))

console.log(failed ? `\n${failed} check(s) failed` : '\nall checks passed')
process.exit(failed ? 1 : 0)
