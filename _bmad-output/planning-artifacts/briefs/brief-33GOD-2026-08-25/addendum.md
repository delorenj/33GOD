---
title: "DeloHQ Product Concept: Idea Bank"
status: exploratory
created: 2026-08-25
updated: 2026-08-25
product: DeloHQ
---

# DeloHQ Idea Bank

These concepts extend the product brief. They are possibilities to test, not
committed scope.

## Telegram-Native Ideas

### Contextual HQ notifications

The HQ bot sends only four classes of message: briefing, approval, exception,
and completed outcome. Every message carries a deep link that opens DeloHQ at the
specific object rather than dropping Jarad on a generic home screen.

### Home-screen HQ

Offer Telegram's **Add to Home Screen** capability after DeloHQ has earned repeat
use. The shortcut opens the company directly while Telegram remains the secure
host and notification channel.

### Full-screen company map

Use Mini App full-screen mode for the org chart and company replay. Compact mode
remains appropriate for a single approval or office opened from a notification.

### Tactile decisions

Use restrained haptic feedback for approve, reject, acknowledge, and completed
receipts. Never use it as ambient decoration.

### Shareable company context

Generate a compact context card for an agent, project, decision, or exception
that Jarad can send into a relevant Telegram conversation. The card links back
to live DeloHQ context instead of copying stale status into chat.

## Company Experience Ideas

### Morning brief and evening close

Momo assembles a morning brief around objectives, decisions, and risks. The
evening close records outcomes, unresolved items, and tomorrow's first decisions.
Both are generated from durable evidence and remain available in the company
replay.

### Company replay

Turn Candystore history into a readable timeline of the day. Related events
collapse into one narrative thread. Jarad can scrub backward to see when a
project changed state, why, and which decision caused it.

### Intervention mode

When an initiative becomes critical, promote it into a temporary focus view with
the responsible agents, shared objective, current evidence, decisions, and a
single activity narrative. This is a small operational room, not another chat.

### Boardroom

Convene a structured multi-agent session around a decision. Momo facilitates,
agents contribute recommendations from their domains, and Jarad receives a
decision packet rather than a wall of chat. TheBoard Room may eventually own the
meeting experience; DeloHQ owns entry, executive decision, and outcome tracking.

### Delegation slip

Jarad gives an objective to a person or department with desired outcome,
constraints, urgency, and an optional budget. DeloHQ tracks acceptance,
delegation, work, evidence, and completion through Bloodbank receipts.

### Company memory

An agent office can surface the small set of durable Hindsight memories that
explain current behavior: active decisions, accepted constraints, recurring
risks, and recent lessons. It should never expose a raw memory dump.

### Executive budget view

Once model usage and cost attribution are reliable, show budget by initiative
and department. The executive question is not "how many tokens?" but "what did
this initiative spend, what outcome did it produce, and does it need a limit or
exception?"

### Voice brief

HeyMa or Voxxy can read the morning brief, answer "what needs me?", and open the
relevant DeloHQ screen. Voice should navigate and summarize the same company
model rather than creating another source of status.

## TDLib Expansion

TDLib becomes valuable when DeloHQ needs to act as Jarad's Telegram client rather
than merely host a Mini App.

### Departments as chat folders

Create and maintain native Telegram folders such as Platform, Products, Client
Operations, and Executive. Folder membership mirrors the resolved company
presentation model. DeloHQ remains authoritative about the proposed grouping;
TDLib applies it to Jarad's Telegram account.

### Unified agent inbox

Aggregate unread agent conversations, mentions, pinned decisions, and recent
chat activity without replacing the native chats. DeloHQ can sort these by
company meaning rather than Telegram recency alone.

### Conversation-aware offices

Show recent Telegram conversation context alongside project and event evidence,
with a hard distinction between private chat content and durable company record.
Nothing becomes a decision merely because it was said in chat.

### Native client caution

TDLib introduces a persistent user session, local encrypted state, broader
Telegram permissions, and more operational responsibility. It should live in an
isolated adapter with narrow commands and read models. It must not become the
source of agent identity, hierarchy, work state, or command truth.

## Org Evolution

### Presentation now

Departments, titles, display ordering, and visual grouping can remain a DeloHQ
presentation overlay while PJangler supplies the actual roster.

### Authority later

When Flume has a real contract, reporting lines, delegation authority,
escalation, budget limits, and temporary teams move there. DeloHQ then renders
and operates that model rather than inferring authority from a diagram.

### Reorganization as a governed event

A future drag-and-drop org edit should create a proposed reorganization,
describe its effects, request approval, and publish the accepted change. Moving
a card on screen alone must never silently rewrite company authority.

## Ideas Deliberately Rejected for the First Release

- A dashboard tile for every service and metric.
- A live firehose of Bloodbank events.
- Free-form shell or systemd commands from Telegram.
- Rebuilding each agent's full chat inside DeloHQ.
- Treating activity volume as productivity.
- Letting Telegram folders define the company hierarchy.
- Inventing a virtual office aesthetic before the information model works.

## Grounding References

- [Telegram Mini Apps](https://core.telegram.org/bots/webapps): menu and deep-link
  launches, full-screen mode, home-screen shortcuts, haptics, device storage,
  secure storage, and notification capabilities.
- [Telegram bot menu button](https://core.telegram.org/api/bots/menu): the
  persistent **Open HQ** entry point used by DeloHQ today.
- [TDLib `createChatFolder`](https://core.telegram.org/tdlib/docs/classtd_1_1td__api_1_1create_chat_folder.html): grounding for the future departments-as-folders concept.
- [33GOD PRD](../../../../PRD.md): current product ownership and DeloHQ's bounded
  executive-surface role.
- [33GOD product map](../../../../33god-platform/docs/product-map.md): relationship
  among DeloHQ, Holocene, Flume, Bloodbank, and the wider platform.
