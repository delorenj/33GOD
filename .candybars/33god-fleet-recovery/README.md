# Fleet recovery — temporary Candybar desk

Owned parent integration follow-up for the November 22 recovery request. This is
not another dispatcher or permanent fleet service. Component fixes remain with
Bloodbank, Flume and PJangler. Only Candybar owns the five-minute clock.

## Review / activation

Manifest: `../33god-fleet-recovery.candybar.toml`, created **disabled**.
The existing definition sync registered it disabled while source was being
written; no scheduled fires or PM recovery writes have occurred. Parent review
must precede `candybar resume 33god-fleet-recovery` from the parent checkout.
Read back with `candybar show 33god-fleet-recovery --json`; then inspect actual
scheduled history and `runtime/runs/*/receipt.json`. Do not use a manual recovery
run as a substitute for the scheduled proof window.

Run tests: `/usr/bin/python3 -I .candybars/33god-fleet-recovery/test_check.py`.
Read-only real-engine probe: `/usr/bin/python3 -I .candybars/33god-fleet-recovery/check.py probe`.
Probe state is separate and never seeds the production gate or completion proof.

## Behavior

Each fire reads `krebs status --json` plus eight live tracked Pilot tickets in
parallel. Stable sorted queue/turn identities and full evidence hashes omit
volatile clocks/ETAs. Unchanged evidence costs zero tokens; a persisting condition
gets a coarse 30-minute escalation. Missing data remains failed/unknown, never
an empty green board. Nonblocking flock covers collection through terminal turn.

Changed evidence invokes a fresh synchronous `hermes -p 33god-pm chat -Q
--query-file - -t terminal,file,no_mcp --max-turns 6 --reasoning medium
--ignore-rules --format stream-json --source tool`. The parent waits at most
240 seconds. The live gateway rejects `--run-budget` despite CLI help, so it is
not passed. On failure/timeout the installed gateway client's session.interrupt
is used for this exact session only; an unsettled/crashed turn blocks subsequent
officers until readback proves it idle. This helper never creates sessions or
spawns gateways. Unknown session identity requires manual inspection; no blind
retry. Actual terminal tool result, session ID, result and measured tokens are
required. Token spend is reported to Candybar; unknown spend is not reported as 0.

Contract: `contract.md`. PM may reconcile only its own board using shared owner
lease/Pilot, route other work through owning PMs, and record quiet local notes.
No dispatch, implementation, restart, credentials or routine Telegram. Explicit
local-only and human holds remain binding. No runtime automatic Git mutations.

Retirement requires PM judgment, installed independent review evidence for
BB-62/FLUME-111/PJAN-229, useful starts/handbacks across affected ready scopes,
three clean spaced scheduled samples spanning >=10 minutes, classified real
held scopes and no unexplained stale ready/failure loops. Original checked
receipts are required under runtime. Driver validates structural evidence,
re-reads sources and pauses only its own named registration through the API,
with pending/completion receipts. Structural validation is not a substitute for
the PM's independent substantive review.

## Real verification

16 isolated tests passed (stable gate/aging/backoff, compact evidence hashing,
unavailable data, real subprocess boundary, timeout, overlap, corruption,
terminal/result evidence, proof rejection and exact self-pause readback).
A read-only real PM probe completed, session
`local-401f909763075296a96ef966116d6fee83c31106fd2090658c4f21dc7e090c76`,
66,785 measured tokens, actual terminal exit 0. It reported all three systemic
fixes still NOT VERIFIED INSTALLED, no recovery writes. Receipt:
`runtime/probes/406918386e404ab79eab8c9a22e12f33/runs/20261123T000814Z-a29fbba2/receipt.json`.
Exact-session gateway readback: settled true, running false, no pending/prompts.

`uv run candybar doctor --repo . --live --json` from candybar exited **2**:
repo pass, zero violations, machine unknown because
`hermes:earshot-pm:b0a35860840f` has no enabled Candybar owner. This unrelated
finding was not changed. Full output: `runtime/verification/doctor.txt`.
Runtime/probe/log files are explicitly ignored; no secrets committed.

## Remaining acceptance

Independent parent review and enabling are deliberately outstanding. No claim
of a scheduled terminal recovery pass, stable live second-fire savings, fixes
installed, or fleet recovery completion is made by this installation.
