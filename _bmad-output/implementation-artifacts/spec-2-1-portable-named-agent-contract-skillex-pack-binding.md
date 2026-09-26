---
title: 'Story 2.1: Portable Named Agent Contract & Skillex Pack Binding'
type: 'feature'
created: '2026-09-26'
status: 'draft'
route: 'dispatch'
review_loop_iteration: 0
context:
  - _bmad-output/implementation-artifacts/epic-2-context.md
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Current workforce agents are tightly coupled to repository checkouts (e.g. `<repo>/agents/hermes/pm`), forcing skills to live in repo `.agents/skills` and preventing the creation of portable, role-bound specialist agents that travel anywhere with their own memory and capabilities.

**Approach:** Define a canonical schema and contract for repo-independent named agents that decouples identity and charter from repositories, binds curated skills through reference-only Skillex packs (`~/code/skillex/packs/` adhering to ADR-0001), and materializes a portable desk (`~/.agents/workforce/<name>/`) with verified skill symlinks and traveling Hindsight memory (`agent-<name>`).

## Boundaries & Constraints

**Always:**
- Follow Skillex ADR-0001 reference-only topology: canonical skill definitions live strictly in `~/code/skillex/all-skills/`, and packs contain references only.
- The agent's desk directory (`~/.agents/workforce/<name>/`) provides compiled `.agents/skills` symlinks pointing to canonical skills, never unmanaged file copies.
- Named agent definitions must be completely valid without requiring `repo` or `project_path`.
- Memory bank binding must be explicitly configured as `agent-<name>` to ensure personal memory travels across invocation contexts.
- Provide deterministic schema validation for named agent contracts.

**Never:**
- Never copy `SKILL.md` or tool payloads into packs or desk directories.
- Never modify or break existing repo-bound Hermes PM scaffolds (`agents/hermes/pm`).
- Never write plaintext secrets or credentials into agent definitions or desk files.
- Never bypass Skillex catalog ownership when resolving skill references.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Valid Named Agent Definition | YAML file defining `id`, `role`, `display_name`, `charter`, `skills.pack`, and `memory.write_bank` | Successfully passes validation; resolves desk path and pack mapping | N/A |
| Missing Required Field | Definition omitting `id`, `role`, or `memory.write_bank` | Validation fails with clear field error report | Throws schema validation error identifying missing key |
| Unresolved Canonical Skill | Agent pack references skill not present in `~/code/skillex/all-skills/` | Validation / resolution detects missing canonical target | Fails with missing skill diagnostic and Skillex catalog path |
| Desk Materialization | Valid agent definition and target desk directory `~/.agents/workforce/<name>/` | Creates directory structure and materializes `.agents/skills` symlinks | Reports filesystem creation error if permission denied |
| Idempotent Re-provisioning | Desk directory already exists with existing symlinks | Reconciles symlinks to match current pack without deleting user notes | Logs updated/preserved symlink counts |

</frozen-after-approval>

## Code Map

- `flume/contracts/handbook.yaml` -- Authority declarations and fleet service model contract.
- `flume/contracts/named-agent.schema.json` -- JSON Schema defining the portable named agent specification.
- `flume/packages/flume-hr/src/workforce/types.ts` -- TypeScript interfaces for named agent contracts, charters, and desks.
- `flume/packages/flume-hr/src/workforce/validator.ts` -- Validator checking definitions against `named-agent.schema.json`.
- `flume/packages/flume-hr/src/workforce/desk.ts` -- Desk provisioner managing `~/.agents/workforce/<name>/` and `.agents/skills` symlinks.
- `flume/packages/flume-hr/src/index.ts` -- Module exports exposing workforce types and functions.
- `flume/tests/named-agent-contract-regressions.ts` -- Regression tests verifying schema validation and desk symlink materialization.
- `~/code/skillex/packs/` -- Destination for reference-only agent skill packs.

## Tasks & Acceptance

**Execution:**
- [ ] `flume/contracts/named-agent.schema.json` -- Create schema -- Author JSON Schema for portable named agents declaring id, display_name, role, charter, skills, memory, and desk attributes.
- [ ] `flume/packages/flume-hr/src/workforce/types.ts` -- TypeScript declarations -- Define NamedAgentContract, AgentCharter, AgentSkillsBinding, and AgentDeskManifest interfaces.
- [ ] `flume/packages/flume-hr/src/workforce/validator.ts` -- Validation logic -- Implement schema validator parsing YAML/JSON named agent definitions.
- [ ] `flume/packages/flume-hr/src/workforce/desk.ts` -- Desk provisioner -- Implement function to materialize desk directory and compile `.agents/skills` symlinks from Skillex pack.
- [ ] `flume/packages/flume-hr/src/index.ts` -- Export workforce API -- Re-export workforce types, validator, and desk manager from package entry point.
- [ ] `flume/tests/named-agent-contract-regressions.ts` -- Regression test suite -- Add tests for valid agent parsing, invalid schema rejection, and desk symlink reconciliation.

**Acceptance Criteria:**
- Given a valid named agent definition without `repo` or `project_path`, when validated, then it passes schema validation and parses identity, charter, and memory settings.
- Given an agent declaration with a Skillex pack reference, when resolving skills, then all symlinks point to canonical targets in `~/code/skillex/all-skills/`.
- Given an agent desk path `~/.agents/workforce/<name>/`, when provisioned, then `.agents/skills` contains verified symlinks for each declared skill.
- Given an agent definition referencing a non-existent canonical skill, when validated, then an explicit diagnostic error identifies the missing skill.

## Implementation Notes

## Spec Change Log

## Review Triage Log

## Design Notes

The named agent definition uses YAML for human readability and version control:

```yaml
schema_version: 1
id: n8n-specialist
display_name: "N8N Workflow Specialist"
role: workflow-specialist
charter:
  purpose: "Design and maintain high-reliability n8n workflows following homelab conventions."
  directives:
    - "Prefer built-in nodes over code nodes unless transformations require custom libraries."
    - "Expose minimal required fields in intermediate node outputs."
  tone: direct
skills:
  pack: agent-n8n
memory:
  write_bank: agent-n8n-specialist
  recall_banks:
    - agent-n8n-specialist
desk:
  path: "~/.agents/workforce/n8n-specialist"
```
