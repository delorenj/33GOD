# Aperture G5 — Project Tooling

**run-only tool images; no daemons**. G5 has no long-running services, network,
volume lifecycle, or published host ports. Other groups' agent hosts invoke
these artifacts when needed. Nothing is started merely by building G5.
[Charter](../../CHARTER.md) applies; PM review precedes merge.

## Why there is no g5 compose.yml

The governing root architecture directive is: **“No component receives a fake
server merely to appear in Compose.”** CommonProject requires no runtime image;
PJangler is an optional run-only tool; Skillex needs no stack image unless it
introduces a network service. The existing [platform runtime contract](../../../README.md)
also defines PJangler CLI/MCP as run-only, zero-replica tools with no listener.
This bundle follows that directive instead of the old eight-groups/eight-images
shorthand in the Aperture overview.

G5 is **three artifact kinds — tool image / template / registry — not a service
graph**. Bake builds images; it is not an orchestrator and cannot publish ports.
The optional Skillex CLI image is a portable executable, not a registry server.
A stdio MCP image is also a tool image: one foreground process per agent-host
session, ending at stdin EOF; not an installed background process or a network
service. “Run-only” does not mean a fresh process per individual MCP message:
an agent host may keep that session open for multiple calls.

| Component | Artifact kind | What was packaged / why |
|---|---|---|
| PJangler | run-only tool image | `Dockerfile.pjangler`: builds `pj` from its own source/lockfile; non-root Node CLI entrypoint |
| Skillex CLI | run-only tool image | `Dockerfile.skillex`: installs public npm `@delorenj/skillex@0.3.1`; non-root `skillex` entrypoint |
| CodeGraph Voyage MCP | stdio tool image | `Dockerfile.mcp-codegraph`: uv installs only its Python module sources; non-root `codegraph-voyage-mcp`, default stdio |
| CommonProject | Copier template mount | caller supplies a versioned read-only checkout at `/opt/pjangler/templates/commonproject`; no image and no copied template payload |
| Skillex catalog | registry of files/references | caller supplies its own `all-skills/`, `sets/`, `packs/` checkout; no registry image or live operator selection is shipped |

**Inventory:** exactly **one** MCP server directory was present in the inspected
Skillex checkout: `mcp-servers/codegraph-voyage-mcp/`. Actual console script:
`codegraph_voyage_mcp.server:main`. No second server was invented. The handoff's
`skill-sets/global` layout is not present; this checkout uses `sets/`, `packs/`,
and `all-skills/`. These remain file artifacts, not a service.

## Source reality and deliberate deviations

The supplied Python/uv PJangler recipe cannot install today's source. The
available PJangler checkout is the monorepo child `pjangler/`, **not** a sibling
checkout; it has `package.json`, no `pyproject.toml` or Python distribution.
Its package is `@delorenj/pjangler` 1.5.18. Both it and Skillex declare Node
**>=24**, so using the requested Node 20 would violate both packages' engines.
Both CLI images therefore use Node 24.6.0 slim. Python 3.12 slim + uv is used
only for the actual Python MCP package. These changes follow source evidence,
not an emulated CLI or wrapper server.

The PJangler image deliberately builds only `src/index.ts` and copies the
tracked notebook skill export, package/lockfile and production dependencies.
It does not copy arbitrary source-checkout files, host config, template state,
registry state, or a service binary. Do not mistake `--help` proof for complete
provisioning: `pj init` currently also needs trusted Copier, Git, other external
CLIs, and local lifecycle prerequisites. Those are not silently provisioned by
this thin image; the full real-project gate is [deferred](DEFERRED.md).

## Build and prove (Docker + POSIX shell only on the host)

Work from this directory. Requires Buildx with Bake/named contexts. Export
absolute paths to extracted source checkouts; no checkout is modified.
`.env.example` lists all `GOD_*` overrides; Bake does **not** auto-load `.env`.

```sh
export GOD_PJANGLER_CONTEXT="$PWD/../../../../pjangler"
export GOD_MCP_CONTEXT="$HOME/code/skillex/mcp-servers/codegraph-voyage-mcp"
export GOD_COMMONPROJECT_CONTEXT="$HOME/code/CommonProject"
docker buildx bake --print
./smoke/smoke.sh
```

