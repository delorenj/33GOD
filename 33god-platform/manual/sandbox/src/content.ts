// Every word a reader sees lives here, so Jarad can rewrite copy without touching the scene.
// Canon: ../../world/warehouse-bible.md. Voice: ../../world/tone.md.
// [J] = Jarad's direction, [P] = proposal.

export type Vec3 = [number, number, number]

export type StationId =
  | 'bays' | 'courier' | 'dock' | 'labeldesk' | 'belt'
  | 'archive' | 'rules' | 'control' | 'cataloguer' | 'clock' | 'crew'

export type BulbId = 'normalization' | 'failopen' | 'fanout' | 'eventcommand' | 'retention' | 'workqueue' | 'idempotent'

export interface Station {
  id: StationId
  name: string // world word, printed large
  real: string // real name, printed small
  bloodbank: boolean // part of Material Handling (Bloodbank)
  does: string[]
  breaks?: string
  evidence: string[]
  label: Vec3
  view: { pos: Vec3; target: Vec3 }
  bulbs: BulbId[]
}

export const OVERVIEW = { pos: [24, 17, 30] as Vec3, target: [-2, 4, 0] as Vec3 }
// a phone held upright has a narrow horizontal field of view: pull back so the bays and the belt both fit
export const OVERVIEW_PORTRAIT = { pos: [38, 30, 58] as Vec3, target: [-10, 3, 0] as Vec3 }
export const isPortrait = () => innerWidth / innerHeight < 0.9
export const overview = () => (isPortrait() ? OVERVIEW_PORTRAIT : OVERVIEW)

