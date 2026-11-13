# FLUME-76 minimal review-access handoff

## Preserved state

- Candidate frozen: bb9f5603a8ca78d77c9eedd9e64c3e5cfa0356d1.
- BASE: df252be3e2b854abe3449276fa3ac06461d0f8d9.
- Denied review: BLOCKED_NOT_REVIEWED, no SPEC verdict; QUALITY not started.
- Exact denial: flume76-review-denial.md in this directory.
- No retry of denied command, alternate source path/tool or replacement agent.

## Minimal operator-approved scope

A reviewer whose PRIMARY working directory is the existing checkout:
/home/delorenj/code/33GOD/flume/.claude/worktrees/FLUME-76-agent-message-coordination

Read this checkout and linked Git metadata needed for read-only status/revision/
diff inspection, live FLUME-76 ticket via read-only px, prior scratch review reports,
and referenced parent acceptance/denial evidence. No source/index/ref writes.

Optional validation scope must be explicit: execute the inspected local structural
validator/regression scripts with Python bytecode disabled; allow temporary
artifact-copy mutations and report writes only under /home/delorenj/.claude/tmp/.
No native messaging, Redis, gateway control, board writes, merge/push/publication.
Tests/reports are not included in a plan-mode read-only grant automatically.

## Supported operator launch route

Operator starts a new session rooted in the approved checkout, not another
pjangler-isolated agent. In a terminal (or using the current session's ! prefix):

```sh
cd /home/delorenj/code/33GOD/flume/.claude/worktrees/FLUME-76-agent-message-coordination
claude --permission-mode plan
```

Do not use -w/--worktree for this launch: it must inspect the already existing
candidate, not create another default-branch checkout. This is a proposed operator
action, NOT something this orchestrator ran or an exception to a denying guard.

Initial prompt to the newly approved session:

> Independent SPEC review of FLUME-76. Inspect the actual BASE
> df252be3e2b854abe3449276fa3ac06461d0f8d9 to HEAD
> bb9f5603a8ca78d77c9eedd9e64c3e5cfa0356d1 diff and live ticket read-only.
> Preserve earlier BLOCKED_NOT_REVIEWED record. Check all four AC and prior
> QUALITY Q1-Q3 repairs; structural validity is not native capability.
> No source/Git/board mutations, native input, gateway action or publication.
> Return SPEC PASS/FAIL or a precise access blocker. Do not execute tests or write
> reports until those scratch-only operations receive their applicable approval.
> After SPEC PASS, a distinct independent QUALITY reviewer is required.

/add-dir or --add-dir is not documented as overriding worktree-isolation Git
checks; do not offer it as sufficient or disable a guard/permission mode. If a
correctly rooted session is still denied, obtain the guard owner's supported
path-and-operation-specific authorization; its custom exception route is not
established by official CLI docs. Do not retry through different tooling.

Sources checked by documentation-only support agent:
- https://code.claude.com/docs/en/sub-agents.md#worktree-isolated-subagents
- https://code.claude.com/docs/en/permissions.md#working-directories
- https://code.claude.com/docs/en/cli-reference.md#cli-flags
- https://code.claude.com/docs/en/hooks-guide.md#hooks-and-permission-modes

## Independent lane closed without touching this boundary

Completed BB-32 fresh local validation is durably recorded at
`i9-bb32-validation.md`: separate 84+2 ASM and 19 attention receipts, unchanged
candidate, no6379 connect trace, owned resource teardown and pytest cleanup caveat.
Remote CI/landing not proven; BB-33 retains its existing prerequisite.
No additional unclaimed ready implementation slice was established in the prior
owner survey; do not invent native code home or duplicate BB-32/BB-35 ownership.
