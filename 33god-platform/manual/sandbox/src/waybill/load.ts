// Getting a waybill into the player: ?waybill=<url>, a file picker, drag-and-drop, the sample list.
import { parseWaybill } from './types'
import { wb } from './state'

export interface Sample { file: string; title: string; cli?: string; surface?: string; duration_ms?: number; recorded_at?: string; /** a hand-made illustration, not a real recording */ fixture?: boolean }

const base = () => (import.meta.env.BASE_URL || '/')

/** Absolute URLs pass through; anything else is relative to the site base (so `fixture.waybill.json` just works). */
export function resolveUrl(u: string): string {
  if (/^[a-z][a-z0-9+.-]*:\/\//i.test(u) || u.startsWith('//')) return u
  const b = base().endsWith('/') ? base() : base() + '/'
  return b + u.replace(/^\/+/, '')
}

/** True when the bytes start with the gzip magic number (1f 8b): a .waybill.json.gz, whatever the server called it. */
export const isGzip = (b: Uint8Array) => b.length > 2 && b[0] === 0x1f && b[1] === 0x8b

/** Bytes to text. A gzip stream is inflated with the browser's own DecompressionStream; plain JSON is just decoded. */
export async function bytesToText(buf: ArrayBuffer): Promise<string> {
  const b = new Uint8Array(buf)
  if (isGzip(b)) {
    if (typeof DecompressionStream === 'undefined') throw new Error('this browser cannot unzip gzip files (no DecompressionStream). Unzip the .gz first, or use a current Chrome, Firefox or Safari.')
    const stream = new Blob([b]).stream().pipeThrough(new DecompressionStream('gzip'))
    return new TextDecoder('utf-8').decode(await new Response(stream).arrayBuffer())
  }
  return new TextDecoder('utf-8').decode(b)
}

export function loadText(text: string, source: string, startStop = 0): boolean {
  const r = parseWaybill(text)
  if (!r.ok) {
    wb.setLoad({ state: 'error', message: r.error, source })
    wb.openPicker(true)
    return false
  }
  wb.play(r.waybill, source, r.warnings, startStop)
  return true
}

export async function loadFromUrl(url: string, startStop = 0): Promise<boolean> {
  const full = resolveUrl(url)
  wb.setLoad({ state: 'loading', source: url })
  let res: Response
  try {
    res = await fetch(full, { credentials: 'omit', cache: 'no-cache' })
  } catch (e) {
    wb.setLoad({ state: 'error', source: url, retry: url, message: `Could not reach ${full}. The server may be down, or it does not allow this page to read it (CORS). ${(e as Error).message}` })
    wb.openPicker(true)
    return false
  }
  if (!res.ok) {
    wb.setLoad({ state: 'error', source: url, retry: url, message: res.status === 404 ? `Nothing at ${full} (404). Check the link or pick a sample.` : `${full} answered ${res.status} ${res.statusText}.` })
    wb.openPicker(true)
    return false
  }
  if ((res.headers.get('content-type') ?? '').includes('text/html')) {
    wb.setLoad({ state: 'error', source: url, retry: url, message: `${full} returned a web page, not a waybill. The path is probably wrong.` })
    wb.openPicker(true)
    return false
  }
  let text: string
  try {
    text = await bytesToText(await res.arrayBuffer())
  } catch (e) {
    wb.setLoad({ state: 'error', source: url, retry: url, message: `Could not read ${full}: ${(e as Error).message}` })
    wb.openPicker(true)
    return false
  }
  return loadText(text, url, startStop)
}

export async function loadFile(f: File): Promise<boolean> {
  wb.setLoad({ state: 'loading', source: f.name })
  if (f.size > 64 * 1024 * 1024) {
    wb.setLoad({ state: 'error', source: f.name, message: `${f.name} is ${(f.size / 1048576).toFixed(0)} MB. A waybill is normally a few hundred KB (a big one gzips to a fraction of that).` })
    return false
  }
  try {
    return loadText(await bytesToText(await f.arrayBuffer()), f.name)
  } catch (e) {
    wb.setLoad({ state: 'error', source: f.name, message: `Could not read ${f.name}: ${(e as Error).message}` })
    return false
  }
}

export async function fetchSamples(): Promise<Sample[]> {
  const res = await fetch(`${base()}waybills/index.json`, { credentials: 'omit', cache: 'no-cache' })
  if (!res.ok) throw new Error(`the sample list answered ${res.status}`)
  const j = (await res.json()) as { samples?: Sample[] }
  return Array.isArray(j.samples) ? j.samples.filter((s) => s && typeof s.file === 'string') : []
}

export const sampleUrl = (s: Sample) => `waybills/${s.file}`
