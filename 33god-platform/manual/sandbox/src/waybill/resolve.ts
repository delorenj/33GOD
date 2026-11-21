// Which component is this event? The player's half of the one resolver (I-10.2).
// atlas.py renders the registry's resolution map into cast.generated.json (`resolve`); waybill/waybill/registry.py
// reads the same map, and tools/cast/selfcheck.ts runs the shared cases (tools/cast/resolve.cases.json) through both.
// Order (first match wins): source rules (relay claims on the CloudEvent source + type), tenant rules (product and
// client projects -> `tenant:<slug>` at the one annex), desk families (`hermes-agent:<profile>` ->
// `hermes-desk:<profile>`), producer surfaces (exact, then the longest glob), a producer spelled like a registry id,
// alias or extra, else `unknown`. Globs are `*` and `?` only (atlas enforces it), the same as Python's fnmatch.
import cast from '../cast.generated.json' with { type: 'json' }

export type Via = 'source' | 'tenant' | 'desk' | 'producer' | 'id' | 'unknown'
export interface Resolved {
  /** waybill / Factory id: a registry id, an extra, `hermes-desk:<profile>`, `tenant:<slug>` or `unknown` */
  id: string
  /** the registry component that answers for the event (null for tenants, extras and unknown) */
  owner: string | null
  via: Via
  /** desk profile or tenant slug */
  key: string | null
}

interface SourceRule { source: string; type: string | null; id: string }
interface DeskFamily { owner: string | null; producer: string; bare: string[]; near: string; name: string; instance: string; malformed: string[]; routes: { instance: string; id: string }[] }
interface ResolveMap {
  unknown: string
  type_prefix: string
  sources: SourceRule[]
  tenants: { prefix: string; annex: string; rules: { producer: string; slug: string }[] }
  desks: Record<string, DeskFamily>
  producers: { producer: string; id: string }[]
}
interface CastIds { components: Record<string, unknown>; extras: Record<string, unknown>; aliases: Record<string, string>; resolve?: ResolveMap }

const CAST = cast as unknown as CastIds
const EMPTY: ResolveMap = { unknown: 'unknown', type_prefix: 'bloodbank.', sources: [], tenants: { prefix: 'tenant:', annex: 'tenant-annex', rules: [] }, desks: {}, producers: [] }
export const RESOLVE: ResolveMap = { ...EMPTY, ...(CAST.resolve ?? {}) }

const isGlob = (p: string) => p.includes('*') || p.includes('?')
const globRe = new Map<string, RegExp>()
/** Python's fnmatch.fnmatchcase for `*` and `?` (case-sensitive, whole string). */
export function globMatch(value: string, pattern: string): boolean {
  let re = globRe.get(pattern)
  if (!re) {
    re = new RegExp('^' + pattern.split('').map((ch) => (ch === '*' ? '[\\s\\S]*' : ch === '?' ? '[\\s\\S]' : ch.replace(/[\\^$.|+()[\]{}/-]/g, '\\$&'))).join('') + '$')
    globRe.set(pattern, re)
  }
  return re.test(value)
}

/** What a pattern's wildcard part matched: the value minus the pattern's literal head and tail. */
function stripGlob(pattern: string, value: string): string {
  const head = pattern.split(/[*?]/)[0]
  const tail = isGlob(pattern) ? pattern.split(/[*?]/).pop()! : ''
  let out = value.startsWith(head) ? value.slice(head.length) : value
  if (tail && out.endsWith(tail)) out = out.slice(0, out.length - tail.length)
  return out
}

const exact = new Map<string, string>()
for (const p of RESOLVE.producers) if (!isGlob(p.producer) && !exact.has(p.producer)) exact.set(p.producer, p.id)
const globs = RESOLVE.producers.filter((p) => isGlob(p.producer))
const deskRe: Record<string, RegExp> = Object.fromEntries(Object.entries(RESOLVE.desks).map(([f, d]) => [f, new RegExp(d.instance || '.+')]))

/** A registry id, alias or extra (with or without `ext:`) -> its canonical cast id. */
export function canonicalId(id: string): string | null {
  for (const k of [id, id.startsWith('ext:') ? id.slice(4) : `ext:${id}`]) {
    if (k in CAST.components || k in CAST.extras) return k
    if (CAST.aliases[k]) return CAST.aliases[k]
  }
  return null
}

