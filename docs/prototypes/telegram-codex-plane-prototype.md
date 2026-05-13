# Telegram → Codex → Plane Prototype Plan
**Epic:** BRD-2 | **Tickets:** BRD-3 (TEL-1), BRD-4 (PLN-1), BRD-5 (TSK-1)
**Goal:** One-command `/goal fix the auth bug` in Telegram spawns Codex, tracks in Plane, reports back.

---

## Integration Points (Exact)

| Layer | File/Path | Purpose |
|-------|-----------|---------|
| **Telegram Plugin** | `~/.openclaw/openclaw.json` → `plugins.entries.telegram` | Already enabled. Routes `@GrolfBot` or DM messages to Grolf session. |
| **Agent Config** | `~/.openclaw/openclaw.json` → `agents.list[]` id=`eng` (Grolf) | Grolf receives Telegram messages. `tools.allow` includes `sessions_send`, `exec`. |
| **Codex Dispatch** | `sessions_spawn` with `runtime: "acp"`, `agentId: "codex"` | Native OpenClaw ACP runtime. Spawns Codex in isolated session. |
| **ACPX Binary** | `${ACPX_PLUGIN_ROOT}/node_modules/.bin/acpx` | Direct harness fallback if ACP runtime borks. |
| **Plane API** | `https://plane.delo.sh/api/v1/workspaces/33god/projects/BRD/issues/` | Create + PATCH issues. Key: `plane_api_1396234737e5448fb8980ff84104d54f` |
| **Plane States** | Backlog `f0ed86cd...` / Todo `84bdf414...` / In Progress `e60c590f...` / Done `d2081905...` / Cancelled `d04987a1...` | State machine mapping. |
| **TaskFlow Runtime** | `api.runtime.tasks.flow.fromToolContext(ctx)` | Managed flow lifecycle: create → runTask → setWaiting → finish/fail. |
| **Grolf Workspace** | `~/.openclaw/workspace-grolf/` | Skill files, MEMORY.md, prototype scripts live here. |
| **33GOD Project** | `~/code/33GOD/` | BMAD docs, domain GOD docs, eventual home for the skill package. |

---

## Prototype Architecture

```
Telegram DM (@GrolfBot)
    ↓
Grolf (agent:eng) — parses `/goal <text>`
    ↓
[1] Plane API POST → Create issue BRD-N (state=Todo, label=codex)
    ↓
[2] TaskFlow.createManaged({ controllerId: "telegram-codex-orchestrator", goal: <text> })
    ↓
[3] sessions_spawn({ runtime: "acp", agentId: "codex", thread: true, task: <text> })
    ↓
Codex session runs (isolated, ACP runtime)
    ↓
[4] Grolf polls/watches session via sessions_send or heartbeat
    ↓
[5] On completion:
    - TaskFlow.finish()
    - Plane PATCH → state=Done + append summary
    - Telegram reply: "✅ BRD-N complete: <summary>"
    ↓
[6] On failure:
    - TaskFlow.fail()
    - Plane PATCH → state=Backlog + append error
    - Telegram reply: "❌ BRD-N failed: <error>"
```

---

## Phase 0: Validation (Do This First)

1. **Verify Codex ACP spawn works:**
   ```bash
   # From Grolf session, spawn a trivial Codex task
   sessions_spawn({
     task: "Say hello and confirm you are Codex.",
     runtime: "acp",
     agentId: "codex",
     thread: true,
     mode: "session"
   })
   ```
   → If this fails, fix ACPX plugin first (`acpx` reinstall, gateway restart).

2. **Verify Plane API from Grolf:**
   ```bash
   curl -s -H "X-API-Key: plane_api_1396234737e5448fb8980ff84104d54f" \
     "https://plane.delo.sh/api/v1/workspaces/33god/projects/BRD/issues/BRD-3/"
   ```
   → Must return TEL-1 ticket JSON.

3. **Verify TaskFlow API exists:**
   ```bash
   openclaw status | grep -i taskflow
   # Or check plugin list for taskflow/lobster
   ```

---

## Phase 1: TEL-1 — Telegram /goal Parser (BRD-3)

**Files to create:**
- `~/.openclaw/workspace-grolf/skills/telegram-codex-orchestrator/SKILL.md`
- `~/.openclaw/workspace-grolf/skills/telegram-codex-orchestrator/dispatch.js` (or .ts if Lobster)

