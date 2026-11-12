import { DOMAINS, PARTS, type DomainId } from '../domains'
import type { GlyphName, Pt } from './svg'

// What the map draws, as data. Bricks sit on PARTS.at and bags/zones on DOMAINS (src/domains.ts is the single
// source for position). The line routes below are authored lanes between those bricks.

export type ObjKind = 'postit' | 'env' | 'ghost' | 'parcel' | 'card' | 'copy' | 'plug' | 'grab' | 'globe'
export type Kind = 'hook' | 'parcel' | 'card' | 'event' | 'command' | 'copy' | 'take' | 'http' | 'trace'

/** Four cues say what a line is: colour + dash + the object riding it + the arrowhead. Thick = the real note, thin = a copy. */
export const KINDS: Record<Kind, { col: string; w: number; dash: string; obj: ObjKind; name: string; say: string }> = {
  hook: { col: '#14416b', w: 0.16, dash: '', obj: 'plug', name: 'hook', say: 'a button press' },
  parcel: { col: '#B7791F', w: 0.16, dash: '', obj: 'parcel', name: 'parcel', say: 'to the desk' },
  card: { col: '#B7791F', w: 0.16, dash: '.5 .35', obj: 'card', name: 'card', say: 'the reply' },
  event: { col: '#E0A100', w: 0.2, dash: '', obj: 'postit', name: 'post-it', say: 'it happened' },
  command: { col: '#D6404B', w: 0.2, dash: '', obj: 'env', name: 'envelope', say: 'please do this' },
  copy: { col: '#1E9E6A', w: 0.15, dash: '.45 .3', obj: 'copy', name: 'copy', say: 'tear one off' },
  take: { col: '#D6404B', w: 0.2, dash: '.9 .3', obj: 'grab', name: 'take', say: 'one taker only' },
  http: { col: '#4a5568', w: 0.15, dash: '.08 .38', obj: 'globe', name: 'plain call', say: 'direct, no bus' },
  trace: { col: '#8a97a8', w: 0.15, dash: '.25 .35', obj: 'ghost', name: 'trace', say: 'no taker' },
}
export const LEGEND: Kind[] = ['hook', 'parcel', 'card', 'event', 'command', 'copy', 'take', 'http', 'trace']
export const LEGEND_SUMMARY = 'Thick = the real note. Thin = a copy. Post-it = news. Envelope = a job.'

export const BAG: Record<DomainId, number> = { agents: 1, bloodbank: 2, memory: 3, holocene: 4, triggers: 5, workers: 6, voice: 7 }
/** where each zone's bag header sits (top-left, except Voice: its top-left is taken by Voxxy) */
export function bagAt(id: DomainId): Pt {
  const d = DOMAINS.find((x) => x.id === id)!
  const [x0, z0, , z1] = d.rect
  return [x0 + 0.55, id === 'voice' ? z1 - 2.8 : z0 + 0.5]
}

export interface BrickDef { id: string; s: Pt; lab: string[]; tag: string; side: 'b' | 't' | 'r'; glyph: GlyphName }
export const BRICKS: BrickDef[] = [
  { id: 'bbhook', s: [2.2, 1.4], lab: ['bb-hook'], tag: 'the messenger', side: 'b', glyph: 'plane' },
  { id: 'hookhub', s: [2.6, 2.0], lab: ['hook-hub'], tag: 'the front desk', side: 't', glyph: 'bell' },
  { id: 'naming', s: [2.6, 1.4], lab: ['naming contract'], tag: 'one name per thing', side: 'b', glyph: 'tag' },
  { id: 'pad', s: [4.6, 1.6], lab: ['Agent Pad'], tag: 'your phone app', side: 'b', glyph: 'phone' },
  { id: 'dashboard', s: [3.4, 1.8], lab: ['Holocene dashboard'], tag: 'screens to watch', side: 'b', glyph: 'screen' },
  { id: 'n8n', s: [2.6, 1.5], lab: ['n8n'], tag: 'the rule book', side: 't', glyph: 'book' },
  { id: 'aigateway', s: [2.0, 1.5], lab: ['AutomaticAI', 'gateway'], tag: 'picks the AI brain', side: 't', glyph: 'chip' },
  { id: 'enricher', s: [2.0, 1.6], lab: ['Enricher'], tag: 'writes summaries', side: 'r', glyph: 'pencil' },
  { id: 'candystore', s: [3.2, 1.8], lab: ['Candystore'], tag: 'the archive', side: 'r', glyph: 'drawer' },
  { id: 'hindsight', s: [3.0, 1.8], lab: ['Hindsight'], tag: 'lessons library', side: 'b', glyph: 'bulb' },
  { id: 'voxxy', s: [3.0, 1.8], lab: ['Voxxy'], tag: 'the voice booth', side: 'b', glyph: 'speaker' },
  { id: 'wax', s: [2.4, 1.6], lab: ['wax'], tag: 'the sound wing', side: 'b', glyph: 'wave' },
]
export const partById = Object.fromEntries(PARTS.map((p) => [p.id, p]))
export const atOf = (id: string): Pt => partById[id].at
const brickDef = Object.fromEntries(BRICKS.map((b) => [b.id, b]))

