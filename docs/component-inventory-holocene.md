# Holocene UI Component Inventory

## Application Surfaces

| Surface | Location | Responsibility |
|---|---|---|
| Mission-control shell | `apps/web/app/page.tsx` | Fleet, Tooling, Systems, Containers tabs and shared state |
| Tooling panels | `apps/web/app/tooling.tsx` | Hook definitions, health stats, refresh/live views |
| Systems panels | `apps/web/app/systems.tsx` | Inventory, history, preview, and host actions |
| Container panels | `apps/web/app/containers.tsx` | Traefik Deathwatch target status |
| Clock card | `apps/web/app/clock-card.tsx` | Clock state and n8n mutations |
| HQ Mini App | `apps/web/app/hq/` | Telegram-authenticated org hierarchy and agent contact |

## Shared UI Libraries

Radix Dialog, Hover Card, and Toggle Group provide interactive primitives. The current implementation uses generic collection/live panels; older documentation naming dedicated `BaseStatCard`, `PollingStatCard`, and `SSEStatCard` components is historical.

## State Patterns

The main UI uses client-side React state with polling and SSE snapshot replacement. Systems/containers poll on longer intervals; HQ polls org-tree; clock also persists local state. There is no shared application state store.

## Reuse and Change Guidance

Reuse generic panels and org-model projections before adding parallel feature-specific state. Mutating controls must expose errors, keyboard/focus behavior must be verified for dialogs, and data labels must match actual metrics. Any new control must be paired with API authorization and allowlist tests.
