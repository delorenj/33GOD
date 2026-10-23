# agent-hooks — deferred with extraction contract (D4)

**Status: NOT packaged in G3.** Per D4: "containerize only if its CLI-path
assumptions tolerate a container fs; else documented-deferred with extraction
contract."

## What agent-hooks is

`bloodbank/services/agent-hooks/` is a host-side tool that discovers agent
CLI executables and mutates their hook configs (`sync.py`,
`forward_envelope.py`, `cli_paths.py`). It publishes through the same stdlib
NATS publisher hook-hub uses (`core/nats_publish.py`).

## Why it is deferred

`cli_paths.py` discovers CLIs via `Path.home()` and `shutil.which()` over
paths such as `~/.local/bin`, `~/.kimi-code/bin`, `~/.config/...`. Those are
host agent installs; a container filesystem has none of them, so a
containerized agent-hooks would discover nothing and sync nothing. It is a
host provisioning tool, not a container service.

## What G3 ships instead

The transport layer agent-hooks uses — `core/nats_publish.py`'s socket
primitives — is cribbed verbatim and generalized into the shared G3
`heartbeat/nats_publish.py` (see `hook-hub/DEFERRED.md` for the full crib
line reference). No agent-hooks daemon or CLI-sync is faked in G3.

## Extraction contract

A future group that wants agent-hooks containerized must mount the host agent
CLI workspaces (or provide them as an image) and map the discovered paths
explicitly; the sync semantics then run unchanged. Until then it stays
host-side, which is where the agent CLIs actually live.