export const STATIONS: Station[] = [
  {
    id: 'bays', name: 'Vendor bays', real: 'agent CLIs: Claude Code, Codex, Kimi, Copilot, Gemini, opencode', bloodbank: false,
    does: [
      'Each coding tool you use is a vendor with its own bay. It packs its news in its own label language.',
      'A parcel is what a vendor sends when something happens, such as you pressing Enter, exactly as it packed it.',
    ],
    breaks: 'Vendors do not drive anywhere. They run on your machine and leave a peg out for our courier to hang on. You’ll hear that peg called a hook.',
    evidence: ['bloodbank/services/agent-hooks/hooks.master.json (one source, fanned out to every dialect)'],
    label: [-24, 4.6, 0], view: { pos: [-11, 8, 15], target: [-23, 1.5, 0] }, bulbs: [],
  },
  {
    id: 'courier', name: 'The courier', real: 'bb-hook', bloodbank: true,
    does: [
      'One uniform at every bay. The courier carries each parcel to the receiving dock, waits at the window for the clerk’s answer (a briefing card, or a yes or no), and hands that back to the vendor.',
      'If the dock door is shut, the courier turns round with the parcel still in hand. The vendor carries on working, without the briefing. No post-it gets written.',
    ],
    breaks: 'The real trip takes milliseconds, inside your machine, not a walk across the floor.',
    evidence: ['bb-hook → $XDG_RUNTIME_DIR/33god/hook-hub.sock', 'bb-hook: 3 s deadline; after one stall, 0.25 s probes for 30 s (the Mac wrapper bounds it to about 1 s, W2-4)'],
    label: [-17, 2.6, 4.2], view: { pos: [-9, 6, 11], target: [-17, 0.6, 1] }, bulbs: ['failopen'],
  },
  {
    id: 'dock', name: 'Receiving dock', real: 'hook-hub', bloodbank: true,
    does: [
      'Parcels in, post-its out. A clerk opens every parcel and copies the news onto one house post-it.',
      'The vendor’s name goes in the small “from” corner. The original packing slip, everything the vendor sent, is stapled to the back.',
    ],
    breaks: 'The dock rewrites the label, not the whole parcel. The packing slip still carries the vendor’s own JSON.',
    evidence: ['hook-hub/handlers.toml', 'agent-hooks/clients/*.py build one envelope', 'core/validate.py assert_contract'],
    label: [-9.5, 4.9, 0], view: { pos: [-3.5, 5, 9.5], target: [-9.5, 1.5, 0] }, bulbs: ['normalization'],
  },
  {
    id: 'labeldesk', name: 'Label desk', real: 'naming contract', bloodbank: true,
    does: [
      'Keeps the house dictionary of legal label words and a form pad for every kind of note.',
      'Every note written at the dock is checked against the dictionary here. Checking it against the form pad is optional, and off by default.',
    ],
    breaks: 'The belt itself never proofreads. A note written somewhere else can skip this desk: watch the cataloguer. A note that fails the check is not held or sent back. It is dropped, with a line in the receipt log.',
    evidence: ['bloodbank/schemas/bloodbank/v1/**', 'validate.py assert_contract (always); JSON Schema only with BLOODBANK_HOOK_VALIDATE=1'],
    label: [-8, 1.3, 5.1], view: { pos: [-5, 4, 10], target: [-9.5, 0.8, 3] }, bulbs: [],
  },
  {
    id: 'belt', name: 'The belt', real: 'the bus: one place for every room to stick news, instead of phoning each other', bloodbank: true,
    does: [
      'A tall belt that turns slowly, all day, whether or not anyone is watching. Height is age.',
      'Front face: post-its, kept 7 days. Back face: envelopes, kept 1 day.',
      'Anyone with news sticks a note on. Readers come to the belt and tear off a copy.',
    ],
    breaks: 'Real streams do not move. The motion stands for age, not for travel.',
    evidence: ['NATS JetStream, two streams: bloodbank/compose/nats/streams.json: BLOODBANK_EVENTS 7d limits, BLOODBANK_COMMANDS 1d workqueue'],
    label: [0, 15.4, 0], view: { pos: [10, 9, 27], target: [0, 7.2, 0] }, bulbs: ['fanout', 'eventcommand', 'retention'],
  },
  {
    id: 'archive', name: 'The archive', real: 'Candystore', bloodbank: false,
    does: [
      'A filing clerk tears off a copy of every post-it and files it on the racks.',
      'Before filing, the clerk checks the label fields and the Note ID. A note with fields missing goes in the rejects drawer, and a copy already on the rack is not filed twice.',
    ],
    breaks: 'The racks have no scraper of their own today and make no promise either way. Nothing deletes a filed note now, but nobody has promised to keep it.',
    evidence: ['candystore db.py: ON CONFLICT (id) DO NOTHING; REQUIRED_ENVELOPE_FIELDS → dead_letter', 'durable consumer candystore-events, deliver all'],
    label: [10.7, 3.8, 5.6], view: { pos: [16, 6, 14], target: [8, 1.5, 5] }, bulbs: ['idempotent'],
  },
  {
    id: 'rules', name: 'Rules cabinet', real: 'n8n', bloodbank: false,
    does: [
      'Rule cards, each with its own clip on the belt: a bookmark that remembers how far that card has read. A pick list says which notes a card cares about.',
      'This card only wants “invocation completed”. Every other note goes past it. Other cards here stick envelopes on the back, to hand jobs to the crew hall.',
    ],
    breaks: 'The pick list shown here is an example. Real cards choose their own.',
    evidence: ['n8n-nodes-bloodbank durable triggers: n8n-<workflow>-<node> on BLOODBANK_EVENTS', 'Fleet.node.ts publishes bloodbank.cmd.agent.invocation.start'],
    label: [5.5, 3, 8.5], view: { pos: [12, 5, 17], target: [5.5, 1, 8.5] }, bulbs: [],
  },
  {
    id: 'control', name: 'Control room', real: 'Holocene', bloodbank: false,
    does: [
      'Up on the mezzanine, watching the floor through a visitor’s window.',
      'It has no clip on the belt. It keeps its own place in its own notebook, and takes a fresh visitor’s pass each visit.',
    ],
    breaks: 'The window shows the floor a moment late, never in the same instant.',
    evidence: ['holocene/packages/bloodbank-client: ephemeral ordered consumer, ack none, own checkpoint'],
    label: [12.6, 5.4, 3.2], view: { pos: [18, 9, 9], target: [9.5, 4, 0.5] }, bulbs: [],
  },
  {
    id: 'cataloguer', name: 'The cataloguer', real: 'Enricher', bloodbank: false,
    does: [
      'Reads a note saying a session ended, asks the archive for that session’s history, and writes a one-paragraph summary.',
      'Its runner, a helper who stands at the belt for a room with no window of its own, sticks that note straight on. It never visits the label desk, so it has no barcode and no “from” corner.',
    ],
    breaks: 'The archive turns this note away: it has no producer, service, domain or kind, so it lands in the rejects drawer, not on the racks. The belt still carries it and the control room still sees it. Of the writers drawn on this floor, it is the only one that sticks notes through a runner.',
    evidence: ['33god-platform/enricher/main.py:164 emit_event via enricher-daprd /v1.0/publish', 'durable enricher-events on bloodbank.evt.>, acts on agent.session.ended', 'candystore main.py _drop: dead_letter "missing CloudEvents fields"'],
    label: [2.9, 1.7, 1.6], view: { pos: [1, 3, 9], target: [4.8, 1, 2.4] }, bulbs: [],
  },
  {
    id: 'clock', name: 'The clock', real: 'Candybar', bloodbank: false,
    does: [
      'One bell on the wall. Anything that repeats is meant to ring from it, and from nowhere else.',
      'Every minute it sticks a tick post-it on the front of the belt. The planner at the desk beside it reads each tick, checks the chore list, and sticks an envelope on the back for the clock’s own hands, who run the chore.',
    ],
    breaks: 'The bell owns when a chore runs, not always who does it. A signed list of alarms still rings outside it, each with a named owner and a reason. Drawn with far fewer ticks than one a minute.',
    evidence: ['candybar/src/candybar/dispatcher/role.py: tick in, bloodbank.cmd.cron.candybar.invoke out', 'executor/role.py: durable candybar-executor-invoke'],
    label: [-6, 7.6, -6], view: { pos: [1, 7.5, -9.5], target: [-5.2, 2.8, -4.6] }, bulbs: [],
  },
  {
    id: 'crew', name: 'Crew hall', real: 'hermes-gateway', bloodbank: false,
    does: [
      'A hatch on the back of the belt keeps taking envelopes while there is room in its tray, and a few desks work at once. Each envelope names the one worker it is for.',
      'An envelope is not gone when it is taken. It is gone when the worker signs it off, or when the 1-day scraper reaches it. Then the hall sticks a post-it on the front: completed, or failed.',
    ],
    breaks: 'A signature means finished with the envelope, not that the job worked. Drawn with 4 desks and a tray of 4; the real hall’s tray holds 64. The real hall also has a second, express hatch for jobs a person is waiting on.',
    evidence: ['bloodbank/services/hermes-gateway/bloodbank_hermes_gateway/contract.py:40-49: durable bloodbank-hermes-gateway pulls bloodbank.cmd.agent.invocation.start (batch); bloodbank-hermes-gateway-interactive pulls ...invocation.invoke', 'live: max_ack_pending 68, max_deliver 5'],
    label: [8.5, 3.4, -10.6], view: { pos: [4.5, 9.5, 1.5], target: [7, 1, -7.2] }, bulbs: ['workqueue'],
  },
]

