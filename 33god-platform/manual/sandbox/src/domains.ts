// The floor is zoned into domains: non-overlapping areas, each holding a set of tightly related
// 33GOD components. One source for the painted floor zones, the labels' colours and the overworld map.
// World is top-down: x grows east (right), z grows toward the front (down the map). Metres.

export type DomainId = 'agents' | 'bloodbank' | 'holocene' | 'triggers' | 'workers' | 'memory' | 'voice'

export interface Domain {
  id: DomainId
  name: string
  says: string // one plain line: what this part of the platform is for
  color: string
  rect: [number, number, number, number] // x0, z0, x1, z1
}

export const DOMAINS: Domain[] = [
  { id: 'agents', name: 'Agents', says: 'Where people type', color: '#EA580C', rect: [-27, -13, -19.2, 16] },
  { id: 'bloodbank', name: 'Bloodbank', says: 'Carries the news', color: '#2563EB', rect: [-19.2, -3.2, 3.4, 7] },
  { id: 'holocene', name: 'Holocene', says: 'What you look at', color: '#475569', rect: [-19.2, 7, 3.4, 16] },
  { id: 'triggers', name: 'Triggers', says: 'Starts work', color: '#B23A48', rect: [-19.2, -13, -2.4, -3.2] },
  { id: 'workers', name: 'Workers', says: 'Does the work', color: '#2F7F7A', rect: [-2.4, -13, 14.5, -3.2] },
  { id: 'memory', name: 'Memory', says: 'Remembers', color: '#7C4DBA', rect: [3.4, -3.2, 14.5, 16] },
  { id: 'voice', name: 'Voice', says: 'Talks and listens', color: '#DB2777', rect: [14.5, -13, 25, 16] },
]

export const domainById = Object.fromEntries(DOMAINS.map((d) => [d.id, d])) as Record<DomainId, Domain>

/** The whole zoned floor: what the top-down view fits on screen. */
export const MAP_BOUNDS = { x0: -27, z0: -13, x1: 25, z1: 16 }

/** Every real component on the floor, for the map. `station` links to the 3D station (and its panel). */
export interface Part {
  id: string
  name: string
  domain: DomainId
  at: [number, number] // x, z
  station?: string
  plain: string
  parts?: string[]
}

export const PARTS: Part[] = [
  { id: 'clis', name: 'Agent CLIs', domain: 'agents', at: [-24, 0], station: 'bays', plain: 'Six coding helpers people type into.', parts: ['Claude Code', 'Codex', 'Kimi', 'Copilot', 'Gemini', 'opencode'] },
  { id: 'bbhook', name: 'bb-hook', domain: 'bloodbank', at: [-16.5, 1.5], station: 'courier', plain: 'Carries each hook to hook-hub and waits for a reply card.' },
  { id: 'hookhub', name: 'hook-hub', domain: 'bloodbank', at: [-9.5, 0], station: 'dock', plain: 'Opens every parcel and writes the news as one event.' },
  { id: 'naming', name: 'Naming contract', domain: 'bloodbank', at: [-9.5, 3], station: 'labeldesk', plain: 'One way to name things.' },
  { id: 'bus', name: 'Bloodbank bus', domain: 'bloodbank', at: [0, 0], station: 'belt', plain: 'Events on the front, commands on the back.' },
  { id: 'pad', name: 'Agent Pad', domain: 'holocene', at: [-14.5, 12.5], plain: 'The phone app: record a memo, hear the answer.' },
  { id: 'dashboard', name: 'Holocene', domain: 'holocene', at: [-5, 11.5], station: 'control', plain: 'Screens that show every event.' },
  { id: 'candybar', name: 'Candybar', domain: 'triggers', at: [-6, -6], station: 'clock', plain: 'The one clock for anything that repeats.' },
  { id: 'n8n', name: 'n8n', domain: 'triggers', at: [-14, -7], station: 'rules', plain: 'Rules that start jobs when something happens.' },
  { id: 'gateway', name: 'hermes-gateway', domain: 'workers', at: [7, -7.5], station: 'crew', plain: 'Hands each job to a Hermes agent.' },
  { id: 'aigateway', name: 'AutomaticAI gateway', domain: 'workers', at: [13, -6.2], plain: 'Picks the AI model that does the thinking.' },
  { id: 'candystore', name: 'Candystore', domain: 'memory', at: [8, 5], station: 'archive', plain: 'Keeps a copy of every event.' },
  { id: 'enricher', name: 'Enricher', domain: 'memory', at: [4.6, 2], station: 'cataloguer', plain: 'Writes a summary when a session ends.' },
  { id: 'hindsight', name: 'Hindsight', domain: 'memory', at: [9.9, 11], plain: 'The lessons library behind each briefing card.' },
  { id: 'voxxy', name: 'Voxxy', domain: 'voice', at: [17.4, -11], plain: 'Turns text into speech. Plain web calls, not the bus.' },
  { id: 'wax', name: 'wax', domain: 'voice', at: [20.6, -4], plain: 'Leaves audio trace records nobody takes.' },
]
