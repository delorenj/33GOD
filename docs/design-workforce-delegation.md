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

**Decided: JetStream KV.** Rationale, since KV is the less familiar option:

JetStream KV is a key/value store built *on top of* a JetStream stream — the
same NATS server, the same auth, the same ops surface already carrying the
command lane. A bucket is a stream; a key is a subject within it; `put`/`get`/
`delete` are publishes and lookups. It gives you last-value-wins semantics,
optional history depth, per-key TTL, and atomic compare-and-set — which is
enough for "one task record per correlationid, expiring on its own."

- JetStream is already the command transport. KV rides the same server, same
  auth, same ops surface.
- Native per-key TTL gives ephemeral-task semantics without a reaper.
- Redis would be a **third** source of truth alongside JetStream and
  Candystore. Three stores means three-way reconciliation when a task wedges.

Redis is fine as a **cache**. It should not be the record.

### 3.4 Ticketing — cut

**Decided: no ticketing for ephemeral tasks.** The original motivation was an
audit trail, and Candystore already provides one for free by projecting the
event stream. A Plane ticket per dispatch would have round-tripped
Plane → n8n → HMAC → NATS for work already in-band on the bus, added board
noise proportional to spawn rate, and put ticket-creation latency in front of
a subagent that may return in two minutes.

Durable, human-visible, resumable work still gets a ticket — but that work is
what Plane is already for, and it enters through the existing ingress. It is
not the ephemeral-contractor path this document describes.

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
| 6 | Optional: zellij read-side pane fed by `bloodbank.evt.v1.agent.*` | M | Polish. |

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

---

## 7. Control surface — inventory and correction

Surveyed on big-chungus 2026-08-27. Every claim below was verified directly
(`systemctl`, `ss`, `curl`, NATS monitoring endpoints, filesystem).

### 7.1 Correction: n8n is not containerized

An earlier read in this design assumed n8n ran in Docker and therefore could
not reach the host's systemd user session. **That is wrong.** n8n runs on the
host as a node process under PM2/mise. Its environment already carries
`XDG_RUNTIME_DIR=/run/user/1000` and `DBUS_SESSION_BUS_ADDRESS`, lingering is
enabled (`Linger=yes`), and the Execute Command node inherits `process.env`.

**n8n can start, stop, and inspect every `systemd --user` unit and every
docker container today, with zero new code** — and already does, via active
workflows running `systemctl restart tailscaled`, `docker compose restart
ssbnk-web`, and a lease-gated `gpu-gaming-mode` CLI.

So the missing piece is not *access*. It is **restraint and typing**.

### 7.2 Fix the security posture before adding lifecycle controls

Three verified facts compose into a LAN-reachable root shell:

| Fact | Verified |
|---|---|
| `delorenj ALL=(ALL) NOPASSWD: ALL` | `/etc/sudoers.d/` |
| n8n listens on `0.0.0.0:5678` | `N8N_LISTEN_ADDRESS=0.0.0.0` |
| Code nodes can read process env | `N8N_BLOCK_ENV_ACCESS_IN_NODE=false` |

Anyone reaching n8n on the LAN can execute arbitrary commands as root. Adding
a lifecycle control surface on top of this ships convenience over an open root
shell. **Correct order: narrow sudoers to the shim binary, bind n8n to
127.0.0.1 behind Traefik, set `N8N_BLOCK_ENV_ACCESS_IN_NODE=true` — then add
lifecycle nodes.**

Separately: `~/.config/systemd/user/bloodbank-http.service:12` carries a
plaintext `Environment=RABBITMQ_PASS=`. Rotate it and replace with an
`op://DeLoSecrets` reference via `EnvironmentFile`.

### 7.3 The real inventory problem

**Five consumers, five start mechanisms, four repos.** Two are defined outside
both surveyed repos entirely:

| Consumer | Delivery | Started by |
|---|---|---|
| `candystore-events` | durable | docker compose (`33god-platform/compose.yaml`) |
| `bloodbank-event-toaster` | ephemeral core sub | docker compose (a *different* project) |
| `bloodbank-hermes-gateway-v1` | durable | `systemd --user` |
| `curator-drain` | durable | `systemd --user`, script symlinked out of skillex |
| `deckard` | ephemeral core sub | `systemd --user` template unit, Rust binary in `code/deckard` |

`hook-hub.service` is routinely mistaken for a sixth; it dispatches and does
not touch the bus.

There is **no uniform way to enumerate consumers and their state.**
`components/*.yaml` has no field for subject, durable name, delivery mode, or
start mechanism. `bb doctor` only checks that scaffold files exist. Holocene's
`/api/modules/systems/inventory` — the one attempted unified view — returns
**HTTP 500**, shelling out to a `bgls` binary that does not exist.

Ephemeral consumers are invisible when stopped: they appear only as live rows
in `connz`, so a survey cannot distinguish "never existed" from "died an hour
ago."

