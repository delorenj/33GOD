# Damian G1/G2 native ARM64 deployment acceptance and seam blocker

Status: **two isolated bundles accepted for synthetic ARM64 bring-up; G2 → G1 integration NOT accepted**.
Charter v1.0 loaded/acknowledged by Rererere. User authorized integration; Grolf remains internal architecture/artifact owner. All actions on Damian's Studio were performed by parent Rererere. Independent reviewer inspected files and ran eight outbox tests without remote authority.

## Exact release / deployment

- Monorepo: `3d3c393cb06259fa39f885f0d7069096d1fb00ea`.
- Candystore: `767ebb5eb8351b43b43bb6406aa1882ef3912713`.
- Remote release: `/Users/hellosubconscious/infra/aperture-g1-g2/releases/3d3c393cb06259fa39f885f0d7069096d1fb00ea`.
- Committed source archives only; no dirty sibling submodule content transferred. Candystore instruction-alias symlinks CLAUDE/GEMINI omitted after archive safety check; actual build sources retained.
- Fresh `god-g1`/`god-g2` resources, no adopted networks/volumes, no published host ports. Fresh credentials generated on target, mode600 ignored .env, values never emitted or copied.
- G1 site-only `compose.damian.yml` adds memory/CPU bounds; internal bundle source unchanged. G2 shipped caps retained. Total Docker VM7.745GiB unchanged. No catalog extras enabled.
- Existing Damian n8n2.44.4 remains separate; G2 ships1.120.4 solely as an isolated synthetic demo, not migration/downgrade of existing state.

## Parent-executed proof

### G1

Native linux/arm64 images built/pulled and actual runtime architecture inspected for all six service images. nats-init exit0; NATS/Postgres/Candystore healthy; placement/daprd running; Dapr HTTP readiness checked.

Published synthetic event `73b1ee2e-eeeb-471c-858f-918c32b0ef00`, correlation `0edc0544-7338-407a-b51f-74be2acba22e`, onto G1 NATS. Candystore API `GET /events/<id>/raw` returned the same id/type/subject/correlation/producer/data through the real JetStream/Dapr path. Readback repeated successfully after G2 deployment.

Original G1 smoke's `/proc/sys/kernel/random/uuid` host assumptions fail on macOS. A deployment-side Python runner exercised the transport/fidelity checks without editing upstream smoke. It reused the source-smoke envelope shape: **transport proof, not canonical Bloodbank schema acceptance**. An initial incomplete proof envelope/readback attempt and a subsequent syntax error are preserved in scratch logs; only the final successful call is accepted.

### G2

Build/up exit0 native arm64. Unmodified `python3 smoke/check.py` on Studio passed twice, before and after owned outbox restart:

- Four long-running services healthy, importer exit0, zero published ports.
- Exactly three saved workflows; saved nodes AND connections equal distributed JSONs, independently checked against owned Postgres.
- Only `apertureG2Smoke01` active; `apertureG2Sched01` and fail-closed `apertureG2Plane01` inactive.
- Zero credentials in fresh demo DB.
- Actual active webhook rejects missing header401 and malformed synthetic input400.
- Valid request returns JetStream persistence acknowledgment; `/latest` queries retained NATS message, matching envelope and sequence.
- First event `93b27e2f-d66c-40b7-ba45-4295bef0e395`, sequence1 survived outbox restart unchanged.
- Second event `064c8614-44f8-4805-89f0-78978b226eef`, sequence2 passed repeat smoke.
- Repeat compose up succeeded; source nodes/connections remained exact after re-up. Successful execution rows intentionally absent under shipped save-none settings; no retained execution-history claim. Real webhook responses + NATS readback establish executed path, not fixtures alone.

All G1/G2 containers stabilized with zero OOM kills/restart counts; one-shots exited normally. Idle combined snapshot ~535MiB, not load/capacity guarantee. No Docker resource settings changed.

## Preservation

Baseline24 original container IDs, start times, state, restart counts, images and host bindings compared unchanged after both deployments and G2 outbox restart. Existing n8n readiness and Plane loopback health both200. No existing workflow, owner/MFA, credential database, Tailscale Serve, external callback, production routing, paid route or real business data changed. No broad checkpoint hook, teardown or volume deletion invoked.

## Grolf action required: internal integration seam

1. `g2/compose.yml:75-98` and `outbox/server.py:15-18,55-60,119-123` bind G2 to an owned local broker and `G2_SMOKE`. Merely attaching its outbox to G1 attempts overlapping stream creation under G1 `bloodbank.evt.>`; G2 also checks acknowledgment stream == G2_SMOKE. Supply a versioned, reviewed G1 transport mode instead of a deployment hack.
2. G1/G2 smoke puts the five-token NATS subject in CloudEvent `type`; canonical Bloodbank type omits `evt`. G2 also lacks kind/actor/ordering_key/causationid. Grolf/Bloodbank owner must choose an approved test envelope/namespace and tighten producer/validator/acceptance together.
3. G2 demo env-header auth remains demo-only. Native credential binding, real Plane raw-body HMAC, curator and callback ingress are not implemented, activated or accepted here.
4. G1 portable smoke fix needed upstream; confirmed `/proc` usage. Reviewer also asserted bare BSD mktemp incompatibility, but parent did not independently establish that claim and does NOT treat it as a verified blocker.
5. G2 REVIEW-PENDING.md remains in artifact. This independent deployment review is not retroactive proof of Grolf's PM merge gate; he owns reconciling that status.

## Evidence locations

Parent local scratch `/home/delorenj/.hermes/profiles/rererere/cache/scratch/`:
- `aperture-g1-arm64-bringup.log`
- `aperture-g1-arm64-acceptance.log`
- `aperture-g1-preservation.log`
- `aperture-g2-arm64-bringup.log`
- `aperture-g2-arm64-smoke.log`
- `aperture-g2-arm64-saved-persistence.log`
- `aperture-g1-g2-final-verification.log`
- `aperture-g1-g2-review.md` (independent source review, includes explicitly unverified secondary portability assertions)

Remote root holds `baseline.json`, `release.json`, `g2-acceptance.json`; first G1 acceptance written under release tree and located/read during final verification. No raw secrets in evidence. This handoff is recorded in-repo; no direct delivery to Grolf claimed. Both bundles remain running privately for follow-up. Ship-board integration checkboxes were not advanced.
