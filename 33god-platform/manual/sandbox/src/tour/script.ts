// Warehouse Tour Mode: the screenplay as rail-engine data (draft 2, 2026-11-12).
// Source of truth: ../../../tour/script.md (scenes, shot notes, evidence, where-it-breaks lines, cue vocabulary).
// Canon: ../../../world/warehouse-bible.md. Voice: ../../../world/tone.md.
// [J] = Jarad's words (the manager's opening three lines). Everything else is [P], a proposal.
// One beat = one camera stop. `set` and `hero.at` are station ids or new set ids (see sets.ts).
//
// Staging data the engine may play (all optional, none of it changes what a line says):
//   line.cue    names a bit of business from the cue vocabulary in script.md ("stamp", "regard-palm", ...).
//               The playable engine ignores unknown cues, so adding the animation later changes nothing here.
//   line.hold   milliseconds of silence BEFORE the next line (the pause before Cruz's stamp is the joke).
//   beat.present  people on set who never speak (Wren, whose typewriter does her talking).
//   beat.split  a reading on the pad's working clock, shown in a HUD corner. Timings come from the live trace of
//               2026-11-12 (correlation bdd7a80d...: upload 01:25:28, turn done 01:26:39.7, first sound 01:26:42).
//               The memo's WORDS in this tour are staged; its SHAPE and TIMINGS are the traced run's.
//   beat.side   a labelled side scene: not on this errand's route.

export interface Line { who: string; text: string; cue?: string; hold?: number }

export interface Beat {
  id: string
  set: string
  caption: string
  hero: { form: 'parcel' | 'postit' | 'envelope' | 'slip' | 'recording' | 'none'; at: string }
  lines: Line[]
  bulb?: 'normalization' | 'failopen' | 'fanout' | 'eventcommand' | 'retention' | 'workqueue' | 'idempotent'
  teaches: string
  present?: string[]
  split?: string
  side?: boolean
}

// Faces go on people, never on data. Blue is the belt's colour, so only Professor Haugen wears it.
// Everyone is drawn to the same proportions. The oversized knee-length vest carries "new", not a body.
export const CAST: Record<string, { name: string; role: string; real: string; color: string; accent: string; height: number }> = {
  damian: { name: 'Damian', role: 'new hire', real: 'you, the reader', color: '#F97316', accent: '#FDE68A', height: 1.0 },
  manager: { name: 'Mr. Abernathy', role: 'floor manager', real: 'a human who wants something done', color: '#3F3F46', accent: '#DC2626', height: 1.3 },
  dash: { name: 'Dash', role: 'the courier', real: 'bb-hook', color: '#0F766E', accent: '#F472B6', height: 0.98 },
  odette: { name: 'Odette', role: 'lessons librarian', real: 'Hindsight, via hindsight-recall', color: '#7E22CE', accent: '#FAF5E4', height: 0.9 },
  fenwick: { name: 'Fenwick', role: 'receiving clerk', real: 'hook-hub', color: '#B91C1C', accent: '#D4A017', height: 1.1 },
  cruz: { name: 'Inspector Cruz', role: 'label desk', real: 'naming contract and validator', color: '#166534', accent: '#E5E7EB', height: 0.95 },
  kofi: { name: 'Kofi', role: "the dock's poster", real: 'agent-hooks publisher', color: '#F87171', accent: '#FFFFFF', height: 1.4 },
  haugen: { name: 'Professor Haugen', role: 'belt geologist', real: 'NATS JetStream', color: '#2563EB', accent: '#EA580C', height: 1.05 },
  lefevre: { name: 'Monsieur Lefèvre', role: 'the cataloguer', real: 'Enricher', color: '#581C87', accent: '#F5F5F4', height: 1.25 },
  reggie: { name: 'Reggie', role: 'memo doorman', real: 'Agent Pad and upload proxy', color: '#7F1D1D', accent: '#CA8A04', height: 1.15 },
  priya: { name: 'Priya', role: 'the memo desk', real: 'Holocene inbox-watcher', color: '#C2410C', accent: '#475569', height: 0.88 },
  wren: { name: 'Wren', role: 'Whisper booth', real: 'faster-whisper on the GPU', color: '#84A98C', accent: '#374151', height: 0.9 },
  okafor: { name: 'Mr. Okafor', role: 'crew hall concierge', real: 'hermes-gateway', color: '#14532D', accent: '#D4AF37', height: 1.2 },
  holly: { name: 'Holly', role: 'workstation holocene-pm', real: 'a Hermes profile', color: '#9A3412', accent: '#FEF3C7', height: 1.0 },
  mags: { name: 'Mags', role: 'staffing desk', real: 'AutomaticAI gateway', color: '#0D9488', accent: '#CA8A04', height: 1.0 },
  vinnie: { name: 'Vinnie', role: 'voice booth window', real: 'Voxxy (vox core)', color: '#BE123C', accent: '#111827', height: 1.1 },
  mo: { name: 'Big Mo', role: 'the voice', real: 'Voxxy (voxcpm engine)', color: '#5B21B6', accent: '#E9D5FF', height: 1.45 },
  constance: { name: 'Constance Bell', role: 'the bellkeeper', real: 'Candybar', color: '#1C1917', accent: '#B45309', height: 1.05 },
  gloria: { name: 'Gloria Waxman', role: 'sound wing super', real: 'HeyMa and waxd', color: '#BE7C8B', accent: '#E5E7EB', height: 0.92 },
  fitch: { name: 'Mr. Fitch', role: 'archive clerk', real: 'Candystore', color: '#78350F', accent: '#D6D3D1', height: 1.15 },
}

