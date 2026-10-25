# Aperture final integration handoff — Grolf → Rererere, 2026-10-25

**Status: RESEARCH + VERSIONED DELIVERABLES, not a deployment authorization.**
All eight groups are built, PM-gated, and merged to main (G8 at `542699e`).
Nothing here says "install on Damian's machine." What ships, when, and on
which host is yours per the charter. What this handoff does: give you the
complete deploy-and-accept picture in one place — install order, the seams
already proven, the gate you own for each group, and the coexistence rules
that keep multiple groups on one bus from splitting events between stores.

Reply convention (yours, kept): verify independently, then send an ack file
stating what you confirmed, adopted, corrected, or rejected.

## 0. The one-paragraph mental model

Aperture is eight portable Compose bundles, one shared bus contract. Each
group is a self-contained `god-gN` project (own volumes/networks, no host
ports, images pinned + arm64/amd64-manifest-verified, zero AAI, client-owned
LLM surfaces with EMPTY defaults that degrade instead of crash). G1 provides
the bus + candystore; G2–G8 attach to it via each bundle's
`compose.attach.yml`. Everything is proven on the build host; nothing has
touched the target. Your job: deploy in dependency order, run each group's
`accept/` gate with Damian's real hands, and record evidence.

## 1. Install order and what each group is

`G1 → G2 → G3 → G4 → G5 → G6 → G7 → G8` (dependency order; G3–G6 need only
their named prerequisites).

| Group | Plane | Deploy shape | Your gate (ACCEPTANCE.md) |
|---|---|---|---|
| G1 | Event bus | NATS JetStream + candystore + dapr; **the bus others attach to** | founder decision record (`accept-g1.sh`) |
| G2 | Event lake + agent ingest | attaches to G1 | client builds own workflow (`accept-g2.sh`) |
| G3 | Notifications | ntfy; needs topic subscribe on Damian's device | phone buzz, stage 1 |
| G4 | Observability | Prometheus/Grafana/Loki + Alertmanager→ntfy | kill a container, get paged, watch it heal |
| G5 | Project tooling | pj + Skillex + notebook | a real project born on the stack |
| G6 | Voice pipeline | intake → transcription → Wax → event | real recording → verbatim transcript check |
| G7 | Memory + enrichment | candystore + enrichment + hindsight-bridge | recall from stored real history (`accept-g7.sh`) |
| G8 | Orchestration + apps | momod + board + code-worker + dashboard | **Momo closes a real ticket with real code** (`accept-g8.sh`) |

## 2. Deployment mechanics (identical for every group)

```sh
cd 33god-platform/aperture/groups/gN
cp .env.example .env                    # review; LLM vars stay EMPTY by default
docker compose up -d --build --wait     # standalone (own bus)

# attached (G2+ joining G1's bus — the production shape):
GOD_BUS_NATS_URL=nats://nats:4222 GOD_G1_BUS_NETWORK=g1-bus \
docker compose -f compose.yml -f compose.attach.yml up -d --build --wait
```

- In-network only: no published host ports anywhere; probe via
  `docker compose exec` or an SSH tunnel.
- Cold-start truth: **fresh dapr sidecars bind their durable 10–60s late.**
  Every gate kit and smoke runs a readiness canary (publish→readback round
  trip) before client checks; never publish-then-check without it.
- Tail/recall latency is 3–8s — every acceptance check polls; single-shot
  queries produce false failures.
- Evidence dirs (`accept/evidence/`) are untracked; evidence stays on the
  machine that ran the gate.

## 3. THE COEXISTENCE RULE (the one hard invariant)

**Every group owns its own JetStream durable + queue names.** G1 keeps
`candystore-events`/`candystore`; G7 owns `g7-candystore-events`; G8 owns
`g8-candystore-events`. Two consumers sharing one durable round-robin the
stream and silently split events between databases — candystore's own
AGENTS.md warns exactly this. Proven per pair: G1+G7 (`g7/smoke/coexist.sh`,
8/8) and G1+G8 (`g8/smoke/coexist.sh`, 9/9, including G8's own cycle output
reaching both stores). If you add any group to a shared bus, verify its
`dapr/pubsub.yaml` durable is its own before `up`.

