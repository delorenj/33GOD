// The waybill narrator: speaks each stop's line (src/waybill/narration.ts) as the player arrives at it, and tells the
// driver when the line is done, so playback never moves on while the voice is still talking.
//
//   arrive at a stop     -> voice.speak(<line id>); `narr.done` is false until it ends (or is missing, muted, cut off)
//   pause / play         -> the line holds and picks up where it stopped
//   autoplay refused     -> playback pauses and the HUD asks for one tap ("needsTap"); that tap replays the line
//   leave the mode       -> silence
//
// Audio comes from public/voice/manifest.json (tools/waybill/narrate.ts renders it). A waybill whose lines were never
// rendered plays silent at the visual pace, exactly as before.
import { music } from '../audio/music'
import voice from '../audio/voice'
import { lineId, narrationFor } from './narration'
import { useWb } from './state'

/** Read by the driver every frame. */
export const narr = {
  /** the current stop's line has finished (or there is nothing to wait for) */
  done: true,
  /** how long the current line runs, in ms, once known (0 = unknown): the stop is held at least this long */
  holdMs: 0,
}

let key = ''

function arrive(): void {
  const s = useWb.getState()
  const st = s.dir?.stops[s.stop]
  if (!s.waybill || !st) return
  const my = `${s.waybill.id}#${s.stop}`
  key = my
  narr.done = false
  narr.holdMs = 0
  const id = lineId(narrationFor(st))
  void voice.duration(id).then((d) => { if (key === my && d) narr.holdMs = d * 1000 + 600 })
  void voice.speak(id).then((outcome) => {
    if (key !== my) return
    narr.done = true
    if (outcome === 'blocked') useWb.setState({ playing: false, needsTap: true })
  })
  // a stop the presenter stepped to while paused is still read out; keep it held if we are paused
}

/** Start narrating the loaded waybill. Returns the stop function (unmount / leave). */
export function startNarrator(): () => void {
  let last = useWb.getState()
  arrive()
  const unsub = useWb.subscribe((s) => {
    const prev = last
    last = s
    if (s.waybill !== prev.waybill || s.stop !== prev.stop) return arrive()
    if (s.playing === prev.playing) return
    if (!s.playing) return voice.pause()
    if (prev.needsTap || s.needsTap) { useWb.setState({ needsTap: false }); return arrive() } // the tap is the gesture: say it again, properly
    if (voice.held) voice.resume()
  })
  const unduck = voice.onSpeaking((on) => music.duck(on))
  const unmute = voice.onMuted((m) => { if (m) narr.done = true })
  return () => {
    unsub()
    unduck()
    unmute()
    key = ''
    narr.done = true
    narr.holdMs = 0
    voice.stop()
    music.duck(false)
  }
}
