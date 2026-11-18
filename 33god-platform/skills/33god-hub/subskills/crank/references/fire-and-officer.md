# One crank fire: the gate and the officer

A fire is an **interval driver** (the `interval-driver` skill). A deterministic gate decides,
and the LLM runs only when the pane changed in a way that needs it.

## The chain

1. Candybar runs the binding's row → `pj crank fire <binding>`. pj checks that the agent
   process is the same incarnation and that the project still wants cranking, then pipes
   the policy JSON (project, root, cli, session_id, pid, pid_start, interval, prompt,
   target, rules, officer_profile, officer_max_turns) into the engine.
2. `crank-pane --binding NAME --pane-id N [--session S] < policy.json`
   (`~/.local/bin/crank-pane` → `~/.agents/tools/jev-clairic/bin/crank-pane`). Set
   `CRANK_ENGINE` to swap it out in tests.

## The gate (crank-pane)

| Pane state | Result |
|---|---|
| zellij no longer lists the pane | exit 10 → pj ends the binding, `pane_closed` |
| working (this session's own ASM row, else the pane's ASM row, else the screen moving) | log only |
| working 2h+ straight, first fire of each new hour | officer, class `burn<H>` |
| shell or unknown screen | log only (never type into a shell) |
| waiting, response changed | officer, class `poke` |
| waiting, unchanged for 2 or 6 fires | officer, class `interrogate<N>` |
| waiting, otherwise unchanged | log only |

ASM state is trusted only when the `asm:sweeper` key is present and the row's process is
alive. `failed`, `starting`, `stale` and `gone` fall back to the screen. `failed` is
**not** waiting.

Exit codes: `0` fired or skipped, `10` pane gone, `2` bad input, `3` officer failed.
State: `~/.local/state/crank/<binding>.json` (last class, last officer run). Log:
`~/.local/state/crank/log/<binding>.jsonl`. `pj crank sessions` surfaces both as
`last_class` and `last_officer`.

## The officer

`hermes -p <officer_profile, default 33god-pm> chat -Q …`, kept lean with a few max turns,
on a single-pane brief: the fire's class, the project's `prompt`/`target`/`rules`, and the
agent's last response. The contract text is
`~/.agents/tools/jev-clairic/hermes/crank-officer-prompt.txt`, the source of truth for what
the officer may do. Its budget is at most 3 tool calls; one send is normal, and zero is right
when the pane needs nothing. It ends with `<pane> -> <what you did>`.

The rules it follows are in [officer-contract.md](officer-contract.md).

## Changing it

- Gate logic → `crank-pane`. Officer wording → `crank-officer-prompt.txt`. Policy keys and
  fire preconditions → `pjangler/src/crank/sessions.ts` and `policy.ts`.
- The gate's screen readers are shared with the legacy gate (`zcrank_screen.py`,
  `zcrank.py` classify). Change them once.
- Tests: pjangler `TMPDIR=/tmp node scripts/run-tests.mjs --no-build crank`. They use a
  throwaway redis-server, never the live 6379.