/** an edge point of a single brick, from PARTS.at, so a lane that ends on it follows the brick */
function edge(id: string, side: 'l' | 'r' | 't' | 'b', off = 0): Pt {
  const [x, z] = atOf(id)
  const [w, h] = brickDef[id].s
  if (side === 'l') return [x - w / 2, z + off]
  if (side === 'r') return [x + w / 2, z + off]
  if (side === 't') return [x + off, z - h / 2]
  return [x + off, z + h / 2]
}

// composite parts (submodel plates) are authored on the same floor coordinates as their PARTS.at
export const BUS = { s: [4.2, 2.0] as Pt }
export const CLI_NAMES = ['Claude Code', 'Codex', 'Kimi', 'Copilot', 'Gemini', 'opencode']
export const CLI_BAYS = [-7.5, -4.5, -1.5, 1.5, 4.5, 7.5]
export const CANDY = { plate: [-10.6, -8, -3, -3.9], clock: [-5, -6.5, 2.2, 1.2], exec: [-8.8, -5.6, 2.2, 1.2], disp: [-4.6, -4.6, 2.6, 1.0] }
export const GATE = { plate: [3, -9.6, 10.6, -5.4], batch: [5.6, -7.0, 3.2, 1.5], express: [8.8, -7.0, 3.2, 1.5] }

// The lanes below are authored for these centres; warn (dev only) if src/domains.ts moves one.
const AUTHORED: Record<string, Pt> = { clis: [-24, 0], bbhook: [-16.5, 1.5], hookhub: [-9.5, 0], bus: [0, 0], pad: [-14.5, 12.5], dashboard: [-5, 11.5], candybar: [-6, -6], n8n: [-14, -7], gateway: [7, -7.5], candystore: [8, 5], wax: [20.6, -4] }
if (import.meta.env?.DEV) {
  for (const id in AUTHORED) {
    const a = atOf(id)
    if (Math.hypot(a[0] - AUTHORED[id][0], a[1] - AUTHORED[id][1]) > 0.5) console.warn(`map: ${id} moved in domains.ts; re-route its lines in map/graph.ts`)
  }
}

