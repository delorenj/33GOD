#!/usr/bin/env node
// Every line the sandbox reads aloud, pulled from src/content.ts so the audio can never drift from the panels.
//
//   node tools/voice/lines.mjs > tools/voice/items.json      (then: node tools/voice/render.mjs tools/voice/items.json --prune)
//
// Ids are what the HUD asks voice.say() for: st-<station>-<n> (narrator) and bulb-<bulb>-<n> (tips), n from 0, in
// reading order, so the player just counts up until an id is missing.
import { BULBS, STATIONS } from '../../src/content.ts'

// Real names the voices mangle, spelled the way they should sound. Extend after listening.
const SAY = [
  [/\bhook-hub\b/g, 'hook hub'],
  [/\bbb-hook\b/g, 'B B hook'],
  [/\bhermes-gateway\b/g, 'Hermes gateway'],
  [/\bn8n\b/gi, 'N eight N'],
  [/\b33GOD\b/g, 'thirty-three God'],
  [/\bAutomaticAI\b/g, 'Automatic A I'],
  [/\bCLIs\b/g, 'C L Is'],
  [/\bNATS\b/g, 'nats'],
  [/\bJetStream\b/g, 'jet stream'],
]
const speakable = (t) => SAY.reduce((s, [re, to]) => s.replace(re, to), t.replace(/[`*_]/g, '').replace(/\s+/g, ' ').trim())

const items = []
const push = (id, role, text) => { if (text && text.trim()) items.push({ id, role, text: speakable(text) }) }

for (const st of STATIONS) {
  const real = st.real.charAt(0).toUpperCase() + st.real.slice(1).replace(/[^.!?]$/, '$&.')
  const lines = [`${st.name}. ${real}`, ...st.does]
  if (st.breaks) lines.push(`Where the picture breaks. ${st.breaks}`)
  lines.forEach((t, n) => push(`st-${st.id}-${n}`, 'narrator', t))
}
for (const b of BULBS) {
  const lines = [b.title, ...b.body.filter((p) => !p.startsWith('> '))]
  if (b.metBefore) lines.push(`You've already met this. ${b.metBefore}`)
  if (b.breaks) lines.push(`Where the picture breaks. ${b.breaks}`)
  lines.forEach((t, n) => push(`bulb-${b.id}-${n}`, 'tips', t))
}

process.stdout.write(JSON.stringify(items, null, 1) + '\n')
