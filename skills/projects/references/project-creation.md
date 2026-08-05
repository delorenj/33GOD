---
pipeline-status:
  - new
---
# Project Creation via pjangler

The deployer is **pjangler** (`~/code/pjangler`, installed as `pjangler` on PATH; engine at
`~/.local/libexec/pjangler-engine`). It vendors both templates as submodules under
`~/code/pjangler/templates/` and version-locks against them.

## 1. Bootstrap the repo from CommonProject

CommonProject is a copier template with an interactive wizard. From a CommonProject checkout
(or the vendored `~/code/pjangler/templates/commonproject`):

```bash
mise run init-project              # interactive: name, description, identifier, provider
# or non-interactive:
mise run init-project-non-interactive
```

`init-project.sh` does, in order:
1. Gathers project name/description/identifier/workspace (+ ticket provider, default `plane`).
2. Creates the ONE repo ticket board via `create-plane-project.sh` — named after the
   **project name with no role suffix**, identifier = `slug[:4]` uppercased. On 400/409 it
   resolves the existing board by identifier instead of failing.
3. Runs `copier copy gh:delorenj/CommonProject` with all answers, rendering the skeleton.
4. Installs BMAD (see [bmad-init.md](bmad-init.md)).

**Result — `.project.json` (the SOT):**
```json
{
  "project_name": "Drumjangler", "project_description": "...", "project_slug": "drumjangler",
  "repo_path": "/home/delorenj/code/drumjangler",
  "ticket_provider": { "type": "plane", "workspace": "33god", "identifier": "DRUM",
    "board_id": "<uuid>", "board_url": "https://plane.delo.sh/33god/projects/<uuid>/issues/" },
  "agents": {}
}
```
There is **no** `.plane.json` — board binding lives only in `.project.json.ticket_provider`.
`repo_path` is stamped by a post-gen task; `agents` is filled as agents are provisioned.

## 2. Provision a Hermes Project Manager (PM)

```bash
cd <repo>
pjangler hermes-agent          # interactive TUI
```

The recipe (`HermesAgentRecipe`) chain:
`EnsureTemplateConfig → PromptForAgentConfig → RunCopierTemplate → WireTelegram → WireEmail → PrintHermesSummary`.

`PromptForAgentConfig` asks:
- **Role** (select): *Project Manager (pm)* / *Scrum Master (Ticket Sentinel)* / dev / review / ops / qa.
- **Ticket board provider** (select): defaults to the repo's existing `.project.json` provider.
- **Also provision the paired Scrum Master?** (confirm, **pm only**) — provisions the
  companion sentinel in the same run (see §3).
- purpose, soul tone, model overrides, Telegram/email wiring.

It renders `agents/hermes/pm/` (role.yaml, SOUL.md, `hermes` wrapper, `.scripts/`, runtime
submodule). `42-ticket-provider.sh` **binds the PM to the board already in `.project.json`**
— it does not create a `"<Repo> PM"` board. If the repo has no board yet, it bootstraps one
repo-named board and writes it back to `.project.json`. The agent is added to
`.project.json.agents` and the binding mirrored into `role.yaml` for back-compat.

Non-interactive: `pjangler hermes-agent --yes` (accepts defaults, provider inherited from
`.project.json`, skips Telegram/email).

### Inherited profile config

New 33god Hermes agents use opt-in inherited config instead of cloned
standalone config. pjangler creates a named profile such as
`~/.hermes/profiles/drumjangler-pm`, points it at
`agents/hermes/pm/runtime/`, and writes this metadata into
`runtime/profile.yaml`:

```yaml
config:
  inherit_from: default
  save_mode: delta
```

This keeps the common, non-secret settings in the fleet default
`~/.hermes/config.yaml`. A practical example: when the operator changes the
default model from one OpenAI model to another, the PM and Ticket Sentinel pick
up the new model automatically. If a repo agent only needs a local working
directory, its `runtime/config.yaml` can stay as small as:

```yaml
terminal:
  cwd: /home/delorenj/code/drumjangler
```

Only `config.yaml` inherits. API keys, Telegram tokens, SOUL, memories,
sessions, skills, gateway state, cron, and runtime files remain profile-local
inside the runtime repo. Treat inherited config as maintenance convenience, not
as a security boundary.

## 3. The Ticket Sentinel (folded into the PM heartbeat)

There is **no separate scrum-master role** — it was retired in the unified
single-PM model (June 2026). The sentinel duties (board reconciliation,
evidence checks, worker-state supervision through the provider-agnostic
adapter `lib/ticket-provider.sh` + `providers/{plane,linear,trello}.sh`) run
**inside the PM's heartbeat**: `hermes-<agent_id>-heartbeat.timer` fires
`.scripts/heartbeat.sh` (~1-min cadence), which runs the sentinel pass
out-of-band when `role.yaml` `reconcile.enabled: true` and otherwise ticks
checkpoint-only. Provisioning the PM installs everything; there is nothing
extra to provision.

Per-agent systemd units are ONLY the gateway service and the heartbeat timer.
Bloodbank command ingress is the single fleet-shared
`hermes-fleet-bloodbank-gateway.service` — never a per-agent consumer. Drift is
converged with `pj migrate hermes.registry-parity`.

## Where the templates live

- pjangler resolution order for the hermes template: `PJANGLER_HERMES_TEMPLATE` env →
  vendored `templates/hermes-agent` → `~/code/33GOD/hermes-agent-template` → `gh:delorenj/hermes-agent-template`.
- For live template development, point `PJANGLER_HERMES_TEMPLATE=~/code/33GOD/hermes-agent-template`;
  otherwise the vendored submodule (version-locked) is used. After pushing template changes,
  bump the submodule pointer: `git -C ~/code/33GOD/pjangler submodule update --remote`.
