# Epic 1 Context: Open HQ and Understand the Company

<!-- Generated from planning artifacts. Regenerate with compile-epic-context if planning docs change. -->

## Goal

Give the solo executive a truthful, mobile-first read-only entry into DeloHQ: open `/hq` from Telegram without a second login, see the real organization (Departments, Employees, roles, ownership) as projected from the workforce authority, understand each Employee's posture in plain company language, and drill into owned context without losing place. This vertical slice also lays the foundation every later surface (Now, Inbox, Agent Office, Actions) depends on: the one shared versioned projection contract, the verified Telegram route boundary, and the freshness/error envelope that keeps DeloHQ from ever presenting unsupported state as healthy.

## Stories

- Story 1.1: Establish the Shared DeloHQ Projection Contract
- Story 1.2: Open HQ Through the Verified Telegram Boundary
- Story 1.3: Show the Flume-Backed Company Projection
- Story 1.4: Explain Employee Posture in Company Language
- Story 1.5: Navigate from Company to Owned Context

## Requirements & Constraints

- **Company projection:** Departments, Employees, roles, and ownership come from one Flume-backed workforce snapshot, with source and freshness shown. A newly provisioned Employee must appear without hand-editing any DeloHQ roster.
- **Posture:** Exactly six postures: Working, Waiting on you, Blocked, Quiet, Unavailable, Unknown. "Waiting on you" references the specific awaiting context. Stale, missing, or contradictory evidence yields Unknown with explanation, never a healthy default.
- **Navigation:** From a Department or Employee, reach Agent Office, Project, Evidence, or Telegram conversation and return with filters, scroll position, and context preserved. Missing or unprovisioned targets show an explicit state, not a broken route.
- **Telegram entry:** Bot-menu, notification, and conversation entry land in the exact DeloHQ context.
- **Truthfulness:** Nothing is shown as current, healthy, or complete without canonical evidence. Unknown, stale, unavailable, and contradictory are explicit states. Absence or timeout is never read as empty or healthy.
- **Accessibility:** Usable in the mobile Telegram Mini App. State and urgency must be clear from text and structure, not color alone.
- **Data boundary:** One Executive Operator in v1. No shadow permission model, and no raw private agent memory exposed.
- **Observability:** Adapters record source, correlation, outcome, timestamp, and a concise failure reason, never credentials, prompts, or raw memory.
- **Success signal:** Within 30 seconds of opening DeloHQ, the executive can tell what is happening, what needs attention, and who owns it.
- **Out of scope:** DeloHQ-owned workforce registry, workforce reorganization, writes to `org.yaml` or the registry, TDLib, and separate DeloHQ infrastructure.

## Technical Decisions

- **Host:** Extend Holocene (`apps/web/app/hq`, `apps/api`, shared packages). v1 adds no DeloHQ service, database, event stream, or runtime. `holocene-api.service` stays the host-side integration authority. Traefik routes `/hq` to `holocene-web`, which proxies to the host API. Proxy or dependency failure degrades to an explicit error, stale, or Unknown state.
- **Contract registry:** `holocene/packages/delohq-contracts/` is the only browser and command contract source. It holds envelopes, view models, canonical reference types, freshness vocabulary, Unknown/error shapes, and evidence metadata. Adapters, routes, views, and tests import it. Contract tests reject local dialects. Incompatible changes need an explicit versioned migration.
- **Envelope:** Every projection carries `schema_version`, `source`, `generated_at`, `observed_at`, freshness state, and evidence or error detail. Each surface declares a max-age policy owned by the Holocene API.
- **Identity:** Opaque canonical `*_id` / `*_ref` values (for example `agent_ref`, `project_ref`, `evidence_ref`) are the only join and routing keys. Display names, repo labels, and Telegram usernames are labels only. `*_at` timestamps are ISO-8601 UTC. Upstream field names stay inside adapters; view models use TypeScript camelCase.
- **API seam:** The browser calls only authenticated `/hq/api/*` routes that return typed, versioned envelopes. It never reads `org.yaml`, registries, systemd, Candystore, Bloodbank, Flume stores, or internal Fastify routes directly. GET/read paths have no side effects.
- **Telegram auth:** Every public `/hq` request verifies Mini App `initData` (bot token, freshness, operator allowlist) and derives actor context carrying `actor_ref`, `auth_observed_at`, and originating route metadata. Auth failures return a typed error with no source data or command capability. The internal Fastify API is not the trust boundary.
- **Workforce adapter:** Until a Flume read transport is chosen, one transitional adapter (`apps/api/src/org.ts`) may read the registry, treated as operational reference, and `org.yaml`, treated as presentation metadata only. Neither is writable. Each response carries one projection ID and generation timestamp, and Company and Office use the same snapshot within a response cycle. Pure Company vocabulary and resolver live in `packages/org-model`. Hermes runtime state for posture comes via the `fleet.ts` adapter.
- **Authority split:** Flume owns workforce identity, hierarchy, and policy. PJangler owns projects. Krebs and Pilot own tickets. Bloodbank and Candystore own events and history. Hermes owns runtime and receipts. DeloHQ only projects, explains, and links.
- **Stack:** Next.js 15 / React 18.3 web, Fastify 5.1 / TypeScript 5.6 API, Node 22 Compose target, pnpm 10 / Turbo 2, and Flume handbook schema 5 / contract 1.4.0. Use the existing Telegram WebApp SDK URL. The Node 26.5 host shim failure must be resolved before package-manager evidence is trusted.
- **Open decisions (do not invent answers):** numeric freshness budgets per surface, the Flume read transport and `org.yaml` retirement, which current `/hq` controls are retained or retired, and Telegram notification classes.

## UX & Interaction Patterns

- The UX design documents are draft shells. Do not invent mobile information architecture, visual identity, or mockups as finalized requirements.
- Settled constraints: mobile-first Telegram Mini App, text- and structure-based state meaning, and context-preserving drill-down and return.

## Cross-Story Dependencies

- 1.1 (contract) comes before everything. 1.2 (auth boundary and envelope failure states) gates every `/hq/api/*` route. 1.3 (Company snapshot) is required by 1.4 (posture on those Employees) and 1.5 (navigation from them).
- 1.5 links to Agent Office, Evidence, and conversation targets that Epics 3 and 5 build out. Until then, those targets must render explicit unprovisioned or unavailable states.
- The contract, envelope, and auth boundary built here are reused by Epics 3 to 6. Posture evidence depends on Hermes runtime and Bloodbank/Candystore event sources. Epic 2 named specialists should appear in Company through the workforce projection with no DeloHQ roster edits.