In a worktree the relative PJangler default points at the empty submodule
location: override it to the real clean source checkout. The smoke explicitly
grants BuildKit read access to only the two supplied source contexts, builds
all three native images and loads them. It checks both CLI helps/versions, MCP
help **and a real initialize/tools-list exchange**, read-only template mount,
non-root image users, zero exposed/published ports, immutable base manifests,
and every group file for forbidden credential/host markers. It uses stdlib
Python/Node **inside the images**, not host Python/Node, curl, jq, or npm.
Source Git before/after evidence is recorded separately in [PROOF.md](PROOF.md).

For multi-platform publication, choose your own registry tags and builder:

```sh
export GOD_PJANGLER_IMAGE=registry.example/g5-pjangler:0.1
export GOD_SKILLEX_IMAGE=registry.example/g5-skillex:0.1
export GOD_MCP_IMAGE=registry.example/g5-mcp-codegraph:0.1
docker buildx bake --allow="fs.read=$GOD_PJANGLER_CONTEXT" \
  --allow="fs.read=$GOD_MCP_CONTEXT" --push
```

This command is an operator recipe, **not a claim of publication**. Bake
advertises `linux/amd64,linux/arm64`; the smoke overrides to the native platform
for `--load`. Use a native arm64 builder on an arm64 target. No cross-built or
arm64-executed application images are claimed here.

## Agent-host invocation

```sh
docker run --rm god-g5-pjangler:0.1 --help
docker run --rm god-g5-skillex:0.1 --help
# Agent host owns stdin/stdout. Do not allocate a TTY or detach it.
docker run --rm -i god-g5-mcp-codegraph:0.1 --transport stdio
```

An MCP host config uses `command: "docker"` and
`args: ["run", "--rm", "-i", "god-g5-mcp-codegraph:0.1", "--transport", "stdio"]`.
The upstream executable also supports SSE, but that transport is **not** the G5
contract, is never invoked here, and has no published port. No `-p`, `-P`, `-d`,
restart policy, Compose service, or readiness loop belongs in the host config.

The MCP SDK actually installed here uses **newline-delimited JSON-RPC**, not
Content-Length framing. `smoke/mcp.py` verifies `serverInfo` on initialize,
five advertised tools on tools/list, and a clean EOF exit. This is a real stdio
handshake, not merely an import check. It does not execute indexing/search.
For those calls, mount a deployment-owned project at `/workspace`, pass
`project_path: "/workspace"`, and provide its `.codegraph/codegraph.db` and
`tools/codegraph_voyage` module plus their own Python dependencies/credentials.
Writes such as index need an intentionally writable project mount. No project
DB, embedding state or credentials are baked in.

## CommonProject and registry mounts

The smoke proves this mount contract without running template tasks:

```sh
docker run --rm \
  --mount "type=bind,src=$GOD_COMMONPROJECT_CONTEXT,dst=/opt/pjangler/templates/commonproject,readonly" \
  god-g5-pjangler:0.1 --help
```

The template source stays read-only; the consuming agent host's trusted Copier
9.x installation renders into a **separate writable project**. The consumer
must pin/review the template, supply deployment-owned answers, and deliberately
authorize its tasks. No generic fake template or operator answers are included.
A full `pj init` inside this image is not yet an accepted extraction contract.

For catalog operations, supply a recipient-owned catalog at `/registry` and
use `skillex --registry-root /registry ...`. Inspection can use a read-only
mount; authoring/sync requires deliberately writable catalog/output mounts and
matching non-root permissions. The npm CLI does not contain the skill catalog.
Do not mount any operator home/config tree or copy live profile selections.

## arm64 / amd64 support

Every `FROM` is pinned to a tag **and immutable index digest**; exact index and
platform digests live in [base-images.json](base-images.json) and PROOF.md.

| External base | amd64 | arm64 | Used by |
|---|---|---|---|
| `node:24.6.0-bookworm-slim` | manifest verified; native smoke passed | manifest verified only | PJangler build/runtime, Skillex |
| `python:3.12.12-slim-bookworm` | manifest verified; native smoke passed | manifest verified only | CodeGraph MCP |

The uv binary is installed as a pinned PyPI wheel, not another external image.
No other image is used by the smoke. Base-image multi-arch support does **not**
prove transitive dependencies or tool behavior on arm64.

## Intentionally NOT here / deployment reality

No long-running G5 service, stack network, port, healthcheck, startup dependency,
background scheduler, hosted registry, MCP hub, image publication, live board,
personal config, source mutation, or credentials. The tool images are consumed
by other groups' agent hosts. [DEFERRED.md](DEFERRED.md) separates artifact proof
from publication, full project provisioning, skill execution, notebook roundtrip,
and attached event-bus/recipient acceptance. This branch is implementer evidence;
independent PM review and target-host acceptance remain open.
