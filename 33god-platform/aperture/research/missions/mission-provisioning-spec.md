# Mission provisioning spec — leasing an agent to a client (v0.1)

How a client goes from "signed" to "their named agent is working" with zero
stack exposure. This is the build spec; `1-lease-agents-deep-dive.md` is the
why. Grounded in the actual mechanics: Flume hire, Hermes profile isolation,
AutomaticAI gateway tokens, Bloodbank attribution.

## What exists today (no new tech needed for v0.1)

- `flume hire` provisions a Hermes employee: profile dir, SOUL, Telegram
  wire-up, systemd units, board link — with `--model-*` overrides pointing
  the agent at any OpenAI-compatible endpoint (ours: the gateway).
- Per-profile isolation: own SOUL, sessions, memory, Hindsight bank
  (`agent-<name>`), own Telegram bot identity.
- Gateway tokens: per-token model_limits + quota → per-client spend control.
- Rererere is the living precedent: a named agent with a real charter, scoped
  memory, direct tone, delegating and verifying — everything a leased agent
  needs except the client wrapper.

## The Mission object

Lives in the client's repo at `mission.yaml` (customer-visible artifact;
we keep the template):

```yaml
# mission.yaml — the entire client-facing surface of the lease
mission: damian-alpha
client:
  name: Damian
  context: ./client-context.md     # operator braindump: who he is, how he works
pillars: ./PILLARS.md              # client's priority-ordered doctrine
scope:
  repos: [delorenj/33GOD]          # what the agent may touch (their accounts)
  boards: [damian-dogfood]         # Plane project or their tracker
  channels: [telegram]             # how the client reaches the agent
budget:
  gateway_token: <minted at provision, model_limits scoped>
  hard_stop_usd_day: 25            # gateway-side enforcement
  alert_usd_day: 15                # ntfy → operator
deliverables:
  review_cadence: daily            # evidence-style reports
  definition_of_done: ticket closed with reviewer != implementer
```

## Provisioning flow (v0.1 = one operator command)

`aperture mission provision <mission.yaml>` (thin wrapper, humans run it):

1. **Hire**: `flume hire --definition <client-agent.def> --skip-plane`
   — new profile `damian-alpha`, own SOUL rendered from charter template
   (role: client's mission, tone per pillars, recall scope = ONLY
   `agent-damian-alpha` + mission banks).
2. **Charter the SOUL**: pillars imported verbatim; client context loaded as
   standing context; decision compass cites THEIR pillars; crank doctrine +
   reviewer≠implementer + WIP=1 baked in (our defaults, not negotiable —
   they're what makes the autonomy safe).
3. **Mint gateway token**: group per pricing tier (e.g. `lease-fast` =
   auto/fast tier only; `lease-strong` adds strong tier), quota +
   `hard_stop_usd_day`, `unlimited_quota=false`. Token lands in the profile's
   `.env` via the `.env.op` ref pattern — never in git.
4. **Wire channels**: Telegram bot (BotFather) via `flume hire`'s existing
   wire-up; group-chat membership per the client's preference.
5. **Bus attribution**: agent id `damian-alpha` on every event (envelope
   `actor.agent_id`) → Candystore queries = per-client audit export.
6. **Crank + watchdog**: enroll the profile in zcrank registry (enabled=1);
   watchdog alert threshold = `alert_usd_day`.
7. **Prove it**: agent answers a smoke prompt through its Telegram with a
   gateway-metered call; event lands in Candystore; token spend visible in
   the gateway ledger. Provision receipt: all three checks green.

## Boundaries (the moat stays home)

- Client sees: their agent, their board, their reports, their spend summary.
- Client never sees: fleet internals, routing topology, other clients,
  stack source. The Hermes runtime itself is the lease boundary.
- Memory: client agent reads/writes ONLY its own bank. Recall scope is
  pinned in the SOUL (Rererere pattern: "Recall scope (only these banks)").
- Creds: client's repos authenticated with THEIR tokens in their vault slot;
  our gateway token is the only secret the agent holds of ours.

## Enforcement points (all existing machinery)

| Guarantee | Enforced at |
|---|---|
| Spend ceiling | gateway token quota + hard stop |
| Model access | token model_limits (tier groups) |
| Action audit | Bloodbank events → Candystore (per agent id) |
| Memory isolation | profile + Hindsight bank scope |
| Autonomy safety | doctrine in SOUL + crank watchdog |
| Channel identity | per-agent Telegram bot |

## v0.1 scope (what Damian's mission needs — nothing more)

- [ ] Charter template + mission.yaml schema (this doc's shape)
- [ ] Provision wrapper script (steps 1–7 above, ~an afternoon)
- [ ] Lease-fast gateway group + first token mint
- [ ] Client-context template (braindump format)
- [ ] Daily evidence report (reuse the activity-report skill pattern)
- [ ] Spend summary query (candystore + gateway ledger join)

Deferred to v0.2+: multi-client dashboard, self-serve onboarding, SLA
monitoring, contract/termination flow (offboard = `flume offboard` + token
revoke — already exists).

## Pricing hook (from the deep-dive)

Two weeks of Damian's mission produces: tokens/day, intervention rate,
delivery rate. Price = gateway cost × 3–5× or retainer sized from those
numbers. No speculation needed — measure first.