### 7.4 The fleet has the same shape, worse

- **29 gateway units, 15 heartbeat timers, zero sockets**, all generated by
  `70-systemd.sh` from `role.yaml`. `agents-registry.yaml` is written
  *post hoc* by `80-registry.sh` and **nothing reads it back to drive
  systemd** — that split is the whole "hanging around" feeling.
- **The registry under-records reality**: 14 heartbeat timers fire every 60s,
  only 9 are declared. Anything reconciling from the registry silently leaves
  five running.
- **And over-records**: `delonet-director` advertises two units that were
  never installed. `systemctl start` on them fails with NoSuchUnit.
- **Seven orphan profile dirs**, including a case-duplicate
  `OptionJangler-pm` / `optionjangler-pm` pair.
- **No fleet CLI exists.** `hermes` has 60+ subcommands but no `fleet`, and
  all are scoped to one profile. Raw `systemctl --user` is the entire
  documented control surface — and it requires an agent-id that the registry
  stores but no command prints.
- **26 gateways carry a `10-versioned-runtime.conf` drop-in overriding
  ExecStart, with no generator anywhere on disk** and no commit that ever
  contained the string. Unexplained provenance on almost every unit.

### 7.5 The status commands lie

This is the finding that most justifies building something.

`hermes-33god-pm-gateway.service` has restarted **10,427 times**, exiting
`status=78/CONFIG` every ~11s (no Telegram bot token). Because
`Restart=on-failure` keeps re-arming it, it reports as `activating`, **never
`failed`** — so it does not appear in the status commands the runbook
recommends.

Meanwhile the *only* unit `--state=failed` returns is
`hermes-plane-webhook-bridge.service`, whose **unit file does not exist**;
systemd is holding a failed job for a phantom.

**The fleet's single failure signal points at a unit that isn't there, while
its loudest genuine breakage is invisible.** Note this is the 33GOD PM — the
agent this document would be handed to.

### 7.6 What to build

Not access. A **registry and a boundary**:

1. **A consumer/agent registry** — `name → subject → durable|ephemeral →
   start mechanism → definition path`. This is the single highest-value
   missing artifact; it is what makes a lifecycle node's dropdown finite and
   safe, and what lets anything reconcile intent against reality.
2. **An allowlist shim** — a ~200-line near-clone of the existing
   `gpu-gaming-mode` CLI, whose entire security value is refusing units
   outside a fixed list (`readonly -a UNITS=(...)`). Copy that pattern
   verbatim, including its lease-awareness: the difference between a button
   that stops a service and a controller that knows whether stopping is safe
   and what to restore.
3. **A joined state read** — `systemctl show -p ActiveState,SubState,NRestarts`
   gives process state; NATS `jsz` gives bus-binding state. Nothing joins
   them, so *a consumer whose unit is active while its JetStream consumer is
   unbound looks healthy and is not.* The `status` verb must return both.
4. **A failure signal** — no `WatchdogSec`, no `sd_notify` anywhere, so a
   flapping consumer emits nothing a workflow can trigger on. `NRestarts` is
   the cheapest available flap signal; the proper answer publishes a
   `service-state-changed` event so a Bloodbank trigger drives the onError
   branch natively. This is what would have surfaced the 10,427 restarts.

n8n then becomes the control surface the way it already is for GPU mode: a
typed node per consumer, backed by the registry, calling the allowlisted shim.

### 7.7 Two correctness bugs found in passing

- **Subject coverage seam.** `BLOODBANK_EVENTS` accepts `bloodbank.evt.v1.>`
  plus `bloodbank.evt.v2.repo.maintenance.failed`, but the toaster's filter is
  `bloodbank.evt.v1.>` — it silently never sees the v2 subject. Nothing checks
  that the union of consumer filters covers the stream's subject set.
- **Commands expire silently.** `BLOODBANK_COMMANDS` is `retention=workqueue,
  max_age=1d`, and no dead-letter handling is implemented. An unhandled
  command is dropped after a day with no signal. That directly affects §3.

---

## 8. Open questions

- **Ephemeral agent identity.** The gateway resolves `target_agent_id` through
  the fleet registry with default-deny. Ephemeral contractors have no registry
  entry by definition. Does the orchestrator hold a wildcard entry, or does the
  registry grow a "contractor" class? This is the main unresolved design point.
- **Cost attribution.** Provider arbitrage only pays off if spend per pool is
  measurable. Is that a Candystore projection or a separate meter?
- **Nested delegation.** May an orchestrator-spawned agent itself dispatch?
  `causationid` supports the chain; runaway-fan-out policy is undefined.

## 9. Provenance

Every "live/dead" claim in §2 and §6 was verified directly on `big-chungus`
on 2026-08-27 — `systemctl` state, listening ports, `git log`/`git blame`
dates, and filesystem existence. Claims sourced from an agent report were
independently re-verified before inclusion. Items that could not be verified
are marked in the originating review, not asserted here.
