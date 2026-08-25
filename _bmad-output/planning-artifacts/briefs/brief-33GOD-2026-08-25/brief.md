---
title: "DeloHQ: The Company in Your Pocket"
status: ready-for-review
created: 2026-08-25
updated: 2026-08-25
product: DeloHQ
project: 33GOD
---

# DeloHQ: The Company in Your Pocket

## The Idea

DeloHQ is the executive interface to Jarad's agent company. It turns a fleet of
project agents, boards, event streams, and runtime services into something that
feels like an organization: departments with purpose, people with current work,
an inbox of decisions, and a trustworthy record of what happened next.

It lives where Jarad already talks to the company: Telegram. Individual agent
chats remain the offices where work conversations happen. The DeloHQ Mini App is
the shared company map and executive desk that Telegram chats cannot provide on
their own.

The product promise is simple. Within thirty seconds of opening DeloHQ, Jarad
can answer four questions:

1. What is the company doing right now?
2. What needs my attention?
3. Who should I talk to?
4. Did the action I took actually happen?

## Before and After

### Before: a collection of capable front doors

Today, each Hermes agent has a Telegram doorway, a repository, a project board,
and operational machinery behind it. Holocene has an early org chart, but it
still interprets the fleet through an older runtime model. The result is a
company that exists but does not yet present itself as one.

Jarad has to remember which agent owns what, infer whether silence means idle or
broken, jump between chats and boards, and understand implementation details to
interpret status. The interface can report `unknown` even while the underlying
agent is healthy. Operational controls are available, but the executive meaning
of those controls is not.

### After: a company that explains itself

Jarad opens Telegram and taps **Open HQ**. DeloHQ opens directly to a living org
chart. Departments show what they are responsible for and whether anything
inside needs attention. Each agent shows a meaningful state such as **Working**,
**Waiting on you**, **Blocked**, **Quiet**, or **Unavailable**, with a short human
explanation instead of a raw service label.

A compact **Now** area answers what changed since the last visit. The **Executive
Inbox** contains only decisions, exceptions, and requests that genuinely need
Jarad. Tapping an agent opens their **Office**, which connects their mission,
current initiative, latest outcome, project board, company memory, and Telegram
conversation.

When Jarad approves a recommendation or requests an intervention, DeloHQ does
not stop at a success toast. It shows a receipt as the request moves from
accepted to in progress to completed or failed. The company is not merely
visible; it is accountable.

## A Day With DeloHQ

At 8:30 AM, the HQ bot sends Jarad a short morning brief: three agents are
working, one project is blocked, and two decisions are waiting. The message does
not dump status. It offers **Open Morning Brief**.

The link opens DeloHQ directly to Now. Jarad sees that the PJangler agent finished
a fleet migration and the Holocene agent is waiting for approval to adopt the
new projection. He opens the recommendation, checks its evidence, and approves
it. DeloHQ shows that the command was accepted and then completed.

Later, an exception notification opens directly to the affected agent's office.
Jarad sees the difference between "agent is quiet" and "agent cannot work," taps
**Message Agent**, and continues the conversation in Telegram with the project
context already clear.

At the end of the day, Now has become a compact replay of what the company moved,
what Jarad decided, and what remains open tomorrow.

## The Core Experience

### 1. Company

The first screen is the organization itself, not a dashboard of infrastructure.
It shows departments, ownership, and the people inside them. The chart is both a
status surface and the primary navigation model.

The visual hierarchy answers "where does this work belong?" Operational health
is present but subordinate. A broken runtime becomes a visible exception on the
responsible agent; it does not turn the company into a server console.

### 2. Now

Now is a concise account of meaningful movement:

- work started or completed;
- a project became blocked;
- an agent requested a decision;
- a delivery gate passed or failed;
- an important recommendation was made;
- a runtime problem is preventing work.

This is not a raw event feed. DeloHQ groups related events into a readable story
and links every item to the agent, project, decision, and evidence behind it.

### 3. Executive Inbox

The inbox is the product's center of gravity. It separates:

- **Approvals:** a proposed action is ready for a human decision;
- **Exceptions:** work cannot continue normally;
- **Questions:** an agent needs context or judgment;
- **Briefings:** useful awareness that requires no action.

