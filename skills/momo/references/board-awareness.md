# Board awareness — resolving the repo and reading the world

Momo is repo-agnostic. Everything is resolved at runtime from the nearest ancestor
`.project.json` (the pjangler CommonProject marker). Nothing is hardcoded to a repo.

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

## Reading the board — always through the adapter

Do **not** call Plane/Linear/Trello directly, and do **not** use the
`project-lifecycle` skill's `plane-workspaces.json` path for state
transitions — it can resolve a different board and desync from Hermes. The `tp` adapter is
the single source of truth and keeps you byte-identical to the sentinel. Use the wrapper:

```bash
bash <skill_dir>/scripts/momo-board.sh list_issues        # [{id,key,title,state,state_type,...}]
bash <skill_dir>/scripts/momo-board.sh active_milestone   # {id,name,state} (Plane cycle; may be empty)
bash <skill_dir>/scripts/momo-board.sh get_issue <uuid>   # incl description + comments
bash <skill_dir>/scripts/momo-board.sh comment <uuid> "…" # post a PM/review note (sign it: "— momo")
bash <skill_dir>/scripts/momo-board.sh transition <uuid> <state>
```

Reason in **normalized states** only: `backlog | unstarted | started | in_review | completed`.
The wrapper finds the repo root + role_dir, and (for Plane) maps the per-workspace secret
`PLANE_<WORKSPACE>_API_KEY` (from `~/.config/zshyzsh/secrets.zsh`) into the `PLANE_API_KEY`
the adapter needs. `PLANE_BASE` defaults to `https://plane.delo.sh`.

## Provider = trello (self-contained adapter + config-driven lanes)

`momo-board.sh` dispatches on `.project.json` `ticket_provider.type`. For `plane`/`linear`
it uses the repo's installed `tp` adapter (above). For **`trello`** it uses Momo's OWN
bundled adapter — `scripts/providers/trello.py` (stdlib-only; no `uv`/`httpx`; no per-repo
scaffold and **no `role_dir` required**). Same normalized ops, so all doctrine below is
provider-uniform. Creds: `TRELLO_API_KEY` (or `TRELLO_KEY`) + `TRELLO_TOKEN`; board id from
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
  "write_targets": { "in_review": "Ready for testing" },  // canonical lane a `transition <state>` writes to (else lanes[state][0])
  "lane_notes":    { "Awaiting approval": "blocked on PR approval", … }  // human semantics, optional
}
```

`transition <id> <target>` accepts a normalized state (→ its `write_targets`/first lane) OR
a literal lane name (moved verbatim — e.g. to pick the PR-blocked vs QA lane explicitly). It
**fails loud** on any target that is neither a known state nor a live lane; lanes off the map
read back as `state:"other"` with their real `list` preserved. Never guess a lane.

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
4. **Record the decision** (`record-decision.py`, basis `one-source-of-truth`,
   `respect-the-contracts`) — this is a shared-state change Hermes will also read.

This backfill is a config repair, not a code mutation, so Momo may do it directly. Anything
beyond a binding repair still goes through a delegated worker.

## Seeing what Hermes is doing (avoid double-driving)

- `<role_dir>/runtime/continuous-ticket-sentinel-state.json` — machine-readable feed:
  `status` (idle|checking|active|blocked|stalled|error), `active_issue`, `session`,
  `worktree`, `last_heartbeat_at`. **May be absent** when reconcile is disabled
  (`role.yaml` has no `reconcile: {enabled: true}` block) — then Hermes only checkpoints.
- Tail `<role_dir>/runtime/logs/heartbeat.log` and read `<role_dir>/runtime/memories/MEMORY.md`
  ("Recent context") for Hermes' mental model.
- Honor **WIP=1**: if Hermes shows an active worker, do not start a second. If you take a
  ticket, you own the WIP slot until it clears.

## Local truth surfaces (proof, not the board)

- Evidence: `_bmad-output/implementation-artifacts/issue-evidence/<ISSUE>.md`
- Decision/event trail: `_bmad-output/implementation-artifacts/bloodbank-events.jsonl`
- Live workers: `git status`, branches, `git worktree list`, recent commits, zellij sessions.

When the board and the evidence disagree, the evidence wins; post a truth-check comment on
the ticket and keep it open.
