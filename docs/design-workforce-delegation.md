# Design: Workforce Delegation — bus-mediated agent dispatch

**Status:** proposal
**Author:** Claude Opus 5, session `0175htc4wWXdNhirfrFaYj2c`, 2026-08-27
**For:** 33GOD engineering
**Origin:** fallout from a Claude Code `teammateMode: tmux` bug; the debugging
surfaced that the command lane is further along than anyone remembered, and
that its documentation points at a component deleted three months ago.

---

## 1. Problem

Agent delegation today is **bound to the CLI that spawns it**. When a session
delegates work, the spawning CLI owns the child process, its provider, its
token budget, and its result. Three consequences:

1. **No provider arbitrage.** Kimi exhausted mid-task means the caller fails,
   even though OpenAI, Claude, Copilot, Gemini, and OpenRouter pools are idle.
   Provider selection is a caller concern when it should be a scheduling one.
2. **No durable record.** A spawned agent's existence, cost, and result live
   only in the parent's context. Nothing is queryable after the session ends.
3. **Transport coupling leaks.** The immediate trigger for this document: with
   `teammateMode: tmux`, named spawns became detached CLI processes in tmux
   panes with **no return channel**. The parent received only content-free
   idle pings and had to extract results with round-trips, each costing a full
   CLI turn. The host runs zellij, so the panes were invisible.

Point 3 is fixed (config removed). It is included because it is the clearest
demonstration of the design rule this proposal exists to enforce:

> **Display is not control flow.** A delegation mechanism that hosts a process
> inside a UI surface inherits that surface's addressability. Panes are for
> looking at; buses are for routing.

---

## 2. Current state — corrected

Earlier analysis in-session claimed the command lane was dark. **That was
wrong**, and the correction matters because it changes the build from
"construct a command lane" to "authorize the one that is already running."

| Component | State | Evidence |
|---|---|---|
| Event lane `bloodbank.evt.v1.>` | **live** | hooks → NATS → toaster + Candystore |
| Candystore projection | **live** | listening `127.0.0.1:8683` |
| `hermes-fleet-bloodbank-gateway.service` | **live, 5 days** | `active (running) since 2026-08-22`; durable JetStream pull consumer on `bloodbank.cmd.v1.agent.invocation.start` (`bloodbank_hermes_gateway/contract.py:21`) |
| `hook-hub.service` + `.socket` | **live** | successor to the original "universal hook fan-out" idea |
| Command **routability** | **0 of 30 agents** | none pass `bloodbank.enabled AND gateway_scope==fleet AND target_agent_id AND profile_name` |
| Reply lane `bloodbank.rpy.v1.*` | convention only | no publisher, no consumer |
| `hookd_bridge` | **does not exist** | deleted 2026-05-11 in `38fd18b`; see §6 |

**The command lane works. Nothing is authorized to use it.** The blocker is
registry eligibility, not missing infrastructure.

---

## 3. Design

### 3.1 Shape

```
caller (any CLI/session)
  │  publish CloudEvents command envelope
  ▼
bloodbank.cmd.v1.agent.invocation.start        [JetStream, durable]
  │
  ├──▶ hermes-fleet-bloodbank-gateway   (EXISTS) → registry-resolved Hermes agents
  └──▶ workforce-orchestrator           (NEW)    → ephemeral/contractor tasks
         │  selects provider from pool by quota + health
         │  spawns, tracks, emits lifecycle events
         ▼
bloodbank.rpy.v1.agent.invocation.completed    correlationid = originating command id
  │
  ▼  caller (or its successor) resolves the result
```

Two consumers on one subject, distinguished by envelope content — not by two
parallel lanes. The gateway handles *named, durable, registry-backed* agents;
the orchestrator handles *ephemeral, provider-flexible* work.

### 3.2 Result routing is already solved

`correlationid` / `causationid` are existing CloudEvents extension fields in
`_common/cloudevent_base.v1.json`. The reply carries the originating command's
id. **Do not invent a task-id scheme.** This is the single highest-leverage
observation in this document — the hard part of delegation (knowing who to
hand results back to) is already in the envelope contract.

