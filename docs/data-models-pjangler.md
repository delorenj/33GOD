# PJangler Data Models

## Central Project Registry

Default path: `~/.config/pjangler/projects.yaml`, schema version 1. Records include name, slug, repository path, description, lifecycle status, sources, Copier metadata, Plane/Trello configuration, agents, automation, and timestamps. Validation checks top-level shape and identity conflicts but is not a comprehensive nested schema.

Writes use temporary-file rename, preventing partial files but not lost concurrent updates. `PJ_PROJECT_REGISTRY` overrides the path.

## Repository Projection

`.project.json` contains project identity/path, ticket-provider configuration, namespaced agents, and automation/reconciliation settings. It omits catalog-only fields such as timestamps, lifecycle status, and some source/template metadata.

Authority split:

- Central registry: catalog and bootstrap authority.
- `.project.json`: repository-local runtime and board projection.

## Initialization Plan

Typed actions describe registry upsert, Copier render, local manifest write, ticket-provider creation/linkage, and Hermes provisioning. Execution implements only a subset; plan presence is not proof of side effects.

## Parity Model

Eleven rule identifiers represent desired repository/user state. Audits emit findings and migrations apply repairs. Some ostensibly read-only resolution can populate caches or inspect user systemd.

## Schema and Concurrency Limits

No JSON Schema exists for registry or local projection; TypeScript interfaces and runtime checks are authoritative. Arbitrary target paths are possible, and no transaction spans registry, template, provider, manifest, and Hermes actions.
