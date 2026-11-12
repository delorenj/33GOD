import { useEffect, useState } from 'react'
import { BULBS, STATIONS, bulbById, stationById, type StationId } from './content'
import { domainById } from './domains'
import { MapOverlay } from './map/MapOverlay'
import { HANDS_SLOT, TRAY_SLOT, hoursNow, ui, useWorld } from './sim/store'
import { TourHud, tour } from './tour/TourHud'

const BB_PARTS: StationId[] = ['courier', 'dock', 'labeldesk', 'belt']
const HINTS: Record<string, string> = {
  courier: 'Who carries the parcels?',
  dock: 'Where do parcels go in?',
  labeldesk: 'Who checks the words on a label?',
  belt: 'Where does every note end up?',
}
const pl = (k: number, one: string, many = one + 's') => `${k} ${k === 1 ? one : many}`
const goTo = (name: string) => `Go to ${/^(the|a) /i.test(name) ? name.toLowerCase() : 'the ' + name.toLowerCase()}`

function SimClock() {
  const [h, setH] = useState(hoursNow())
  useEffect(() => {
    const id = setInterval(() => setH(hoursNow()), 250)
    return () => clearInterval(id)
  }, [])
  const day = Math.floor(h / 24) + 1
  const hh = String(Math.floor(h % 24)).padStart(2, '0')
  return <span className="simclock" title="Time runs fast here: one second is two hours on the belt">Day {day} · {hh}:00</span>
}

function Intro() {
  return (
    <div className="intro">
      <div className="intro-card">
        <div className="eyebrow">The 33GOD Manual · experiment v0.1</div>
        <h1>The Factory</h1>
        <p>You are on the floor of the warehouse where news from your AI tools gets sorted, kept and acted on. Every part is a real piece of 33GOD.</p>
        <p><b>Your first job: find Bloodbank.</b> On this floor it is a department called Material Handling, painted blue. Look for the blue Bloodbank badge, then click each part.</p>
        <p className="muted">Bobbing lightbulbs explain the idea behind a station. Click any note on the belt to read it. This is a picture, so it breaks in places; each card says where.</p>
        <div className="intro-actions">
          <button className="primary" onClick={() => tour.start()}>Take the new-hire tour</button>
          <button className="ghost" onClick={() => useWorld.setState({ intro: false })}>Explore freely</button>
        </div>
      </div>
    </div>
  )
}

function Quest() {
  const found = useWorld((s) => s.foundStations)
  const bulbs = useWorld((s) => s.foundBulbs)
  const done = BB_PARTS.every((p) => found.includes(p))
  return (
    <div className="quest card">
      <div className="eyebrow">Find Bloodbank</div>
      <ul>
        {BB_PARTS.map((p) => (
          <li key={p} className={found.includes(p) ? 'got' : ''}>
            <button onClick={() => ui.openStation(p)}>
              <span className="box">{found.includes(p) ? '✓' : ''}</span>
              {found.includes(p) ? stationById[p].name : <span className="hint-q">{HINTS[p]}</span>}
            </button>
          </li>
        ))}
      </ul>
      {done && <p className="done">Found it. The courier, the dock, the label desk and the belt are Bloodbank. Everything else on the floor sticks notes on, tears copies off, or takes envelopes, and a few do more than one.</p>}
      {!done && <p className="muted small">Some parts are round the back of the belt. Orbit round, or use Go to…</p>}
      <div className="bulbcount">💡 {bulbs.length} of {BULBS.length} lightbulbs</div>
    </div>
  )
}

