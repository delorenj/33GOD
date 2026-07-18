# Board awareness — resolving the repo and reading the world

Momo is repo-agnostic. PJangler's nearest-ancestor `.project.json` supplies
stable project/bootstrap identity and provider binding inputs. It does not
contain authoritative lifecycle state.

## What `.project.json` gives you

```jsonc
{
  "project_slug": "candystore",          // -> hindsight bank, data.repo, service
  "ticket_provider": {
    "type": "plane",                      // adapter provider (plane|linear|trello)
    "workspace": "33god",                 // -> Plane workspace + PLANE_<WS>_API_KEY
    "board_id": "82e5…",                  // Plane project UUID (may be EMPTY — see self-heal)
    "identifier": "CANDYS"                // board key prefix
  },
  "agents": { "candystore-pm": { "role": "pm", "role_dir": "agents/hermes/pm" } }
}
```

- **Slug** = `project_slug` → the hindsight bank name and `data.repo` on decision events.
- **role_dir** → where the shared machinery lives: `<repo>/<role_dir>/.scripts/…`
  (the `tp` adapter, sentinel bin scripts, the runtime submodule, evidence dir).

Use the stable slug/binding to resolve Lifecycle, then fetch its authoritative
snapshot: lifecycle ID, spec/state versions, legal frontier, obligations,
blockers, and capability grants. Use `scripts/lifecycle_client.py fetch` and
follow `lifecycle-client.md` for the implemented fail-closed read/command path.

## Authoritative lifecycle and provider projection

Lifecycle is the single source of project-lifecycle truth. It alone calculates
state, legal frontier, obligations, and capability validity. Momo submits
idempotent intent with the expected state version and renders the returned
accepted/rejected/stale/unavailable result.

The current adapter remains useful to read and compare provider projections:

```bash
bash <skill_dir>/scripts/momo-board.sh list_issues        # [{id,key,title,state,state_type,...}]
bash <skill_dir>/scripts/momo-board.sh active_milestone   # {id,name,state} (Plane cycle; may be empty)
bash <skill_dir>/scripts/momo-board.sh get_issue <uuid>   # incl description + comments
bash <skill_dir>/scripts/momo-board.sh comment <uuid> "…" # post a PM/review note (sign it: "— momo")
```

Do not call `momo-board.sh transition` in the target workflow. That operation is
a legacy direct provider write retained only for migration compatibility.
Normalized adapter values (`backlog | unstarted | started | in_review |
completed`) are projection vocabulary, not the authoritative state model.
The wrapper finds the repo root + role_dir, and (for Plane) maps the per-workspace secret
`PLANE_<WORKSPACE>_API_KEY` (from `~/.config/zshyzsh/secrets.zsh`) into the `PLANE_API_KEY`
the adapter needs. `PLANE_BASE` defaults to `https://plane.delo.sh`.

## Provider = trello (legacy/projection adapter)

`momo-board.sh` dispatches on `.project.json` `ticket_provider.type`. For `plane`/`linear`
it uses the repo's installed `tp` adapter (above). For **`trello`** it uses Momo's OWN
bundled adapter — `scripts/providers/trello.py` (stdlib-only; no `uv`/`httpx`; no per-repo
scaffold and **no `role_dir` required**). Its normalized reads support projection
comparison; its transition operation is not target authority. Creds:
`TRELLO_API_KEY` (or `TRELLO_KEY`) + `TRELLO_TOKEN`; board id from
`.project.json` `ticket_provider.board_id`.

Trello columns rarely match Momo's five normalized stages 1:1, so the per-repo lane mapping
lives in **`<root>/.momo/config.json`** (NOT in `.project.json`, which is provider identity
only). Schema:

```jsonc
{
  "provider": "trello",
  "board_id": "…",
  "lanes": {                       // normalized state -> one OR MORE real lane names
    "backlog":   ["Backlog", "Inbox"],
    "unstarted": ["Priority", "Assigned"],
    "started":   ["In proggress"],
    "in_review": ["Ready for testing", "Awaiting approval"],
    "completed": ["Completed"]
  },
  "write_targets": { "in_review": "Ready for testing" },  // legacy migration mapping only
  "lane_notes":    { "Awaiting approval": "blocked on PR approval", … }  // human semantics, optional
}
```

The adapter's current `transition` operation can map a state or literal lane, but
the corrected target never invokes it directly. Only Lifecycle may cause a
provider projection change through its authorized adapter boundary. Lanes off the map read as
`state:"other"`; never infer lifecycle legality from a lane.

**First-run setup (one time per repo).** If `.momo/config.json` is absent, run
`scripts/momo-config.py detect` — it reports `is_standard`, `unmapped_lanes`, and
`states_with_missing_lane`. If non-standard, interactively map the odd lanes WITH the
operator (their board, their call), then persist:
`scripts/momo-config.py set --lanes '{…}' [--write-targets '{…}'] [--notes '{…}']`.
Thereafter the mapping is just data the adapter reads.

## board_id self-heal (a recorded decision, not a silent patch)

`plane.sh` reads the board id ONLY from `.project.json` `ticket_provider.board_id`. If that
is empty, every op except `create_board` dies with `plane: project not set`. When you hit
this:

1. Look for the provisioning fallback `<role_dir>/.scripts/.plane-project-id` (a bare UUID).
2. Else query the workspace and match by name/identifier:
   `curl -fsS -H "X-API-Key: $PLANE_API_KEY" "$PLANE_BASE/api/v1/workspaces/<ws>/projects/"`
   — **verify by name**, because near-duplicate boards exist (e.g. in `33god`: "Candy Store"
   CSTOR, "Candybar" CANDY, "Candystore" CANDYS — only the exact repo name is correct).
3. Backfill `.project.json` `ticket_provider.board_id` (and correct `identifier` if wrong).
4. Submit the repaired binding as an observation and **record the decision**
   (`record-decision.py`, basis `one-source-of-truth`,
   `respect-the-contracts`). This is bootstrap metadata, not a lifecycle write.

This backfill is a config repair, not a code mutation, so Momo may do it directly. Anything
beyond a binding repair still goes through a delegated worker.

## Seeing what Hermes is doing (avoid double-dispatch)

- `<role_dir>/runtime/continuous-ticket-sentinel-state.json` — machine-readable feed:
  `status` (idle|checking|active|blocked|stalled|error), `active_issue`, `session`,
  `worktree`, `last_heartbeat_at`. **May be absent** when reconcile is disabled
  (`role.yaml` has no `reconcile: {enabled: true}` block) — then Hermes only checkpoints.
- Tail `<role_dir>/runtime/logs/heartbeat.log` and read `<role_dir>/runtime/memories/MEMORY.md`
  ("Recent context") for Hermes' mental model.
- Honor **WIP=1**: if Hermes shows an active worker, do not start a second. If you take a
  ticket, you own the WIP slot until it clears.

## Evidence and projection surfaces

- Authority: versioned Lifecycle snapshot/command result via
  `scripts/lifecycle_client.py` and Candystore's read-only projection API
- Evidence: `_bmad-output/implementation-artifacts/issue-evidence/<ISSUE>.md`
- Decision/event trail: `_bmad-output/implementation-artifacts/bloodbank-events.jsonl`
- Live workers: `git status`, branches, `git worktree list`, recent commits, zellij sessions.

When the provider board, evidence, and Lifecycle disagree, Lifecycle remains the
state authority. Submit the evidence/discrepancy as an observation, record a
truth-check decision, and render the authoritative version; Momo does not choose
or write the winning state.
