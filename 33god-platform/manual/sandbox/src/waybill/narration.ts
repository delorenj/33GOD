// Narration copy for a waybill stop: the stop's own plain words, made speakable. PURE, shared by the player
// (src/waybill/narrator.ts) and the offline renderer (tools/waybill/narrate.ts).
//
// A line's audio id is a hash of its text (`wbn-<hash>`), so audio is content-addressed:
//   - any waybill, from the picker, a drop or a published URL, is narrated once its lines are rendered;
//   - a copy change in the director never plays stale audio, the new line is just missing (silent) until re-rendered;
//   - lines shared by many waybills ("ntfy-router lights up") render once.
import type { Stop } from './director'

const ONES = ['', 'once', 'twice']

/** Turn on-screen shorthand into words a voice reads well. Pronunciation of single words lives in voices.json "lexicon". */
export function speakable(s: string): string {
  return s
    .replace(/[“”"‘’]/g, '')
    .replace(/\s*→\s*/g, ' to ')
    .replace(/(\S+) ×(\d+)/g, (_, w: string, n: string) => `${w}, ${Number(n) < 3 ? ONES[Number(n)] : `${n} times`}`)
    .replace(/\b(claude|gpt|gemini|kimi|glm)-([a-z]+)-(\d+)-(\d+)\b/gi, (_, a: string, b: string, x: string, y: string) => `${cap(a)} ${cap(b)} ${x} point ${y}`)
    .replace(/(\d+(?:\.\d+)?)k\b/g, '$1 thousand')
    .replace(/(\d+) m (\d+) s\b/g, '$1 minutes $2 seconds')
    .replace(/\b(\d+) h\b/g, (_, n: string) => `${n} ${n === '1' ? 'hour' : 'hours'}`)
    .replace(/(\d+(?:\.\d+)?) ms\b/g, '$1 milliseconds')
    .replace(/(\d+(?:\.\d+)?) s\b/g, (_, n: string) => `${n} ${n === '1' ? 'second' : 'seconds'}`)
    .replace(/(?<=[a-z])\.(?=[a-z])/g, ' ') // agent.tool.completed -> agent tool completed; sentence ends keep their space
    .replace(/(?<=[a-z])_(?=[a-z])/g, ' ')
    .replace(/(?<=[a-z])([A-Z])(?=[a-z])/g, ' $1') // SessionStart -> Session Start, AutomaticAI -> Automatic AI
    .replace(/(\d+)\.0+\b/g, '$1') // 5.00 seconds -> 5 seconds
    .replace(/\s*\(([^()]*)\)/g, ', $1,') // VoxCPM reads parentheses as stage directions: speak them as an aside
    .replace(/:\s/g, ', ')
    .replace(/,\s*([.,;!?])/g, '$1')
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/(^|[.!?]\s+)([a-z])/g, (_, a: string, b: string) => a + b.toUpperCase()) // every sentence starts with a capital
}

const cap = (w: string) => w.charAt(0).toUpperCase() + w.slice(1)

/** What the narrator says on arriving at a stop. */
export function narrationFor(stop: Stop): string {
  const title = stop.title.trim().replace(/[.!?]?$/, '.')
  return speakable(`${title} ${stop.caption ?? ''}`)
}

/** cyrb53: a fast 53-bit string hash, plenty for a few thousand lines. */
function hash53(str: string): string {
  let h1 = 0xdeadbeef
  let h2 = 0x41c6ce57
  for (let i = 0; i < str.length; i++) {
    const ch = str.charCodeAt(i)
    h1 = Math.imul(h1 ^ ch, 2654435761)
    h2 = Math.imul(h2 ^ ch, 1597334677)
  }
  h1 = Math.imul(h1 ^ (h1 >>> 16), 2246822507) ^ Math.imul(h2 ^ (h2 >>> 13), 3266489909)
  h2 = Math.imul(h2 ^ (h2 >>> 16), 2246822507) ^ Math.imul(h1 ^ (h1 >>> 13), 3266489909)
  return (4294967296 * (2097151 & h2) + (h1 >>> 0)).toString(36)
}

/** The voice manifest id for a narration line. */
export const lineId = (text: string): string => `wbn-${hash53(text)}`
