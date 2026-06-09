# 33GOD Pipeline MCP Hub

A multi-domain [MCP](https://modelcontextprotocol.io) server that fronts many tool
domains (Plane, BloodBank, ticket-lifecycle, …) behind **one** small, stable surface —
so an agent isn't flooded with hundreds of tool schemas / millions of tokens.

Served at **`https://mcp.delo.sh/mcp`** (header-PAT auth).

## How it works — discovery + dispatcher gating

The hub exposes only three tools to clients:

| Tool | Purpose |
| --- | --- |
| `list_domains()` | List available domains (name, description, tool_count). **Start here.** |
| `list_domain_tools(domain)` | Load + list one domain's tools, each with its `input_schema`. This is the "load a domain's toolset" step — schemas enter context only now. |
| `call_domain_tool(domain, tool, arguments)` | Invoke a specific domain tool; `arguments` must match its `input_schema`. |

Underlying domain tools are held in an internal registry and are **never advertised
directly**, so the per-request tool-schema cost stays tiny and constant. This works on
any MCP client regardless of `notifications/tools/list_changed` support.

> Trade-off: domain tools are invoked through `call_domain_tool(...)` rather than as
> native function calls. The hub validates arguments against the real tool schema and
> returns clear errors. (A future "native passthrough" mode could expose real prefixed
> tools for clients that already defer schemas, like Claude Code.)

## Domains

- **plane** — reuses `plane-mcp-server`'s tools in-process (work items, projects, cycles,
  epics, etc.). Auth + Plane API calls use the caller's PAT from the request context.
- **bloodbank** *(Phase 1)* — publish/trace events on the BloodBank NATS bus.
- **lifecycle** *(Phase 2)* — opinionated ticket state machine (pull → triage → … → done).

## Auth

HTTP mode uses the same header scheme as `plane-mcp-server`:

- `Authorization: Bearer <PLANE_PAT>`
- `x-workspace-slug: <workspace-slug>`

## Run locally

```bash
# Install the hub + the plane domain dependency (from the local checkout)
uv pip install -e .
uv pip install -e ../../plane-mcp-server

# stdio (no auth; Plane tools use env fallback)
PLANE_API_KEY=... PLANE_WORKSPACE_SLUG=... python -m pipeline_hub stdio

# http (header-PAT auth) on :8080 at /mcp
PLANE_INTERNAL_BASE_URL=http://localhost:8000 python -m pipeline_hub http
```

## Deploy (DeLoNET)

Docker stack at `~/docker/stacks/ai/pipeline-mcp-hub/`. It builds this repo and pulls the
`plane-mcp-server` source via a named build context, joins the `proxy` network, and is
routed by Traefik at `Host(mcp.delo.sh)`. `*.delo.sh` already wildcards through the
Cloudflare tunnel → Traefik.

```bash
cd ~/docker/stacks/ai/pipeline-mcp-hub
docker compose up -d --build
```

Requires Docker Compose ≥ v2.17 (for `build.additional_contexts`).

### Key env

| Var | Default | Purpose |
| --- | --- | --- |
| `HUB_PORT` | `8080` | Listen port inside the container |
| `PLANE_INTERNAL_BASE_URL` | — | Server-to-server Plane API base; set to `http://plane-backend:8000` (SDK appends `/api/v1`) |
| `PLANE_BASE_URL` | `https://api.plane.so` | Fallback Plane API base |

Phase 0 needs **no secrets** — the Plane PAT arrives per-request in the client's headers.
