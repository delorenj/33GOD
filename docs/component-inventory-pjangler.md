# PJangler Component Inventory

| Component | Location | Responsibility |
|---|---|---|
| CLI | `src/index.ts` | Commander command tree and operator interaction |
| MCP server | `src/mcp-server.ts` | Twelve stdio tools and result serialization |
| Project subsystem | `src/project/` | Registry, projection, planning, bootstrap execution |
| Parity subsystem | `src/parity/` | Nineteen audit/migration rules |
| Recipe framework | `src/recipes/` | Mise, Docker, Node, BMAD, notebook, and hook orchestration |
| Command framework | `src/commands/` | Dry-run-aware command helpers |
| Registry utilities | `src/utils/registry.ts` | Recipe/command registration |
| CommonProject template | `templates/commonproject/` | Base project projection and BMAD scaffolding |
| Regression suites | `tests/` | Sixty-one suites run by `scripts/run-tests.mjs`: parity, MCP, project-registry, notebook, and generated-project filesystem tests |

CLI and MCP overlap but do not share uniformly safe mutation defaults or structured failure propagation. Template components execute with host-user authority and require provenance review.
