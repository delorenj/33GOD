---
name: 33god-hub
description: Unified entrypoint for the private 33GOD productized development environment. Use when work spans Bloodbank, Candystore, Holocene, PJangler, Hermes Fleet, Skillex, Hindsight, Pipeline MCP Hub, Candybar, HeyMa, hooks, changelogs, backfills, or local/cloud platform composition.
---

# 33GOD Hub

Start here for platform work. This skill routes by product component and
cross-component contract, not by whichever repo happens to be open.

## Product rule

33GOD is one private development environment made from multiple repos. Component
repos own implementation; the platform control plane owns composition,
changelog, skill routing, and backfill coordination.

## Component map

| Need | Component |
|---|---|
| Event schemas, NATS/Dapr, agent lifecycle events | Bloodbank |
| Durable event history, sessions, event summaries | Candystore |
| Dashboard, live status, tool health | Holocene |
| Project/agent provisioning, project registry | PJangler |
| Long-running agents, profiles, fleet defaults | Hermes Fleet |
| Skill packs and agent capability distribution | Skillex |
| Recall/retain/journal memory hooks | Hindsight |
| Compact MCP tool gateway | Pipeline MCP Hub |
| Topology/event visualization | Candybar |
| Voice/transcription/TTS interface | HeyMa |

## Operating procedure

1. Read `33god-platform/components.yaml`.
2. Load the matching `components/<id>.yaml`.
3. If a change affects more than one component, add a pipeline changelog entry.
4. If old repos/configs can drift, add or update a backfill check.
5. Route implementation details to the component skill or repo AGENTS.md.

## Commands

```bash
cd ~/code/33GOD/33god-platform
python3 scripts/platform.py validate
python3 scripts/platform.py components list
python3 scripts/platform.py backfills check
```