## 4. Gate status at handoff (all build-host-proven, none client-run)

| Gate | Kit | Build-host proof | What Damian supplies |
|---|---|---|---|
| G1 decision record | `accept-g1.sh` | 10/10 smoke + decision round-trip | a real decision in his own words |
| G2 client workflow | `accept-g2.sh` | canonical + seam proof | his own first workflow |
| G3 phone buzz | stage-1 script | pipeline proven; push untested on-device | ntfy topic subscribe on his phone |
| G4 paging | chaos script | stack self-monitors | a `docker stop` + on-device page receive |
| G5 project birth | scripted | scaffold flow proven | the real project name + first run |
| G6 voice gate | scripted | pipeline proven | **operator-provided recording ≥60s** + spot-check phrases |
| G7 recall | `accept-g7.sh` | 11/11 kit run green | two real notes in his own words |
| G8 ticket cycle | `accept-g8.sh` | 18/18 smoke: ticket→real commit→done, one correlationid, 6-event chain, dashboard | the ticket title (human initiates; the stack does the rest) |

G8's gate evidence shape (so you know what green looks like): board `state:
done` with `commit_sha` == `git log HEAD` in the code-worker's repo; a real
2-file commit ("module + test"); one `correlationid` across six canonical
events (ticket.created → ticket.started → code.commit.landed →
tests.passed → review.completed → ticket.completed); dashboard `/items`
shows it done with the chain; momod's WIP lease acquired/released; reviewer
degraded-deterministic with EMPTY `GOD_LLM_*` (zero AAI is the tested
default; a client-owned endpoint upgrades review, never required).

## 5. Honest boundaries (unchanged from prior acks, still true)

1. **Board honesty**: G8's `board` is a REAL sandbox board (SQLite) speaking
   Plane's state vocabulary — not the live Plane service. `px`/Plane
   integration is a config boundary, deliberately (the spec's "Board
   honesty" section). If Damian's acceptance requires the real Plane board,
   that's a wiring decision for you two, not a defect.
2. **Sandbox repo**: G8's code-worker commits to a scratch repo inside its
   own volume — real commits, real tests, not the client's production repo.
3. **arm64**: every image is manifest-verified arm64+amd64; runtime
   execution on arm64 hardware remains a deployment-time check (no arm64
   host was available to the build).
4. **Memory**: summed standing caps are G1≈? + … + G8 1184 MiB. Budget each
   VM for the sum of the groups you co-locate; per-group caps are in each
   README; measured warm usage is far below caps everywhere.
5. **LLM surfaces**: all EMPTY by default. Degraded behavior is the proven
   path (G7 bridge healthz names the missing vars; G8 momod runs
   deterministic evidence review). Point `GOD_LLM_*` at any
   OpenAI-compatible endpoint Damian owns to upgrade; never required.

## 6. The acceptance runbook, in one pass

1. Stand up G1 on the target (standalone shape = it IS the bus). Run
   `accept-g1.sh` with a real decision.
2. Attach G2, then G3–G8 in order (§2 command). After each attach, the
   readiness canary in that group's smoke tells you delivery is bound.
3. Run each group's `accept/` gate with Damian's real inputs. Evidence lands
   in `accept/evidence/` locally — copy what you want to keep into the
   handback; the dirs are untracked on purpose.
4. Coexistence is pre-proven pairwise; if you co-locate beyond the proven
   pairs, re-run the newer group's `coexist.sh` shape against the live bus.
5. When all eight gates are green, that's Aperture accepted: send the
   handback with the gate-evidence bundle, and I'll record the
   `bloodbank.repo.decision.recorded` close-out.

— Grolf (`33god-pm`), 2026-10-25. G8 merged at `542699e`; all groups'
proofs re-runnable from their `smoke/` dirs. Charter v1.0 loaded every
session; charter-ack on every commit.
