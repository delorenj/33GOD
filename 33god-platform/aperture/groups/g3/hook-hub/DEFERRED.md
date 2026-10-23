# hook-hub — deferred with extraction contract

**Status: NOT packaged in G3.** This records the exact read-only crib and the
reasons hook-hub cannot be containerized honestly. This is the G2-curator
pattern, not a fake stub: G3 ships the *event-publication contract* hook-hub
owns, but not the daemon.

## What hook-hub is

`bloodbank/services/hook-hub/` is the single dispatcher for every agent CLI's
hooks. It listens on a host Unix socket, reads `handlers.toml`, executes hook
handlers against host agent CLIs, writes receipts to a host sqlite3 journal,
and publishes `bloodbank.agent.hook.updated` / `bloodbank.system.hook.updated`
facts through a stdlib NATS JetStream publisher.

## Why it is deferred (host-bound, and partly out of scope by D1)

1. **Unix socket to host agent CLIs.** `hub.py` serves a socket under
   `$XDG_RUNTIME_DIR`; the handlers it dispatches are host agent CLIs
   (`~/.local/bin/...`) that do not exist in a container filesystem. A
   containerized hub would accept requests and dispatch nothing.
2. **Handlers reference host paths and services.** `handlers.toml` resolves
   `~/.agents/hooks/hub/concerns.py`, zellij notify scripts, Orca, and
   Hindsight recall — none present or reachable from the G3 bundle.
3. **AAI gateway routing is in-scope content for the host service.** The
   `automaticai-routing-*` handler rows and `automaticai.py` embed the
   AutomaticAI gateway's routing checks. D1 explicitly excludes AAI gateway
   content from G3, so a faithful crib is impossible without violating D1.
4. **Sqlite receipts live on the host.** `receipts.py` writes
   `~/.local/state/...`; persisting those in a container would fake
   persistence G3 does not own.

## What G3 ships instead (the extraction contract)

The one piece of hook-hub that is container-portable — its event publication
path — is cribbed **verbatim** and generalized into the shared
`heartbeat/nats_publish.py` (copied to every G3 service):

- **Crib source:** `bloodbank/services/hook-hub/observations.py` `publish()`
  (lines 20–68): HPUB with `Nats-Msg-Id` + `Nats-Expected-Stream`, correlated
  reply inbox, and PubAck verification (`stream`, `seq >= 1`, no `error`) —
  a PONG is transport progress, never a persistence acknowledgment.
- **Crib source:** `bloodbank/services/agent-hooks/core/nats_publish.py`
  (socket primitives `_connect`/`_send`/`_read_line`/`_config`), with env var
  names adapted from `BLOODBANK_*`/`DECKARD_NATS` to the G3 `GOD_NATS_*`
  convention.

The G3 `G3_EVENTS` stream is the self-contained analogue of hook-hub's
`BLOODBANK_EVENTS` target; it is a fresh, bundle-owned stream, not a second
production Bloodbank bus.

## Extraction contract (what a future group must build)

To containerize hook-hub faithfully, a later group must: (1) provide the host
agent CLIs and their hook workspaces as mounted/adjacent resources, (2) strip
or feature-flag the AAI routing handlers behind a non-AAI decision, (3) replace
the host Unix socket with an in-network transport, and (4) own the receipt
journal as a named volume. Until then it stays host-side, exactly as the
fleet runtime does today.