function Controls() {
  const { paused, speed, dockShut, sources } = useWorld()
  return (
    <div className="controls card">
      <button onClick={() => useWorld.setState({ paused: !paused })} aria-label={paused ? 'Play' : 'Pause'}>{paused ? '▶' : '❚❚'}</button>
      {[1, 4, 16].map((x) => (
        <button key={x} className={speed === x ? 'on' : ''} onClick={() => useWorld.setState({ speed: x })}>{x}×</button>
      ))}
      <SimClock />
      <button className={dockShut ? 'on warn' : ''} onClick={() => useWorld.setState({ dockShut: !dockShut })}>{dockShut ? 'Open the dock' : 'Shut the dock'}</button>
      <button className={sources ? 'on' : ''} onClick={() => useWorld.setState({ sources: !sources })}>{sources ? 'Hide the code' : 'Show the code'}</button>
      <button onClick={() => ui.top(true)} title="The map (Esc). Scroll up for the top view, scroll down to dive in.">Map <kbd>Esc</kbd></button>
      <select value="" onChange={(e) => (e.target.value === 'overview' ? ui.overview() : ui.openStation(e.target.value as StationId))}>
        <option value="" disabled>Go to…</option>
        <option value="overview">Whole floor</option>
        {STATIONS.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
      </select>
    </div>
  )
}

function LiveStat({ id }: { id: StationId }) {
  const s = useWorld((st) => st.stats)
  const notes = useWorld((st) => st.notes)
  const desks = useWorld((st) => st.desks)
  const lines: string[] = []
  if (id === 'archive') lines.push(`${pl(s.filed, 'note')} filed this visit`, `${pl(s.rejected, 'note')} turned away to the rejects drawer`, `${pl(s.dupes, 'second copy', 'second copies')}, nothing filed`)
  if (id === 'control') lines.push(`${pl(s.control, 'note')} seen through the window`)
  if (id === 'rules') lines.push(`${pl(s.rules, 'finished job')} matched the pick list`)
  if (id === 'courier') lines.push(`${pl(s.turnedBack, 'parcel')} turned round at a shut door`)
  if (id === 'clock') lines.push(`${pl(s.ticks, 'tick')} stuck on the front`, `${pl(s.chores, 'chore')} handed to the clock’s hands`)
  if (id === 'crew') {
    const tray = notes.filter((n) => n.hatch === 'crew' && n.heldBy === TRAY_SLOT).length
    const waiting = notes.filter((n) => n.hatch === 'crew' && n.heldBy === null).length
    lines.push(
      `${s.signed} signed off · ${s.handedBack} handed back · ${s.failed} failed`,
      desks.map((d, i) => `desk ${i + 1}: ${d.holding === null ? 'free' : 'working'}`).join(' · '),
      `${tray} in the tray · ${pl(waiting, 'envelope')} waiting on the belt`,
    )
  }
  if (id === 'belt') {
    const front = notes.filter((n) => n.kind === 'post').length
    const back = notes.filter((n) => n.kind === 'env')
    const grey = back.filter((n) => n.hatch === null).length
    lines.push(`${pl(front, 'post-it')} on the front`, `${pl(back.length, 'envelope')} on the back, ${grey} grey (no hatch takes them)`, `${s.scraped} scraped so far`)
  }
  if (!lines.length) return null
  return <div className="live">{lines.map((l) => <div key={l}>{l}</div>)}</div>
}

function StationPanel() {
  const id = useWorld((s) => s.station)
  const sources = useWorld((s) => s.sources)
  const inspecting = useWorld((s) => s.inspect !== null)
  if (!id || inspecting) return null // the note inspector takes this spot; closing it brings the panel back
  const st = stationById[id]
  return (
    <aside className="panel card">
      <button className="x" onClick={() => ui.overview()} aria-label="Close">×</button>
      <div className="chip" style={{ background: domainById[st.domain].color, color: '#fff' }}>{domainById[st.domain].name} · {domainById[st.domain].says.toLowerCase()}</div>
      <h2>{st.name}</h2>
      <div className="real">{st.real}</div>
      <div className="place">On the floor: {st.place.replace(/^The /, 'the ')}</div>
      {st.does.map((d) => <p key={d}>{d}</p>)}
      <LiveStat id={id} />
      {st.breaks && (
        <div className="breaks"><b>Where the picture breaks.</b> {st.breaks}</div>
      )}
      {st.bulbs.length > 0 && (
        <div className="bulbrow">
          {st.bulbs.map((b) => (
            <button key={b} className="bulbbtn" onClick={() => ui.openBulb(b)}>💡 {bulbById[b].title}</button>
          ))}
        </div>
      )}
      {sources && (
        <div className="evidence">
          <div className="eyebrow">In the code</div>
          {st.evidence.map((e) => <code key={e}>{e}</code>)}
        </div>
      )}
    </aside>
  )
}

function Inspector() {
  const id = useWorld((s) => s.inspect)
  const note = useWorld((s) => s.notes.find((n) => n.id === s.inspect))
  const sources = useWorld((s) => s.sources)
  const [, tick] = useState(0)
  useEffect(() => {
    const t = setInterval(() => tick((x) => x + 1), 500)
    return () => clearInterval(t)
  }, [])
  if (id === null || !note) return null
  const ageH = hoursNow() - note.bornH
  const age = ageH >= 24 ? `${Math.floor(ageH / 24)} d ${Math.floor(ageH % 24)} h` : `${Math.floor(ageH)} h`
  const post = note.kind === 'post'
  let status = ''
  if (post) status = 'Still on the belt. A reader who comes by before the 7-day scraper reaches it can tear off a copy.'
  else if (note.hatch === null) status = 'No hatch takes this kind of envelope. The sound wing wrote it only so the job can be traced. It will ride up untouched until the 1-day scraper scrapes it.'
  else if (note.heldBy === TRAY_SLOT) status = 'In the crew hall’s tray, waiting for a desk. Taken, but not gone: it stays on the belt, pinned, until a worker signs it off.'
  else if (note.heldBy === HANDS_SLOT) status = 'With the clock’s hands. Taken, but not gone: it stays pinned until they sign it off.'
  else if (note.heldBy !== null) status = `Pinned to desk ${note.heldBy + 1}. Taken, but not gone: the worker signs it off, or the 1-day scraper scrapes it.`
  else if (note.hatch === 'crew') status = note.tries > 0 ? `Handed back after try ${note.tries}. It is offered again after a short wait.` : 'Waiting. The desks are busy and the tray is full, so the hatch stays shut for now.'
  else status = 'Waiting for the clock’s hands to finish the chore before this one.'
  const archiveChip = note.readBy.includes('archive-rejected') ? 'archive: turned away' : 'archive'
  return (
    <aside className="inspector card">
      <button className="x" onClick={() => useWorld.setState({ inspect: null })} aria-label="Close">×</button>
      <div className="eyebrow">{post ? 'A post-it (an event)' : 'An envelope (a command)'}</div>
      <div className={post ? 'paper postit' : `paper envelope ${note.hatch === null ? 'orphan' : ''}`}>
        <div className="headline">{note.headline}</div>
        {post && (note.from ? <div className="fromcorner">{note.from}</div> : <div className="nofrom">no “from” corner</div>)}
      </div>
      <dl>
        <dt>Note ID</dt><dd><code>{note.noteId}</code> never changes, even on a second copy</dd>
        <dt>Barcode</dt><dd>{note.barcode ? <><code>{note.barcode}</code> one per conversation</> : <span className="muted">none{post && !note.viaDesk ? ': stuck by the cataloguer’s runner, past the label desk' : ''}</span>}</dd>
        <dt>Belt number</dt><dd><code>#{note.seq}</code> stamped by the belt, {post ? 'front' : 'back'} face</dd>
        <dt>Age</dt><dd>{age}</dd>
        {post && <><dt>Copies torn off</dt><dd>{['archive', 'control', 'rules'].map((r) => {
          const got = r === 'archive' ? note.readBy.some((x) => x.startsWith('archive')) : note.readBy.includes(r)
          const rej = r === 'archive' && note.readBy.includes('archive-rejected')
          return <span key={r} className={`reader ${got ? 'yes' : ''} ${rej ? 'rej' : ''}`}>{r === 'control' ? 'control room' : r === 'rules' ? 'rule card' : archiveChip}</span>
        })}</dd></>}
        {!post && <><dt>From</dt><dd>{note.from}</dd></>}
      </dl>
      <p className="status">{status}</p>
      {sources && <code className="src">{note.subject}</code>}
    </aside>
  )
}

function BulbModal() {
  const id = useWorld((s) => s.bulb)
  const sources = useWorld((s) => s.sources)
  if (!id) return null
  const b = bulbById[id]
  const close = () => useWorld.setState({ bulb: null })
  return (
    <div className="modal-backdrop" onClick={close}>
      <div className="modal" onClick={(e) => e.stopPropagation()} role="dialog" aria-labelledby="bulb-title">
        <button className="x" onClick={close} aria-label="Close">×</button>
        <div className="modal-bulb">💡</div>
        <h2 id="bulb-title">{b.title}</h2>
        {b.body.map((para, i) =>
          para.startsWith('> ') ? (
            <div key={i} className="labelstrip"><span>{para.slice(2).split('|')[0]}</span><code>{para.split('|')[1]}</code></div>
          ) : (
            <p key={i}>{para}</p>
          ),
        )}
        <div className="met"><b>You’ve already met this:</b> {b.metBefore}</div>
        {b.breaks && <div className="breaks"><b>Where the picture breaks.</b> {b.breaks}</div>}
        {sources && <div className="evidence"><div className="eyebrow">In the code</div><code>{b.evidence}</code></div>}
        <div className="modal-foot">
          {b.status === 'proposal' && <span className="chip">draft copy · proposal</span>}
          {id === 'failopen' && useWorld.getState().mode !== 'tour' && (
            <button className="primary" onClick={() => { useWorld.setState({ dockShut: true, bulb: null }); ui.openStation('courier') }}>Shut the dock and watch</button>
          )}
          <button onClick={() => { close(); ui.openStation(b.station) }}>{goTo(stationById[b.station].name)}</button>
        </div>
      </div>
    </div>
  )
}

export function Hud() {
  const intro = useWorld((s) => s.intro)
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== 'Escape') return
      const s = useWorld.getState()
      if (s.intro || (s.mode === 'tour' && !s.bulb)) return
      // Esc: close a pop-up first; otherwise rise to the top view and open the map (Esc again closes the map)
      if (s.bulb) useWorld.setState({ bulb: null })
      else if (s.mapOpen) useWorld.setState({ mapOpen: false })
      else ui.top(true)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])
  const panelOpen = useWorld((s) => s.station !== null || s.inspect !== null)
  const mode = useWorld((s) => s.mode)
  if (intro) return <Intro />
  if (mode === 'tour') return (<><TourHud /><BulbModal /></>)
  return (
    <div className={panelOpen ? 'has-panel' : ''}>
      <div className="title card"><b>The Factory</b> <span className="muted">33GOD Manual · v0.1</span></div>
      <Quest />
      <Controls />
      <StationPanel />
      <Inspector />
      <MapOverlay />
      <BulbModal />
    </div>
  )
}