const ownerOf = (id: string) => (id in CAST.components ? id : null)
const shortType = (t: string) => (RESOLVE.type_prefix && t.startsWith(RESOLVE.type_prefix) ? t.slice(RESOLVE.type_prefix.length) : t)

const cache = new Map<string, Resolved>()
export function resolveProducer(producer?: string | null, type?: string | null, source?: string | null): Resolved {
  const p = producer ?? '', t = shortType(type ?? ''), s = source ?? ''
  const ck = `${p}\u0000${t}\u0000${s}`
  const hit = cache.get(ck)
  if (hit) return hit
  const r = resolveUncached(p, t, s)
  cache.set(ck, r)
  return r
}

/** Resolve a waybill / Candystore event: its producer, type and (when the file carries it) CloudEvent source. */
export function resolveEvent(e: { producer?: string | null; type?: string | null; source?: string | null }): Resolved {
  return resolveProducer(e.producer, e.type, e.source)
}

function resolveUncached(producer: string, t: string, source: string): Resolved {
  for (const rule of RESOLVE.sources) {
    if (rule.type && !(t && globMatch(t, rule.type))) continue
    if (rule.source !== '*' && !(source && globMatch(source, rule.source))) continue
    return { id: rule.id, owner: ownerOf(rule.id), via: 'source', key: null }
  }
  for (const rule of RESOLVE.tenants.rules) {
    if (producer && globMatch(producer, rule.producer)) {
      const slug = rule.slug === '*' ? stripGlob(rule.producer, producer) : rule.slug
      return { id: `${RESOLVE.tenants.prefix}${slug}`, owner: null, via: 'tenant', key: slug }
    }
  }
  for (const [fam, d] of Object.entries(RESOLVE.desks)) {
    if (d.bare.includes(producer)) return { id: `${fam}:unknown`, owner: d.owner, via: 'desk', key: 'unknown' }
    if (d.producer && producer.startsWith(d.producer)) {
      const inst = producer.slice(d.producer.length)
      const route = d.routes.find((r) => globMatch(inst, r.instance))
      if (route) return { id: route.id, owner: ownerOf(route.id) ?? d.owner, via: 'desk', key: inst }
      if (d.malformed.includes(inst) || !deskRe[fam].test(inst)) return { id: `${fam}:unknown`, owner: d.owner, via: 'desk', key: 'unknown' }
      return { id: `${fam}:${inst}`, owner: d.owner, via: 'desk', key: inst }
    }
  }
  const ex = exact.get(producer)
  if (ex) return { id: ex, owner: ownerOf(ex), via: 'producer', key: null }
  for (const g of globs) if (producer && globMatch(producer, g.producer)) return { id: g.id, owner: ownerOf(g.id), via: 'producer', key: null }
  const c = producer ? canonicalId(producer) : null
  if (c) return { id: c, owner: ownerOf(c), via: 'id', key: null }
  return { id: RESOLVE.unknown, owner: null, via: 'unknown', key: null }
}

/** A keyed family member the cast does not list one by one: a Hermes desk (`hermes-desk:<profile>`) stands at its
 *  own kiosk near its family's station; every tenant (`tenant:<slug>`) stands at the one tenant annex. */
export interface Family { kind: 'desk' | 'tenant'; family: string; key: string; name: string; near: string | null; annex: string | null }
export function familyOf(id: string): Family | null {
  const tp = RESOLVE.tenants.prefix
  if (tp && id.startsWith(tp) && id.length > tp.length) return { kind: 'tenant', family: tp.slice(0, -1), key: id.slice(tp.length), name: id.slice(tp.length), near: null, annex: RESOLVE.tenants.annex }
  for (const [fam, d] of Object.entries(RESOLVE.desks)) {
    if (id.startsWith(`${fam}:`) && id.length > fam.length + 1) {
      const key = id.slice(fam.length + 1)
      return { kind: 'desk', family: fam, key, name: key === 'unknown' ? `${d.name} (unnamed)` : key, near: d.near, annex: null }
    }
  }
  return null
}
