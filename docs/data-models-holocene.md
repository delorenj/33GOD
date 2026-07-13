# Holocene Data Models

## Persistence Model

Holocene owns no application database. Its models are transient projections over external sources and browser state.

## Fleet Projection

Fleet entries combine Hermes registry identity, project/role metadata, systemd unit state, runtime activity files, logs, and optional Candystore event history. Active work tracks status, issue/session/worktree, heartbeat/activity timestamps, last runner result, evidence paths, and age.

## Organization Projection

The org model deterministically merges `~/.hermes/org.yaml`, registry entries, and live fleet state. Explicit placement wins, hidden agents are removed, project-path derivation follows, and unmatched agents appear under Unassigned.

## Tooling and Systems Projections

Tooling definitions join local hook configuration with Redis health snapshots. Systems join bgls inventory/action metadata with Prometheus history. Containers project Traefik Deathwatch targets. These models are recomputed or polled rather than persisted.

## Browser State

React client state stores selected tabs, snapshots, loading/error state, and mutation feedback. Clock state additionally uses `localStorage`. HQ polls org-tree state every five seconds.

## Contract Risks

Candystore errors collapse into an empty event array, so absence and outage are indistinguishable. “Ticket velocity” is derived from heartbeat/invocation counts. Historical and current segments are not always combined consistently.