export interface Conn { f: string; t: string; k: Kind; lab: string; r: Pt[]; lt: number }
const nm = edge('naming', 't')
const nmR = edge('naming', 'r', 0)
const ag = edge('aigateway', 'l')
const vx = edge('voxxy', 'l')
export const CONNS: Conn[] = [
  /* 0 */ { f: 'clis', t: 'bbhook', k: 'hook', lab: 'you press Enter', r: [[-21.2, 1.5], [-17.6, 1.5]], lt: 0.5 },
  /* 1 */ { f: 'bbhook', t: 'hookhub', k: 'parcel', lab: '', r: [[-15.4, 1.15], [-14, 1.15], [-14, 0.45], [-10.8, 0.45]], lt: 0.5 },
  /* 2 */ { f: 'hindsight', t: 'hookhub', k: 'http', lab: 'lessons for the card', r: [[9.4, 10.1], [9.4, 8.4], [-6.6, 8.4], [-6.6, 0.2], [-8.2, 0.2]], lt: 0.35 },
  /* 3 */ { f: 'hookhub', t: 'bbhook', k: 'card', lab: '', r: [[-10.8, -0.4], [-16, -0.4], [-16, 0.8]], lt: 0.5 },
  /* 4 */ { f: 'hookhub', t: 'naming', k: 'hook', lab: 'name it one way', r: [[-9.5, 1], [nm[0], nm[1]]], lt: 0.5 },
  /* 5 */ { f: 'naming', t: 'bus', k: 'event', lab: 'turn started', r: [[nmR[0] - 0.1, nmR[1]], [0, nmR[1]], [0, 1]], lt: 0.45 },
  /* 6 */ { f: 'bus', t: 'candystore', k: 'copy', lab: 'files everything', r: [[0.7, 1], [0.7, 5], [6.4, 5]], lt: 0.7 },
  /* 7 */ { f: 'bus', t: 'dashboard', k: 'copy', lab: 'shows everything', r: [[0.7, 1], [0.7, 9.4], [-5, 9.4], [-5, 10.6]], lt: 0.45 },
  /* 8 */ { f: 'bus', t: 'enricher', k: 'copy', lab: 'session ended', r: [[0.7, 1], [0.7, 2.5], [3.6, 2.5]], lt: 0.75 },
  /* 9 */ { f: 'enricher', t: 'bus', k: 'event', lab: 'summary written', r: [[3.6, 1.9], [1.3, 1.9], [1.3, 1]], lt: 0.5 },
  /* 10 */ { f: 'bus', t: 'n8n', k: 'copy', lab: 'job finished', r: [[-0.6, 1], [-0.6, 2.5], [-4.2, 2.5], [-4.2, -2.95], [-14.4, -2.95], [-14.4, -6.25]], lt: 0.62 },
  /* 11 */ { f: 'n8n', t: 'bus', k: 'command', lab: 'start: job', r: [[-12.7, -7], [-11.4, -7], [-11.4, -3.35], [-1.2, -3.35], [-1.2, -1]], lt: 0.5 },
  /* 12 */ { f: 'candybar', t: 'bus', k: 'event', lab: 'tick fired', r: [[-3.9, -6.4], [-2.7, -6.4], [-2.7, 1.5], [-1.8, 1.5], [-1.8, 1]], lt: 0.3 },
  /* 13 */ { f: 'bus', t: 'candybar', k: 'copy', lab: 'dispatcher reads ticks', r: [[-1.2, 1], [-1.2, 2], [-3.6, 2], [-3.6, -4.1]], lt: 0.6 },
  /* 14 */ { f: 'candybar', t: 'bus', k: 'command', lab: 'start: chore', r: [[-3.3, -4.6], [-0.4, -4.6], [-0.4, -1]], lt: 0.3 },
  /* 15 */ { f: 'bus', t: 'gateway', k: 'take', lab: 'job envelopes', r: [[1, -1], [1, -4.6], [4.4, -4.6], [4.4, -5.4]], lt: 0.55 },
  /* 16 */ { f: 'gateway', t: 'aigateway', k: 'http', lab: 'which model?', r: [[10.6, ag[1]], [ag[0], ag[1]]], lt: 0.5 },
  /* 17 */ { f: 'gateway', t: 'bus', k: 'event', lab: 'job finished', r: [[5.8, -5.4], [5.8, -4.1], [2.8, -4.1], [2.8, 1.45], [1.85, 1.45], [1.85, 1]], lt: 0.3 },
  /* 18 */ { f: 'pad', t: 'bus', k: 'command', lab: 'invoke', r: [[-12.45, 11.8], [-12.45, -2.55], [-1.8, -2.55], [-1.8, -1]], lt: 0.62 },
  /* 19 */ { f: 'gateway', t: 'voxxy', k: 'http', lab: 'read it out loud', r: [[9.4, -9.6], [9.4, vx[1]], [vx[0], vx[1]]], lt: 0.6 },
  /* 20 */ { f: 'gateway', t: 'pad', k: 'http', lab: 'the answer comes back', r: [[9.4, -5.4], [9.4, -4.3], [13.9, -4.3], [13.9, 15.6], [-17.6, 15.6], [-17.6, 12.5], [-16.7, 12.5]], lt: 0.5 },
  /* 21 */ { f: 'wax', t: 'bus', k: 'trace', lab: 'audio task', r: [[19.4, -3.5], [1.7, -3.5], [1.7, -1]], lt: 0.5 },
  /* 22 */ { f: 'bus', t: 'candybar', k: 'take', lab: 'its own chores', r: [[0.3, -1], [0.3, -3.75], [-9.3, -3.75], [-9.3, -5]], lt: 0.55 },
]

