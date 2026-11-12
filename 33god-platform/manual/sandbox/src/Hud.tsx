import { useEffect, useState } from 'react'
import { BULBS, STATIONS, bulbById, stationById, type StationId } from './content'
import { hoursNow, ui, useWorld } from './sim/store'
import { TourHud, tour } from './tour/TourHud'

const BB_PARTS: StationId[] = ['courier', 'dock', 'labeldesk', 'belt']

function SimClock() {
  const [h, setH] = useState(hoursNow())
  useEffect(() => {
    const id = setInterval(() => setH(hoursNow()), 250)
    return () => clearInterval(id)
  }, [])
  const day = Math.floor(h / 24) + 1
  const hh = String(Math.floor(h % 24)).padStart(2, '0')
  return <span className="simclock">Day {day} · {hh}:00</span>
}

function Intro() {
  return (
    <div className="intro">
      <div className="intro-card">
        <div className="eyebrow">The 33GOD Manual · experiment v0.1</div>
        <h1>The Factory</h1>
        <p>You are standing on the floor of the warehouse that runs your AI tools. Everything here is a real part of 33GOD, drawn as something you could walk up to.</p>
        <p><b>Your first job: find Bloodbank.</b> On this floor it is a department called Material Handling, painted blue. Click its parts to see what each one does.</p>
        <p className="muted">Bobbing lightbulbs explain the idea a station is built on. Click any note on the belt to read it.</p>
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
              {found.includes(p) ? stationById[p].name : '???'}
            </button>
          </li>
        ))}
      </ul>
      {done && <p className="done">Found it. Bloodbank owns the courier, the dock, the label desk and the belt. Everything else on the floor either sticks notes on or tears copies off.</p>}
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
      <button className={sources ? 'on' : ''} onClick={() => useWorld.setState({ sources: !sources })}>Sources</button>
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
  if (id === 'archive') lines.push(`${s.filed} filed this visit`, `${s.dupes} second copies, filed nothing`)
  if (id === 'control') lines.push(`${s.control} notes seen through the window`)
  if (id === 'rules') lines.push(`${s.rules} summaries matched the pick list`)
  if (id === 'courier') lines.push(`${s.turnedBack} parcels turned round at a shut door`)
  if (id === 'crew') lines.push(`${s.signed} signed off · ${s.handedBack} handed back`, desks.map((d, i) => `desk ${i + 1}: ${d.holding === null ? 'free' : 'working'}`).join(' · '))
  if (id === 'belt') {
    const front = notes.filter((n) => n.kind === 'post').length
    const back = notes.filter((n) => n.kind === 'env')
    lines.push(`${front} post-its on the front`, `${back.length} envelopes on the back, ${back.filter((n) => n.hatch === null).length} with no hatch`, `${s.scraped} scraped so far`)
  }
  if (!lines.length) return null
  return <div className="live">{lines.map((l) => <div key={l}>{l}</div>)}</div>
}

function StationPanel() {
  const id = useWorld((s) => s.station)
  const sources = useWorld((s) => s.sources)
  if (!id) return null
  const st = stationById[id]
  return (
    <aside className="panel card">
      <button className="x" onClick={() => ui.overview()} aria-label="Close">×</button>
      {st.bloodbank && <div className="chip bb">Part of Bloodbank</div>}
      <h2>{st.name}</h2>
      <div className="real">{st.real}</div>
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
          <div className="eyebrow">Sources</div>
          {st.evidence.map((e) => <code key={e}>{e}</code>)}
        </div>
      )}
    </aside>
  )
}

function Inspector() {
  const id = useWorld((s) => s.inspect)
  const note = useWorld((s) => s.notes.find((n) => n.id === s.inspect))
  const desks = useWorld((s) => s.desks)
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
  if (post) status = 'Still on the belt. Anyone can tear off a copy until the 7-day scraper takes it.'
  else if (note.hatch === null) status = 'No hatch takes this kind of envelope. It will ride up untouched until the 1-day scraper.'
  else if (note.heldBy !== null) status = `Pinned to desk ${note.heldBy + 1}. Taken, but not gone: it leaves the belt only when the worker signs it off.`
  else status = desks.every((d) => d.holding !== null) ? 'Waiting. Both desks are busy, so the hatch stays shut.' : 'Waiting for the hatch.'
  return (
    <aside className="inspector card">
      <button className="x" onClick={() => useWorld.setState({ inspect: null })} aria-label="Close">×</button>
      <div className="eyebrow">{post ? 'A post-it (an event)' : 'An envelope (a command)'}</div>
      <div className={post ? 'paper postit' : `paper envelope ${note.hatch === null ? 'orphan' : ''}`}>
        <div className="headline">{note.headline}</div>
        {post && (note.from ? <div className="fromcorner">{note.from}</div> : <div className="nofrom">no "from" corner</div>)}
      </div>
      <dl>
        <dt>Note ID</dt><dd><code>{note.noteId}</code> never changes, even on a second copy</dd>
        <dt>Barcode</dt><dd>{note.barcode ? <><code>{note.barcode}</code> one per conversation</> : <span className="muted">none{post ? ': stuck by the cataloguer’s runner, past the label desk' : ''}</span>}</dd>
        <dt>Belt number</dt><dd><code>#{note.seq}</code> stamped by the belt, {post ? 'front' : 'back'} face</dd>
        <dt>Age</dt><dd>{age}</dd>
        {post && <><dt>Copies torn off</dt><dd>{['archive', 'control', 'rules'].map((r) => <span key={r} className={`reader ${note.readBy.includes(r) ? 'yes' : ''}`}>{r === 'control' ? 'control room' : r === 'rules' ? 'rules card' : 'archive'}</span>)}</dd></>}
      </dl>
      <p className="status">{status}</p>
      {sources && <code className="src">{post ? `bloodbank.evt.${note.headline === 'turn started' ? 'conversation.turn.started' : 'report.session.completed'}` : `bloodbank.cmd.${note.hatch ? 'v1.agent.invocation.start' : 'audio.task.start'}`}</code>}
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
        <div className="met"><b>You have met this before:</b> {b.metBefore}</div>
        {b.breaks && <div className="breaks"><b>Where the picture breaks.</b> {b.breaks}</div>}
        {sources && <div className="evidence"><div className="eyebrow">Sources</div><code>{b.evidence}</code></div>}
        <div className="modal-foot">
          {b.status === 'proposal' && <span className="chip">draft copy · proposal</span>}
          <button onClick={() => { close(); ui.openStation(b.station) }}>Go to {stationById[b.station].name.toLowerCase()}</button>
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
      if (s.mode === 'tour' && !s.bulb) return
      if (s.bulb) useWorld.setState({ bulb: null })
      else if (s.inspect !== null) useWorld.setState({ inspect: null })
      else if (s.station) ui.overview()
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
      <BulbModal />
    </div>
  )
}
