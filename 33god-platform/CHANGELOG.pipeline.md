# 33GOD Pipeline Changelog

This changelog records changes that affect more than one 33GOD component. It is
fed by `changes/*.jsonl`; update both when a contract shifts.

## 2026-08-13

### Agent session broker boundary

Approved the LiteLLM Agent Control Plane for a gated evaluation as 33GOD's
subordinate agent execution/session broker. ACP is explicitly not the 33GOD
control plane: Flume retains workforce and delegation policy; PJangler and the
fleet registry retain permanent identity; Bloodbank retains command ingress;
Candystore retains audit history; Hindsight retains durable memory; DeLoNET
LiteLLM retains provider credentials, budgets, aliases, and fallbacks; Holocene
and DeLoHQ retain operator experience.

The decision defines the `33god-hermes` adapter mapping, the missing correlated
assistant-message contract, a removable four-stage pilot, security and shutdown
gates, and BMAD deliverables owned by `33god-pm`. ACP, Flume, DeLoHQ, and
OpenNotebook remain integration boundaries rather than active component
registry members until each satisfies the normal repository/deployment,
lifecycle, health, source-of-truth, and validation gates.

### 33GOD research custody

Declared OpenNotebook a searchable research/read model over canonical Git and
BMAD evidence. The deterministic project corpus is named
`33GOD - Platform Architecture and Control Plane`. Notebook sources, chats,
summaries, and insights are non-authoritative until promoted into Git/BMAD.
Secrets and runtime state are excluded from ingestion. Source custody may begin
without embeddings while the new OpenNotebook deployment has no configured
model provider; provider credentials must not be added until its tracked
encryption/database secret debt is removed.

The notebook is now live with ID `notebook:5n0x8mn63mvijhj7b2zl`. All 11
provenance-stamped initial sources completed processing with embeddings off and
no configured model provider. The exact source IDs, revisions, classifications,
and ingestion hashes are recorded in
`knowledge/open-notebook-33god.yaml`.

## 2026-08-11

### One Lifecycle Machine

`momo/lifecycle/` is deleted. Krebs is now the only ticket-lifecycle machine,
satisfying FR12.

This was not a plain delete. Comparing the two specs semantically rather than
textually showed Krebs was **missing** content the Momo copy carried:

- `blocked -> backlog` via `operator_reopen`. The rationale doc is explicit that
  `blocked` is "terminal for the loop, re-openable by operator" — without this
  edge a blocked ticket could never return to the board.
- `on_fail: blocked_funnel` on all three failure edges into `blocked`, the
  "single blocked funnel" the rationale calls a promoted gotcha fix. Krebs's
  schema also had to gain `transitions[].on_fail`, since it set
  `additionalProperties: false`.

Both were ported into Krebs first; transition parity is now 14/14 and
`lifecycle.v1.yaml` validates against `lifecycle.schema.json`. Krebs keeps its
own `acquired` guard name, which is what PJangler's CommonProject steps already
call; Momo's `picked_up` was a local rename with no other consumer.

The copy's rationale (15K) and changelog moved to
`krebs/spec/lifecycle-rationale.md` and `krebs/spec/lifecycle-CHANGELOG.md`,
repointed to Krebs paths with a provenance banner.

Momo's `SKILL.md`, `board-clearing-loop.md`, and `docs/fleet-normalization.md`
all named `momo/lifecycle/` as the SSOT and now name `krebs/spec/`. Its
`lifecycle_pointer` already targeted Krebs.

`momo-lifecycle-duplicate-v1` passes and is retained as a reintroduction guard:
it scans all of Momo for the old path and for the fork's self-identifying
`kind: momo.ticket-lifecycle` marker. All five backfills now report OK.

### Company-Reporter Split Resolved

The company-reporter work spanned two repositories and had to be separated
rather than merged or dropped wholesale.

Kept, into `hermes-agent-template`:

- the `reporter` role in `copier.yml` and `SOUL.md.jinja`;
- a least-privilege reporter runtime contract — delta save mode, disabled
  toolsets, `no_mcp` platform toolsets, spawn depth 1, no MCP inheritance;
- reporters never inherit the staging profile's `.env`;
- reporters skip systemd gateway/consumer installation;
- `secret-scan.py`, now run against the rendered scaffold before anything is
  copied into the runtime;
- `reporter-watchdog.py`, the one file on the parent branch with no counterpart
  anywhere. Every deployment constant it hardcoded is now a `REPORTER_*`
  environment override.

Dropped:

- the parent's generated `agents/hermes/reporter/` profile, regenerable from the
  template now that the reporter role exists;
- its tracked `runtime` submodule and `.gitmodules` entry — the exact FR4
  violation;
- its `.done-*` provisioning markers;
- its `scrum-master/` tooling, already renamed to `sentinel/` upstream;
- its standalone `continuous-ticket-sentinel.sh` runner and second systemd
  timer, superseded by the fused `heartbeat.sh` and `sentinel.prompt.md.jinja`;
- `gh repo create` remote-runtime provisioning, `target_repo`-qualified review
  subjects, and a re-hoisted `already_done` that would have regressed main's
  legacy-consumer remediation ordering.

`test_runtime_bootstrap_scans_before_commit_and_push` asserted on `git add -A`
and `git push -u origin main` — code main deleted when runtimes moved local. It
was replaced with the equivalent local invariant plus a guard that provisioning
never resurrects a per-agent runtime remote. 60/60 template tests pass.