// The end card: the third check from tone.md section 1 ("can the reader name one post-it and one envelope from
// their own app?"), then an honest list of the rooms the rail never entered. The 24 `teaches` lines live in the
// notebook drawer, not here.
export const END_CARD = {
  headline: 'You followed it all the way round.',
  ask: 'Your own app. Name one post-it it would stick, and one envelope it would write.',
  offRouteTitle: 'Rooms the rail did not enter',
}

// "Visit every component" is honest only if the skipped ones are labelled. These are on the lobby plaque
// (Scene 1's rail map shows them dashed) and on the end card. The directory, the registry board and the ntfy bell
// also get a one-line glance on the route.
export const OFF_ROUTE: { name: string; real: string; why: string }[] = [
  { name: 'The ticket board and the marker', real: 'Plane and px', why: 'No ticket is involved in a memo. White printed cards in pockets, never sticky notes.' },
  { name: 'HR and the job description binder', real: 'Flume and the role template', why: 'HR furnishes a workstation. Holly was furnished long before the tour began.' },
  { name: 'The building directory', real: 'pjangler', why: 'The lobby board says which project lives where. Glanced at in the lobby, never used by the errand.' },
  { name: 'The tool crib', real: 'Skillex', why: 'The master copy of every how-to placard. Holly’s placards point at it.' },
  { name: 'Shift leads and the playbook', real: 'PM desks and Momo', why: 'They groom the ticket board and comment. Nothing on this errand asks them.' },
  { name: 'The inspector on call', real: 'Jev', why: 'Stamps pass or fail on request. Nobody called him.' },
  { name: 'Maintenance', real: 'monitoring stack and ntfy', why: 'Sensors, rounds and a radio page. Only a failed memo rings its bell, and this one did not fail.' },
  { name: 'The outbound dock', real: 'Telegram and ntfy pings', why: 'Where results leave the building by other roads. This answer left by the pad.' },
  { name: 'The dictation mic', real: 'Vinyl', why: 'Sits at your own workstation, beside the sound wing’s word list.' },
  { name: 'Flat-pack crates', real: 'Aperture', why: 'Crates for building a second warehouse. Some are still being designed.' },
]

