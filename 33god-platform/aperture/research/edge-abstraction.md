# Edge abstraction — how the stack stays edge-agnostic (traefik / caddy / none)

Question (operator, 2026-10-23): traefik is an opinionated choice. Package it
as optional? Abstract so 33GOD works with caddy or nothing? If we ship both
as concrete swappable modules, how do we facilitate that — composable
compose.ymls?

## The seam

**Apps never know the edge exists.** Every service binds to the internal
compose network only (no published ports except loopback for debugging).
TLS termination, hostname routing, and public exposure live entirely in an
edge module. That single rule makes the edge swappable.

## Mechanism: Compose `include` + profiles

Docker Compose ≥2.20 supports `include:` — a base file pulls in other compose
files and they share networks/volumes by name. Combined with `profiles:`.
Adopted refinement (Rererere handoff 2026-10-23): incompatible selections
(e.g. two edges at once) are rejected at **config-render time** by a
pre-flight validator — never by a late runtime rejection container.

```
33god-stack/
  compose.yml                 # the 8 groups, internal binds only, no edge
  edges/
    traefik.compose.yml       # include-able: traefik + labels-based routing
    caddy.compose.yml         # include-able: caddy + generated Caddyfile
    none.compose.yml          # loopback ports only (LAN/tailscale deploy)
```

Bring-up variants:

- `docker compose -f compose.yml up` — headless (internal network only)
- `docker compose -f compose.yml -f edges/traefik.compose.yml up` — traefik edge
- `docker compose -f compose.yml -f edges/caddy.compose.yml up` — caddy edge

(or `include: [edges/${GOD_EDGE:-none}.compose.yml]` with a .env selecting it,
so the default single-command promise holds: `GOD_EDGE=traefik docker compose up`.)

## Routing table ownership — the real problem

Traefik discovers routes via docker labels; caddy via Caddyfile directives.
If apps carry traefik labels, caddy can't read them — that's the coupling to
kill. Options, ranked:

1. **Edge module owns the whole routing table** (recommended). Each edge module
   contains its own complete route config (traefik: dynamic file provider or
   labels applied via the edge's own service definitions; caddy: Caddyfile
   generated at image build). Apps stay pure. Cost: adding a service means
   touching the edge module too — acceptable, services change rarely.
2. **Shared service registry + generator.** One `routes.yaml` (service →
   hostname → upstream), each edge module builds its config from it at startup
   (entrypoint script or build step). More machinery; pays off only if we
   add/remove services often or support a third edge.
3. **Labels with an adapter.** Apps carry neutral labels (`god.route=foo.delo.sh`),
   each edge module translates. Fragile; skip.

Start with (1); graduate to (2) when a third edge or frequent service churn
appears.

## What ships in phase 1

- G-groups with internal binds (also fixes a latent security smell: several
  current stacks publish ports that only the edge needs)
- `edges/none` (default: loopback/tailscale) + `edges/traefik` (reference)
- caddy module as a fast-follow proving the seam is real — a second consumer
  is the only honest test of an abstraction

## Decisions needed from operator

- Default edge for the product: none (loopback) vs traefik?
- Is wildcard-DNS + ACME (the delo.sh pattern) part of the product, or does
  the customer bring their own domain story? (Lean: customer's domain, their
  DNS; we document the ACME generic.)