**Implementation:**
1. Hook into Grolf's message handler. In OpenClaw, Telegram messages to `@GrolfBot` already route to Grolf session.
2. Parse command regex: `^/goal\s+(.+)$`
3. Reject if no goal text → reply "Usage: `/goal <description>`"
4. On valid parse:
   - Generate deterministic session name: `codex-goal-<timestamp>-<hash>`
   - Call `sessions_spawn` with ACP runtime
   - Return immediate acknowledgment: "🚀 Spawning Codex for: *<goal>* | Session: `<name>`"

**Command variants to support:**
- `/goal <text>` — create + spawn
- `/goal status <session>` — query state
- `/goal list` — list active flows
- `/goal cancel <session>` — requestCancel + cancel

**Exact `sessions_spawn` payload:**
```json
{
  "task": "<goal text from user>",
  "runtime": "acp",
  "agentId": "codex",
  "thread": true,
  "mode": "session",
  "sessionKey": "agent:eng:telegram:default:direct:7564050286"
}
```

---

## Phase 2: PLN-1 — Plane Auto-Create + Sync (BRD-4)

**Files to create:**
- `~/.openclaw/workspace-grolf/lib/plane-client.js` — thin wrapper around Plane REST API

**API wrapper methods:**
```javascript
async createIssue({ name, description, state, labels, parent }) 
async updateIssue(issueId, { state, description }) 
async getIssue(issueId)
```

**State mapping:**
| Event | Plane State ID |
|-------|---------------|
| /goal received | `84bdf414-1f1d-41a3-bd85-d9b6c1c7342b` (Todo) |
| Codex session started | `e60c590f-6513-4114-9115-dcfc3c2f5b39` (In Progress) |
| Codex completed | `d2081905-65f2-49f5-b455-d08347bd1632` (Done) |
| Codex failed | `f0ed86cd-0db2-4166-8fff-ab97536e9060` (Backlog) |
| Cancelled | `d04987a1-d9d4-42b8-82e9-a7f7d9521e41` (Cancelled) |

**Sync trigger points:**
1. **On dispatch** — POST issue, capture `sequence_id` (e.g. BRD-42)
2. **On child task start** — PATCH state → In Progress
3. **On completion** — PATCH state → Done, append Codex final output to description
4. **On failure** — PATCH state → Backlog, append error trace
5. **On cancel** — PATCH state → Cancelled

**Label IDs to attach:**
- `545e9488-67f3-479a-aef4-71e0d119366a` (codex)
- `7720942a-7f41-4815-94d4-7b21986cf43d` (feature)

---

## Phase 3: TSK-1 — TaskFlow Durable Wrapper (BRD-5)

**Files to create:**
- `~/.openclaw/workspace-grolf/lib/taskflow-wrapper.js`

**Flow lifecycle:**
```javascript
const flow = api.runtime.tasks.flow.fromToolContext(ctx);

// 1. Create
const created = flow.createManaged({
  controllerId: "telegram-codex-orchestrator",
  goal: goalText,
  currentStep: "dispatch",
  stateJson: {
    goal: goalText,
    telegramChatId: ctx.chatId,
    planeIssueId: null,
    codexSessionKey: null,
    spawnResult: null,
  },
});

// 2. Run child task (Codex)
const child = flow.runTask({
  flowId: created.flowId,
  runtime: "acp",
  childSessionKey: "agent:eng:acp:codex:<uuid>", // or let runtime assign
  runId: `codex-${Date.now()}`,
  task: goalText,
  status: "running",
  startedAt: Date.now(),
  lastEventAt: Date.now(),
});

// 3. Set waiting (async poll)
flow.setWaiting({
  flowId: created.flowId,
  expectedRevision: created.revision,
  currentStep: "await_codex",
  stateJson: { ... },
  waitJson: { kind: "completion", sessionKey: child.sessionKey },
});

// 4. On resume (completion event from Codex)
flow.resume({ ... });

// 5. Finish or fail
flow.finish({ flowId, expectedRevision, stateJson });
// OR
flow.fail({ flowId, expectedRevision, stateJson, reason: "..." });
```

**Key design decision:**
- Grolf (the orchestrator) remains the owner.
- TaskFlow persists the map between `flowId` ↔ `planeIssueId` ↔ `codexSessionKey`.
- On gateway restart, Grolf reads `memory/context-compaction-latest.md` or queries TaskFlow API for active flows, then resumes polling.

---

## Phase 4: Wire It Together (End-to-End)

**Single handler function:** `handleGoalCommand(ctx, goalText)`

