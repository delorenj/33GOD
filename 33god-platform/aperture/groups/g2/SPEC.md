---
title: Aperture G2 isolated integration-plane bundle
type: feature
created: '2026-10-23'
status: in-review
route: oneshot
review_loop_iteration: 0
---

<frozen-after-approval reason="delegated implementation intent">

## Intent

Provide a self-contained `god-g2` Compose bundle under this directory: n8n,
Postgres, fresh sanitized workflows and a documented curator deferral if the
host implementation cannot be made portable without expanding scope. Prove a
synthetic webhook → CloudEvent → isolated NATS round trip on this host. Inspect
every external image manifest for linux/arm64 and linux/amd64; do not claim
arm64 runtime acceptance from an amd64 run. No host ports, production mounts,
custom nodes, live credentials or copied workflow exports. Keep total configured
memory below 2.5 GiB. Push `aperture/g2-bundle`, do not merge; parent PM reviews.

</frozen-after-approval>

## Implementation Notes

- Charter v1.0 read before work; session marker created in isolated worktree.
- G1 conventions inspected: `name: god-g2`, GOD_* configuration, owned g2-* networks/volumes, no published ports.
- g33 preflight PASS (legacy execution WARN). Routing heuristic selected unrelated execution/UI routes; explicit platform composition ownership controls this task.
- CodeGraph query blocked by mixed fake/real model indexes; index left untouched. Direct source inspection used instead.
- Host terminal tool returned empty output even for `pwd`; verified that no commands executed through that login-shell path. Execution uses Python subprocess with explicit environment and captures real exit codes/stdout/stderr.
- Curator source is a DeLoDocs vault script with hardcoded gateway/vault lookups. Defer its container instead of shipping personal paths or redesigning it here. Read-only systemd crib details recorded in curator/DEFERRED.md.
- Use built-in n8n nodes only. A small isolated HTTP→JetStream outbox avoids exporting n8n NATS credentials. Local JetStream is proof-only; G1 wiring is deliberately not activated.
- Review remains independent at the parent PM, before merge. No reviewer agent tool is available in this worker runtime; the full prompt is in REVIEW-PENDING.md.
- Final cold config/up/health/import/auth/validation/JetStream round trip passed. The owned n8n DB has exactly three workflows and zero credential records. All five external image manifests include linux/arm64 and linux/amd64; actual runtime proof is amd64 only.
- Eight stdlib outbox unit tests passed; repeated up skipped workflow overwrite; outbox restart retained stream sequence. All god-g2 containers/volumes/network removed after proof. PROOF.md contains actual trimmed receipts and known limitations.
- Root .gitignore hides .env.example; explicitly force-added only the sanitized example template.
