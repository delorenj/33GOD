# Damian's skills: decision menu for Jarad

Read-only research. I changed nothing on the Mac or in git.

## 1. The decision

**Pick the one global skill set for Damian's Mac: A (mirror you), B (lean core, recommended) or C (core plus design and full BMAD).**

All six desks have `inherit_global: true` and no skills of their own. Under the 2026-10-27 rule, global is the floor every desk gets, so this one choice sets what all six receive. That includes `private-desk` and `aai-team`, which are conversational or intake-only.

## Facts behind the menu

- **Mac selection today.** `~/.agents/skills.json` on the Mac is an older copy of yours: the `bmad@6.12.1-next.1` pack plus 71 skills.
  - It lacks 7 of yours: `33god-features`, `artifacts`, `heyma`, `interval-driver`, `krebs`, `pillars`, `stitch`.
  - It adds 7 of its own: `coaching-practice-catalog`, `org-chart`, `momo`, `wax-pipeline`, `create-enrichment-pass`, `html-artifact-delivery`, `delegate-to-rere`.
- **Mac skill links.** The Mac's `~/.agents/skills` has 127 entries: 64 resolve, 50 are broken, 13 are real directories.
  - The 50 broken are the 47 `bmad-*` plus `delonet-conventions`, `delonet-daily-report` and `delonet-dotenv`.
  - They break because the Mac catalog (`all-skills` at `c281845`, 341 skills) predates them. Your catalog has 457 and upstream `delorenj/skills` is at `ec902ce`.
  - The 13 real directories are Stripe, `connect-*`, `metronome`, `synced` and `source-command-*`. Skillex does not own them and I left them out of every option.
- **Damian-only skills.** Some skills exist only in the Mac catalog: `coaching-practice-catalog`, `org-chart`, `ep133-music-lab`, `mission-control-reporter`, `obsidian-vault-management` and a few more. So the Mac catalog cannot be replaced wholesale. It can only be topped up.
- **Damian uses BMAD.** `_bmad` exists in `hello-subconscious-team-inbox`, `Music Lab`, `pjangler-learning-lab` and `33GOD`.
- **What was read on the Mac.** Counts are from `~/.codex` and `~/.claude` session logs and mostly reflect Rererere-driven sessions, not Damian typing.
  - `delegate-to-rere` 58, `candystore-context` 33, `33god-hub` 21, `agent-fleet-operations` 18, `worktrunk` 16, `candybar` 16, `hindsight` 14, `pilot` 9.
  - `wax-pipeline`, `create-enrichment-pass` and `html-artifact-delivery` were read 7-8 times each.
  - `bmad-build` 6 and `bmad-brainstorming` 4 are the only BMAD hits.
- **Live resync state (2026-11-15 13:19 EST).** The resync is at run 66 since its last restart, exit 1.
  - All 6 desks now report `error: no recorded project`, meaning the receipt is missing. This started 2026-11-14 ~20:29 EST, which differs from the W1-3 diagnosis (bmad `E_SKILL_MISSING`).
  - Two repairs are needed: catalog top-up, then `profile sync` per desk.
  - Each desk's own project root is `~/.hermes/profiles/<desk>/.skillex-selection`. It exists for `aai-team` and `private-desk`.

## 2. Three options

| | **A. Mirror Jarad** | **B. Lean core (recommended)** | **C. Core + design + full BMAD** |
|---|---|---|---|
| Composition | Your 71 skills minus `delohome`, `delonet-parental-controls`, `liam-dev`, plus Damian's `coaching-practice-catalog`, `org-chart`, `momo`, plus the full bmad pack (47) | 45 individual skills plus a 14-skill BMAD subset. No pack. | B without the BMAD subset, plus 6 design skills (`impeccable`, `design-md`, `canvas-design`, `shadcn-components`, `spa-host`, `stitch`), plus the full bmad pack (47) |
| Count | 118 (68 + 47 + 3) | 59 | 98 (51 + 47) |
| Imports into the Mac catalog | 57 | 17 | 51 |
| Gains | Identical to you, including BMAD CIS coaches and loop tooling | Every skill resolves and works on macOS. Plan-critical skills are present. Light for `private-desk` and `aai-team`. | Design work and the whole BMAD toolkit. Everything works on macOS. |
| Loses / risk | 14 skills useless or wrong on a Mac: `kapture`, `agent-workspace-linux`, `zellij-workspace-ops`, `ebook-to-audiobook`, `vox-tts`, `vox-voice-persona`, `monitoring-stack`, `ego-browser`, `computer-use`, `artifacts` (publishes to your MinIO), `heyma`, `krebs`, `pillars`, `interval-driver`. Heaviest skill index in every desk turn. | The 33 other BMAD skills (CIS coaches, `bmad-loop-*`, testarch and so on). No design or UI skills. | Heavier than B for every desk. No `krebs` or `pillars`, as in B. |

All three drop the 3 Jarad-only skills named in section 4, plus the Jarad-only extras listed there.

