# I-11 brownfield evidence and ownership

Inspected 2026-11-11 EST / 2026-11-12 UTC by 33god-pm. Source evidence, not runtime activation proof. Preserve unrelated working-tree changes.

## Existing building blocks

| Owner / revision inspected | Evidence | Reuse and limit |
|---|---|---|
| HeyMa `2594c85b4500d2ec7fe5473d87a8ca42a9b0c3a4` | `~/HeyMa/components/wax/config/passes.d/bin/project-extraction` lines 64–74, 115–145, 159–203; matching YAML | Already uses independent `noul` questions for every eligible project, one request when size permits, thresholds .60/.75 above 30K chars, max eight accepted. Comments report historical jitter +/- .06 and measured mention accuracy; neither was remeasured here. Preserve existing documents/no-clobber behavior. |
| HeyMa registry adapter | `components/wax/src/wax/pjregistry.py` lines 17–22, 81–149; `config/project-aliases.yaml` | Compact registry candidates + provisional spoken aliases/about hints. Failure is failure, never empty candidates. Do not copy a full registry to a model; it can contain a secrets block. A portable classifier contract needs owner extraction, not copying this script into a profile. |
| Bloodbank `6364fdd6151fcba63cdd90561d96f1977d905690` | `services/hook-hub/{hub.py,handlers.toml,concerns.py,README.md}`; `services/agent-hooks/hooks.master.json` and `clients/hermes.py` | Canonical role mapping, sync context, async behavior, durable metadata receipts/outbox and one publisher already exist. Handler selection is ordered. Existing skill reminder order is 0; simply adding a later row cannot claim before-skills routing. Hermes has native skill instructions, not the generic reminder. |
| Bloodbank native limitations | `clients/hermes.py` lines 52–60, 121–150; `hook-hub/concerns.py:context_output` | Hermes pre_llm_call maps to turn-start context and can repeat. Hermes consumes JSON `context`, not arbitrary stdout; other CLIs have different native formats. Must prove true-user-turn dedupe and prompt consumption in the actual host. Antigravity lacks a normal prompt-submit/pre-tool surface. |
| Bloodbank contract | `docs/event-naming.md` §§2–3.2; `schemas/bloodbank/agent/invocation.start.json` | Type is four tokens; transport subject adds kind. Existing batch invocation uses `data.target_agent_id`; PM planning is batch, not interactive reserved lane. No new awareness event vocabulary selected/published here. |
| PJangler `a460076c401e781cdceaacb74d7bc856d33b249e` | `src/project/index.ts:245–268`, canonical manifests; read-only `pj list --json` and `GET localhost:8764/v1/registry` | 53 projects in current snapshot. Declared project/board bindings exist. Inspected interface/snapshots do not demonstrate typed responsibility, alias or cross-project contract dependencies. Recipe `dependencies` are build/bootstrap relationships, not product consumer edges. Unknown fields do not make an enforced dependency contract. |
| Flume `19f4c862e044083f91b29fd6cb97aed8528c7af8` | `~/.hermes/agents-registry.yaml` selected fields + manifests | Eligible `bloodbank-pm`, `pjangler-pm`, `flume-pm`, `heyma-pm`, `voxxy-pm` declare fleet scope, enabled true and matching target/profile. This is routing eligibility, not proof their new planning turn executed. Flume owns named responsibility/subscription declarations; project agents are a projection, not another roster. |
| Candystore | Existing Bloodbank event-history path | Reuse durable event lookup. No Candystore change is presumed; open owner request only if schema/readback needs cannot be served. |

## Pilot identity and dependency

- **Provider:** user-facing Vox/Voxxy is registered project **`voxxy`**, checkout `~/code/voxxy`, board **VOXXY**, PM **`voxxy-pm`**. `voxxy/.project.json` and README agree; inspected head `0c6e020757ef6c7a2136d574ab82038c25543936`. `~/code/vox` is not evidence of a second registered provider.
- **Consumer:** canonical project **`phonograph`**, checkout `~/code/phonograph`, board **PHONOGRAPH**. Manifest's `project_name` still says `dubplate`; `renamed_from` records `dubplate`/DUBP. AGENTS.md confirms current IntelliForia product name, legacy compatibility imports/deployment identities and Vinyl as the separate speech core. Inspected head `22ad6bae56ca544896e889a81ae393aa871204c1`.
- **Source-proven dependency:** `phonograph/hooks.py` defaults Vox URL to `https://vox.delo.sh` (line 44); `VoiceCatalog._fetch` calls `GET /voices` (lines 294–328); synthesis posts `/synthesize` and reads `X-Vox-Engine` and `X-Vox-Voice-Source` (lines 429–461). Voice ID/catalog shape, synthesis payload/response and voice-source semantics are actual affected contracts, not mere audio-topic similarity.
- **Unproven:** live service compatibility and runtime-selected endpoint were not exercised; no synthesis or playback requested. No typed PJangler dependency edge was found in inspected metadata. Source evidence is input for owner-confirmed declaration, not an invented installed graph.
- **Receiver gap:** Phonograph manifest has `agents: {}` and no matching eligible fleet agent was found. A PHONOGRAPH backlog ticket alone would not reach an enrolled PM. Flume's planning intake must return a real designated receiver or precise enrollment gap, not silently invent `phonograph-pm`, reuse HeyMa PM, or hire an agent during this pass.

## Overlap and boundaries

- Root initiatives I-1/I-4 own workforce/routing foundations and g33 ecosystem consultation. Reuse them; the g33 route helper returned Bloodbank/PJangler entrypoints but is not a runtime semantic classifier.
- I-9's existing untracked `spec-i9-agent-message-owner-handoff` is native incarnation-safe crank input/Fleet contract planning. It does not solve ownership inference; no modification or duplicate native-message worker here. FLUME-76/77 and PJAN-204 remain separate.
- FLUME-6 and FLUME-7 are old mailroom contract/router proposals. Their bodies use legacy `corp.mail.*` names; they are historical requirements, not authorized current event schemas. Ask Flume to reconcile overlap; Bloodbank owns any canonical transport contract. No competing mailroom.
- Title-filtered readback covered root 79, BB 35, PJAN 201, FLUME 82, HEYMA 12, VOXXY 1, PHONOGRAPH 37 returned tickets. This bounded check found no exact awareness initiative; it is not exhaustive body/history search. Owner planning must check again before adding implementation stories.
- Hermes Fleet has a known separate enrollment/intake gap documented under I-9. This initiative does not reopen it or grant Flume Fleet code ownership. First use a supported hook surface; request native runtime changes only through a verified owner.

## Tooling observations

`codegraph-voyage status` found 15,427 fake embeddings of 15,437 total. No semantic results were used and no index/purge was run. Notebook status/audit found Overview `.project.json: reference-changed` and two older possibly-dispatched note actions. No repair or retry of those unrelated actions was made. Planning files are canonical repo artifacts; notebook delivery is a separate scoped operation, never an implied repair.