export interface Journey { name: string; steps: number[][]; extra: number[]; cap: string[] }
/** the builds: each step lists the connection indexes that wear its number */
export const JOURNEYS: Journey[] = [
  { name: 'You type a prompt', steps: [[0], [1], [4], [5], [6, 7]], extra: [3, 2], cap: ['You press Enter', 'bb-hook grabs the words', 'hook-hub names it', 'It lands on the bus', 'Candystore files it. Holocene shows it.'] },
  { name: 'A voice memo', steps: [[18], [15], [16], [19], [20]], extra: [17], cap: ['Speak into the app', 'The express hatch takes it', 'A model is picked', 'Voxxy says it out loud', 'The answer comes back'] },
  { name: 'The clock', steps: [[12], [13], [14], [22]], extra: [], cap: ['The clock ticks', 'The dispatcher hears it', 'It writes a chore', 'The executor does it'] },
]
/** where each step number sits (a dotted leader joins it to its line) */
export const BUBBLES: Record<number, Pt> = { 0: [-20.1, 0.45], 1: [-11.5, 1.9], 4: [-8.2, 1.75], 5: [-3.6, 4.25], 6: [4, 6.25], 7: [-2, 10.5], 18: [-11.3, 10.4], 15: [1.8, -6.1], 16: [11.25, -5.1], 19: [12.8, -9.8], 20: [-18, 11.2], 12: [-3.1, -7.7], 13: [-4.9, 0.4], 14: [-1.5, -5.9], 22: [-10.6, -3] }

// ---------------- page 2: Bloodbank zoomed in ----------------
export const L2_VIEWBOX = '-4 -3 42 23.5'
export const L2_PLATE: [number, number, number, number] = [3.6, 3, 36, 13.2] // x0, z0, x1, z1
export const L2_BUS = { x: 12.2, z: 4.6, w: 22.6, h: 3 }
export const L2_PIPE = [
  { id: 'bbhook', x: 5.4, z: 10.9, w: 2.4, h: 1.5, lab: 'bb-hook', tag: 'the messenger', glyph: 'plane' as GlyphName, side: 't' as const },
  { id: 'hookhub', x: 10.4, z: 10.9, w: 2.8, h: 1.8, lab: 'hook-hub', tag: 'the front desk', glyph: 'bell' as GlyphName, side: 't' as const },
  { id: 'naming', x: 15.4, z: 10.9, w: 3, h: 1.5, lab: 'naming contract', tag: 'one name per thing', glyph: 'tag' as GlyphName, side: 'b' as const },
]
export interface L2Line { pts: Pt[]; k: Kind; lab?: string; pz?: number; px?: number; al?: 'l' | 'r'; ot: number; b: number[] }
export const L2_LINES: L2Line[] = [
  { pts: [[-0.1, 10.9], [4.2, 10.9]], k: 'hook', lab: 'you press Enter', pz: 10.2, px: 2.05, ot: 0.3, b: [1] },
  { pts: [[6.6, 10.45], [9, 10.45]], k: 'parcel', ot: 0.5, b: [1] },
  { pts: [[9, 11.35], [6.6, 11.35]], k: 'card', ot: 0.5, b: [1] },
  { pts: [[11.8, 10.9], [13.9, 10.9]], k: 'hook', ot: 0.5, b: [1] },
  { pts: [[10.4, 14.75], [10.4, 11.8]], k: 'http', lab: 'lessons for the card', pz: 14.0, px: 10.4, ot: 0.3, b: [1] },
  { pts: [[15.4, 10.15], [15.4, 7.6]], k: 'event', lab: 'turn started', pz: 9.3, px: 15.4, ot: 0.75, b: [1] },
  // front face: post-its in (amber), copies out (green dashes)
  { pts: [[18.1, 14.75], [18.1, 7.6]], k: 'event', lab: 'tick fired', pz: 13.9, al: 'r', ot: 0.25, b: [3] },
  { pts: [[18.9, 7.6], [18.9, 14.75]], k: 'copy', lab: 'reads ticks', pz: 10.3, al: 'l', ot: 0.75, b: [3] },
  { pts: [[21.5, 7.6], [21.5, 14.75]], k: 'copy', lab: 'job finished', pz: 12.0, ot: 0.75, b: [] },
  { pts: [[24.5, 7.6], [24.5, 14.75]], k: 'copy', lab: 'shows everything', pz: 13.4, ot: 0.75, b: [1] },
  { pts: [[27.5, 7.6], [27.5, 14.75]], k: 'copy', lab: 'files everything', pz: 9.8, ot: 0.75, b: [1] },
  { pts: [[29.7, 7.6], [29.7, 14.75]], k: 'copy', lab: 'it ended', pz: 11.4, al: 'r', ot: 0.75, b: [] },
  { pts: [[31.3, 14.75], [31.3, 7.6]], k: 'event', lab: 'new summary', pz: 13.0, al: 'l', ot: 0.2, b: [] },
  { pts: [[33.9, 14.75], [33.9, 7.6]], k: 'event', lab: 'job finished', pz: 10.2, ot: 0.2, b: [2] },
  // back face: envelopes in (red), one taker out (red long dashes), a trace in (grey)
  { pts: [[16, 1.55], [16, 4.6]], k: 'command', lab: 'invoke', pz: 3.1, ot: 0.25, b: [2] },
  { pts: [[19, 1.55], [19, 4.6]], k: 'command', lab: 'start: job', pz: 3.1, ot: 0.25, b: [] },
  { pts: [[21.6, 1.55], [21.6, 4.6]], k: 'command', lab: 'chore', pz: 3.2, al: 'r', ot: 0.2, b: [3] },
  { pts: [[22.4, 4.6], [22.4, 1.55]], k: 'take', lab: 'executor', pz: 2.2, al: 'l', ot: 0.55, b: [3] },
  { pts: [[25, 4.6], [25, 1.55]], k: 'take', lab: 'job envelopes', pz: 3.5, ot: 0.75, b: [2] },
  { pts: [[28, 1.55], [28, 4.6]], k: 'trace', lab: 'audio task', pz: 3.1, ot: 0.25, b: [] },
]
/** which pill each page-2 line ends in (line index to exit id); the first lines are inside Bloodbank and have none */
export const L2_EXIT_OF: Record<number, string> = { 0: 'clis', 4: 'hindsight', 6: 'candyB', 7: 'candyB', 8: 'n8nB', 9: 'dash', 10: 'store', 11: 'enr', 12: 'enr', 13: 'gateB', 14: 'pad', 15: 'n8nT', 16: 'candyT', 17: 'candyT', 18: 'gateT', 19: 'wax' }
/** build-1 step numbers on page 2: [n, x, z, the line index it points at] */
export const L2_BUBBLES: [number, number, number, number][] = [[1, 0.8, 12.3, 0], [2, 7.8, 9.0, 1], [3, 12.9, 9.4, 3], [4, 13.7, 8.4, 5], [5, 23.6, 10.9, 9], [5, 26.1, 11.8, 10]]