**B contents (59).**
- **Mirror, ops and plan-critical (14).** `delonet-dotenv`, `delonet-conventions`, `delonet-daily-report`, `activity-report`, `candybar`, `bloodbank-integration`, `automaticai-provider-gateway`, `hindsight`, `candystore-context`, `skillex-skill-registry`, `agent-config-fanout`, `agent-fleet-operations`, `hermes-pm-template-maintenance`, `33god-hub`.
- **Boards (7).** `pilot`, `project-lifecycle`, `project-jangler`, `projects`, `project-notebook`, `momo`, `board-taxonomy`.
- **Dev hygiene (16).** `merge-forward`, `worktrunk`, `code-reviewer`, `pr-creator`, `subagent-driven-development`, `detached-worker-completion`, `gitignore-maintenance`, `mise-configuration`, `mise-tasks`, `mise-versioning`, `find-skills`, `skill-maintenance`, `recap`, `mental-model-jotting`, `codegraph-voyage`, `web-search`.
- **Writing (6).** `antislop`, `antislop-code`, `antislop-copywriting`, `antislop-human`, `antislop-ui`, `humanizer`.
- **Damian's own (2).** `coaching-practice-catalog`, `org-chart`.
- **BMAD subset (14).** `bmad-help`, `bmad-agent-pm`, `bmad-agent-dev`, `bmad-agent-architect`, `bmad-product-brief`, `bmad-prd`, `bmad-create-epics-and-stories`, `bmad-sprint-planning`, `bmad-code-review`, `bmad-brainstorming`, `bmad-correct-course`, `bmad-retrospective`, `bmad-build`, `bmad-party-mode`.

**Optional add-ons, each one line to add to B:**
- `krebs`: only if Damian's PM desks run Plane lanes.
- `heyma`, `wax-pipeline`, `create-enrichment-pass`: only once I-6.2 puts HeyMa on the Mac. The last two are stubs pointing at `~/HeyMa`.
- `disk-space-maintenance`: it has macOS profiles.
- `hermes-project-avatar`: Telegram avatars from project branding.
- `ep133-music-lab`: skipped, since Music Lab is not important.

**Recommendation: B.**
- It is the smallest set that satisfies the plan (W0-5 resolver, W9 report, Candybar, Bloodbank) and Damian's BMAD repos.
- Everything resolves on macOS.
- It keeps the union floor small for the conversational desks.
- It needs 17 imports instead of 57.
- Upgrading from B to C later is a single edit to the selection.

## 3. Per-desk needs and recommended default

All six default to global-only (the B set) and no extra skills.

| Desk | Role | Needs | Recommended default |
|---|---|---|---|
| `aai-team` | Conversational company coordination for Damian and Jarad. No shell, filesystem or browser. | Nothing beyond global. | Global-only. Receipt repair: `profile sync aai-team --project ~/.hermes/profiles/aai-team/.skillex-selection --skillex-only`. |
| `hello-subconscious-team-inbox-team-inbox` | Cruise Control, Damian and Lilian coordination. Live gateway on `:8642`, Damian's own. | Global, plus `coaching-practice-catalog` and `org-chart`, which are already in B. | The blocker is not a skill choice: it has an unowned `.hub` entry and 12 dangling runtime links. Preview `hermes-skillex-cutover.py` only. Apply it with your go, because it is a live Damian service. |
| `lamp-ops-task-agent-team-inbox` | Flume-placeholder SOUL, 0 skills, no receipt. `lamp-skills` stays stopped. | Nothing. | Global-only with its own `.skillex-selection` as the project root, created by `skillex init`. If you would rather not run it, ask Damian to park it. |
| `music-lab-pm` | Music Lab PM. | Nothing. `~/code/Music Lab` exists again, so `E_PROJECT_ROOT` is stale. | Global-only: `profile sync music-lab-pm --project "~/code/Music Lab" --skillex-only`. No music skills, per your note. |
| `private-desk` | Damian's private intake and sorting. Approved folders only, model via the AAI gateway. | `domain-triage` and `hindsight`, plus the global set. `domain-triage` is already in global; B does not select it, so I would add it to B. | Global-only. Receipt repair with project `~/.hermes/profiles/private-desk/.skillex-selection`. |
| `space-owner` | Flume-placeholder SOUL, workspace `~/code/space`. | Nothing identified. | Global-only. The project root is my guess (`~/code/space`) and is unconfirmed. |

## 4. Jarad-only skills to exclude

Hard exclusions, in every option:

- `delohome`: Hue, Z-Wave and Chromecast control of the DeLorenzo house.
- `delonet-parental-controls`: your AdGuard and Netgear RS700 enforcement.
- `liam-dev`: your Kapture fork (`~/code/liam`, `@delorenj/liam`).
- `delegate-to-rere`: delegates to Rererere, who is your agent. Damian has no Rererere to delegate to. Its 58 reads on the Mac came from your driver sessions.

Also out of B, with reasons:

