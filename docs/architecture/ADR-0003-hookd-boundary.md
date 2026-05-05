# ADR-0003: hookd Boundary — standalone producer, not a Bloodbank subcommand

**Status:** Accepted
**Date:** 2026-05-05
**Relates to:** [ADR-0001](./ADR-0001-v3-platform-pivot.md) (Role reassignments), [ADR-0002](./ADR-0002-holyfields-scope-refactor.md) (scope-narrowing precedent)

> **Correction note (2026-05-05):** This ADR was originally drafted with the
> incorrect premise that `bloodbank/hookd_bridge/` was a hookd consumer
> adapter. It is not. That package is an unrelated OpenClaw HTTP-to-command
> shim that happens to share a name prefix. The decision in this ADR (do not
> absorb hookd into bloodbank) is unaffected, but supporting claims about
> `hookd_bridge/` were wrong and have been corrected in-place. The actual
> seam between hookd and bloodbank is the AMQP exchange contract
> (`bloodbank.events.v1` + `tool.mutation.*` routing keys), not a directory.

## Context

`hookd/` (Rust) sits at the boundary between AI coding agent tool execution
(Claude Code today; Gemini CLI, Codex, Cursor planned) and the 33GOD event
bus. Its only purpose is to publish `tool.mutation.*` events into Bloodbank.
That tight coupling has produced recurring pressure to fold hookd into
Bloodbank itself. Two open questions are explicitly recorded in
`bloodbank/GOD.md` next to the hookd references:

> **hookd** (separate repo, `~/code/33GOD/hookd/`) — Rust daemon bridging
> Claude Code hooks → Bloodbank (DO WE NEED THIS?!)

> Open Question ❓ Do we still need this??

The proposal under review is some variation of: move hookd into Bloodbank,
either as `bloodbank/bin/hookd` or as a subcommand of the v3 operator CLI
(`bb_v3 hook ...`).

The pressure is real:

1. hookd has zero reason to exist outside Bloodbank's dependency graph.
2. ADR-0001 names the v3 operator CLI surface as `doctor / trace / replay /
   emit`, and "emit" reads adjacent to what `hookd-emit` does.
3. A separately-named `bloodbank/hookd_bridge/` package exists, and its
   name suggested integration work in flight. (It does not. The package is
   an OpenClaw HTTP-to-command shim; the name collision contributed to the
   recurring "absorb hookd into bloodbank" question by implying a seam that
   does not exist.)
4. Two separately-deployed components for one logical capability adds
   apparent ops surface.

This ADR records why we resist absorption and what the correct seam is.

## Decision

**hookd remains a standalone Rust producer at `/home/delorenj/code/33GOD/hookd/`.**
Bloodbank does not absorb it.

The boundary is producer / transport, the same boundary every other producer
(heartbeat emitter, infra-dispatcher, OpenClaw bridge, ad-hoc API clients)
already respects. hookd is a peer producer, not a special case.

### Specifically

| Concern | Decision |
|---|---|
| `hookd` daemon (Rust) | Stays at `/home/delorenj/code/33GOD/hookd/`. Owns its own Cargo workspace, lockfile, and release cadence. |
| `hookd-emit` (shell client) | Stays at `/home/delorenj/code/33GOD/hookd/bin/hookd-emit`. It is hookd's agent-side fire-and-forget contract, not Bloodbank's CLI. |
| `bloodbank/hookd_bridge/` (unrelated) | Out of scope for this ADR. Despite the name, this package is the OpenClaw HTTP-to-command shim, not a hookd consumer. Name-collision mitigation tracked under Implementation. |
| Producer / transport seam | The AMQP exchange contract: exchange `bloodbank.events.v1`, routing keys `tool.mutation.*`, payload schema `ToolMutationEvent`. The seam is a contract, not a directory. The actual consumer is `services/mutation-ledger/`, outside both `hookd/` and `bloodbank/`. |
| Operator CLI (`bb_v3`) | Per ADR-0001, owns `doctor / trace / replay / emit`. May grow a `bb_v3 emit hook ...` subcommand for **human / test** emission against the same Dapr publish API hookd uses. This is an operator surface, not a replacement for hookd's hot path. |
| Service registry | hookd is registered in `services/registry.yaml` as `producer:hookd`, on equal footing with `producer:heartbeat-emitter`, `producer:infra-dispatcher`, etc. |

### Layering invariant (locked by this ADR)

```
PRODUCERS                       TRANSPORT                  CONSUMERS
─────────                       ─────────                  ─────────
hookd (Rust, host daemon)
heartbeat-emitter (Python)      Bloodbank        ──→       candystore
infra-dispatcher (Python)       (event bus +               holocene
openclaw bridge (Python)        operator CLI)              mutation-ledger
api clients / curl                                         agent inboxes
bb_v3 emit (operator)
```

Producers are language-agnostic and topology-independent. Bloodbank is the
event bus and operator surface. Producers do not live inside Bloodbank.

