// Warehouse Tour Mode: the screenplay as rail-engine data.
// Source of truth: ../../../tour/script.md (scenes, shot notes, evidence, where-it-breaks lines).
// Canon: ../../../world/warehouse-bible.md. Voice: ../../../world/tone.md.
// [J] = Jarad's words (the manager's opening three lines). Everything else is [P], a proposal.
// One beat = one camera stop. `set` and `hero.at` are station ids or new set ids (see sets.ts).

export interface Beat {
  id: string
  set: string
  caption: string
  hero: { form: 'parcel' | 'postit' | 'envelope' | 'slip' | 'recording' | 'none'; at: string }
  lines: { who: string; text: string }[]
  bulb?: 'normalization' | 'failopen' | 'fanout' | 'eventcommand' | 'retention' | 'workqueue' | 'idempotent'
  teaches: string
}

// Faces go on people, never on data. Blue is the belt's colour, so only Professor Haugen wears it.
export const CAST: Record<string, { name: string; role: string; real: string; color: string; accent: string; height: number }> = {
  damian: { name: 'Damian', role: 'new hire', real: 'you, the reader', color: '#F97316', accent: '#FDE68A', height: 0.85 },
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

export const TOUR: Beat[] = [
  // ---------- Scene 1: the briefing ----------
  {
    id: 'brief', set: 'entrance', caption: 'The entrance', hero: { form: 'recording', at: 'entrance' },
    lines: [
      { who: 'manager', text: "Look, I know you're new here. But what better way to learn your way around. The campus. Or something." },
      { who: 'manager', text: "I need you to deliver this message to the guys down in Voxxy. Now, it's packaged up. So you're gonna have to take it through processing yourself." },
      { who: 'manager', text: "When the guys are done, take their result and bring it back here. I'll be waiting for you." },
      { who: 'damian', text: "Processing. Right. Where's the message?" },
      { who: 'manager', text: "On you. This is Warehouse One, twice the rooms of yours, so stay on the rail. I'll be here. Waiting. Seriously." },
      { who: 'damian', text: "On me. So it's whatever I write down." },
    ],
    teaches: 'The errand: a question goes in, an answer comes back. This is Warehouse One, not your building.',
  },

  // ---------- Leg A: the dock lesson ----------
  {
    id: 'enter', set: 'bays', caption: 'Enter', hero: { form: 'parcel', at: 'bays' },
    lines: [
      { who: 'damian', text: 'Dear Voxxy. The manager wants an answer, please. Love, Damian. And... Enter.' },
      { who: 'dash', text: 'Box for the dock.' },
      { who: 'damian', text: "It's for Voxxy." },
      { who: 'dash', text: "It's for the dock. That label is Codex saying “he asked something”, in Codex's own handwriting. Every vendor writes its own." },
      { who: 'damian', text: 'And the answer?' },
      { who: 'dash', text: "Codex already went to its own model, by its own road. We're not on that road. I carry the news that you asked." },
    ],
    teaches: 'Pressing Enter fires a hook, and the vendor packs one parcel in its own words. The warehouse sits beside the road to the model, never on it.',
  },
  {
    id: 'courier', set: 'courier', caption: 'The courier', hero: { form: 'parcel', at: 'courier' },
    lines: [
      { who: 'damian', text: "What if the dock's closed?" },
      { who: 'dash', text: "Then I turn round with the box. I don't knock twice, I don't leave it on the step, and I don't bother Codex about it." },
      { who: 'damian', text: 'So the news...' },
      { who: 'dash', text: "Never gets written down. No queue, no second try. You'll hear this called fail-open: the helper is down, the real work carries on." },
      { who: 'damian', text: "That's a little bleak." },
      { who: 'dash', text: "It's a little fast. The whole trip takes a few thousandths of a second. The skates are for morale." },
    ],
    bulb: 'failopen',
    teaches: 'If the dock is shut, the courier turns round. Nothing queues, the vendor never waits, and no post-it is written. That is fail-open.',
  },
  {
    id: 'window', set: 'library', caption: 'The driver’s window', hero: { form: 'parcel', at: 'dock' },
    lines: [
      { who: 'fenwick', text: 'Codex question. Window cards run in order: reminders, the library, the code map. You wait, Dash.' },
      { who: 'dash', text: "I always wait at the window. It's the only place anyone hands me anything back." },
      { who: 'odette', text: "Last time on this project, you learned the voice booth reads one script at a time. Card's printing." },
      { who: 'fenwick', text: 'Briefing card. It goes back to Codex before Codex carries on. It never goes on the belt.' },
      { who: 'damian', text: "And if the library's slow?" },
      { who: 'odette', text: "Then the card leaves without my paragraph, dear. The hourglass doesn't wait for me, and neither does Codex." },
    ],
    teaches: 'Some parcels wait at the window for a briefing card. It goes back to the vendor in time or not at all, and never goes on the belt.',
  },
  {
    id: 'receiving', set: 'dock', caption: 'Receiving', hero: { form: 'postit', at: 'dock' },
    lines: [
      { who: 'fenwick', text: 'Codex writes “UserPromptSubmit”. Gemini writes “BeforeAgent”. opencode writes “chat.message”. They all mean one thing, and the house writes it one way.' },
      { who: 'fenwick', text: '“Turn started.” Codex goes in the small corner, never the headline. Its own packing slip, stapled to the back.' },
      { who: 'damian', text: "What's the stripe along the bottom?" },
      { who: 'fenwick', text: "The barcode. One per conversation, made from Codex's own session number. Every note from this chat wears it." },
      { who: 'dash', text: "I don't wait for any of that. The back room writes it after I've gone." },
    ],
    bulb: 'normalization',
    teaches: 'Parcels in, one house post-it out: “turn started”, vendor in the corner. One barcode per conversation. That is normalization.',
  },
  {
    id: 'labeldesk', set: 'labeldesk', caption: 'The label desk', hero: { form: 'postit', at: 'labeldesk' },
    lines: [
      { who: 'fenwick', text: 'Headline for the inspector: “Codex turn started.”' },
      { who: 'cruz', text: 'Refused. Vendors live in the corner. The headline uses house words only, and every word is in the book.' },
      { who: 'damian', text: "What's written inside? My question?" },
      { who: 'cruz', text: 'Word for word. Anyone who tears off a copy can read what you asked.' },
      { who: 'damian', text: 'I wrote “Love, Damian.”' },
      { who: 'cruz', text: 'Then the whole building knows.' },
    ],
    teaches: 'The label desk allows house words only, and the vendor never goes in the headline. Your question rides on the post-it for anyone to read.',
  },
  {
    id: 'loading', set: 'belt', caption: 'The belt', hero: { form: 'postit', at: 'belt' },
    lines: [
      { who: 'kofi', text: '“Come in,” it says. So it’s on.' },
      { who: 'haugen', text: "It says it heard you, Kofi. That isn't the same as kept. Your doorbell never waits for a receipt." },
      { who: 'kofi', text: "And if the door's shut?" },
      { who: 'haugen', text: 'Then your note hits the floor and nobody tries again. Now watch it climb. Height is age. At seven days the scraper takes it, read or not.' },
      { who: 'damian', text: 'So the belt carries it to Voxxy.' },
      { who: 'haugen', text: "The belt carries it nowhere. It's a noticeboard that scrolls up at the speed of the clock. Readers come to it." },
    ],
    bulb: 'retention',
    teaches: 'The dock’s poster rings a doorbell: heard is not kept. On the belt height is age, and the scraper takes post-its at seven days, read or not.',
  },
  {
    id: 'readers', set: 'cataloguer', caption: 'Tear off a copy', hero: { form: 'postit', at: 'belt' },
    lines: [
      { who: 'haugen', text: "Readers. The archive's runner tears off a copy for the racks. The control room reads through its visitor's window, with a pass and a notebook." },
      { who: 'damian', text: 'They took it off the belt?' },
      { who: 'haugen', text: "They took a copy. The original stays for the next reader. You'll hear this called fan-out." },
      { who: 'lefevre', text: '“Turn started”? Non. I tag finished tool calls. A question is not a finished anything.' },
      { who: 'damian', text: "So who's reading it for Voxxy?" },
      { who: 'lefevre', text: 'Look at the clips, monsieur. Do you see one for Voxxy?' },
    ],
    bulb: 'fanout',
    teaches: 'Readers tear off copies and the original stays. A pick list lets other notes slide past. That is fan-out.',
  },
  {
    id: 'turn', set: 'belt', caption: 'Nobody asked anybody', hero: { form: 'postit', at: 'belt' },
    lines: [
      { who: 'haugen', text: "That's a note about a question. It says “he asked”. It doesn't ask anyone to do anything." },
      { who: 'damian', text: 'Then how does anything get done?' },
      { who: 'haugen', text: 'Somebody writes an envelope: one instruction, for one worker, round the back. Nobody at the dock writes envelopes.' },
      { who: 'damian', text: 'And Voxxy?' },
      { who: 'haugen', text: "Not on the belt at all. No clip, no hatch. They have a door you slide things under. What's that in your vest?" },
      { who: 'damian', text: "The manager's pad. One memo, unsent. The message was on me the whole time." },
    ],
    bulb: 'eventcommand',
    teaches: 'A post-it announces; an envelope asks one worker to do one thing. Nothing at the dock writes envelopes, and Voxxy is not on the belt.',
  },

  // ---------- Leg B: the memo run (a different door, a different barcode) ----------
  {
    id: 'memodoor', set: 'entrance', caption: 'The memo door', hero: { form: 'recording', at: 'entrance' },
    lines: [
      { who: 'reggie', text: "Memo door. Pads only. That's a tape, son, not a parcel. Parcels go to the dock." },
      { who: 'damian', text: "It's for Voxxy." },
      { who: 'reggie', text: "It's for holocene-pm. That's a worker. Voxxy doesn't answer questions. Voxxy reads answers out loud." },
      { who: 'reggie', text: 'On the shelf: inbox, holocene-pm, today. That shelf address is your barcode now. Every note from this errand wears it.' },
      { who: 'reggie', text: "“Memo uploaded,” stuck. And a ring for the memo desk, so it doesn't wait for its next look round." },
    ],
    teaches: 'The errand enters by the memo door, not the dock. The tape’s shelf address becomes the barcode every later note wears.',
  },
  {
    id: 'memodesk', set: 'control', caption: 'The memo desk', hero: { form: 'recording', at: 'control' },
    lines: [
      { who: 'priya', text: "Ring heard. “Memo received,” stuck. Worker holocene-pm, routable. Level's fine. Wren?" },
      { who: 'wren', text: 'He said: “Holly. Why does the car take so long to talk back. Thirty words. Go.”' },
      { who: 'priya', text: '“Memo transcribed,” stuck: the words, how long it ran, which ears heard it.' },
      { who: 'damian', text: "Couldn't you answer it yourself?" },
      { who: 'priya', text: 'Some memos I can, at the quick desk, with no envelope at all. This one is addressed to a worker. So it gets an envelope.' },
    ],
    teaches: 'The memo desk turns the tape into text and sticks a post-it for each step. A memo for a worker gets an envelope.',
  },
  {
    id: 'envelope', set: 'control', caption: 'The first envelope', hero: { form: 'envelope', at: 'control' },
    lines: [
      { who: 'priya', text: 'An envelope. One instruction, for one worker. Outside, “invoke”. Inside: holocene-pm, his words, the thread, and which agency to phone.' },
      { who: 'damian', text: "That's the first envelope I've seen anyone write." },
      { who: 'priya', text: 'I copy the barcode on. A barcode only crosses rooms when the next writer copies it.' },
      { who: 'priya', text: 'And a safe-to-repeat code under the flap, because envelopes can come round twice.' },
      { who: 'priya', text: "Checked, rung, gone. “Memo dispatched.” I don't trust doorbells, so I'll read the crew hall's ledger to see it landed." },
    ],
    teaches: 'The memo desk, not the dock, writes the envelope: “invoke”, for one worker, with the copied barcode and a safe-to-repeat code.',
  },
  {
    id: 'hatch', set: 'crew', caption: 'The express hatch', hero: { form: 'envelope', at: 'crew' },
    lines: [
      { who: 'okafor', text: 'Welcome to the crew hall. Express hatch, for envelopes a human is waiting on. Each kind of envelope has one hatch at most.' },
      { who: 'damian', text: "You've taken it, so it's off the belt." },
      { who: 'okafor', text: 'Taken is not gone, sir. It stays on the belt, marked in hand, until I sign it off. If I go quiet, it will be offered again.' },
      { who: 'okafor', text: 'One line in my ledger. Then two post-its at the registered counter, and I wait for a receipt with the belt number on it.' },
      { who: 'damian', text: "“Turn started.” That's what the dock wrote for me." },
      { who: 'okafor', text: 'Same words, different poster, different barcode. The dock had nothing to do with this one.' },
    ],
    bulb: 'workqueue',
    teaches: 'One hatch per kind of envelope. Taken is not gone: it stays on the belt, in hand, until signed off. That is a work queue.',
  },
  {
    id: 'staffing', set: 'staffing', caption: 'The workstation phones out', hero: { form: 'envelope', at: 'crew' },
    lines: [
      { who: 'holly', text: 'Envelope for me. Badge, locker, placards. Right. I need a model.' },
      { who: 'mags', text: 'Staffing desk. The envelope names a route, so I ring the first agency on its list. If it rings out, I try the next number.' },
      { who: 'damian', text: 'Is the agency in the building?' },
      { who: 'mags', text: 'Across town, love. Their answers come back to Holly, never across your belt.' },
      { who: 'okafor', text: "“Still working.” I stamp it every so often, so nobody thinks I've gone quiet and offers it to someone else." },
      { who: 'holly', text: "Thinking out loud. That's “invocation progressed”: bits of my working. Never the final answer." },
    ],
    teaches: 'A workstation sleeps until an envelope wakes it. Its model call goes through the staffing desk, which tries agencies in order.',
  },
  {
    id: 'booth1', set: 'voxxy', caption: 'The voice booth', hero: { form: 'envelope', at: 'crew' },
    lines: [
      { who: 'damian', text: "I've come about the manager's message. Are you the guys?" },
      { who: 'vinnie', text: "We're the guys. We don't take deliveries, kid. No envelopes, no clips, no hatch. You slide it under the door." },
      { who: 'vinnie', text: "Like that. Priya reads Holly's working off the archive, and every half minute or so she sends me the newest line." },
      { who: 'mo', text: '“Holly is checking the memo desk’s timings now.”' },
      { who: 'vinnie', text: 'Script in, recording out, and she waits at the door for it. A plain API call, no belt anywhere. She files it and sticks “memo narrated”.' },
      { who: 'damian', text: "So that wasn't the answer." },
    ],
    teaches: 'Voxxy is not on the belt. A script slides under the door and a recording comes back: a plain API call.',
  },

  // ---------- Scene 13: side scenes, not on this errand's route ----------
  {
    id: 'clock', set: 'clock', caption: 'Side scene: the clock', hero: { form: 'envelope', at: 'crew' },
    lines: [
      { who: 'damian', text: 'Is this on my route?' },
      { who: 'constance', text: 'No. Nothing on your errand waits for a bell. I own when things happen, not what anyone asked.' },
      { who: 'constance', text: 'When I ring, the planner writes an envelope for each chore due. My hands take them through my two hatches and check the safe-to-repeat code first.' },
      { who: 'damian', text: 'Could I set a reminder to collect the answer?' },
      { who: 'constance', text: "A private alarm. In this building. One bell, no private alarms. The guard at the dock's window confiscates them." },
    ],
    teaches: 'Side scene: the clock owns when. Its chores go out as envelopes, and there is one bell and no private alarms.',
  },
  {
    id: 'soundwing', set: 'soundwing', caption: 'Side scene: the sound wing', hero: { form: 'envelope', at: 'crew' },
    lines: [
      { who: 'damian', text: 'You do audio. Do you send things to Voxxy?' },
      { who: 'gloria', text: 'Never have. My wing takes recordings in through three doors, locks them in the cage first, and runs eight passes over each transcript.' },
      { who: 'gloria', text: 'We write envelopes too. Look at that grey stack. No hatch for that kind. Up they go, unsigned, until the one-day scraper.' },
      { who: 'damian', text: 'So not every envelope gets handled.' },
      { who: 'gloria', text: 'Some never get opened, dear. An envelope with no hatch is a letter to an empty room.' },
    ],
    teaches: 'Side scene: the sound wing never calls Voxxy, and some of its envelopes have no hatch, so they wait for the scraper.',
  },

  // ---------- back on the route ----------
  {
    id: 'signoff', set: 'crew', caption: 'Signed off', hero: { form: 'postit', at: 'crew' },
    lines: [
      { who: 'okafor', text: 'Holly has finished. “Invocation completed”, “turn completed”, stuck. Then I sign it off: finished with it, not proof it worked.' },
      { who: 'damian', text: "This post-it says which hatch and how long it took. Where's the answer?" },
      { who: 'okafor', text: "In Holly's session book, sir. Post-its say what happened, not what was said." },
      { who: 'damian', text: "Don't I get a reply slip?" },
      { who: 'okafor', text: 'There is a window for those. Dashed tape: Pilot and Krebs use it, and nobody is at it today. In this hall, done is a post-it.' },
    ],
    teaches: 'A signature means finished with the envelope, not that it worked. Done is a post-it, and the answer is not on it.',
  },
  {
    id: 'ledger', set: 'control', caption: 'Take their result', hero: { form: 'none', at: 'control' },
    lines: [
      { who: 'priya', text: "I don't wait for the post-it. I read the crew hall's ledger, the line for my envelope. It says finished." },
      { who: 'priya', text: "Then Holly's session book: the thread with my memo's barcode, the newest answer, written after I sent the envelope." },
      { who: 'damian', text: 'So the answer never went on the belt.' },
      { who: 'priya', text: "Not a word of it. The belt has notes about the answer. The answer lives in Holly's book." },
      { who: 'damian', text: "“Take their result and bring it back.” I thought I'd be carrying something." },
      { who: 'priya', text: 'You are. A key to a shelf. Come on. It needs a voice.' },
    ],
    teaches: 'The memo desk learns it is done from the crew hall’s ledger and reads the answer from the session book. The answer never rides the belt.',
  },
  {
    id: 'booth2', set: 'voxxy', caption: 'One script at a time', hero: { form: 'recording', at: 'voxxy' },
    lines: [
      { who: 'vinnie', text: 'Thirty words, he asked for. She wrote ninety. Long ones I cut at the full stops. Three pieces.' },
      { who: 'mo', text: 'One at a time. “Because your memo goes through a desk, a hatch, a workstation and a voice booth...”' },
      { who: 'vinnie', text: "Each piece goes out the moment it's done, and Priya takes it at the door. We keep a copy on the rack for an hour. Then it's gone." },
      { who: 'damian', text: 'The librarian said you only read one script at a time.' },
      { who: 'mo', text: "She's always right. Give me two at once and the second one waits at the door." },
    ],
    teaches: 'The reply is cut at sentence ends and read one piece at a time. No envelope, hatch or reply slip is involved.',
  },
  {
    id: 'pad', set: 'entrance', caption: 'Bring it back', hero: { form: 'recording', at: 'entrance' },
    lines: [
      { who: 'reggie', text: 'Piece one’s on the reply shelf. “Memo voiced.” The post-it says where it is and what it says. Never the sound itself.' },
      { who: 'reggie', text: "That's my bell to the pad. It fetches the piece off the shelf and plays it. Car or phone, never both." },
      { who: 'manager', text: '“...and the booth reads one script at a time.” I said thirty words.' },
      { who: 'reggie', text: "“Memo replied,” stuck. That's the last step anyone in here can see. The pad sends back “memo played” when it's done." },
      { who: 'manager', text: 'You took the long way round.' },
      { who: 'damian', text: 'I took both ways round.' },
    ],
    teaches: 'Each piece goes on the reply shelf with a post-it saying where it is. A bell tells the pad to fetch and play it, car or phone, never both.',
  },
  {
    id: 'barcode', set: 'archive', caption: 'One barcode', hero: { form: 'postit', at: 'archive' },
    lines: [
      { who: 'fitch', text: 'Barcode, please. Uploaded, received, transcribed, dispatched, started, narrated three times, completed, voiced, replied, played. About forty notes.' },
      { who: 'damian', text: 'Some of those came in twice.' },
      { who: 'fitch', text: "Then I filed them once. Same Note ID, same slot. You'll hear this called idempotent." },
      { who: 'manager', text: 'And this one?' },
      { who: 'fitch', text: 'Different barcode. A Codex chat. It says he asked something, and nobody was asked to do anything.' },
      { who: 'manager', text: 'Good work, Damian. And stop writing “Love, Damian” on things. The whole building reads them.' },
    ],
    bulb: 'idempotent',
    teaches: 'One barcode rebuilds the whole errand, and the archive files each note once. Your Codex question wears a different barcode.',
  },
]
