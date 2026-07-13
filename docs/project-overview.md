# 33GOD Project Overview

**Date:** 2026-07-13
**Type:** Four-part monorepo knowledge boundary
**Architecture:** Event-driven pipeline with local control-plane and read-side integrations

## Executive Summary

33GOD is a private, local-first agentic development environment. The documented product boundary contains four active repositories: Bloodbank, Candystore, Holocene, and PJangler. They form a pipeline, but they are not one deployable stack today. Bloodbank is contract-complete and runtime-partial; Candystore is a compact durable event-history service; Holocene is an operational single-user dashboard with host-control powers; PJangler is a local provisioning and parity control plane.

The central design is asynchronous CloudEvents over NATS JetStream. Current implementation also has intentional or transitional exceptions: Holocene reads Candystore over HTTP, hook health reaches Holocene through Redis, and PJangler exchanges local registry and runtime projections. These exceptions must be documented rather than hidden behind an “all traffic uses Bloodbank” claim.

## Project Classification

- **Repository type:** Multi-part monorepo workspace
- **In-scope parts:** Bloodbank, Candystore, Holocene, PJangler
- **Primary languages:** Python, TypeScript, SQL, JSON Schema, YAML, Shell
- **Operating model:** Independently versioned components coordinated by `33god-platform/`
- **Deployment maturity:** Local development topology; product Compose remains a validation scaffold

## Multi-Part Structure

| Part | Classification | Purpose | Core stack |
|---|---|---|---|
| Bloodbank | Backend/infrastructure | Own event names, schemas, NATS streams, Dapr pub/sub, hook publication | Python, JSON Schema, NATS 2.10, Dapr 1.13 |
| Candystore | Web/backend | Persist events, expose query/session/summary APIs, serve audit UI | Python 3.11, PostgreSQL 16, React 19, Dapr 1.13 |
| Holocene | Web/control plane | Observe and mutate Hermes fleet, host services, containers, hooks, and clock workflows | TypeScript, Fastify 5, Next.js 15, pnpm/Turbo |
| PJangler | CLI/provisioning | Maintain project registry/projections, parity rules, recipes, templates, and MCP automation | TypeScript, Node 20+, Commander, MCP SDK, Copier |

## Architecture Highlights

- Bloodbank-local JSON Schemas and the locked event-naming document are canonical for event identity.
- Candystore is the durable read model, but enforces a weaker envelope contract than Bloodbank and has no operator replay feature.
- Holocene’s live Bloodbank client package is a stub; the running API combines host state, Redis projections, and Candystore HTTP reads.
- PJangler’s central registry is the project catalog/bootstrap authority; `.project.json` is the repository-local runtime projection.
- Root documentation governs interfaces and deployment relationships. Component docs govern internals.
- The precedence rule is live manifests/code/tests, then current docs, then historical planning artifacts.

## Current Guarantees

The following are demonstrated by live source or focused verification:

- Bloodbank contains 61 valid JSON Schema documents and a locked five-token type/six-token subject convention.
- Candystore deduplicates by event UUID, persists accepted events in PostgreSQL, and exposes event/session/aggregate reads.
- Holocene has live web and API entrypoints, but no substantive application test suite.
- PJangler typechecking and built CLI loading succeed; its package version is 1.2.18.
- `33god-platform/compose.yaml` validates as a Compose model but starts only a `platform-ready` tools scaffold.

## Known Contract Drift

High-risk live contradictions include:

- Bloodbank’s runtime validator does not enforce semantic equality between CloudEvents `type` and NATS `subject`.
- Bloodbank’s heartbeat Compose/CI references a missing service directory.
- Candystore acknowledges poison input even if dead-letter persistence fails.
- Holocene defaults to the wrong Candystore URL and silently converts failure into empty history.
- Holocene’s host-control API binds all interfaces without application authentication.
- PJangler generates Bloodbank subscriptions that violate the canonical six-token routing rule.
- The platform registry resolves PJangler to `/home/delorenj/code/pjangler`, not the in-scope repository.
- PJangler package and lockfile versions disagree, and vendored template state is not reproducible from the parent commit.

See [Drift Governance](./drift-governance.md) for ownership and gates.

## Development Overview

Each component retains its package manager and runtime. Do not run root `mise` shell-entry hooks merely to inspect the repository: they may link agent files, inject secrets, or sync codegraph state. Prefer the explicit commands in the four [development guides](./index.md#part-documentation).

## Documentation Map

- [Documentation Index](./index.md)
- [Source Tree Analysis](./source-tree-analysis.md)
- [Integration Architecture](./integration-architecture.md)
- [Deployment Guide](./deployment-guide.md)
- [Drift Governance](./drift-governance.md)

---

_Generated using the BMAD Method `document-project` workflow._
