# Monetization avenue 1 — Lease agents (keep stack local)

**Model.** The stack stays on our hardware; agents are exposed as public,
paid endpoints. Money comes in per use or subscription; the moat never leaves
the building.

**Channels that exist today**
- Cloudflare Agents (public agents, pay-per-use billing primitives)
- Telegram bots (payments built in; the fleet already speaks Telegram natively
  via hermes-gateway)
- Any OpenAI-compatible front door (we own a gateway fork — metering, quotas,
  tokens are already solved problems in new-api)

**What we already have**
- hermes-gateway: multi-profile messaging ingress, running 24/7
- Bloodbank event audit (every agent action is a metered, queryable event)
- Cost bridge: per-call LLM cost lands on the bus already
- Gateway token/quota machinery (model_limits, unlimited_quota flags)

**Gaps to close**
- Tenant isolation: per-customer profiles (Flume can provision these)
- Public billing surface: Stripe/CF checkout in front of token minting
- Abuse controls: rate limits, sandboxing for delegated work, egress policy
- SLA/observability per tenant (G4 stack is the base; needs multi-tenant views)

**Fit with the moat.** High — leasing prices the *integration* (lifecycle,
enrichment, audit), not just a model. Competitors leasing single agents can't
match a full productized dev loop.

**Risk.** Operational: uptime becomes a promise. Support load. One bad tenant
on shared hardware.
