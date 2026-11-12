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

export const STATIONS: Station[] = [
  {
    id: 'bays', name: 'Vendor bays', real: 'agent CLIs: Claude Code, Codex, Kimi, Copilot, Gemini, opencode', bloodbank: false,
    does: [
      'Each coding tool you use is a vendor with its own bay. It packs its news in its own label language.',
      'A parcel is one raw hook, exactly as the vendor sent it.',
    ],
    breaks: 'Vendors do not drive anywhere. They run on your machine and leave a peg, a hook, that our courier hangs on.',
    evidence: ['bloodbank/services/agent-hooks/hooks.master.json (one source, fanned out to every dialect)'],
    label: [-24, 4.6, 0], view: { pos: [-11, 8, 15], target: [-23, 1.5, 0] }, bulbs: [],
  },
  {
    id: 'courier', name: 'The courier', real: 'bb-hook', bloodbank: true,
    does: [
      'One uniform at every bay. The courier carries each parcel to the receiving dock.',
      'If the dock door is shut, the courier turns round with the parcel still in hand, and the vendor carries on working.',
    ],
    breaks: 'The real trip takes milliseconds, over a local socket, not a walk across the floor.',
    evidence: ['bb-hook → $XDG_RUNTIME_DIR/33god/hook-hub.sock', 'W2-4 bounded a hung hub to about 1 s'],
    label: [-17, 2.6, 4.2], view: { pos: [-9, 6, 11], target: [-17, 0.6, 1] }, bulbs: ['failopen'],
  },
  {
    id: 'dock', name: 'Receiving dock', real: 'hook-hub', bloodbank: true,
    does: [
      'Parcels in, post-its out. A clerk opens every parcel and copies the news onto one house post-it.',
      'The vendor goes in the small "from" corner. The original packing slip is stapled to the back.',
    ],
    breaks: 'The dock rewrites the label, not the whole parcel. The vendor’s own contents still ride along, stapled on.',
    evidence: ['hook-hub/handlers.toml', 'agent-hooks/clients/*.py build one envelope', 'core/validate.py assert_contract'],
    label: [-9.5, 4.9, 0], view: { pos: [-3.5, 5, 9.5], target: [-9.5, 1.5, 0] }, bulbs: ['normalization'],
  },
  {
    id: 'labeldesk', name: 'Label desk', real: 'naming contract, schemas, validator', bloodbank: true,
    does: [
      'Keeps the house dictionary of legal label words and a form pad for every kind of note.',
      'Notes written at the dock are checked here before they go up.',
    ],
    breaks: 'The belt itself never proofreads. A note written somewhere else can skip this desk. Watch the cataloguer.',
    evidence: ['bloodbank/schemas/bloodbank/v1/**', 'validate.py assert_contract'],
    label: [-9.5, 2.3, 3.6], view: { pos: [-5, 4, 10], target: [-9.5, 0.8, 3] }, bulbs: [],
  },
  {
    id: 'belt', name: 'The belt', real: 'the bus: NATS JetStream, two streams back to back', bloodbank: true,
    does: [
      'A tall belt that turns slowly, all day, whether or not anyone is watching. Height is age.',
      'Front face: post-its (events), kept 7 days. Back face: envelopes (commands), kept 1 day.',
      'Posters stick notes on. Readers come to the belt and tear off a copy. The belt never delivers.',
    ],
    breaks: 'Real streams do not move. The motion stands for age, not for travel.',
    evidence: ['bloodbank/compose/nats/streams.json: BLOODBANK_EVENTS 7d limits, BLOODBANK_COMMANDS 1d workqueue'],
    label: [0, 15.4, 0], view: { pos: [9, 9, 19], target: [0, 7, 0] }, bulbs: ['fanout', 'eventcommand', 'retention'],
  },
  {
    id: 'archive', name: 'The archive', real: 'Candystore', bloodbank: false,
    does: [
      'A filing clerk tears off a copy of every post-it and files it on the racks.',
      'Before filing, the clerk checks the Note ID. A copy that is already on the rack is not filed twice.',
    ],
    breaks: 'The racks are not "forever". They keep their own copy on their own rules, apart from the belt’s scraper.',
    evidence: ['candystore db.py: ON CONFLICT (id) DO NOTHING', 'durable consumer candystore-events, deliver all'],
    label: [9.2, 4.4, 5.6], view: { pos: [16, 6, 14], target: [8, 1.5, 5] }, bulbs: ['idempotent'],
  },
  {
    id: 'rules', name: 'Rules cabinet', real: 'n8n', bloodbank: false,
    does: [
      'Rule cards, each wired to its own clip on the belt. A pick list says which notes a card cares about.',
      'Here the card only wants session summaries. Every other note goes past it.',
    ],
    breaks: 'The pick list shown here is an example. Real cards choose their own.',
    evidence: ['n8n-nodes-bloodbank durable triggers: n8n-<workflow>-<node> on BLOODBANK_EVENTS'],
    label: [5.5, 3, 8.5], view: { pos: [12, 5, 17], target: [5.5, 1, 8.5] }, bulbs: [],
  },
  {
    id: 'control', name: 'Control room', real: 'Holocene', bloodbank: false,
    does: [
      'Up on the mezzanine, watching the floor through a visitor’s window.',
      'It keeps its own place in its own notebook, and gets a fresh visitor’s pass each visit. The belt does not remember it.',
    ],
    breaks: 'The window shows the floor a moment late, never in the same instant.',
    evidence: ['holocene/packages/bloodbank-client: ephemeral ordered consumer, ack none, own checkpoint'],
    label: [12.6, 5.4, 3.2], view: { pos: [18, 9, 9], target: [9.5, 4, 0.5] }, bulbs: [],
  },
  {
    id: 'cataloguer', name: 'The cataloguer', real: 'Enricher', bloodbank: false,
    does: [
      'Writes an end-of-session summary. Its runner sticks that note straight on the belt.',
      'That note never visits the label desk, so it has no barcode and no "from" corner.',
    ],
    breaks: 'This is the one writer that posts through a runner. Everyone else sticks notes by hand.',
    evidence: ['33god-platform/enricher/main.py:164 emit_event via enricher-daprd /v1.0/publish'],
    label: [2.9, 1.7, 1.6], view: { pos: [11, 4.5, 8], target: [4.6, 1, 2] }, bulbs: [],
  },
  {
    id: 'clock', name: 'The clock', real: 'Candybar', bloodbank: false,
    does: [
      'One bell on the wall, and no private alarms anywhere.',
      'When it rings, a chore goes out as an envelope on the back of the belt.',
    ],
    evidence: ['candybar/README.md: the single clock'],
    label: [-6, 7.6, -6], view: { pos: [-13, 8, -17], target: [-6, 3, -6] }, bulbs: [],
  },
  {
    id: 'crew', name: 'Crew hall', real: 'hermes-gateway', bloodbank: false,
    does: [
      'One hatch on the back of the belt. It opens only when a desk is free, so each envelope goes to one worker.',
      'An envelope is not gone when it is taken. It is gone when the worker signs it off.',
    ],
    breaks: 'A signature means finished with the envelope, not that the job worked.',
    evidence: ['hermes-fleet-bloodbank-gateway subscribes bloodbank.cmd.v1.agent.invocation.start'],
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
      'Vendors’ vans pull up all day, and no two pack alike. Each parcel carries a label in the vendor’s own words:',
      '> Claude, Codex, Kimi|UserPromptSubmit',
      '> Copilot|userPromptSubmitted',
      '> Gemini|BeforeAgent',
      '> opencode|chat.message',
      'A clerk opens every parcel and copies the news onto one house post-it: “turn started.” The vendor’s name goes in the small “from” corner, never the headline.',
      'You’ll hear this called normalization: many shapes come in, one agreed shape goes out.',
      'Without the dock, every reader on the floor would have to learn every vendor’s accent. With it, each accent is learned once, at the door. A new vendor tomorrow means only the dock learns something new.',
    ],
    metBefore: 'A shop that takes Stripe and PayPal turns both into one “payment received” record.',
    evidence: 'hooks.master.json maps each vendor hook to one role (prompt_submit → conversation.turn.started); clients/*.py build one envelope, raw payload kept in data.',
  },
  {
    id: 'failopen', title: 'What is Fail-open?', at: [-15, 2.4, 3], station: 'courier', status: 'proposal',
    body: [
      'Press “Shut the dock” below and watch the couriers.',
      'Each one walks to the door, finds it shut, and turns round with the parcel still in hand. The vendor never waits for the dock. It carries on with your work.',
      'You’ll hear this called fail-open: when the helper is down, the main job keeps going without it.',
    ],
    metBefore: 'An analytics script that fails while the page still loads.',
    breaks: 'Nothing queues at the door. That news never reaches the belt, so no reader will ever see it.',
    evidence: 'bb-hook exits clean when hook-hub.sock is unreachable; the hub bounds a hung call (W2-4).',
  },
  {
    id: 'fanout', title: 'What is Fan-out?', at: [3.1, 3.4, 1.3], station: 'belt', status: 'proposal',
    body: [
      'Watch the front of the belt. A post-it goes up once. The archive tears off a copy. So does the control room. The rules cabinet takes one only when the note is on its pick list.',
      'The original never leaves. Each reader gets the same note at its own pace, and nobody at the dock knows who read it.',
      'You’ll hear this called fan-out: one note, many readers, no extra work for whoever stuck it.',
    ],
    metBefore: 'One button with several click handlers.',
    breaks: 'A reader that arrives late can only tear copies of notes still on the belt. Whatever the scraper took is gone from here.',
    evidence: 'BLOODBANK_EVENTS has limits retention; each consumer keeps its own position.',
  },
  {
    id: 'eventcommand', title: 'Event or command?', at: [-3.1, 6, 0], station: 'belt', status: 'proposal',
    body: [
      'Two kinds of paper ride this belt, on opposite faces.',
      'A post-it says something happened: “turn started”, “summary written”. It is for anyone, and it has no address.',
      'An envelope asks for something to be done: “start: daily report”. It is for one kind of worker, and one worker takes it.',
      'You’ll hear these called events and commands.',
      'A useful test: if nobody reads it, is anything wrong? An unread post-it is fine. An unopened envelope is a job not done.',
    ],
    metBefore: '“The oven beeped” versus “take the cake out”.',
    evidence: 'Subjects bloodbank.evt.> (BLOODBANK_EVENTS) and bloodbank.cmd.> (BLOODBANK_COMMANDS).',
  },
  {
    id: 'retention', title: 'What is Retention?', at: [3.1, 13.2, 1.2], station: 'belt', status: 'proposal',
    body: [
      'The belt climbs a little every hour. Height is age.',
      'At the top of the front face, the 7-day mark, a scraper takes whatever reaches it, read or not. The back face’s scraper sits much lower, at one day.',
      'You’ll hear this called retention: how long the belt keeps a note before letting it go.',
    ],
    metBefore: '“Keep my messages for 30 days.”',
    breaks: 'The scraper never touches the archive’s copies. Those live on the racks, on the archive’s own rules.',
    evidence: 'streams.json: BLOODBANK_EVENTS max_age 7d, discard old; BLOODBANK_COMMANDS 1d.',
  },
  {
    id: 'workqueue', title: 'What is a Work queue?', at: [9.9, 3.3, -5.4], station: 'crew', status: 'proposal',
    body: [
      'Round the back, envelopes ride up until a hatch takes them. The crew hall’s hatch opens only when a desk is free.',
      'A taken envelope stays on the belt, pinned to its desk, until the worker signs it off. Only then is it gone. If the worker hands it back, the pin comes out and the next free desk can take it.',
      'You’ll hear this called a work queue.',
    ],
    metBefore: 'The ticket machine at a deli counter.',
    breaks: 'Some envelopes have no hatch at all. They ride up untouched until the 1-day scraper takes them. Look for the grey ones.',
    evidence: 'BLOODBANK_COMMANDS workqueue retention; ack removes, nak redelivers; max ack pending bounds the hatch.',
  },
  {
    id: 'idempotent', title: 'What does Idempotent mean?', at: [8, 3.4, 6.6], station: 'archive', status: 'proposal',
    body: [
      'Now and then a copy reaches the archive twice. That is normal on a belt: a reader that is not sure it signed for a note will ask for it again.',
      'The filing clerk checks the Note ID first. Already on the rack? Nothing gets filed, and the clerk moves on.',
      'Doing it twice leaves the same result as doing it once. You’ll hear this called idempotent.',
    ],
    metBefore: 'Pressing the lift button twice. An upsert.',
    evidence: 'candystore db.py: INSERT … ON CONFLICT (id) DO NOTHING.',
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