### 3.3 Task state — JetStream KV, not Redis

The riffed design put task state in Redis. Recommend **JetStream KV** instead:

- JetStream is already the command transport. KV rides the same server, same
  auth, same ops surface.
- Native per-key TTL gives ephemeral-task semantics without a reaper.
- Redis would be a **third** source of truth alongside JetStream and
  Candystore. Three stores means three-way reconciliation when a task wedges.

Redis is fine as a **cache**. It should not be the record.

### 3.4 Ticketing — opt-in, by task class

The riffed design created a short-lived Plane ticket per dispatch, labelled
sub/contractor. Recommend **opt-in via an envelope field**, not automatic:

- Automatic ticketing round-trips Plane → n8n → HMAC → NATS for work already
  in-band on the bus.
- It adds board noise and a cleanup burden proportional to spawn rate.
- It puts ticket-creation latency in front of a subagent that may return in
  two minutes.

Ticketing earns its cost for **durable, human-visible, resumable** work. For
"read these files and summarize," the event stream already *is* the audit
trail — that is what Candystore is for. Make the caller declare which it is.

### 3.5 Provider pools as data

Pool state (quota remaining, health, cost tier, capability) belongs in a
queryable store, not in orchestrator code. Two reasons: selection logic stays
declarative, and **a caller can ask what is available before dispatching**
rather than discovering exhaustion as a failure.

This is where "out of Kimi → fall back to codex non-interactive" lives.

### 3.6 Sync vs async — decide deliberately

Today an in-process subagent returns its result into the caller's context
synchronously. Bus-mediated, the caller either blocks on a reply subject or
goes async. **Async is architecturally correct and changes how sessions
work**: fire, continue, results arrive later as notifications.

Recommend async-only, with the caller free to await a reply subject if it
genuinely needs to block. Do not build a synchronous facade — that reintroduces
the coupling this design removes.

---

## 4. Non-goals

- **A zellij equivalent of tmux teammates.** It reproduces the original flaw:
  a pane-hosted agent has no return channel. If agent visibility is wanted,
  build a **read-side** pane subscribed to `bloodbank.evt.v1.agent.*`. The
  pane must never own a process.
- **Replacing in-process subagents.** They are correct for fast, contextual,
  short work and now return results properly. This system is for long,
  expensive, parallel, or provider-flexible work. Both should exist.
- **A new HTTP front door.** See §6.

---

## 5. Sequenced plan

| # | Step | Size | Why first |
|---|---|---|---|
| 1 | Make **one** agent fleet-routable; publish one command; verify in toaster **and** Candystore | S | Everything above is speculative until one command executes end-to-end. `0/30` is the real blocker. |
| 2 | Implement the **reply lane** — publish `bloodbank.rpy.v1.agent.invocation.completed` carrying `correlationid` | S | Without it there is no hand-back and no way to close the loop. |
| 3 | **Provider pool registry** — quota/health as queryable data | M | The actual motivating problem (provider arbitrage). Useful standalone, before any orchestrator exists. |
| 4 | **workforce-orchestrator** consumer — select, spawn, track in JetStream KV, emit lifecycle + reply | L | Only worth building on top of a proven 1–3. |
| 5 | Skill: `workforce-delegation` — teach agents the routing call (in-process vs bus) | S | The piece that actually changes agent behavior. Cheap; do it as soon as 4 lands. |
| 6 | Optional: opt-in ticketing, zellij read-side pane | M | Polish. |

Steps 1–2 are small and unblock a system that is already built and running.
**Do those regardless of whether 3–6 ever happen.**

---

## 6. Blocking defect: documentation resurrects a deleted component

Anyone implementing §5 will follow the skill docs and hit this immediately.

`skills/bloodbank-integration/SKILL.md:57` instructs:

> "HTTP client that needs to issue a COMMAND envelope → POST to hookd_bridge
> :18790/hooks/agent. See `bloodbank/hookd_bridge/`; command subject is
> `bloodbank.cmd.v1.agent.invocation.start`."

