# Agent leasing — wrap Rererere, sell the outcome (avenue 1 deep-dive)

Operator direction (2026-10-23): deep experimentation on keeping the full
system secret and leasing the agent itself. Mission + client pillars + client
context (braindump) in, autonomous delivery out, every token billed through
AutomaticAI.

## The unit of sale: a Mission

A Mission is the productized version of what 33GOD already does for Jarad:

```
Mission = {
  pillars:     client's priority-ordered doctrine (decision compass)
  context:     operator braindump of the client + their world
  scope:       repos/boards/accounts the agent may touch
  budget:      token/spend ceiling, alert thresholds
  channels:    how the client talks to it (telegram, web, email)
}
```

We already run every piece of this internally: PILLARS.md doctrine, agent
profiles with isolated runtimes, the gateway as single metered front door
(every LLM call through AutomaticAI), Bloodbank audit for every action,
Hindsight memory per client.

## What the client gets

A named agent (like Rererere is for Damian's deployment) that:
- decides with their pillars, not ours
- works their tickets/repos/boards autonomously (crank doctrine: momentum)
- reports with evidence, not status
- is auditable end-to-end (Candystore event trail we can export per client)

What they never get: the stack source, the routing topology, the fleet
internals. The moat stays home. This is "leasing a senior engineer who never
sleeps", not "access to a platform".

## Metering = already solved

- All agent LLM traffic → AutomaticAI gateway → per-token accounting, quotas,
  model routing tiers. `metered_cost` machinery exists.
- Margin: lease price = gateway cost × multiplier (or flat retainer +
  overage). Cost bridge already emits per-call cost events per agent.
- Per-client gateway tokens with model_limits → a client can be restricted to
  cheap tiers or given frontier access as a pricing tier.

## Multi-tenant isolation model (the real engineering)

Per client:
1. **Hermes profile** (Flume-provisioned): own SOUL, own session/memory dirs,
   own Hindsight bank. Nothing shared with other clients.
2. **Gateway token** scoped by model_limits + quota.
3. **Work surfaces**: their repos (their accounts), their board (Plane project
   or their tracker), their Telegram bot front door.
4. **Crank/watchdog** per client profile (the existing cron machinery,
   namespaced).
5. **Secrets**: client credentials in their own vault slot; agent never holds
   ours.

Shared: the bus, the fleet host, observability, the gateway. Bloodbank events
carry agent identity → clean per-client audit extraction.

## Experiment to run first (cheap, decisive)

**Dogfood it on Damian — he's the perfect first customer.**
1. Provision a `rererere-client` mission: pillars from his stated priorities,
   Jarad's braindump as context, scope = his repos, budget = token ceiling.
2. Run a real 2-week engagement (the Aperture dogfood IS the workload).
3. Measure: tokens/day (gateway ledger), intervention rate (how often Jarad/
   Rererere had to step in), delivery rate (tickets closed), client-reported
   value.
4. Price from those numbers: cost × 3–5× or retainer sizing.

## Risks

- **Hallucinated autonomy**: an agent loose on a client's production needs the
  reviewer≠implementer gate and WIP=1 exactly like our internal fleet —
  bake the doctrine into every mission, not just ours.
- **Cross-client contamination**: memory banks and bus events must be
  client-namespaced; audit queries prove it (test: extract "everything client
  A's agent did" with zero client-B events).
- **One bad tenant**: rate limits + budget hard-stops at the gateway tier.
- **It's services disguised as product**: leasing is an ops business. The
  mission spec + provisioning automation is what makes it scale — that's the
  build work.

## Relation to the other avenues

Leasing is the *soonest* revenue: no images, no licensing, no generalization
needed — Damian's mission could be live this week. Whole-stack licensing
(avenue 2) shares the same multi-tenant patterns later. Not mutually
exclusive; leasing funds the build-out.
