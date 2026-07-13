# PJangler Component Inventory

| Component | Location | Responsibility |
|---|---|---|
| CLI | `src/index.ts` | Commander command tree and operator interaction |
| MCP server | `src/mcp-server.ts` | Eleven stdio tools and result serialization |
| Project subsystem | `src/project/` | Registry, projection, planning, bootstrap execution |
| Parity subsystem | `src/parity/` | Eleven audit/migration rules |
| Recipe framework | `src/recipes/` | Mise, Docker, Node, Hermes, and hook orchestration |
| Command framework | `src/commands/` | Dry-run-aware command helpers |
| Registry utilities | `src/utils/registry.ts` | Recipe/command registration |
| CommonProject template | `templates/commonproject/` | Base project projection and BMAD scaffolding |
| Hermes template | `templates/hermes-agent/` | Runtime/provider/systemd/Bloodbank provisioning |
| Regression suites | `tests/` | Parity, MCP, and project-registry filesystem tests |

CLI and MCP overlap but do not share uniformly safe mutation defaults or structured failure propagation. Template components execute with host-user authority and require provenance review.