## Why absorption is wrong

### 1. Toolchain split

hookd is Rust (tokio, lapin, serde). Bloodbank is Python (FastAPI / FastStream
/ aio-pika, managed by uv). Folding a Cargo crate inside a uv-managed Python
repo creates a permanent dual-toolchain footprint:

- Two lockfiles (`Cargo.lock` + `uv.lock`) in one project root
- Two CI lanes per change (Rust build + Python build)
- Two release cadences for one repo's main branch
- Two contributor onboarding paths

The cost is borne forever. The benefit (one repo) is cosmetic.

### 2. Lifecycle topology differs

hookd MUST run as a user-level daemon on the agent's host, because event
enrichment requires `git rev-parse`, `git branch`, and `git remote` against
the developer's local working tree. Per the hookd GOD doc:

> hookd is designed to run as a user-level daemon (not containerized), since
> it needs access to the host filesystem for git context resolution.

Bloodbank API and bloodbank-ws-relay are containerized services on the
`33god-bloodbank` Compose project. They have orthogonal:

- Process supervisors (systemd user vs. Docker)
- Filesystem expectations (host vs. container)
- Failure modes (single-user blast radius vs. shared-bus blast radius)
- Restart policies (developer convenience vs. service availability)

Putting them in one repo does not make them one component. It just
misrepresents the deployment graph.

### 3. ADR-0001 narrows Bloodbank's scope

ADR-0001 explicitly reassigns Bloodbank to "runtime and operations only:
Dapr manifests, NATS bootstrap, Compose files, operator CLI, adapter
migration points, replay and dead-letter tools." Pulling a
language-specific producer into Bloodbank's tree expands scope in the
direction ADR-0001 explicitly closed.

ADR-0002 (Holyfields scope refactor) demonstrates the same pattern from a
different angle: when a component starts accumulating responsibility for
adjacent concerns, narrow it. Don't widen it.

### 4. The producer/transport boundary is load-bearing

Bloodbank already accepts events from at least five distinct producers
(hookd, heartbeat-emitter, infra-dispatcher, OpenClaw bridge, ad-hoc API
clients). Privileging hookd by absorbing it creates a question we cannot
answer cleanly: why hookd and not the others? The producers are symmetric
by design. Asymmetric absorption breaks the model.

### 5. The right seam is already in place, and it is not a directory

The seam between hookd and Bloodbank is the AMQP exchange contract:
exchange `bloodbank.events.v1`, routing keys `tool.mutation.*`, payload
schema `ToolMutationEvent`. hookd publishes; the consumer
(`services/mutation-ledger/`) subscribes. Bloodbank itself does not own a
hookd-aware adapter, and does not need one. Treating the contract as the
seam is the same shape that other producers (`heartbeat-emitter`,
`infra-dispatcher`) already follow.

The `bloodbank/hookd_bridge/` package is sometimes mistaken for this seam
because of its name. It is not. It is an unrelated OpenClaw HTTP shim that
publishes `command.*` envelopes. See the Implementation section for the
clarifying note added to `bloodbank/hookd_bridge/__init__.py`.

## Consequences

### Positive

- **Layering invariant survives.** Producers stay producers; transport stays
  transport. The architectural distinction we already invested in continues
  to pay rent.
- **Zero toolchain pollution.** Bloodbank stays Python-only. hookd stays
  Rust-only. Each repo has one mental model, one CI lane, one lockfile.
- **Independent release cadence.** hookd can iterate on enrichment logic
  without forcing a Bloodbank release. Bloodbank can refactor its consumer
  side without touching hookd.
- **Multi-agent expansion is cheap.** When Gemini CLI, Codex, Cursor support
  lands, those agents pipe through `hookd-emit` (or a peer producer) and
  Bloodbank does not need to know.
- **Operator CLI stays focused.** `bb_v3 emit hook ...` becomes a thin
  test/operator subcommand that wraps the Dapr publish API. It does not
  duplicate hookd's enrichment, socket buffer, or fire-and-forget guarantees.

### Negative / costs

- **Two repos, two READMEs.** Newcomers must read both to understand the
  end-to-end mutation pipeline. Mitigated by cross-links in both GOD docs
  and a clear `services/registry.yaml` entry.
- **The "DO WE NEED THIS?!" comments must be removed from bloodbank/GOD.md.**
  Open questions in canonical docs are an attractor for re-litigation. This
  ADR is the answer; the GOD doc must reflect it.
- **Name-collision risk: `hookd` vs `hookd_bridge`.** The Python package
  `bloodbank/hookd_bridge/` (OpenClaw command shim) sits permanently
  adjacent to `hookd/` (Rust producer) and shares a prefix. Future readers
  will assume a relationship. Mitigated by a clarifying note in the
  `hookd_bridge/__init__.py` docstring and in `bloodbank/GOD.md`. A future
  ADR may rename the package; that is out of scope here.