/** every line that leaves (or enters) Bloodbank ends in a pill in the colour of the zone on the other side */
export interface L2Exit { id: string; zone: DomainId; x: number; z: number; name: string[]; side: 't' | 'b' | 'l' }
export const L2_EXITS: L2Exit[] = [
  { id: 'clis', zone: 'agents', x: -1.35, z: 10.9, name: ['Agent CLIs'], side: 'l' },
  { id: 'hindsight', zone: 'memory', x: 10.4, z: 15.2, name: ['Hindsight'], side: 'b' },
  { id: 'pad', zone: 'holocene', x: 16, z: 1.1, name: ['Agent Pad'], side: 't' },
  { id: 'n8nT', zone: 'triggers', x: 19, z: 1.1, name: ['n8n'], side: 't' },
  { id: 'candyT', zone: 'triggers', x: 22, z: 1.1, name: ['Candybar'], side: 't' },
  { id: 'gateT', zone: 'workers', x: 25, z: 1.1, name: ['hermes-gateway'], side: 't' },
  { id: 'wax', zone: 'voice', x: 28, z: 1.1, name: ['wax'], side: 't' },
  { id: 'candyB', zone: 'triggers', x: 18.5, z: 15.2, name: ['Candybar'], side: 'b' },
  { id: 'n8nB', zone: 'triggers', x: 21.5, z: 15.2, name: ['n8n'], side: 'b' },
  { id: 'dash', zone: 'holocene', x: 24.5, z: 15.2, name: ['Holocene', 'dashboard'], side: 'b' },
  { id: 'store', zone: 'memory', x: 27.5, z: 15.2, name: ['Candystore'], side: 'b' },
  { id: 'enr', zone: 'memory', x: 30.5, z: 15.2, name: ['Enricher'], side: 'b' },
  { id: 'gateB', zone: 'workers', x: 33.9, z: 15.2, name: ['hermes-gateway'], side: 'b' },
]
