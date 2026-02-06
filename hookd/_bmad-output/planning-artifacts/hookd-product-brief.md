---
title: "hookd - Deterministic Hook Event Pipeline"
type: product-brief
status: approved
date: 2026-02-06
component: hookd
parent: 33GOD
---

# hookd - Product Brief

## Problem

Claude Code hooks currently require complex, fragile one-liner shell commands that couple hook logic directly to downstream consumers (like claude-flow). This creates:

- **Unreadable hook configs** - multi-line jq/xargs/bash pipelines that no human can grok
- **Tight coupling** - changing downstream behavior means rewriting every hook command
- **Slow execution** - every hook invocation spawns multiple processes (npx, jq, etc.)
- **No separation of concerns** - fact logging, semantic memory, and formatting all jammed into one command

## Solution

A three-layer event pipeline that decouples hook emission from downstream processing:

1. **hookd-emit** - Ultra-lightweight CLI that reads stdin and fires it to a local Unix socket. Every hook config calls this, nothing else.
2. **hookd** - Rust daemon that listens on the socket, enriches payloads with repo context (git root, branch, HEAD, agent ID), and publishes typed events to Bloodbank (RabbitMQ).
3. **mutation-ledger** - FastStream consumer that stores project mutation facts in per-repo SQLite. The shared "papertrail" of all tool mutations.

## Non-Goals (This Sprint)

- `semantic-witness` (agent memory bridge with Qdrant embeddings) - future sprint
- Standup synthesizer workflow - future sprint
- Multi-repo federation - future sprint

## Success Criteria

- Hook config for any tool mutation is a single, static command: `hookd-emit <event_type> <tool_name>`
- End-to-end latency from hook fire to Bloodbank publish: < 10ms
- `mutation-ledger` stores queryable facts per-repo in SQLite
- Adding a new hook type requires zero changes to hookd or downstream consumers

## Key Decisions

- **Vector DB**: Qdrant (locked, but not this sprint)
- **Message broker**: RabbitMQ via Bloodbank (existing 33GOD infra)
- **Daemon IPC**: Unix domain socket at `/run/user/$UID/hookd.sock`
- **Storage**: SQLite per-repo for mutation-ledger (portable, git-friendly)
- **Language**: Rust for hookd (performance-critical daemon), Python/FastStream for consumers