- **The `bb_v3 emit hook` subcommand creates a second emit path.** This is
  acceptable because the two paths have different audiences (production agent
  hot path vs. human/operator/test) and different guarantees (zero-block
  vs. synchronous-feedback). Documented in the v3 operator CLI guide.

### Neutral / deferred

- **hookd v3 envelope migration.** When hookd publishes via Dapr + NATS
  JetStream + CloudEvents instead of raw RabbitMQ, the boundary in this ADR
  does not change. Only the publish API hookd targets does. Tracked under
  v3 adapter migration points.
- **Future producer registry contract.** A formal schema for what makes a
  "producer" in 33GOD (lifecycle, health, registration) is desirable but
  out of scope here. This ADR settles the hookd question; a separate ADR
  can define the producer-class contract when a third producer needs the
  same treatment.
- **Rewrite hookd in Python.** Considered (see Alternatives). Deferred
  indefinitely; the Rust implementation has properties (zero-block, low
  resource footprint, deterministic shutdown) that a Python rewrite would
  have to re-earn.

## Alternatives considered

- **Move hookd into `bloodbank/bin/`.** Rejected. Drags Rust toolchain into
  the Python repo, conflates producer with transport, and does not eliminate
  the daemon's host-coupled lifecycle.
- **Make hookd a `bb_v3` subcommand (`bb_v3 hookd run`).** Rejected. The
  `bb_v3` CLI is an operator tool per ADR-0001; running a long-lived daemon
  is not an operator action. Subcommand-as-daemon is a category error.
- **Rewrite hookd in Python so it can live inside Bloodbank.** Rejected.
  Throws away a working Rust implementation to solve a perceived org problem
  ("two repos") that is not an actual cost. Python has no advantage at the
  hot-path enrichment step; the work is git-context resolution and AMQP
  publish, both of which Rust handles better.
- **Deprecate hookd entirely; have agents publish CloudEvents directly via
  Dapr.** Rejected for now. Agents (Claude Code, Gemini CLI, Codex) emit raw
  hook payloads, not CloudEvents. Something must enrich and translate. That
  something is hookd. Re-evaluate if and when an agent ships a Dapr-native
  hook contract.
- **Promote hookd to a separate top-level git repo.** Rejected. The
  metarepo structure already gives hookd its own directory; promotion to a
  separate git repo would make atomic cross-component changes (e.g.
  envelope shape changes affecting both hookd and
  `services/mutation-ledger/`) harder. Status quo is the right granularity.

## Implementation

This ADR is a boundary decision, not a rewrite. The implementation is small,
mostly documentation and naming hygiene.

1. **Update `bloodbank/GOD.md`.** Remove "DO WE NEED THIS?!" and the "Do we
   still need this??" open question. Replace with a one-line reference to
   this ADR. Cost: XS.
2. **Update `hookd/GOD.md`.** Add an "Architectural Boundary" section near
   the top that cites this ADR and states explicitly: hookd is a producer,
   Bloodbank is transport, the seam is the AMQP exchange contract
   (`bloodbank.events.v1` + `tool.mutation.*`), and the consumer is
   `services/mutation-ledger/`. Cost: XS.
3. **Add a name-collision clarifying note to
   `bloodbank/hookd_bridge/__init__.py`.** One-line note in the existing
   module docstring stating: this package is unrelated to the `hookd/` Rust
   daemon despite the prefix overlap. Cost: XS.
4. **Register hookd in `services/registry.yaml`.** Entry: `producer:hookd`,
   with metadata for language (Rust), deployment (host daemon), event
   surface (`tool.mutation.*`), owner. Cost: XS.
5. **Add `bb_v3 emit hook ...` subcommand stub.** Operator-side wrapper
   around the Dapr publish API for human/test emission. Out of scope for
   this ADR's acceptance; tracked as a follow-up ticket under v3 operator
   CLI work. Cost: S.
6. **Cross-link from `docs/GOD.md`.** Add hookd to the producer inventory
   so the metarepo-level architecture doc reflects the producer/transport
   model explicitly. Cost: XS.

### Rollback

If a future agent integration (e.g. a hook system that emits CloudEvents
natively) eliminates the need for enrichment, hookd can be deprecated
without affecting any decision in this ADR. Producers come and go;
the boundary stays.

## Review triggers

Revisit this ADR if:

- A second Rust-native producer ships and the dual-toolchain argument no
  longer holds (i.e. Bloodbank already has a Rust subdirectory for some
  other reason).
- hookd's enrichment logic moves entirely into Dapr middleware, leaving
  hookd as a pure socket-to-publish forwarder. At that point the daemon may
  be small enough that the boundary becomes cosmetic.
- A future agent contract emits CloudEvents directly and hookd's reason to
  exist disappears. Then this ADR is moot, not wrong.
- Three or more independent producers materialize and the producer-class
  contract becomes worth formalizing in its own ADR.

In each case, the ADR is amended with a new status block; decisions are not
silently revised.
