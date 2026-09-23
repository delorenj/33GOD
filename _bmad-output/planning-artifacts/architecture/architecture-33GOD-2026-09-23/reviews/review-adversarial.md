# Architecture Spine Review — Adversarial Divergence Hunt

## Method

Constructed pairs of independent builders that obey the written ADs literally
and checked whether they could still produce incompatible DeloHQ behavior.

## Findings

### High

1. **Two view-model dialects can both satisfy AD-3 and AD-11.** A Company
   adapter could emit `status: "working"` while an Inbox adapter emits
   `state: "active"`; both are typed, versioned, and contract-tested locally.
   The spine needs one shared contract package and one state vocabulary, not just
   a requirement that contracts exist.

2. **Two command adapters can normalize receipts differently.** A Hermes
   adapter could map a timed-out execution to `failed`, while a Krebs adapter
   maps the equivalent provider timeout to `unknown`; both obey AD-7's listed
   states. The canonical mapping and source-state preservation must live in one
   shared contract.

### Medium

3. **Company and Agent Office can read different workforce snapshots.** AD-5
   requires a Flume-backed contract and one transitional adapter, but it does
   not require a shared projection version or snapshot identifier. One screen
   could show an employee after a hire while the other still shows the old
   hierarchy. Require all workforce views in one response cycle to use the same
   projection snapshot metadata.

4. **Now and Inbox can disagree about event grouping and attention.** AD-6 says
   grouping uses correlation or causation, but it does not define a shared item
   identity or precedence when one event is both a briefing and an exception.
   Require the shared contract to own grouping identity and attention
   classification; surfaces may filter or order the result but may not
   reclassify it independently.

5. **Verified Telegram identity can be lost between the public proxy and a
   command.** AD-8 requires actor context to accompany a command, but it does
   not name the command-envelope field or require the internal gateway to reject
   its absence. Require `actor_ref`, `auth_observed_at`, and originating route
   metadata in the command envelope, with fail-closed validation at the gateway.

## Verdict

The spine catches the major ownership and deployment hazards, but the shared
contract seam must be made explicit before parallel builders can safely work on
Company, Inbox, and command/receipt units.