export const TOUR: Beat[] = [
  // ---------- Scene 1: the briefing ----------
  {
    id: 'brief', set: 'entrance', caption: 'The entrance', hero: { form: 'recording', at: 'entrance' },
    lines: [
      { who: 'manager', text: "Look, I know you're new here. But what better way to learn your way around. The campus. Or something." },
      { who: 'manager', text: "I need you to deliver this message to the guys down in Voxxy. Now, it's packaged up. So you're gonna have to take it through processing yourself.", cue: 'drop-pad-in-vest' },
      { who: 'manager', text: "When the guys are done. Just take their result and bring it back here. I'll be waiting for you." },
      { who: 'damian', text: "Processing. Right. Where's the message?" },
      { who: 'manager', text: "On you. And this isn't your building. It has rooms yours hasn't got yet. Stay on the rail. Clock's running.", cue: 'stopwatch-click' },
      { who: 'damian', text: "On me. So it's whatever I write down.", cue: 'pat-clipboard' },
    ],
    teaches: 'The errand: a question goes in, an answer comes back. This is Warehouse One, not your building, and the rail does not enter every room.',
  },

  // ---------- Leg A: the dock lesson ----------
  {
    id: 'enter', set: 'bays', caption: 'Enter', hero: { form: 'parcel', at: 'bays' },
    lines: [
      { who: 'damian', text: 'Dear Voxxy. The manager wants an answer, please. Love, Damian. And... Enter.', cue: 'enter-key-down' },
      { who: 'dash', text: 'Box for the dock.', cue: 'catch-parcel' },
      { who: 'damian', text: "It's for Voxxy." },
      { who: 'dash', text: "It's for the dock. That label is Codex saying “he asked something”, in Codex's own handwriting. Every vendor writes its own." },
      { who: 'damian', text: 'And the answer?' },
      { who: 'dash', text: "Codex holds your question while I wait at the window for a card. Then it takes its own road to its own model. We're not on that road. We're beside it." },
    ],
    teaches: 'Pressing Enter fires a hook, and the vendor packs one parcel in its own words. The vendor holds the question until a briefing card comes back, then takes its own road to its model. The warehouse sits beside that road, never on it.',
  },
  {
    id: 'courier', set: 'courier', caption: 'The courier', hero: { form: 'parcel', at: 'courier' },
    lines: [
      { who: 'damian', text: "What if the dock's closed?" },
      { who: 'dash', text: "Shut, I turn round at once. Box still under my arm, no post-it written, nothing queued. I don't knock twice and I don't leave it on the step.", cue: 'what-if-open' },
      { who: 'damian', text: 'So the news...' },
      { who: 'dash', text: "Never gets written down. You'll hear this called fail-open: when the helper is down, the real work carries on without it." },
      { who: 'damian', text: "That's a little bleak." },
      { who: 'dash', text: 'Shut is quick. Jammed is slower: a short wait the first time, then a shorter one for half a minute. The skates are for morale.', cue: 'what-if-close' },
    ],
    bulb: 'failopen',
    teaches: 'A shut door turns the courier round at once, with the parcel still in hand and no post-it written. A jammed door costs the vendor a short wait, then a shorter one for half a minute. That is fail-open.',
  },
  {
    id: 'window', set: 'library', caption: 'The driver’s window', hero: { form: 'parcel', at: 'dock' },
    lines: [
      { who: 'fenwick', text: 'Codex question. Two clerks, one parcel. At the back, a clerk is already writing the post-it. Up front, the window cards run for you: reminders, the library, the code map.', cue: 'glance-alarm-clock-bin' },
      { who: 'dash', text: "I always wait at the window. It's the only place anyone hands me anything back." },
      { who: 'odette', text: "Last time on this project, you learned the voice booth reads one script at a time. Card's printing.", cue: 'hourglass-flip' },
      { who: 'fenwick', text: 'Briefing card. It goes back to Codex before Codex carries on. It never goes on the belt.', cue: 'card-slides-out' },
      { who: 'damian', text: "Doesn't the archive have a card too?" },
      { who: 'fenwick', text: "The archive hands its card out when a session opens, not at every question." },
      { who: 'odette', text: "And if the hourglass runs out, the card leaves without my paragraph, dear. Codex will wait that long, and not a second more." },
    ],
    teaches: 'Some parcels wait at the window for a briefing card. It goes back to the vendor inside a time limit and never goes on the belt. The post-it is written by a different clerk while you wait.',
  },
  {
    id: 'receiving', set: 'dock', caption: 'Receiving', hero: { form: 'postit', at: 'dock' },
    lines: [
      { who: 'fenwick', text: 'Codex writes “UserPromptSubmit”. A capital on every word, very sure of itself. Gemini writes “BeforeAgent”. Same news, different vineyard.', cue: 'taste-label' },
      { who: 'fenwick', text: 'The house writes it one way. “Turn started.” The vendor’s own packing slip goes stapled to the back.', cue: 'hold-up-postit' },
      { who: 'damian', text: "What's the stripe along the bottom?" },
      { who: 'fenwick', text: 'The barcode. One per conversation, made from Codex’s own session number. Every note from this chat wears it. “Came after” names the note before.' },
      { who: 'dash', text: "Still waiting on my card. The post-it isn't my department." },
    ],
    bulb: 'normalization',
    teaches: 'Parcels in, one house post-it out: “turn started”, vendor in the corner. One barcode per conversation. That is normalization.',
  },
  {
    id: 'labeldesk', set: 'labeldesk', caption: 'The label desk', hero: { form: 'postit', at: 'labeldesk' },
    lines: [
      { who: 'damian', text: 'Shouldn’t it say “Codex turn started”? So people know who.' },
      { who: 'cruz', text: 'Refused.', cue: 'stamp-refuse', hold: 400 },
      { who: 'cruz', text: 'Vendors live in the corner. The headline says what happened, in house words, and every word is in the book.', cue: 'tap-dictionary' },
      { who: 'damian', text: "What's written inside? My question?" },
      { who: 'cruz', text: 'Word for word. Anyone who tears off a copy can read what you asked.' },
      { who: 'damian', text: 'I wrote “Love, Damian.”', hold: 600 },
      { who: 'cruz', text: 'Then the whole building knows.', cue: 'stamp' },
    ],
    teaches: 'The label desk allows house words only, and the vendor never goes in the headline. Your question rides on the post-it for anyone to read.',
  },
  {
    id: 'loading', set: 'belt', caption: 'The belt', hero: { form: 'postit', at: 'belt' },
    lines: [
      { who: 'kofi', text: '“Come in.” Another one safely home.', cue: 'bow-to-slot' },
      { who: 'haugen', text: 'It said it heard you, Kofi. It has never once said it kept one.', cue: 'tap-glass' },
      { who: 'kofi', text: '...Never once?' },
      { who: 'damian', text: 'Thank you.', cue: 'face-slot' },
      { who: 'haugen', text: "It heard that. Whether it kept it is another matter. And if the door's shut, your note hits the floor and nobody tries again." },
      { who: 'haugen', text: 'Now watch it climb. Height is age: the bottom is a minute ago, the top is a week. At seven days the scraper takes it, read or not.', cue: 'ruler-tilt-up' },
      { who: 'damian', text: 'So the belt carries it to Voxxy.' },
      { who: 'haugen', text: "Carries it? Nothing on this belt has moved an inch sideways in its life. It's sediment. Readers come to it.", cue: 'rock-hammer' },
    ],
    bulb: 'retention',
    teaches: 'The dock’s poster rings a doorbell: heard is not kept. On the belt height is age, and the scraper takes post-its at seven days, read or not.',
  },
  {
    id: 'readers', set: 'cataloguer', caption: 'Tear off a copy', hero: { form: 'postit', at: 'belt' },
    lines: [
      { who: 'haugen', text: "Readers. The archive's runner tears off a copy for the racks (you'll hear that runner called a sidecar). The control room reads through its visitor's window, pass in one hand, notebook in the other.", cue: 'runner-sprints' },
      { who: 'damian', text: 'They took it off the belt?' },
      { who: 'haugen', text: "They took a copy. The original stays for the next reader. You'll hear this called fan-out." },
      { who: 'lefevre', text: '“Turn started”? Non. I take a copy of everything, monsieur, then bin what is not a finished tool call. A question is not a finished anything.', cue: 'bin-note' },
      { who: 'haugen', text: "That card at the rules cabinet is fussier. It wants only “invocation completed”. Everything else slides past it. That is a pick list.", cue: 'pan-rules' },
      { who: 'damian', text: "So who's reading it for Voxxy?" },
      { who: 'lefevre', text: 'Look at the clips, monsieur. Do you see one for Voxxy?' },
    ],
    bulb: 'fanout',
    teaches: 'Readers tear off copies and the original stays. A pick list, like the rules cabinet’s “invocation completed”, lets other notes slide past. That is fan-out.',
  },
  {
    id: 'turn', set: 'belt', caption: 'Nobody asked anybody', hero: { form: 'postit', at: 'belt' },
    lines: [
      { who: 'haugen', text: "That's a note about a question. It says “he asked”. It doesn't ask anyone to do anything." },
      { who: 'damian', text: 'So how does my message get to Voxxy?' },
      { who: 'haugen', text: "You keep saying “message”. In here that's a post-it or an envelope. A post-it says what happened. An envelope asks one worker to do one thing, and nobody at the dock writes envelopes." },
      { who: 'damian', text: 'And Voxxy?' },
      { who: 'haugen', text: 'Not on the belt at all. No clip, no hatch. They have a door you slide things under. What’s that in your vest?', cue: 'tap-vest' },
      { who: 'damian', text: "The manager's pad. One memo, unsent. It was on me the whole time.", cue: 'pad-record-light' },
    ],
    bulb: 'eventcommand',
    teaches: 'A post-it says what happened; an envelope asks one worker to do one thing. Nothing at the dock writes envelopes, and Voxxy is not on the belt.',
  },

  // ---------- Leg B: the memo run (a different door, a different barcode) ----------
  {
    id: 'memodoor', set: 'entrance', caption: 'The memo door', hero: { form: 'recording', at: 'entrance' }, split: 'Pad clock 0:00',
    lines: [
      { who: 'reggie', text: "Memo door. Pads only. That's a tape, not a parcel. Parcels go to the dock.", cue: 'headset-on-hook' },
      { who: 'damian', text: "It's for Voxxy." },
      { who: 'reggie', text: "It's for holocene-pm. That's a worker. Voxxy doesn't answer questions. Voxxy reads answers out loud.", cue: 'read-pad' },
      { who: 'reggie', text: 'On the shelf: inbox, holocene-pm, today. That shelf address is your barcode now. Every note from this errand wears it.', cue: 'tape-drops-inbox' },
      { who: 'reggie', text: "“Memo uploaded”, stuck. And a ring for the memo desk, so it doesn't wait for its next look round. Miss the ring and it finds the tape a few seconds later anyway.", cue: 'ring-desk-bell' },
      { who: 'reggie', text: "Lobby board's behind you if you ever need to find a project. Not on your rail today.", cue: 'glance-directory' },
    ],
    teaches: 'The errand enters by the memo door, not the dock. The tape’s shelf address becomes the barcode every later note wears.',
  },
  {
    id: 'memodesk', set: 'control', caption: 'The memo desk', hero: { form: 'recording', at: 'control' }, split: 'Pad clock 0:01', present: ['wren'],
    lines: [
      { who: 'priya', text: 'Ring heard. “Memo received”, stuck. Worker holocene-pm, routable. Wren?', cue: 'glance-ticket-board' },
      { who: 'priya', text: 'Wren types it, silently. He said: “Holly. Why does the car take so long to talk back. Thirty words. Go.”', cue: 'whisper-typing' },
      { who: 'priya', text: '“Memo transcribed”, stuck: the words, how long it ran, which ears heard it.' },
      { who: 'damian', text: "Couldn't you answer it yourself?" },
      { who: 'priya', text: "Some I can, at the quick desk, with no envelope at all. “Routed”, stuck. The quick desk looked at this one and said: a job for a worker.", cue: 'quick-desk-glance' },
      { who: 'priya', text: "And if I can't finish, I stick “memo failed”. That is the one memo post-it that rings the maintenance bell.", cue: 'glance-ntfy-bell' },
    ],
    teaches: 'The memo desk turns the tape into text and sticks a post-it for each step. A quick question can be answered at the desk; a memo for a worker gets an envelope.',
  },
  {
    id: 'envelope', set: 'control', caption: 'The first envelope', hero: { form: 'envelope', at: 'control' }, split: 'Pad clock 0:01',
    lines: [
      { who: 'priya', text: 'An envelope. One instruction, for one worker. Outside, “invoke”. Inside: holocene-pm, his words, the thread.', cue: 'draw-envelope' },
      { who: 'damian', text: "That's the first envelope I've seen anyone write." },
      { who: 'priya', text: 'I copy the barcode on. A barcode only crosses rooms when the next writer copies it.', cue: 'copy-barcode' },
      { who: 'priya', text: 'Checked, rung, gone. “Memo dispatched.”', cue: 'stamp-ring' },
      { who: 'priya', text: 'A doorbell only says it heard. The ledger is how I find out whether anyone took it. No line, and I stop waiting and tell the sender.', cue: 'shutter-ledger-up' },
    ],
    teaches: 'The memo desk, not the dock, writes the envelope: “invoke”, for one worker, with the copied barcode. It goes out by doorbell, so the desk reads the crew hall’s ledger to learn whether anyone took it.',
  },
  {
    id: 'hatch', set: 'crew', caption: 'The express hatch', hero: { form: 'envelope', at: 'crew' }, split: 'Pad clock 0:01',
    lines: [
      { who: 'okafor', text: 'Welcome to the crew hall. Express hatch, for envelopes a human is waiting on. Each kind of envelope has one hatch at most.' },
      { who: 'damian', text: "You've taken it, so it's off the belt." },
      { who: 'okafor', text: 'Taken is not gone, sir. It stays on the belt, marked in hand, until I sign it off. If I go quiet, it will be offered again.', cue: 'in-hand-ribbon' },
      { who: 'okafor', text: "If it comes round twice, my ledger has its number. I stick the same post-its again and I don't do the work twice.", cue: 'ledger-line' },
      { who: 'okafor', text: 'One line in my ledger. Then two post-its at the registered counter, “turn started” and “invocation started”, and I wait for a receipt with the belt number on it.', cue: 'registered-counter' },
      { who: 'damian', text: "“Turn started.” That's what the dock wrote for me." },
      { who: 'okafor', text: 'Same words, different poster, different barcode. The dock had nothing to do with this one.' },
      { who: 'okafor', text: 'The registry board tells me which workstation is named inside. Who gets onto that board is HR’s business. Not on your rail.', cue: 'glance-registry-board' },
    ],
    bulb: 'workqueue',
    teaches: 'One hatch per kind of envelope. Taken is not gone: it stays on the belt, in hand, until signed off. If it comes round twice, the ledger knows it. That is a work queue.',
  },
  {
    id: 'staffing', set: 'staffing', caption: 'The workstation phones out', hero: { form: 'envelope', at: 'crew' },
    lines: [
      { who: 'holly', text: 'Who I am. What I remember. What I can do. Right. Somebody get me a brain.', cue: 'unfreeze' },
      { who: 'mags', text: 'Staffing desk. The envelope names the agency it wants. I ring that one first.', cue: 'dial-dead-air' },
      { who: 'mags', text: "That one hasn't been paid. I try the next number on my list. There we are. First agency that picks up.", cue: 'dial-answer' },
      { who: 'damian', text: 'Is the agency in the building?' },
      { who: 'mags', text: 'Across town, love. Their answers go back to Holly, never across your belt.' },
      { who: 'okafor', text: "“Still working.” Every so often, so nobody thinks I've gone quiet and offers it to someone else.", cue: 'stamp-still-working' },
      { who: 'holly', text: 'When I say something next to a tool call, the hall sticks it up as “invocation progressed”. I said nothing today. Most turns I say nothing.', cue: 'no-postit-appears' },
    ],
    teaches: 'A workstation sleeps until an envelope wakes it. Its model call goes through the staffing desk, which tries the agency named, then the next on its list. Progress post-its appear only when the worker says something next to a tool call.',
  },
  {
    id: 'booth1', set: 'voxxy', caption: 'The voice booth, early', hero: { form: 'envelope', at: 'crew' }, split: 'Pad clock 0:08 · 0:17 · 0:26',
    lines: [
      { who: 'damian', text: "I've come about the manager's memo. Are you the guys?" },
      { who: 'vinnie', text: "We're the guys. You're early. We read answers out loud, and nobody's written one yet." },
      { who: 'vinnie', text: "And we don't take deliveries. No envelopes, no clips, no hatch. You slide it under the door.", cue: 'slip-under-door' },
      { who: 'priya', text: '“Still on it.” Off my own shelf, made ahead of time. A file copy. It never went through your window.', cue: 'cue-clip-plays' },
      { who: 'damian', text: 'Why play it at all?' },
      { who: 'priya', text: "Because a worker can be quiet a long while, and the car shouldn't be. If a worker writes a line next to a tool call, I can slide that under the door instead. Most turns write none." },
      { who: 'vinnie', text: "So today it's the shelf. We'll be here when there's an answer." },
    ],
    teaches: 'Voxxy is not on the belt: a script slides under the door and a recording comes back. The “still on it” clips are a shelf of ready-made recordings, never a Voxxy render. Spoken progress is possible, but most turns write none.',
  },

  // ---------- side scenes, not on this errand's route ----------
  {
    id: 'clock', set: 'clock', caption: 'Side scene: the clock', hero: { form: 'envelope', at: 'crew' }, side: true,
    lines: [
      { who: 'damian', text: 'Is this on my route?' },
      { who: 'constance', text: 'No. Nothing on your errand waits for a bell. I own when things happen, not what anyone asked.', cue: 'pocket-watch' },
      { who: 'constance', text: 'When I ring, the planner writes an envelope for each chore due. My hands take the “invoke” ones. My caretaker takes the “steward” ones. One hatch per kind, one worker each.' },
      { who: 'damian', text: 'Could I set a reminder to collect the answer?' },
      { who: 'constance', text: "A private alarm. In this building. One bell, no private alarms. You'll find them in the bin under the dock's window.", cue: 'point-alarm-bin' },
    ],
    teaches: 'Side scene: the clock owns when. Its chores go out as envelopes, one hatch per kind, and there is one bell and no private alarms.',
  },
  {
    id: 'soundwing', set: 'soundwing', caption: 'Side scene: the sound wing', hero: { form: 'envelope', at: 'crew' }, side: true,
    lines: [
      { who: 'damian', text: 'You do audio. Do you send things to Voxxy?' },
      { who: 'gloria', text: 'Never have. My wing takes recordings in through three doors, locks them in the cage first, and runs eight passes over each transcript.' },
      { who: 'gloria', text: 'We write envelopes too. That stack. Letters to an empty room, every one. No hatch for that kind. Up they go, unsigned, until the one-day scraper.', cue: 'point-grey-stack' },
      { who: 'damian', text: "Isn't that what post-its are for?" },
      { who: 'gloria', text: 'We write one of those too. A copy of the envelope, so the archive can find it. Don’t tell the Professor.', cue: 'glance-at-haugen', hold: 500 },
    ],
    teaches: 'Side scene: the sound wing never calls Voxxy. Some of its envelopes have no hatch, so they wait for the scraper; a post-it copy is stuck so the archive can find them.',
  },

  // ---------- Leg B continues: the answer comes back ----------
  {
    id: 'signoff', set: 'crew', caption: 'Signed off', hero: { form: 'envelope', at: 'crew' }, split: 'Pad clock 1:12',
    lines: [
      { who: 'okafor', text: 'Holly has put her pen down. Taken was not gone. Now it is.', cue: 'regard-palm' },
      { who: 'okafor', text: 'Two post-its at the registered counter, “invocation completed” and “turn completed”, same barcode as the first two. Then I sign the envelope off.', cue: 'stamp' },
      { who: 'damian', text: 'Where is the answer? On the post-it?' },
      { who: 'okafor', text: 'Done is a post-it, sir. It says finished, how long it took, which hatch. It has never once carried an answer.', cue: 'regard-palm' },
      { who: 'okafor', text: 'And my signature means I am finished with the envelope. Not that it went well. Read the post-it’s last word: completed, or failed.' },
      { who: 'damian', text: 'So who has the answer?' },
      { who: 'okafor', text: 'Holly wrote it in her own session book. Somebody is on their way to read it. I believe they have been reading my ledger since the first second.', cue: 'glance-up-mezzanine' },
    ],
    teaches: 'The hall sticks “completed” and signs the envelope off. A signature means finished with the envelope, not that it worked. The completed post-it never carries the answer.',
  },
  {
    id: 'ledger', set: 'control', caption: 'The ledger and the session book', hero: { form: 'recording', at: 'control' }, split: 'Pad clock 1:12',
    lines: [
      { who: 'priya', text: 'I did not wait for the post-it. I read Okafor’s ledger. One line for that envelope’s number: done, and how long.', cue: 'ledger-wink' },
      { who: 'damian', text: 'You and the ledger seem close.' },
      { who: 'priya', text: 'It tells me the truth and it does not ask me to dinner.' },
      { who: 'priya', text: 'The answer is not on the belt anywhere. It is in Holly’s session book: her newest page for this barcode, checked fresh against when I sent the envelope.', cue: 'open-session-book' },
      { who: 'priya', text: '“Three steps in a row: it hears you, thinks, then speaks. Each one waits for the one before. I’ll time each step and follow up.” Twenty-six words. Under the thirty.' },
      { who: 'priya', text: 'And under it, a line that starts “BACKGROUND”. That is Holly’s note to me, not to the car. I never read it out. It is a promise, not an answer.', cue: 'tear-off-line' },
      { who: 'priya', text: 'The answer I clean for the car. No asterisks, no code, nothing a person cannot say. Then it goes under the booth door.', cue: 'clean-for-speech' },
    ],
    teaches: 'The memo desk learns the turn is done by reading the crew hall’s ledger, not by waiting for a post-it. The answer lives in the worker’s session book, never on the belt. A BACKGROUND line is a promise and is never spoken.',
  },
  {
    id: 'pad', set: 'entrance', caption: 'First sound', hero: { form: 'recording', at: 'entrance' }, split: 'Pad clock 1:14',
    lines: [
      { who: 'reggie', text: 'Pad’s clock stopped. One minute fourteen. First sound.', cue: 'pad-clock-stops' },
      { who: 'damian', text: 'How did it know?' },
      { who: 'reggie', text: 'The ear. A cup on the wall at the loading slot and a hose down to my desk. It hears every memo post-it that goes up. No clip, no notebook. It hears, or it does not.', cue: 'point-ear' },
      { who: 'reggie', text: 'If the hose goes quiet, I walk to the shelf every few seconds and look. Slower, but it gets there.' },
      { who: 'reggie', text: '“Voiced”, stuck: that piece is on the reply shelf, the car can start speaking from here. A post-it is the doorbell and the shelf is the pickup. Nobody sticks sound to a post-it.', cue: 'fetch-from-shelf' },
      { who: 'reggie', text: 'It says: “Three steps in a row: it hears you, thinks, then speaks. Each one waits for the one before. I’ll time each step and follow up.”', cue: 'voice-from-pad', hold: 500 },
      { who: 'reggie', text: '“Replied”, stuck. Then your pad tells me it played it, and “played” goes up. That is the last thing anybody here can see.' },
    ],
    teaches: 'The pad hears about new notes through an ear at the loading slot, then fetches the recording from the reply shelf. A post-it is the doorbell, the shelf is the pickup, and polling is the fallback.',
  },
  {
    id: 'followup', set: 'crew', caption: 'Later', hero: { form: 'envelope', at: 'crew' }, split: 'Pad clock 1:24, then 1:42:33',
    lines: [
      { who: 'okafor', text: 'Second envelope for Holly. Same barcode, same thread, different number. The memo desk wrote it the moment the first answer went out.', cue: 'copy-barcode' },
      { who: 'okafor', text: 'Kind “start”. That is the ordinary hatch, the one with no stopwatch on it. Two hours, and Holly may use them.' },
      { who: 'holly', text: 'Same thread, so I remember the first answer. I promised to time each step. Back in a bit.', cue: 'unfreeze' },
      { who: 'okafor', text: 'No “still on it” clips for this one, the desk upstairs tells me. Nobody is holding a line.', cue: 'later-card', hold: 800 },
      { who: 'okafor', text: 'An hour and forty-one minutes. Completed, turn completed, signed off. Same two post-its, new numbers, same barcode.', cue: 'regard-palm' },
      { who: 'holly', text: 'Timed it. Listening, about a second. Thinking, most of a minute. Speaking starts two seconds after I finish. Writing it in my book.', cue: 'write-session-book' },
      { who: 'damian', text: 'Do you do this for every memo?' },
      { who: 'holly', text: 'Only when I say I will. One follow-up per memo, and then I stop.' },
    ],
    teaches: 'A long ask becomes a second envelope for the ordinary hatch, with the same barcode and the same thread. There is no stopwatch on that hatch, and nothing is narrated while it runs.',
  },
  {
    id: 'booth2', set: 'voxxy', caption: 'The voice booth, late', hero: { form: 'recording', at: 'voxxy' }, split: 'Pad clock 1:42:33 · 1:42:37 · 1:42:42',
    lines: [
      { who: 'priya', text: 'Holly’s follow-up, cleaned for the car. It is longer than a hundred and sixty letters, so I cut it at the full stops. Short piece first, so you hear something sooner. Longer ones after.', cue: 'cut-at-full-stops' },
      { who: 'vinnie', text: 'We do not cut. We read what is slid under the door, whole. She does the cutting.', cue: 'slip-under-door' },
      { who: 'vinnie', text: 'And one at a time. Mo has one chest.', cue: 'point-at-mo' },
      { who: 'mo', text: 'One. Voice. One. At. A. Time.', cue: 'mo-lock' },
      { who: 'vinnie', text: 'Piece two waits at the door until piece one is done. Waiters queue.' },
      { who: 'mo', text: '“Holly, follow-up. I timed each step.”', cue: 'mo-reads', hold: 400 },
      { who: 'mo', text: '“Listening takes about a second. Thinking takes most of a minute, and that is the slow part.”', cue: 'mo-reads', hold: 400 },
      { who: 'mo', text: '“Speaking starts two seconds after the thinking ends. If you want it faster, shorten the thinking, not the talking.”', cue: 'mo-reads' },
      { who: 'priya', text: 'Each piece goes on the reply shelf, with a “voiced” post-it, and the pad plays them as they land.', cue: 'voiced-postit' },
      { who: 'vinnie', text: 'We keep each recording an hour. After that it is gone. She takes her copy before then.' },
    ],
    teaches: 'The memo desk cleans the answer and cuts it into pieces, and each piece goes under the booth door on its own. Voxxy does no cutting, reads one script at a time, and keeps each recording for an hour.',
  },
  {
    id: 'barcode', set: 'archive', caption: 'One barcode, forty notes', hero: { form: 'postit', at: 'archive' },
    lines: [
      { who: 'fitch', text: 'Barcode, please. Ah. The memo tape. About forty notes, one barcode.', cue: 'pull-drawer' },
      { who: 'fitch', text: 'Fourteen kinds. Uploaded, received, transcribed, routed, dispatched. The hall’s pair, turn started and invocation started. Three clips narrated. Completed. Voiced, replied, played.' },
      { who: 'fitch', text: 'Each one says what “came after” it. Follow them and the whole run reads like a diary. The control room does the same trick, off the same barcode.', cue: 'glance-mezzanine' },
      { who: 'damian', text: 'Is my Codex question in there?' },
      { who: 'fitch', text: 'That wears a different barcode, from a different door. Nothing joins the two but you.' },
      { who: 'damian', text: 'What if one of these came twice?' },
      { who: 'fitch', text: 'A what-if, because it did not happen today. Say the hall replays a finished envelope’s post-its, same Note IDs. I file each one once and move on.', cue: 'what-if-open' },
      { who: 'fitch', text: 'Two envelopes is not that. Two envelopes is two jobs, with their own Note IDs. Both filed. Not twice.', cue: 'what-if-close' },
    ],
    bulb: 'idempotent',
    teaches: 'The archive can rebuild a whole run from one barcode: about forty notes, fourteen kinds, two envelopes. A repeat of the same Note ID is filed once. Two envelopes are two jobs, not a repeat. That is idempotent.',
  },
  {
    id: 'closing', set: 'entrance', caption: 'Back at the entrance', hero: { form: 'recording', at: 'entrance' }, split: 'Pad clock 1:42:42',
    lines: [
      { who: 'manager', text: 'Well?', cue: 'stopwatch-click' },
      { who: 'damian', text: 'Their result.', cue: 'hand-pad' },
      { who: 'manager', text: '“Three steps in a row.” That is the quick one. First sound at one minute fourteen. I have waited longer for the lift.' },
      { who: 'damian', text: 'The long one came an hour and forty-two minutes in.' },
      { who: 'manager', text: 'I went for lunch. It was waiting on the pad when I came back. That is the idea.' },
      { who: 'manager', text: 'You walked the building. Now do it in your own shop. Name me one post-it it would stick, and one envelope it would write.' },
      { who: 'damian', text: 'Now?' },
      { who: 'manager', text: 'Take your time. No, don’t. Clock’s running.', cue: 'stopwatch-click' },
    ],
    teaches: 'The errand ends where it began: a question went in by one door and an answer came back to the pad. The third check is yours: name one post-it and one envelope from your own app.',
  },
]
