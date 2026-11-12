// Every word a reader sees lives here, so Jarad can rewrite copy without touching the scene.
// UX (labels, panels, HUD) speaks in real 33GOD names; the warehouse words live in the world itself (signs).
// Canon: ../../world/warehouse-bible.md. Voice: ../../world/tone.md.
// [J] = Jarad's direction, [P] = proposal.

import type { DomainId } from './domains'

export type Vec3 = [number, number, number]

export type StationId =
  | 'bays' | 'courier' | 'dock' | 'labeldesk' | 'belt'
  | 'archive' | 'rules' | 'control' | 'cataloguer' | 'clock' | 'crew'

export type BulbId = 'normalization' | 'failopen' | 'fanout' | 'eventcommand' | 'retention' | 'workqueue' | 'idempotent'

export interface Station {
  id: StationId
  name: string // the real 33GOD component name: what every label and panel shows
  place: string // the warehouse word: painted on the sign in the world, never in the UX
  real: string // one plain line on what it really is
  domain: DomainId
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
    id: 'bays', name: 'Agent CLIs', place: 'Vendor bays', real: 'the AI coding tools you run: Claude Code, Codex, Kimi, Copilot, Gemini and opencode', domain: 'agents',
    does: [
      'These are the AI coding tools you use, such as Claude Code and Codex. Each one reports what it is doing in its own format. On the floor, each tool is a vendor with its own bay.',
      'When something happens, such as you pressing Enter, the tool sends out a report about it. On the floor, that raw report is a parcel, exactly as the vendor packed it.',
    ],
    breaks: 'No vendor drives anywhere. The tools run on your own machine and leave a small spot where other programs can listen in. That spot is called a hook.',
    evidence: ['bloodbank/services/agent-hooks/hooks.master.json (one source, fanned out to every dialect)'],
    label: [-24, 4.6, 0], view: { pos: [-11, 8, 15], target: [-23, 1.5, 0] }, bulbs: [],
  },
  {
    id: 'courier', name: 'bb-hook', place: 'The courier', real: 'a small program that sends each tool’s news to hook-hub', domain: 'bloodbank',
    does: [
      'bb-hook is a small program. A tool runs it at each hook, which is a spot where the tool lets other programs listen in. On the floor, it is the courier, with one at every bay.',
      'bb-hook passes the news to hook-hub and waits for a reply. The reply can be a briefing, which is extra background for the tool, or a yes or no. On the floor, the courier waits at the window.',
      'If hook-hub is down, bb-hook gives up and the tool carries on without a briefing. No event gets written. On the floor, the courier turns round with the parcel still in hand.',
    ],
    breaks: 'The real trip takes a few thousandths of a second and stays inside your machine. It is not a walk across the floor.',
    evidence: ['bb-hook → $XDG_RUNTIME_DIR/33god/hook-hub.sock', 'bb-hook: 3 s deadline; after one stall, 0.25 s probes for 30 s (the Mac wrapper bounds it to about 1 s, W2-4)'],
    label: [-17, 2.6, 4.2], view: { pos: [-9, 6, 11], target: [-17, 0.6, 1] }, bulbs: ['failopen'],
  },
  {
    id: 'dock', name: 'hook-hub', place: 'Receiving dock', real: 'turns each tool’s raw hook into one standard event', domain: 'bloodbank',
    does: [
      'hook-hub receives the raw news from every tool and writes it again as one standard event. On the floor, it is the receiving dock: parcels in, post-its out.',
      'The event says which tool it came from, in a small “from” field. On the floor, that is the “from” corner of the post-it. The tool’s original report is kept too, stapled to the back.',
    ],
    breaks: 'hook-hub rewrites the label, not the whole parcel. The packing slip on the back still holds the tool’s own data, in the tool’s own format.',
    evidence: ['hook-hub/handlers.toml', 'agent-hooks/clients/*.py build one envelope', 'core/validate.py assert_contract'],
    label: [-9.5, 4.9, 0], view: { pos: [-3.5, 5, 9.5], target: [-9.5, 1.5, 0] }, bulbs: ['normalization'],
  },
  {
    id: 'labeldesk', name: 'Naming contract', place: 'Label desk', real: 'the shared rules for how Bloodbank names things', domain: 'bloodbank',
    does: [
      'The naming contract is a list of the words Bloodbank allows in a note’s label, plus a form for each kind of note. On the floor, it is the label desk, with a house dictionary and a form pad.',
      'hook-hub checks each note it writes against the word list, every time. Checking it against the forms is optional, and it is off by default.',
    ],
    breaks: 'The bus itself never proofreads, so a note written somewhere else can skip this desk. Watch the Enricher do it. A note that fails the check is not held or sent back. It is dropped, with a line in the log.',
    evidence: ['bloodbank/schemas/bloodbank/v1/**', 'validate.py assert_contract (always); JSON Schema only with BLOODBANK_HOOK_VALIDATE=1'],
    label: [-8, 1.3, 5.1], view: { pos: [-5, 4, 10], target: [-9.5, 0.8, 3] }, bulbs: [],
  },
  {
    id: 'belt', name: 'Bloodbank bus', place: 'The belt', real: 'the shared place where every note is posted, run by NATS JetStream', domain: 'bloodbank',
    does: [
      'A bus is a shared line. Programs post notes on it, and other programs read them. On the floor, it is the tall belt that turns all day, and a note’s height shows its age.',
      'Events are the post-its on the front face, kept for 7 days. Commands are the envelopes on the back face, kept for 1 day.',
      'Anyone with news can post a note. A reader tears off a copy, and the original stays on the belt.',
    ],
    breaks: 'Nothing really moves on the real bus. The belt turns here only to show age, not travel.',
    evidence: ['NATS JetStream, two streams: bloodbank/compose/nats/streams.json: BLOODBANK_EVENTS 7d limits, BLOODBANK_COMMANDS 1d workqueue'],
    label: [0, 15.4, 0], view: { pos: [10, 9, 27], target: [0, 7.2, 0] }, bulbs: ['fanout', 'eventcommand', 'retention'],
  },
  {
    id: 'archive', name: 'Candystore', place: 'The archive', real: 'files a copy of every event that has all its label fields', domain: 'memory',
    does: [
      'Candystore reads every event on the bus and files a copy in its database. On the floor, it is the archive. A clerk tears off a copy of each post-it and files it on the racks.',
      'Before filing, it checks the label fields: producer, service, domain and kind. An event missing one goes to the rejects drawer. An event it already has, by Note ID, is skipped and left as it is.',
    ],
    breaks: 'Candystore has no clean-up job today. It makes no promise about how long it keeps things. Nothing deletes a filed event now, but nobody has promised to keep it.',
    evidence: ['candystore db.py: ON CONFLICT (id) DO NOTHING; REQUIRED_ENVELOPE_FIELDS → dead_letter', 'durable consumer candystore-events, deliver all'],
    label: [10.7, 3.8, 5.6], view: { pos: [16, 6, 14], target: [8, 1.5, 5] }, bulbs: ['idempotent'],
  },
  {
    id: 'rules', name: 'n8n', place: 'Rules cabinet', real: 'a workflow tool that reacts to events and starts jobs', domain: 'triggers',
    does: [
      'n8n runs workflows, and each one waits for certain events. Each workflow keeps a bookmark on the bus, so it knows how far it has read. On the floor, each workflow is a rule card in the rules cabinet, with its own clip on the belt.',
      'Each workflow has a pick list of the events it wants. This one wants only “invocation completed”, so every other note goes past it. Other workflows use n8n’s Fleet node to post commands that hand jobs to hermes-gateway.',
    ],
    breaks: 'The pick list shown here is an example. Real workflows choose their own.',
    evidence: ['n8n-nodes-bloodbank durable triggers: n8n-<workflow>-<node> on BLOODBANK_EVENTS', 'Fleet.node.ts publishes bloodbank.cmd.agent.invocation.start'],
    label: [-14, 3, -7], view: { pos: [-8, 6, 1], target: [-14, 1, -7] }, bulbs: [],
  },
  {
    id: 'control', name: 'Holocene', place: 'Control room', real: 'a dashboard that shows what is happening on the bus', domain: 'holocene',
    does: [
      'Holocene reads the events on the bus and shows them to you. On the floor, it is the control room up on the mezzanine, watching the floor through a visitor’s window.',
      'Holocene has no bookmark on the bus. It keeps its own place marker, like a notebook, and gets a fresh visitor’s pass each time it connects.',
    ],
    breaks: 'Holocene is always a moment behind. It never sees an event at the instant it happens.',
    evidence: ['holocene/packages/bloodbank-client: ephemeral ordered consumer, ack none, own checkpoint'],
    label: [-5, 6.2, 12.6], view: { pos: [4, 9, 22], target: [-5, 3.4, 11.5] }, bulbs: [],
  },
  {
    id: 'cataloguer', name: 'Enricher', place: 'The cataloguer', real: 'writes a short summary when a coding session ends', domain: 'memory',
    does: [
      'The Enricher waits for an event that says a session ended. It asks Candystore for that session’s history and writes a one-paragraph summary. On the floor, it is the cataloguer.',
      'It posts the summary through a small helper program, a Dapr sidecar. On the floor, that helper is the runner. The summary never passes the naming check, so it has no barcode and no “from” corner.',
    ],
    breaks: 'Candystore turns this summary away, because it has no producer, service, domain or kind. It lands in the rejects drawer, and none of these summaries are filed. That is a real bug today. The bus still carries the summary, and Holocene still sees it.',
    evidence: ['33god-platform/enricher/main.py:164 emit_event via enricher-daprd /v1.0/publish', 'durable enricher-events on bloodbank.evt.>, acts on agent.session.ended', 'candystore main.py _drop: dead_letter "missing CloudEvents fields"'],
    label: [2.9, 1.7, 1.6], view: { pos: [1, 3, 9], target: [4.8, 1, 2.4] }, bulbs: [],
  },
  {
    id: 'clock', name: 'Candybar', place: 'The clock', real: 'the one scheduler: it decides when repeating jobs run', domain: 'triggers',
    does: [
      'Candybar is meant to be the one clock in 33GOD. Anything that repeats should start from it, and from nowhere else. On the floor, it is the bell on the wall.',
      'Every minute, Candybar posts a “tick fired” event. A dispatcher reads each tick, checks the list of jobs, and posts a command.',
      'Candybar’s own executor picks up that command and runs the job. On the floor, the planner at the desk is the dispatcher, and the clock’s own hands are the executor.',
    ],
    breaks: 'Candybar decides when a job runs, not always who runs it. A signed list of alarms still rings outside it, each with a named owner and a reason. The floor shows far fewer ticks than one a minute.',
    evidence: ['candybar/src/candybar/dispatcher/role.py: tick in, bloodbank.cmd.cron.candybar.invoke out', 'executor/role.py: durable candybar-executor-invoke'],
    label: [-6, 7.6, -6], view: { pos: [1, 7.5, -9.5], target: [-5.2, 2.8, -4.6] }, bulbs: [],
  },
  {
    id: 'crew', name: 'hermes-gateway', place: 'Crew hall', real: 'takes jobs off the bus and hands them to Hermes agents', domain: 'workers',
    does: [
      'hermes-gateway takes job commands off the back of the bus. Each command names the one Hermes agent it is for. On the floor, it is the crew hall, with a hatch, 4 desks and a tray of 4.',
      'A command it has taken stays on the bus until a worker signs it off, or until its 1 day runs out. A job that works posts an “invocation completed” event on the front. A job that fails five times is signed off as failed and posts an “invocation failed” event instead.',
    ],
    breaks: 'A sign-off means the gateway is done with the command, not that the job worked. Here it is drawn with 4 desks and a tray of 4. The real gateway works on 4 jobs at once, with room for 64 more waiting. It also has an express hatch for jobs a person is waiting on, and that one gives each job 8 tries, not 5.',
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
      'hook-hub receives raw hooks from many AI tools, and no two tools write alike. Each one labels its news in its own words.',
      '> Claude, Codex, Kimi|UserPromptSubmit',
      '> Copilot|userPromptSubmitted',
      '> Gemini|BeforeAgent',
      '> opencode|chat.message',
      'hook-hub opens each one and writes the news again as one standard event: “turn started.” On the floor, a clerk at the receiving dock copies it onto a house post-it. The tool’s name goes in the small “from” corner, never in the headline.',
      'You’ll hear this called normalization. Many shapes come in, and one standard shape goes out.',
      'Without hook-hub, every reader would have to learn every tool’s format. With it, each format is learned once, at the door.',
    ],
    metBefore: 'A shop that takes Stripe and PayPal turns both into one “payment received” record.',
    breaks: 'hook-hub makes the label standard, not the whole parcel. The tool’s original report, in its own format, stays stapled to the back.',
    evidence: 'hooks.master.json maps each vendor hook to one role (prompt_submit → conversation.turn.started); clients/*.py build one envelope, raw payload kept in data.',
  },
  {
    id: 'failopen', title: 'What is Fail-open?', at: [-15, 2.4, 3], station: 'courier', status: 'proposal',
    body: [
      'bb-hook calls hook-hub each time a tool reaches a hook. So what happens when hook-hub is down? Shut the dock and watch the couriers.',
      'bb-hook cannot get through, so it gives up. The tool does not wait. It carries on with your work, without the briefing or the safety checks. On the floor, each courier turns round with the parcel still in hand.',
      'You’ll hear this called fail-open: when the helper is down, the main job keeps going without it.',
    ],
    metBefore: 'A web page that still loads when its tracking script fails.',
    breaks: 'Nothing waits in line. No event gets written, so no reader ever sees that news. A door that is stuck, not shut, is worse. The first parcel can wait up to 3 seconds. After that, each one waits about a quarter of a second, for the next half minute.',
    evidence: 'bb-hook exits clean when hook-hub.sock is unreachable or silent; its deadline is 3 s, and 0.25 s probes follow a stall.',
  },
  {
    id: 'fanout', title: 'What is Fan-out?', at: [3.1, 3.4, 1.3], station: 'belt', status: 'proposal',
    body: [
      'An event is posted on the bus once. Candystore reads a copy. So does Holocene. n8n reads a copy only when the event is on a workflow’s pick list.',
      'Nobody takes the original. Each reader takes a copy at its own pace, and whoever posted the event never knows who read it. On the floor, watch the post-it stay on the belt while the copies go.',
      'You’ll hear this called fan-out: one event, many readers, no extra work for whoever posted it.',
    ],
    metBefore: 'One button press that sets off several things at once.',
    breaks: 'A reader that shows up late can only copy events still on the bus. Anything older than 7 days is gone from here.',
    evidence: 'BLOODBANK_EVENTS has limits retention; each consumer keeps its own position.',
  },
  {
    id: 'eventcommand', title: 'Event or Command?', at: [-3.1, 6, 0], station: 'belt', status: 'proposal',
    body: [
      'Two kinds of notes go on the bus, on opposite faces.',
      'An event says something happened, like “turn started” or “invocation completed.” It is for anyone who cares. On the floor, it is a post-it on the front of the belt.',
      'A command asks for something to be done, like “start: daily report.” It is for one kind of worker, and only one worker takes it. On the floor, it is an envelope on the back.',
      'A useful test: if nobody reads it, is anything wrong? An unread event is fine. An unopened command usually means a job was not done, with one exception you will meet at the back of the belt.',
    ],
    metBefore: '“The oven beeped” versus “take the cake out”.',
    evidence: 'Subjects bloodbank.evt.> (BLOODBANK_EVENTS) and bloodbank.cmd.> (BLOODBANK_COMMANDS).',
  },
  {
    id: 'retention', title: 'What is Retention?', at: [3.1, 13.2, 1.2], station: 'belt', status: 'proposal',
    body: [
      'The bus does not keep notes forever. Events on the front stay for 7 days. Commands on the back stay for 1 day.',
      'On the floor, notes ride up the belt a little every hour, so height is age. At the top of the front face, a scraper scrapes off whatever reaches it, read or not. The back face’s scraper sits much lower, at one day.',
      'You’ll hear this called retention: how long the bus keeps a note before letting it go.',
    ],
    metBefore: '“Delete chats after 30 days.”',
    breaks: 'The scraper never touches Candystore’s copies. Candystore keeps an event for as long as it decides.',
    evidence: 'streams.json: BLOODBANK_EVENTS max_age 7d, discard old; BLOODBANK_COMMANDS 1d.',
  },
  {
    id: 'workqueue', title: 'What is a Work Queue?', at: [9.9, 3.3, -5.4], station: 'crew', status: 'proposal',
    body: [
      'The back of the bus is a line of jobs. hermes-gateway takes jobs off it, but only as many as it has room for. On the floor, a hatch takes envelopes while its tray has room, and a few desks work at once. The rest wait on the belt.',
      'A job it has taken stays on the bus, pinned, until the worker signs it off. If the gateway has to stop and cannot start a job, it hands the command back. That is rare. After a short wait, the bus offers it again. After five tries, the gateway signs the job off as failed and posts an “invocation failed” event on the front.',
      'You’ll hear this called a work queue: a line of jobs where each job goes to one worker.',
    ],
    metBefore: 'The ticket machine at a deli counter.',
    breaks: 'Some commands have no worker at all. The sound wing, which is wax, posts a grey envelope for every job it runs itself. It is only a record, so the job can be traced later, and nobody takes it. These ride up untouched until the 1-day scraper scrapes them. On the real bus, almost everything left standing at the back is grey.',
    evidence: 'BLOODBANK_COMMANDS workqueue retention; ack removes, nak(5 s) redelivers; max_ack_pending 68 bounds the hatch; max_deliver 5.',
  },
  {
    id: 'idempotent', title: 'What does Idempotent mean?', at: [8, 3.4, 6.6], station: 'archive', status: 'proposal',
    body: [
      'Sometimes the bus offers Candystore the same event twice. Candystore signs for an event once it has filed it. If that signature is late or lost, the bus waits about 30 seconds and offers the event again.',
      'Candystore checks the Note ID first. If it already has that event, it files nothing and moves on. On the floor, the filing clerk finds the Note ID already on the rack.',
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
