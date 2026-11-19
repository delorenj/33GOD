// URL switches for the asset runtime, read once.
// ?forge            exposes window.__factoryForge (src/assets/forge.ts)
// ?at=<id>&forge    frames that asset alone on a turntable (&spin=0 stops it, &angle=<deg> sets it)
// ?fixture          mounts the pipeline's test crate (forge/fixture) as a kiosk for the fake id `fixture`;
//                   only in dev or together with ?forge, never on the normal floor
const q = new URLSearchParams(location.search)
const angle = Number(q.get('angle') ?? 0)

export const FLAGS = {
  forge: q.has('forge'),
  at: q.get('at'),
  spin: q.get('spin') !== '0',
  angle: Number.isFinite(angle) ? angle : 0,
  fixture: q.has('fixture') && (q.has('forge') || import.meta.env.DEV),
}

export const FIXTURE_ID = 'fixture'
