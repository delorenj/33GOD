# G5 — independent PM review handoff

**Implementer:** delegated G5 worker. **Reviewer:** PM, independent of worker.
**State:** pending; do not merge or report recipient acceptance before review.

## Review prompt

Conduct an independent review of all files in
`33god-platform/aperture/groups/g5/` on branch `aperture/g5-tooling`.
Inspect the changed content directly. Look for missing acceptance and misleading
claims, not only syntax errors. Compute a finding floor from change size:
`N = min(floor(sqrt(kB) + 1), 10)`; state arithmetic and seek at least N findings.
Do not invent problems merely to meet the floor. Return findings with exact
paths/lines and reproducible evidence; separate artifact acceptance from the
broader real-project gate.

Specifically:

1. Read the binding charter and root run-only/no-fake-server directive.
2. Verify package/runtime evidence against actual source. PJangler is Node,
   not Python, and both Node packages require >=24. Exactly one MCP server
   directory exists in the inspected checkout; no second was fabricated.
3. Export source contexts from your machine and run `smoke/smoke.sh`. It builds
   all three native images; examine actual initialize/tools-list/EOF, non-root,
   container port inspection, immutable multiarch manifests, and full-tree scan.
4. Independently compare source Git status before/after; preserve pre-existing
   dirty state. Do not bootstrap anything in source checkouts.
5. Inspect Dockerfiles for copied host config, service wrappers, detachment,
   listener commands or hidden ports. CommonProject must remain a read-only
   template mount and Skillex's catalog must remain a separately owned registry
   artifact. Source SSE capability is not enabled or deployed by this group.
6. Read every deferral. No CLI help, manifest listing, or successful initialize
   proves full provisioning, a semantic result, publication, or arm64 execution.
7. Rerun the upstream MCP tests from PROOF.md; broader Node test suites were
   not run by this worker. Record review findings and acceptance independently.

Do not merge from this prompt without completing the charter's review gate.
The worker runtime has no subagent-launch capability; the independent blind
review layer is handed to the explicitly designated PM rather than fabricated.
