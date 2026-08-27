<!-- GOD-DEPS: 33god-platform,bloodbank,pjangler,krebs,momo,skillex -->

# Skill Dependency Audit: 33GOD Event Journey

## Result

The skill catalog was audited for every package that mentions or owns
Bloodbank, Candystore, Holocene, Plane, n8n, agent dispatch, project identity,
or ticket lifecycle behavior. Direct dependencies now teach the same complete
journey and point back to the relevant component authority instead of carrying
competing pipeline descriptions.

This was a dependency pass, not a blind rewrite of unrelated skills. Generic
tooling and domain-specific pipelines were reviewed and left unchanged when
they neither produce nor consume the 33GOD contracts.

## Inventory reviewed

- 184 packages in the canonical Skillex catalog.
- 67 activated packages in the 33GOD skill topology.
- 21 Skillex packages matched the initial
  `bloodbank|candystore|holocene|plane|n8n` ownership scan.
- Component-local source skills and linked projections were then checked for
  event, command, project-routing, and lifecycle dependencies.

## Updated dependency owners

| Skill package | Source owner | What changed |
|---|---|---|
| `bloodbank-integration` | Bloodbank | Added the canonical end-to-end event/command journey, stream purposes, Plane ingress security, durable-proof checks, command-gateway routing, and retired-path warnings. |
| `delonet-n8n-architecture` | Skillex | Added the exact active Plane workflow, raw-body HMAC contract, per-webhook secret selection, project routing, Candystore proof, and `8477` retirement. |
| `33god-hub` | 33god-platform | Added the cross-component event/command spine, integration boundary map, skill ownership routes, and links to root architecture/diagrams. |
| `agent-fleet-operations` | PJangler | Added command production/consumption, default-deny eligibility, lifecycle-event proof, and the current zero-enabled-route check. |
| `33god-projects` reference | PJangler | Connected `.project.json` project identity to Plane ingress routing and clarified that agent hooks do not each own a competing command consumer. |
| `project-lifecycle` | Krebs | Replaced stale `.plane.json` assumptions with `.project.json.ticket_provider`; documented that Plane mutations automatically emit canonical facts. |
| `task-triage` | Krebs | Replaced the nonexistent `task.inbox.new` trigger with the canonical repo-task event plus `provider_event_type=plane.ticket.created`. |
| `momo` | Momo | Separated automatic Plane lifecycle facts from explicit Momo judgment events and prohibited duplicate ticket-fact emission. |

## Reviewed with no local-contract change

| Skill family | Reason |
|---|---|
| `agent-config-fanout` | Owns topology/fanout mechanics only and already routes event semantics to the owning component skills. |
| `bloodbank-sdk-generation` | Owns schema SDK generation, not a live producer or consumer path. |
| generic `n8n` and `using-n8n-mcp-skills` | Own n8n syntax and tool operation; local webhook IDs, subjects, and secrets belong in the DeLoNET/33GOD integration skill. |
| generic `event-driven-architecture` | Supplies reusable event-design guidance and remains intentionally free of environment-specific 33GOD endpoints. |
| reporting, HeyMa, domain-triage, notebook, AWS, and UI skills | Their mentions describe different pipelines or read models and do not own Plane ingress or Hermes command dispatch. |

## Shared invariants now propagated

1. Events are facts; commands are intent; replies are short-lived request
   correlation, not durable completion evidence.
2. Plane has one public n8n provenance boundary at `/webhook/plane`.
3. HMAC uses the exact raw body and chooses a 1Password reference by
   `webhook_id` before routing.
4. `automaticai` is a Plane tenant identity on personal infrastructure, not a
   separate system boundary.
5. Bloodbank is the contract/transport authority; Candystore is the durable
   history proof; Holocene is a read model.
6. Agent commands are consumed by the durable Hermes gateway and remain
   default-deny until the fleet registry explicitly enables the target.
7. Ticket mutations made through Plane automatically traverse ingress; skills
   must not emit a second copy of the same lifecycle fact.
8. Port `8477`, `.plane.json`, `task.inbox.new`, and Plane use of `/event` are
   retired/stale patterns and must not return.

## Validation

- Every modified skill tree passed Git whitespace/error checks. Five of the
  eight changed skill roots also pass the generic `quick_validate.py` contract.
  The other three report unchanged pre-existing metadata constraints: the
  `agent-fleet-operations` description predates this work at more than 1,024
  characters, while `33god-projects` and `project-lifecycle` use the local
  `pipeline-status` extension that the generic validator does not recognize.
- Krebs workspace detection passed Bash syntax validation and resolved the
  current 33GOD `.project.json` workspace, board, and `plane.delo.sh` base URL.
- The active n8n workflow was reconciled to the committed secure definition.
- Signed and invalid-signature live integration tests both passed.
- The successful event was independently read back from Candystore.
- The root documentation drift gate passed 21 checks with no warnings or
  failures; all 11 focused Compose semantic tests and all four model renders
  passed after reconciling Candystore's `bloodbank.evt.>` durable filter.

The broader Skillex `topology:check` remains red with 173 existing
catalog-link/composition/pack findings in the repository's current migration
state. It reports zero findings for the only Skillex catalog package changed by
this pass, `all-skills/delonet-n8n-architecture`; unrelated topology migration
was not rewritten as part of the event-journey update.

The broader platform-registry validator also retains one unrelated existing
failure: `components/heyma.yaml` declares
`/home/delorenj/code/HeyMa/compose.yml`, but that optional component checkout
currently has no Compose file. The event/command core and its focused gates do
not consume that path.