No worktrees remain in the family.

## 2026-08-10

### Trunk Checkpoint

- Folded every piece of in-flight work to `main` across the family and advanced
  all nine submodule pins to their `origin/main` tips — the first checkpoint
  where that has been true simultaneously.
- Pruned six worktrees. Four held branches already contained in `origin/main`;
  two more (`feature/PJAN-19-hermes-bloodbank-gateway`,
  `codex/reporting-contracts`) looked like thousands of lines of unmerged work
  but were stale pre-rebase duplicates. Content comparison against the merge
  base, not commit count, is the test. The gateway branch was byte-poorer than
  `main` and missing `execution_state.py`; every file conflicted add/add.
  Every one of the eight files the contracts branch added is byte-identical to
  `main`'s copy, so its work had already landed; its only live deltas are
  `validate.py` and `docs/event-naming.md`, both of which predate the `curator`
  domain and `skill` entity and would regress those allowlists if applied.
- Recorded FR14 (trunk discipline) so this state is a gate, not an accident.

### Skill Ownership Relocation

- Moved skill sources of truth out of root `skills/` and into the components
  whose contracts they describe: Bloodbank owns event-integration skills,
  PJangler owns provisioning and mise skills, Krebs owns lifecycle and triage
  skills, and `33god-platform/` owns cross-cutting skills.
- Root `skills/` is now a link farm with no divergent copies.
- Split Skillex pack provisioning from skill fan-out in `mise.toml` so packs
  declared in `.agents/skills.json` resolve before sync runs.

### Registry Expansion

- Registered Momo (PM/EM orchestration agent) and Toad (project custodian
  agent), bringing the active component list to thirteen.
- Required every component to declare a runtime mode, so non-service components
  state an execution model rather than carrying an empty compose block.

### Lifecycle Authority

- Declared Krebs the single ticket-lifecycle authority (PRD FR12). One machine,
  five normalized `tp` bands, per-repo variation limited to label maps.
- Opened `momo-lifecycle-duplicate-v1`: `momo/lifecycle/` still carries the
  pre-promotion copy and both its spec and schema have drifted from
  `krebs/spec/`, while Momo's own agent spec already points at Krebs.

## 2026-07-15

### Root Compose Cutover

- Published Holocene `edaf31b`, pinned all four component gitlinks, and added
  formal Holocene and PJangler submodule mappings at the monorepo root.
- Replaced the three component-owned Compose lifecycles with the root project.
  Bloodbank core, one Candystore triplet, and Holocene web are live under
  `33god-platform`; PJangler remains clean, pinned, and run-only.
- Adopted the Holocene `/hq` plus `/_next/static` routing contract and removed
  the excluded legacy Bloodbank PostgreSQL container.

### Integrated Compose Target

- Replaced the readiness scaffold with a root-owned normalized projection for
  Bloodbank NATS/init/placement, one standalone Candystore triplet, Holocene
  host-API preflight and web, and opt-in run-only PJangler CLI/MCP tools.
- Preserved ports, three external network identities, and five adopted external
  volume identities; excluded Bloodbank's legacy Candystore services and kept
  detached legacy volumes outside the target.
- Added a semantic validator and focused tests for default, `tools`, `full`,
  and render-only unsupported `cloud` models.
- Extended the documentation drift gate to validate the candidate against an
  explicit source root. Cloud deployment remains blocked.
- Hardened every checked-in render task with `--no-env-resolution`, preserved
  caller-selected port overrides for validation, and suppressed captured
  Compose errors that could otherwise disclose component env-file values.
- Expanded semantic/adversarial gates for the canonical Candystore subscription
  and daprd placement path, exact Traefik Host/auth/proxy behavior, and exact
  per-service network isolation. The committed Holocene `/hq` router and its
  `/_next/static` asset path are the pinned baseline.

### Registry Truth Reconciliation

- Corrected PJangler, Hermes Fleet, and HeyMa paths to their live checkouts and
  restored PJangler's canonical npm health command.
- Removed Holyfields and Hookd from the active component list because neither
  repository is present in the current platform checkout. Their manifest files
  remain as historical definitions until those components are deliberately
  restored.
- Re-established the platform manifest validator as a live-truth gate.

## 2026-07-10

### Component Registry Repair

- Restored the Candybar, Holyfields, and Hookd component manifests referenced by
  `components.yaml`.
- Removed the incomplete Flume manifest from the active registry until the repo
  path and platform contract are real.
- Re-established `platform:validate` and `platform:components` as usable
  control-plane gates for the next director handoff.

## 2026-07-08

### Platform Control Plane Bootstrap

- Added the `33god-platform` control-plane scaffold.
- Indexed the current component constellation: Bloodbank, Candystore, Holocene,
  PJangler, Hermes Fleet, Skillex, Hindsight, Pipeline MCP Hub, Candybar, HeyMa,
  Holyfields, and Hookd.
- Established the first machine-readable change entry and read-only backfill
  checks for canonical Hindsight/Bloodbank hook migrations.
- Added a unified `33god-hub` skill entrypoint so agents start from one product
  map before drilling into component-specific skills.

Backfill checks introduced:

- `hindsight-canonical-hooks-v1`
- `bloodbank-canonical-agent-publisher-v1`
- `hermes-inherited-profile-config-v1`
- `skillex-33god-hub-v1`
