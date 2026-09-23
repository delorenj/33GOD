# Architecture Input Reconciliation — Holocene `/hq`

## Sources

- `docs/architecture-holocene.md`
- `docs/data-models-holocene.md`
- `holocene/apps/web/app/hq/`
- `holocene/apps/api/src/org.ts`
- `holocene/apps/api/src/fleet.ts`
- `holocene/apps/api/src/server.ts`
- `33god-platform/compose.yaml`

## Reality ratified by the spine

- `/hq` is an existing Next.js Mini App hosted by `holocene-web`, not a
  greenfield application.
- `/hq/api/org-tree`, `/hq/api/snapshot`, and `/hq/api/action` are the public
  route boundary; they pass Telegram `initData` to server-side verification and
  proxy into the host API.
- Holocene API currently reads the Hermes registry, `org.yaml`, runtime state,
  systemd, and Candystore-derived history. `@holocene/org-model` is a pure
  resolver over those inputs.
- The current client polls the org tree every five seconds and the current
  action proxy is namespace-pinned to Hermes fleet routes.
- `holocene-api.service` owns the host API and root Compose owns the web
  container and Traefik `/hq` carve-out.

## Gaps or migration pressure

1. The current org projection reads registry plus `org.yaml`; AD-5 records this
   as a single transitional adapter until a Flume projection transport exists.
2. The current action proxy forwards a path under a pinned prefix, while AD-7
   requires named typed capabilities, idempotency, and receipt correlation.
3. The current `OrgTree` has `generatedAt` and `source` but not the full
   browser-facing freshness/evidence envelope; AD-9 is the contract to extend.
4. The existing host API documentation says direct API auth is broad/trusted;
   AD-8 keeps the public `/hq` proxy as the Mini App trust boundary and does not
   expand browser access to the host API.

## Operational implication

The spine is an incremental seam-tightening plan inside Holocene. It does not
claim that the current implementation already satisfies every AD; implementation
must migrate the current transitional paths and prove the new contracts.
