import { StrictMode, useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'
import { Hud } from './Hud'
import { bulbById, stationById, type BulbId, type StationId } from './content'
import { seed } from './sim/sim'
import { ui, useWorld } from './sim/store'
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
// Deep links: ?walk skips the intro; ?at=<station> starts there; ?bulb=<id> opens a lightbulb.
{
  const q = new URLSearchParams(location.search)
  const at = q.get('at')
  const bulb = q.get('bulb')
  if (q.has('walk') || at || bulb) useWorld.setState({ intro: false })
  if (at && at in stationById) setTimeout(() => ui.openStation(at as StationId), 400)
  if (bulb && bulb in bulbById) setTimeout(() => ui.openBulb(bulb as BulbId), 600)
}
createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