- `artifacts`: publishes to your MinIO at `s3.delo.sh`. Wait on the W10-2 opt-in.
- `pillars`: your personal decision criteria. The Mac has no `~/.agents/PILLARS.md`.
- `33god-features` and `interval-driver`: your I-9 migration rules and crank-beat tooling.
- `automaticai-provider-gateway-lazy-migration-strategy`: your gateway migration notes.
- `kapture`: your Linux browser tool, with the server on `127.0.0.1:61822`.
- `ego-browser`: points at your Mac browser.
- `agent-workspace-linux` and `zellij-workspace-ops`: Linux and your zellij setup.
- `monitoring-stack`: retired with G4.
- `ebook-to-audiobook`, `vox-tts`, `vox-voice-persona`: voxxy on your RTX 3090 (`vox.delo.sh`). The Mac has no voxxy.
- `heyma`, `wax-pipeline`, `create-enrichment-pass`: there is no Mac install of HeyMa, Wax or Vinyl.
- `html-artifact-delivery`: superseded by `artifacts`.

`delonet-conventions` stays in B but contains your LAN specifics. W9-1 should genericize it.

## 5. What gets applied once you pick

Prerequisites on the Mac:
- Do not touch the dirty `~/code/skillex` tree. The Mac skillex CLI (0.3.1+d20578c) has no `skill import URL`, only `skill import <local path>`.
- `~/.agents` on the Mac is a checkout of `delorenj/agents`, where `skills.json` is tracked and already locally modified. Never commit or push it from the Mac, or it overwrites yours.
- The Mac `all-skills` git remote read as `delorenj/00_ceiling` for me. Verify before any git operation there.

**Steps for B** (A and C use the same steps with a different file and import list):

1. Clone upstream at `ec902ce` into a dir outside every discovery root. Damian's `gh` has READ on the public `delorenj/skills`.
   - `git clone https://github.com/delorenj/skills ~/33god-migration/2026-11-15/skills-upstream`
2. Import only the names missing from the Mac catalog. For B that is 17: `delonet-dotenv`, `delonet-conventions`, `delonet-daily-report`, and the 14 BMAD subset names.
   - For each name: `skillex skill import ~/33god-migration/2026-11-15/skills-upstream/<name> --name <name> --dry-run`, then the same without `--dry-run`.
   - Imports only add new definitions and overwrite nothing.
3. Write `~/.agents/skills.json` on the Mac with this content (59 skills):

```json
{"$schema":"https://raw.githubusercontent.com/delorenj/skillex/main/skills.schema.json","scope":"global","packs":[],"skills":["33god-hub","activity-report","agent-config-fanout","agent-fleet-operations","antislop","antislop-code","antislop-copywriting","antislop-human","antislop-ui","automaticai-provider-gateway","bloodbank-integration","bmad-agent-architect","bmad-agent-dev","bmad-agent-pm","bmad-brainstorming","bmad-build","bmad-code-review","bmad-correct-course","bmad-create-epics-and-stories","bmad-help","bmad-party-mode","bmad-prd","bmad-product-brief","bmad-retrospective","bmad-sprint-planning","board-taxonomy","candybar","candystore-context","coaching-practice-catalog","code-reviewer","codegraph-voyage","delonet-conventions","delonet-daily-report","delonet-dotenv","detached-worker-completion","find-skills","gitignore-maintenance","hermes-pm-template-maintenance","hindsight","humanizer","mental-model-jotting","merge-forward","mise-configuration","mise-tasks","mise-versioning","momo","org-chart","pilot","pr-creator","project-jangler","project-lifecycle","project-notebook","projects","recap","skill-maintenance","skillex-skill-registry","subagent-driven-development","web-search","worktrunk"]}
```

   If you accept my `domain-triage` suggestion for `private-desk`, add it to this list (it is in the Mac catalog). Then `domain-triage` is added and the count is 60.

4. Preview: `skillex sync --scope global --dry-run --json`. Inspect adds, removals and foreign entries before applying. The expected removals are the 33 unselected BMAD links and the dropped Jarad-only links.
5. Apply `skillex sync --scope global`. Run the preview again and expect no managed changes.
6. For each desk, run `skillex profile sync <desk> --project <root> --skillex-only --dry-run --json`, then the same without `--dry-run`. Use the roots in section 3, skip the team-inbox desk, and confirm with `skillex profile show <desk>` returning exit 0.
7. Run `launchctl kickstart gui/501/io.33god.skillex-hermes-resync` and read `~/.local/state/skillex/hermes-resync.last.json`.
   - Expect `exit 0` for everything except the team-inbox desk until the cutover is approved.
   - Moving the resync to Candybar is W5-4 and stays separate.

Option A selection is Jarad's current `skills.json` minus the 3 hard exclusions, plus `coaching-practice-catalog`, `org-chart` and `momo`, with `packs: ["bmad@6.12.1-next.1"]`. Option C is the B file with the 14 BMAD names removed, `packs: ["bmad@6.12.1-next.1"]`, and the 6 design skills added.

## Needs Jarad

- Pick A, B or C.
- Add-ons: `krebs`, `heyma` and friends, `domain-triage`.
- Confirm the project roots for `lamp-ops` and `space-owner`.
- Go or no-go on the team-inbox desk cutover.

## Side finding for task 6

On the Mac, `~/.claude/skills`, `~/.codex/skills` and `~/.kimi/skills` already alias `~/.agents/skills`. I did not check Codex desktop, Claude desktop or the hooks.