```javascript
async function handleGoalCommand(ctx, goalText) {
  // 1. Create Plane ticket
  const planeIssue = await plane.createIssue({
    name: `CODEX: ${goalText.substring(0, 80)}`,
    description: `Auto-generated from Telegram /goal\n\nOriginal: ${goalText}`,
    state: TODO_STATE,
    labels: [CODEX_LABEL, FEATURE_LABEL],
    parent: EPIC_ID, // d5935edd-26d8-4676-a151-2f039d54f85d
  });
  const planeId = planeIssue.sequence_id; // e.g. BRD-42

  // 2. Create TaskFlow
  const flow = await taskflow.create({ goal: goalText, planeIssueId: planeId });

  // 3. Spawn Codex
  const spawnResult = await sessionsSpawn({
    task: goalText,
    runtime: "acp",
    agentId: "codex",
    thread: true,
    mode: "session",
  });

  // 4. Link everything
  await taskflow.linkSession(flow.flowId, spawnResult.sessionKey);
  await plane.updateIssue(planeIssue.id, { state: IN_PROGRESS_STATE });

  // 5. Reply to Telegram
  await telegramReply(ctx, `🚀 Goal #${planeId} dispatched to Codex.\nSession: \`${spawnResult.sessionKey}\`\nTrack: https://plane.delo.sh/33god/issues/${planeId}`);

  // 6. Start async watcher (poll or event-driven)
  watchCodexSession(spawnResult.sessionKey, flow.flowId, planeIssue.id);
}
```

**Watcher pseudo-code:**
```javascript
async function watchCodexSession(sessionKey, flowId, planeIssueId) {
  // Option A: Poll via sessions API (if exposed)
  // Option B: sessions_send to session with "are you done?"
  // Option C: ACP runtime event hook (preferred if available)

  const result = await pollForCompletion(sessionKey, { timeout: 10 * 60 * 1000 });

  if (result.success) {
    await taskflow.finish(flowId, result.output);
    await plane.updateIssue(planeIssueId, { state: DONE_STATE, description_append: result.output });
    await telegramNotify(`✅ #${planeIssueId} complete.\n${result.output.substring(0, 200)}`);
  } else {
    await taskflow.fail(flowId, result.error);
    await plane.updateIssue(planeIssueId, { state: BACKLOG_STATE, description_append: result.error });
    await telegramNotify(`❌ #${planeIssueId} failed.\n${result.error.substring(0, 200)}`);
  }
}
```

---

## Open Questions / Decisions Needed

1. **How does Grolf watch a spawned Codex session for completion?**
   - `sessions_send` to the child session and parse reply? (polling loop)
   - Does OpenClaw expose a `sessionStatus` or `taskStatus` API?
   - Can we hook into ACP runtime completion events via Lobster/taskflow?
   - **Decision needed before TSK-1 implementation.**

2. **Where does the skill code live?**
   - Option A: Inline in Grolf's session (MEMORY.md + exec scripts)
   - Option B: `~/.openclaw/workspace-grolf/skills/telegram-codex-orchestrator/` (proper skill)
   - Option C: `~/code/33GOD/skills/telegram-codex-orchestrator/` (repo-backed, preferred)
   - **Decision: Start with A, migrate to C once proven.**

3. **Security: should any Telegram user be able to /goal?**
   - Currently Grolf's `elevated.allowFrom` includes Jarad's Telegram ID (`7564050286`).
   - If `@GrolfBot` is public, add allowlist check in handler.
   - **Decision: restrict to `from:7564050286` for prototype.**

4. **Plane project for Codex goals?**
   - Currently using 33GOD/BRD.
   - Could create a dedicated `codex-goals` project.
   - **Decision: use BRD for prototype, split later if noisy.**

---

## Files to Touch (Summary)

| File | Action |
|------|--------|
| `~/.openclaw/workspace-grolf/SKILL.md` | Add `/goal` command reference |
| `~/.openclaw/workspace-grolf/lib/plane-client.js` | **NEW** — Plane API wrapper |
| `~/.openclaw/workspace-grolf/lib/taskflow-wrapper.js` | **NEW** — TaskFlow helper |
| `~/.openclaw/workspace-grolf/skills/telegram-codex-orchestrator/SKILL.md` | **NEW** — Skill definition |
| `~/code/33GOD/docs/prototypes/telegram-codex-plane-prototype.md` | **THIS FILE** — living spec |
| `~/.openclaw/openclaw.json` | **MAYBE** — add `goal-orchestrator` agent or keep as Grolf |

---

## Next Action (Immediate)

**Validate Codex ACP spawn from Grolf right now.**

Run the Phase 0 validation step. If Codex spawns and returns output, we have a working harness. If not, fix ACPX first.

Then: implement `plane-client.js` (2 hours), then wire the `/goal` handler (2 hours). End-to-end demo possible today if no blockers.