export const stationById = Object.fromEntries(STATIONS.map((s) => [s.id, s])) as Record<StationId, Station>

export interface Bulb {
  id: BulbId
  title: string
  at: Vec3
  station: StationId
  status: 'drafted' | 'proposal'
  body: string[] // paragraphs; a line starting with "> " renders as a label strip
  metBefore: string
  breaks?: string
  evidence: string
}

export const BULBS: Bulb[] = [
  {
    id: 'normalization', title: 'What is Normalization?', at: [-9.5, 4.1, -1.2], station: 'dock', status: 'drafted',
    body: [
      'Picture the receiving dock. Its real name is hook-hub.',
      'Parcels arrive all day, and no two vendors pack alike. Each carries a label in the vendor’s own words:',
      '> Claude, Codex, Kimi|UserPromptSubmit',
      '> Copilot|userPromptSubmitted',
      '> Gemini|BeforeAgent',
      '> opencode|chat.message',
      'A clerk opens every parcel and copies the news onto one house post-it: “turn started.” The vendor’s name goes in the small “from” corner, never the headline.',
      'You’ll hear this called normalization: many shapes come in, one agreed shape goes out.',
      'Without the dock, every reader on the floor would have to learn every vendor’s accent. With it, each accent is learned once, at the door.',
    ],
    metBefore: 'A shop that takes Stripe and PayPal turns both into one “payment received” record.',
    breaks: 'The dock agrees the label, not the whole parcel. The vendor’s original packing slip, JSON and all, stays stapled to the back.',
    evidence: 'hooks.master.json maps each vendor hook to one role (prompt_submit → conversation.turn.started); clients/*.py build one envelope, raw payload kept in data.',
  },
  {
    id: 'failopen', title: 'What is Fail-open?', at: [-15, 2.4, 3], station: 'courier', status: 'proposal',
    body: [
      'Shut the dock and watch the couriers.',
      'Each one walks to the door, finds it shut, and turns round with the parcel still in hand. With the door shut, the vendor does not wait. It carries on with your work, without the briefing card or the safety checks.',
      'You’ll hear this called fail-open: when the helper is down, the main job keeps going without it.',
    ],
    metBefore: 'An analytics script that fails while the page still loads.',
    breaks: 'Nothing queues at the door. No post-it gets written, so no reader ever sees that news. A stuck door is worse than a shut one: it costs the vendor up to three seconds on the first parcel, then about a quarter of a second each for the next half minute.',
    evidence: 'bb-hook exits clean when hook-hub.sock is unreachable or silent; its deadline is 3 s, and 0.25 s probes follow a stall.',
  },
  {
    id: 'fanout', title: 'What is Fan-out?', at: [3.1, 3.4, 1.3], station: 'belt', status: 'proposal',
    body: [
      'Watch the front of the belt. A post-it goes up once. The archive tears off a copy. So does the control room. The rules cabinet tears one off only when the note is on its pick list.',
      'The original never leaves. Each reader tears off the same note at its own pace, and whoever stuck it never knows who read it.',
      'You’ll hear this called fan-out: one note, many readers, no extra work for whoever stuck it.',
    ],
    metBefore: 'One button with several click handlers.',
    breaks: 'A reader that arrives late can only tear off copies of notes still on the belt. Whatever the scraper scraped is gone from here.',
    evidence: 'BLOODBANK_EVENTS has limits retention; each consumer keeps its own position.',
  },
  {
    id: 'eventcommand', title: 'Event or Command?', at: [-3.1, 6, 0], station: 'belt', status: 'proposal',
    body: [
      'Two kinds of paper ride this belt, on opposite faces.',
      'A post-it says something happened: “turn started”, “invocation completed”. It is for anyone: it says what happened, not who should care.',
      'An envelope asks for something to be done: “start: daily report”. It is for one kind of worker, and one worker takes it.',
      'You’ll hear the post-it called an event, and the envelope a command.',
      'A useful test: if nobody reads it, is anything wrong? An unread post-it is fine. An unopened envelope is usually a job not done, with one exception you will meet at the back of the belt.',
    ],
    metBefore: '“The oven beeped” versus “take the cake out”.',
    evidence: 'Subjects bloodbank.evt.> (BLOODBANK_EVENTS) and bloodbank.cmd.> (BLOODBANK_COMMANDS).',
  },
  {
    id: 'retention', title: 'What is Retention?', at: [3.1, 13.2, 1.2], station: 'belt', status: 'proposal',
    body: [
      'Notes ride up the belt a little every hour. Height is age.',
      'At the top of the front face, the 7-day mark, a scraper scrapes off whatever reaches it, read or not. The back face’s scraper sits much lower, at one day.',
      'You’ll hear this called retention: how long the belt keeps a note before letting it go.',
    ],
    metBefore: '“Delete chats after 30 days.”',
    breaks: 'The scraper never touches the archive’s copies. The racks keep a note for as long as the archive decides.',
    evidence: 'streams.json: BLOODBANK_EVENTS max_age 7d, discard old; BLOODBANK_COMMANDS 1d.',
  },
  {
    id: 'workqueue', title: 'What is a Work Queue?', at: [9.9, 3.3, -5.4], station: 'crew', status: 'proposal',
    body: [
      'Round the back, envelopes ride up until a hatch takes them. The crew hall’s hatch keeps taking while there is room in its tray, and only a few desks work at once. When the tray is full, the rest wait on the belt.',
      'A taken envelope stays on the belt, pinned, until the worker signs it off. If the hall has to close mid-shift and cannot start the job, the worker hands it back, the pin comes out, and it is offered again after a short wait. After five tries the hall stops, signs it off as failed and sticks a “failed” post-it on the front.',
      'You’ll hear this called a work queue: a line of jobs where each job goes to one worker.',
    ],
    metBefore: 'The ticket machine at a deli counter.',
    breaks: 'Some envelopes have no hatch at all. The sound wing writes one for every job it runs itself, only so the run can be traced afterwards, and nobody is meant to take it. They ride up untouched until the 1-day scraper scrapes them. Look for the grey ones: on the real belt almost everything left standing at the back is grey.',
    evidence: 'BLOODBANK_COMMANDS workqueue retention; ack removes, nak(5 s) redelivers; max_ack_pending 68 bounds the hatch; max_deliver 5.',
  },
  {
    id: 'idempotent', title: 'What does Idempotent mean?', at: [8, 3.4, 6.6], station: 'archive', status: 'proposal',
    body: [
      'Now and then the belt offers the archive the same note twice. The archive signs for a note once it has filed it. If that signature is late or lost, the belt waits about half a minute and offers the note again.',
      'The filing clerk checks the Note ID first. Already on the rack? Nothing gets filed, and the clerk moves on.',
      'Doing it twice leaves the same result as doing it once. You’ll hear this called idempotent.',
    ],
    metBefore: 'Pressing the lift button twice. Or a signup form that ignores an email it already has.',
    evidence: 'candystore db.py: INSERT … ON CONFLICT (id) DO NOTHING; ack_wait 30 s.',
  },
]

export const bulbById = Object.fromEntries(BULBS.map((b) => [b.id, b])) as Record<BulbId, Bulb>

export const VENDORS = [
  { name: 'Claude', word: 'UserPromptSubmit', color: '#D97757' },
  { name: 'Codex', word: 'UserPromptSubmit', color: '#3B82F6' },
  { name: 'Kimi', word: 'UserPromptSubmit', color: '#8B5CF6' },
  { name: 'Copilot', word: 'userPromptSubmitted', color: '#10B981' },
  { name: 'Gemini', word: 'BeforeAgent', color: '#F59E0B' },
  { name: 'opencode', word: 'chat.message', color: '#EC4899' },
]
