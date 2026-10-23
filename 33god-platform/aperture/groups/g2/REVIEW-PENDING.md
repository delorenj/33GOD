# Independent review pending — do not merge without PM review

This worker cannot spawn review agents in this runtime. Grolf/parent PM is the
independent review gate required by the charter. Host smoke/unit tests are
implementer evidence, not a review approval or Damian deployment acceptance.

## Context-free reviewer prompt

Conduct a review of the changes on branch `aperture/g2-bundle` versus `main` in
`33god-platform/aperture/groups/g2/`, plus its platform changelog entry.
Inspect the changed files directly, not only the handoff summary.
Look for what is missing, not only what is wrong. Compute N =
min(floor(sqrt(changed kB) + 1), 10); state the arithmetic and identify at least
N concrete issues to fix or improve. Return a Markdown list of findings with
file/line evidence. Do not invoke skills or spawn further reviewers.

Specifically test fresh boot/import idempotence, no credential/workflow export,
header rejection, JetStream persistence versus HTTP acknowledgment, per-image
arm64/amd64 verification, total memory caps, no host ports, no production mounts,
curator deferral honesty, Plane template fail-closed status, and teardown scope.
Execute `docker compose config -q`, outbox unit tests and `bash smoke/smoke.sh`
against isolated `god-g2` resources only. Never access production n8n, its DB,
exports or credentials. Distinguish manifest support from arm64 runtime proof.

No independent review result is claimed in this artifact.