Every clause is false:

- **`bloodbank/hookd_bridge/` does not exist.** Deleted 2026-05-11 in
  `38fd18b` ("collapse v3 scaffold to canonical bloodbank"), as part of the v2
  purge — four days after being marked "permanent."
- **It was never a consumer or a bridge.** It was an HTTP→**RabbitMQ** ingress
  *producer*: `POST /hooks/agent` → hand-rolled envelope → SQLite outbox →
  exchange `bloodbank.events.v1`, routing key `command.{agent}.{action}`.
- **It never published `bloodbank.cmd.v1.*` and structurally could not** — it
  emitted no `specversion`, `subject`, `kind`, or `domain`, all of which
  `services/agent-hooks/forward_envelope.py:44-53` requires.
- **The docs were written 2026-08-10** (`4f394a4`), *three months after the
  deletion*.

**This is not an isolated typo.** `references/producers/README.md:18,22` cite
`bloodbank/event_producers/http.py` for the `/publish` and `/event` methods —
**also deleted in `38fd18b`**. Three of seven rows in that producer table point
at files that have not existed since May. That table was written from memory,
not from disk.

The newest doc, `references/event-journey.md` (2026-08-26), documents the
command lane **correctly** and never mentions hookd_bridge. The rot is confined
to the 2026-08-10 producer docs.

### Remediation

1. `SKILL.md:57` — replace the hookd_bridge branch: publish the
   schema-validated command envelope directly to
   `bloodbank.cmd.v1.agent.invocation.start`; the fleet gateway consumes it.
2. `SKILL.md:32` — drop `hookd_bridge` from the routing table.
3. `references/producers/README.md:23,55` — delete the row and bullet.
4. `references/producers/methods.md:130-145` — delete section 6.
5. `references/producers/README.md:18,22` — same defect, `event_producers/http.py`.
6. **CI check that every path cited in skill docs resolves on disk.** This
   failure mode is now confirmed three times in one table; it will recur.

### Was the pattern wrong, or just the docs?

Both, separately. The component was competently built — durable SQLite outbox
with WAL and capped backoff, bearer auth, health endpoint — and its rationale
("give HTTP-only clients a stable command-emission surface") is a legitimate
ingress-adapter argument. ADR-0003 even anticipated the exact `hookd` /
`hookd_bridge` name collision.

But an HTTP shim in front of *this* command lane is the wrong shape, for a
reason specific to it: **the command lane's contract is validation, schema
conformance, registry-backed authorization, and idempotency.** hookd_bridge
did none of that. It accepted `{"text": ..., "sessionKey": ...}` and *inferred*
intent by regex-scraping `"[Command] action=X"` out of free text, defaulting to
`hook_dispatch` when parsing failed. A front door that manufactures a command
from an unparseable string is worse than no front door — it moves the
authorization boundary from a validating consumer to a regex.

**Rule for §3:** producers speak the schema, not a convenience dialect. A
client that genuinely cannot reach NATS gets an authenticated ingress that
validates the full envelope and rejects anything short of it. `n8n-nodes-bloodbank`
already fills that role.

---

## 7. Open questions

- **Ephemeral agent identity.** The gateway resolves `target_agent_id` through
  the fleet registry with default-deny. Ephemeral contractors have no registry
  entry by definition. Does the orchestrator hold a wildcard entry, or does the
  registry grow a "contractor" class? This is the main unresolved design point.
- **Cost attribution.** Provider arbitrage only pays off if spend per pool is
  measurable. Is that a Candystore projection or a separate meter?
- **Nested delegation.** May an orchestrator-spawned agent itself dispatch?
  `causationid` supports the chain; runaway-fan-out policy is undefined.

## 8. Provenance

Every "live/dead" claim in §2 and §6 was verified directly on `big-chungus`
on 2026-08-27 — `systemctl` state, listening ports, `git log`/`git blame`
dates, and filesystem existence. Claims sourced from an agent report were
independently re-verified before inclusion. Items that could not be verified
are marked in the originating review, not asserted here.
