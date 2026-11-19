# 33GOD Platform Control Plane

This directory owns the normalized cross-component Compose projection, component
registry, change policy, and semantic gates for 33GOD. Component repositories
remain authoritative for their internal implementations. The projection at
`compose.yaml` is validated against those sources; it is a deployment target,
not evidence that the host has been cut over.

## Integrated local target

The no-profile model contains:

- Bloodbank NATS JetStream, one-shot stream initialization, and Dapr placement.
- Exactly one standalone Candystore PostgreSQL, application, and Dapr sidecar.
- A Holocene host-API preflight followed by the Holocene web container. The API
  remains the existing `holocene-api.service` user unit on host port `4000`.

The `tools` and `full` renders additionally expose PJangler CLI and MCP
definitions. Both have zero service replicas and are intended only for explicit
`docker compose run` use. PJangler MCP is stdio; neither definition has a port,
HTTP healthcheck, restart loop, or daemon contract.

The `cloud` profile is render-only and deliberately unsupported. It retains the
local bind/external-network model plus a rejection service so drift remains
visible. The cloud profile has no supported lifecycle surface.

> **Do not run `docker compose --profile cloud up`.** Compose selects every
> unprofiled local service as well as `cloud-unsupported`, so NATS, PostgreSQL,
> Candystore, and Holocene may start and mutate state before the rejection
> container exits. Cloud is configuration/render inspection only, and this repo
> intentionally defines no cloud lifecycle task.

## Ownership and source roots

`33god-platform/compose.yaml` is the root-owned normalized projection. It does
not edit or include the component Compose files and does not replace their
ownership. Source mounts/build contexts resolve from `GOD_SOURCE_ROOT`, which
defaults to the parent of this directory. Set it explicitly when validating
from an isolated worktree:

```bash
export GOD_SOURCE_ROOT=/home/delorenj/code/33GOD
```

No secret values belong in this directory. The model names only these operator
configuration boundaries:

- Bloodbank port keys: `BLOODBANK_NATS_CLIENT_PORT`,
  `BLOODBANK_NATS_MONITOR_PORT`, and `BLOODBANK_DAPR_PLACEMENT_PORT`.
- Candystore port keys: `CANDYSTORE_POSTGRES_PORT`, `CANDYSTORE_PORT`, and
  `CANDYSTORE_DAPR_HTTP_PORT`; database settings remain local-development
  defaults in the candidate and must move to an ignored env/secret source
  before hosted use.
- Holocene web reads the optional component-owned
  `holocene/.env.holocene-web`; sensitive inputs originate from its ignored
  environment/1Password-reference workflow. The host API unit owns
  `CANDYSTORE_API_URL` and related host-service configuration; unset, holocene-api
  falls back to `CANDYSTORE_URL`, then the `127.0.0.1:8683` port contract that
  `scripts/validate-compose.py` pins for the `candystore-app` publish.
- PJangler registry/provider settings remain host-scoped and are not forwarded
  wholesale into the tool containers.

## Static validation

These commands render or inspect files only; they do not start services:

