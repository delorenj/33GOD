// Render the spoken narration for waybill playback (voice: Voxxy's registered "kurzgesagt", role "waybill").
//
//   mise run narrate                         # every sample in public/waybills/index.json
//   mise run narrate -- some.waybill.json https://s3.delo.sh/.../x.waybill.json.gz
//   mise run narrate -- --print              # show the lines and their ids, render nothing
//   mise run narrate -- --dry-run | --force  # passed through to tools/voice/render.mjs
//
// One line per stop: the director's own plain words (src/waybill/narration.ts). Ids are content hashes, so the
// player narrates ANY waybill whose lines exist in public/voice/manifest.json, wherever the waybill was loaded from,
// and lines shared between waybills render once. Audio lands in public/voice/ (gitignored, served by this host);
// `mise run build` ships it with the site.
import { spawn } from 'node:child_process'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { gunzipSync } from 'node:zlib'
import { direct } from '../../src/waybill/director'
import { lineId, narrationFor } from '../../src/waybill/narration'
import { parseWaybill } from '../../src/waybill/types'

const SANDBOX = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..')
const argv = process.argv.slice(2)
const print = argv.includes('--print')
const pass = argv.filter((a) => a === '--dry-run' || a === '--force')
let sources = argv.filter((a) => !a.startsWith('--'))
if (!sources.length) {
  const idx = JSON.parse(readFileSync(path.join(SANDBOX, 'public/waybills/index.json'), 'utf8')) as { samples: { file: string }[] }
  sources = idx.samples.map((s) => path.join(SANDBOX, 'public/waybills', s.file))
}

async function bytes(src: string): Promise<Buffer> {
  if (/^https?:\/\//.test(src)) {
    const r = await fetch(src)
    if (!r.ok) throw new Error(`${src}: HTTP ${r.status}`)
    return Buffer.from(await r.arrayBuffer())
  }
  return readFileSync(src)
}

const items = new Map<string, { id: string; role: string; text: string }>()
for (const src of sources) {
  let raw = await bytes(src)
  if (raw[0] === 0x1f && raw[1] === 0x8b) raw = gunzipSync(raw)
  const p = parseWaybill(raw.toString('utf8'))
  if (!p.ok) { console.error(`narrate: ${src}: ${p.error}`); process.exitCode = 1; continue }
  const stops = direct(p.waybill).stops
  console.log(`${path.basename(src)}: ${stops.length} stops`)
  for (const [i, s] of stops.entries()) {
    const text = narrationFor(s)
    const id = lineId(text)
    if (print) console.log(`  ${String(i + 1).padStart(2)} ${id}  ${text}`)
    items.set(id, { id, role: 'waybill', text })
  }
}
if (print || !items.size) process.exit()

const child = spawn(process.execPath, [path.join(SANDBOX, 'tools/voice/render.mjs'), '-', ...pass], { stdio: ['pipe', 'inherit', 'inherit'] })
child.stdin.end(JSON.stringify([...items.values()]))
child.on('close', (code) => process.exit(code ?? 1))