Every item says who is asking, why it matters now, what happens if Jarad waits,
and what evidence supports the recommendation. Approve and reject are explicit
commands with durable receipts, not conversational guesses.

### 4. Agent Office

An office is the coherent view of one company member:

- role, department, mission, and project ownership;
- what they are doing now and why;
- latest completed outcome and supporting evidence;
- open requests, blockers, and recommendations;
- board, repository, memory, and recent company activity;
- **Message Agent** to continue in the existing Telegram chat.

The office makes different kinds of agents legible. A project manager, director,
reporter, and legal assistant should not all be presented as generic PMs or be
judged by the same activity model.

## Screen Map

| Entry point | Opens | Purpose |
| --- | --- | --- |
| Bot menu: **Open HQ** | Company | See the organization and its current posture |
| Morning or evening brief | Now | Review meaningful movement since the last visit |
| Approval notification | Inbox item | Decide with context and supporting evidence |
| Exception notification | Agent Office | Understand impact and intervene with the owner |
| Agent chat link | Agent Office | Move from conversation to shared company context |

Company, Now, and Inbox form the persistent mobile navigation. Agent Office,
decision detail, exception detail, and action receipt are focused contextual
views opened from those three roots.

## Why Telegram Is More Than a Wrapper

Telegram gives DeloHQ an unusually strong shell for a private executive product:

- the bot menu is a permanent front door;
- a bot notification can deep-link to the exact approval, agent, or exception;
- the Mini App can run full-screen for the org chart and return naturally to chat;
- the app can be added to the mobile home screen;
- haptic feedback can reinforce consequential approvals and acknowledgements;
- secure and persistent device storage can remember harmless view preferences;
- direct agent conversations remain one tap away.

This creates a useful division of labor: Telegram handles presence, delivery,
identity, notification, and conversation; DeloHQ handles company-wide context,
comparison, decisions, and navigation.

## Product Principles

1. **Company language before infrastructure language.** Explain the consequence;
   expose the implementation evidence on demand.
2. **Attention is the scarce resource.** Quiet success stays quiet. Decisions and
   exceptions rise.
3. **One identity, many signals.** Project identity, agent role, runtime health,
   activity, and hierarchy remain distinct but meet in one office.
4. **Every action earns a receipt.** Accepted is not completed.
5. **Conversation stays conversational.** DeloHQ links to agent chats rather than
   rebuilding chat badly inside a dashboard.
6. **The org chart is alive, not decorative.** It is how Jarad understands and
   navigates the company.

## First Product Slice

The first coherent release is intentionally narrow:

- the current fleet appears automatically with accurate roles and ownership;
- Company, Now, Executive Inbox, and Agent Office are usable on mobile;
- agent states distinguish current work, availability, and configuration drift;
- DeloHQ opens the correct Telegram chat, board, repository, and evidence;
- exception and briefing notifications deep-link to the relevant context;
- acknowledgements and approved bounded actions have durable receipts;
- new PJangler-provisioned agents appear without hand-editing the org chart.

It explicitly does not become a general Telegram client, a replacement for
Holocene operations, a raw Bloodbank event viewer, or a second source of truth
for projects and agents.

## Success Looks Like

- Jarad can understand the company's current posture in under thirty seconds.
- `Unknown` is reserved for genuinely missing evidence, not stale integration.
- Every urgent notification opens the exact context that made it urgent.
- Jarad no longer needs to remember which chat, board, or repository owns work.
- Every consequential action is traceable from request through outcome.
- The interface makes adding the thirtieth or fiftieth agent easier, not noisier.

## Open Product Assumptions

- The first version serves Jarad as the sole executive operator.
- Mobile is primary, with desktop remaining useful for broader inspection.
- The living org chart should remain the home rather than becoming one tab among
  many interchangeable dashboards.
- Cost and budget views belong in DeloHQ only after their data is trustworthy
  enough to support decisions.

The adjacent [idea bank](addendum.md) preserves the more ambitious Telegram,
TDLib, Momo, Flume, HeyMa, and company-simulation possibilities without making
them promises of the first release.