```bash
python3 scripts/platform.py validate
python3 scripts/platform.py components list
python3 scripts/platform.py backfills check
python3 scripts/validate-compose.py --source-root "$GOD_SOURCE_ROOT"
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

From the repository root, `mise run platform:compose:validate`,
`mise run platform:compose:test`, and `mise run docs:drift` wrap the same gates.
The semantic validator renders default, `tools`, `full`, and `cloud`, then
asserts service cardinality, environment-selected ports, the exact Bloodbank to
Candystore Dapr subscription path, dependencies, host boundaries, mounts, exact
per-service network isolation, Traefik auth/routing, three external networks,
and five adopted external volumes. Every checked-in JSON render uses Compose
`--no-env-resolution`, so the optional Holocene component env file remains a
path reference and its values do not enter captured output.

## Component CLIs on PATH

Every 33GOD component CLI runs by its native name from any cwd and any PATH
(an agent shell, Candybar, a systemd unit, `env -i`). `cli-launchers.toml`
declares them; one idempotent installer writes the `~/.local/bin` wrappers:

```bash
python3 scripts/cli-launchers.py install [--dry-run]   # write the launchers, then probe every CLI
python3 scripts/cli-launchers.py check                 # (or --check) exit 6 on drift, 1 on a broken CLI; --json for the envelope
python3 scripts/cli-launchers.py upgrade pj skillex    # npm i -g those packages, then rewrite their launchers
python3 scripts/cli-launchers.py upgrade skillex@0.4.10 --dry-run   # pin a version / show the plan only
python3 scripts/cli-launchers.py upgrade --all         # every declared npm-global package
```

- **Node CLIs** (pj, pjangler, px, pilot, flume, fl, krebs, skillex and their
  sibling bins) get a generated `/bin/sh` wrapper that execs mise's Node 24
  (`installs/node/24`, resolved with `mise where node@24`, installed on demand)
  with the package's real `bin` entry from its `package.json`. Entry files stay
  where they are: px/pilot, flume and krebs run from their 33GOD checkouts; pj
  and skillex from the one npm install path, the global prefix `~/.local`
  (`~/.local/lib/node_modules/@delorenj/<pkg>`). A node 20 pin in the caller's
  cwd, or a different `node` first on PATH, no longer changes the interpreter.
- **One install path for npm-distributed CLIs.** No generated path carries a
  version directory (`mise/installs/<tool>/0.4.10/...`), so `mise upgrade` and
  `mise prune` cannot strand a wrapper; a launcher whose entry would carry one
  is refused (`E_VERSIONED_PATH`). There is no global `npm:@delorenj/*` mise tool
  for a 33GOD CLI: its shim runs whatever node is on PATH and shadows the
  launcher (skillex failed with `E_NODE_VERSION` in every repo pinning node < 24
  until the global tool was dropped). Per-repo `npm:@delorenj/skillex` pins are
  Story 7.6.
- **Upgrade with `upgrade`, never bare `npm i -g`.** npm deletes the generated
  launchers of the package it replaces (even with `--no-bin-links`) and refuses
  with EEXIST while one exists. `upgrade` runs `npm i -g --prefix ~/.local --force
  --no-bin-links <pkg>@latest` with the pinned Node's npm, then re-runs install
  for those packages' launchers even when npm failed, so PATH is never left
  without them. `repo:` packages (px, flume, krebs) update with git.
- **Script entries** (`[[script_cli]]`: hermes-pm) are symlinked from a checkout
  file into `~/.local/bin`; `check` covers drift and runs them. This is how
  `hermes-pm` reaches the Mac peer.
- **Python CLIs** (candybar, candystore, bb, wax, waybill) are not wrapped:
  their uv tool venvs and repo launchers already pin the interpreter. `check`
  probes them too.
- Probes run each CLI from a scratch directory in three environments: under
  `env -i HOME PATH=~/.local/bin:/usr/bin:/bin`; with a decoy `node` first on
  PATH and a `mise.toml` pinning node 20 in the cwd; and under
  `mise exec -- <cli>` with mise, the mise shims dir and `~/.local/bin` on PATH
  as an agent shell has them, in a scratch dir whose trusted `mise.toml` pins
  node 20. The third is the one that catches a shim or mise tool shadowing the
  launcher. Limitation: the global mise config's `[env]` runs `op read`; with
  no 1Password session `mise exec` fails and the probe is skipped with a
  `W_MISE_PROBE_SKIPPED` warning (never a silent pass; `--no-mise-probe` skips
  it deliberately). Every bin of every package is probed with a no-side-effect
  invocation where one exists (`--version`, `--help`, `--pm-launcher`) and
  every Node launcher's entry also gets `node --check`, so pjangler-mcp and
  pjangler-prompt are proven to exist and parse.
- Exits follow the shared table: 0 ok, 1 failure, 2 usage/config, 4 partial,
  6 drift. Tests: `tests/test_cli_launchers.py`.

## Runtime inputs

The root stack uses external networks `bloodbank-network`,
`candystore-internal`, and `proxy`, plus the five adopted external volumes.
`holocene-api.service` remains the host API authority. Bloodbank, Candystore,
Holocene, and PJangler sources must be clean and match the root gitlinks.

Verify clean, pinned component inputs without displaying file contents:

```bash
candidate_root=$(git rev-parse --show-toplevel)
for component in bloodbank candystore holocene pjangler; do
  expected=$(git -C "$candidate_root" ls-tree HEAD "$component" | awk '{print $3}')
  actual=$(git -C "$GOD_SOURCE_ROOT/$component" rev-parse HEAD)
  test "$actual" = "$expected"
  test -z "$(git -C "$GOD_SOURCE_ROOT/$component" status --porcelain)"
done
```

The dependency order is NATS, NATS initialization and placement,
Candystore PostgreSQL, Candystore app, exactly one Candystore sidecar, Holocene
API preflight, then Holocene web. Verify the durable `candystore-events`
consumer cardinality after startup.

See [the topology audit](./docs/integrated-compose-topology-audit.md) for the
evidence, port table, health signals, ownership, and cutover acceptance checks.
