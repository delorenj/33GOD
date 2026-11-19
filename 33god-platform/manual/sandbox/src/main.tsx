import { StrictMode, useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'
import { Hud } from './Hud'
import { STAGE_ID, installForge } from './assets/forge'
import { flyToComponent } from './assets/links'
import { bulbById, stationById, type BulbId, type StationId } from './content'
import { seed } from './sim/sim'
import { ui, useWorld } from './sim/store'
import { tour } from './tour/TourHud'
import { loadFromUrl } from './waybill/load'
import { Scene } from './world/Scene'
import './styles.css'

function App() {
  // Note faces are painted on canvases; wait for the fonts so they are not painted in a fallback face.
  const [ready, setReady] = useState(false)
  useEffect(() => {
    const fonts = Promise.all([
      document.fonts.load('600 44px Fredoka'),
      document.fonts.load('700 72px Fredoka'),
      document.fonts.load('400 16px Nunito'),
    ])
    const timeout = new Promise((r) => setTimeout(r, 2500))
    Promise.race([fonts, timeout]).finally(() => setReady(true))
  }, [])
  const fx = !new URLSearchParams(location.search).has('nofx')
  return (
    <>
      {ready ? <Scene fx={fx} /> : <div className="loading">Opening the warehouse…</div>}
      <Hud />
    </>
  )
}

seed()
installForge()
// Deep links: ?walk skips the intro; ?at=<station> or ?at=<component id> starts there; ?bulb=<id> opens a lightbulb;
// ?tour[=N] starts the tour (at stop N); ?at=<id>&forge frames that component's asset alone (src/assets/forge.ts).
{
  const q = new URLSearchParams(location.search)
  const at = q.get('at')
  if (STAGE_ID) useWorld.setState({ intro: false, paused: true })
  const bulb = q.get('bulb')
  if (q.has('walk') || at || bulb) useWorld.setState({ intro: false })
  if (q.has('tour')) {
    const n = Number(q.get('tour'))
    setTimeout(() => (n >= 1 ? tour.go(n - 1) : tour.start()), 300)
  }
  // ?waybill=<url>[&stop=N] plays a recorded prompt (absolute URL, or relative to the site base)
  const wbUrl = q.get('waybill')
  if (wbUrl) {
    useWorld.setState({ intro: false })
    setTimeout(() => void loadFromUrl(wbUrl, Math.max(0, Number(q.get('stop') ?? 1) - 1) || 0), 300)
  }
  if (at && at in stationById) setTimeout(() => ui.openStation(at as StationId), 400)
  else if (at && !STAGE_ID) setTimeout(() => { if (!flyToComponent(at)) console.warn(`[factory] ?at=${at}: no station or Atlas component by that id`) }, 400)
  if (bulb && bulb in bulbById) setTimeout(() => ui.openBulb(bulb as BulbId), 600)
}
createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
