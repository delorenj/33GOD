# Adversarial Audit: node-red-flow-orchestrator

**Date:** 2026-04-01
**Auditor lens:** Communication breakdown across the team; junior architect and implementers; risk of non-idiomatic patterns and architectural non-compliance with 33GOD contracts.

---

## SEVERITY: CRITICAL

### C1. Plaintext Credentials Committed to Git

**File:** `.env:1-2`

```
MINIO_ACCESS_KEY=<redacted>
MINIO_SECRET_KEY=<redacted>
```

There is no `.gitignore` at the project root. The only `.gitignore` in the entire service is inside `scripts/.venv/`. These credentials are committed to the repo and visible to anyone with read access.

**Impact:** Credential exposure. Anyone with repo access gets MinIO admin access.

**Fix:** Add a root `.gitignore` ignoring `.env`, `node_modules/`, `.venv/`, `*.log`. Rotate the exposed MinIO credentials immediately.

---

### C2. Dual Publishing Mechanism Creates a Contract Schism

The service publishes to Bloodbank via **two completely different mechanisms** that are not aware of each other:

1. **Flow JSON (tabs 1 & 3):** Writes envelope to disk, then shells out to `curl -s -X POST http://127.0.0.1:8682/publish -d @file` via exec nodes.
2. **holyfields-out node:** Uses `fetch()` to POST to `http://127.0.0.1:8682/events/custom` with full envelope construction, schema validation, and `ensureEnvelopeCompat()`.

The flow JSON doesn't use the holyfields-out node at all. It hand-rolls envelopes in function nodes with hand-rolled `uuidv4()` implementations (Math.random-based, not crypto-safe), uses a different API endpoint (`/publish` vs `/events/custom`), and bypasses all schema validation.

The C4 dynamic diagram (`docs/architecture/c4-dynamic-ingest-flow.md:27-28`) **claims** the flow uses `holyfields-out` for publishing. It does not. The docs and the implementation are out of sync.

**Impact:** The whole point of building `holyfields-out` was to enforce schema-compliant, validated event publishing. The actual production flow completely bypasses it. The team built the right abstraction and then didn't use it.

---

### C3. Flow JSON Uses Different Endpoint Than holyfields-out

The Bloodbank Integration Report (`flows/BLOODBANK-INTEGRATION-REPORT.md`) documents that `localhost` resolves to IPv6 `::1` on this system, causing silent publish failures. The bugfix switched to `127.0.0.1` (good).

But the flow JSON publishes to `127.0.0.1:8682/publish` while holyfields-out publishes to `127.0.0.1:8682/events/custom`. Nobody documented which endpoint is canonical or whether they behave identically. Two publish paths, two endpoints, zero documented rationale.

---

### C4. No GOD.md

Every 33GOD component is required to have a `GOD.md` documenting its event contracts, role, and integration points. From the root `CLAUDE.md`:

> Check component's GOD.md for event contracts BEFORE making changes

This service has no `GOD.md`. The C4 docs in `docs/architecture/` are a partial substitute but don't follow the GOD doc format or hierarchy described in `docs/GOD-SYSTEM-GUIDE.md`.

---

## SEVERITY: HIGH

### H1. Hand-Rolled UUID Generation (Cryptographically Weak)

Two function nodes in `flows/fireflies-bloodbank.json` implement their own UUID generator:

```javascript
function uuidv4() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
    const r = Math.random() * 16 | 0;
    const v = c === 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}
```

`Math.random()` is not cryptographically secure and has collision potential at scale. Node-RED runs on Node.js which has `crypto.randomUUID()` available (used correctly in `holyfields-out.js`). The team who built holyfields-out knew the right way; the team who built the flows didn't.

**Impact:** Event ID collisions are possible. `event_id` is used for correlation tracking across the entire 33GOD pipeline.

---

### H2. Redundant Python/JS Implementation of Identical Logic

The silence-splitting logic exists in **two independent implementations**:

1. `scripts/split_silence.py` (202 lines) - Python CLI script
2. `nodes/node-red-contrib-split-silence/split-silence.js` (313 lines) - Node-RED node

Both implement identical algorithms (silencedetect, invert-to-activity, extract-chunks) with identical ffmpeg CLI invocations. Neither references the other. The Node-RED node is clearly meant to replace the Python script, but the Python script wasn't removed or deprecated.

Similarly, `scripts/extract_audio.py` duplicates audio extraction logic that could be folded into the split-silence node's pipeline.

**Impact:** Two implementations to maintain, debug, and keep in sync. When one gets a bug fix, the other won't.

---

### H3. `bloodbank_subscribe.py` via exec Node is Fragile Architecture

The RabbitMQ consumer (`bloodbank_subscribe.py`) runs as a long-lived spawned process from Node-RED exec nodes. This means:

- **No reconnection logic exposed to Node-RED.** If RabbitMQ restarts, the subscriber process dies. The exec node sees the process exit and... nothing. No retry. The pipeline is silently dead until someone manually restarts.
- **Two separate subscriber management systems.** `start-subscribers.sh` starts subscribers via nohup, while the flow JSON starts them via exec nodes with `inject once=true`. Both exist. Both claim to manage the same queues (`node-red.fireflies.upload`, `node-red.fireflies.ready`). If both run, you get duplicate consumers.
- **The `ready_json` function node has a hand-rolled JSON line buffer** to handle chunked stdout from the spawned process. This is the kind of fragile glue code that breaks silently.

The `holyfields-in` node was specifically built to solve this problem with proper amqplib connections, reconnection via `amqp.connect`, and clean lifecycle management. Again: the right abstraction was built, then not used.

---

### H4. `generate_password_hash.sh` is a Command Injection Vector

**File:** `.mise/scripts/generate_password_hash.sh:3-4`

```bash
read -sp "Enter password: " PASSWORD
node -e "require('bcryptjs').hash('$PASSWORD', 8).then(h => console.log(h))"
```

`$PASSWORD` is interpolated directly into a `node -e` expression without any escaping. A password containing `', process.exit(1));//` or similar would execute arbitrary JavaScript. Textbook injection.

---

### H5. `apply_config.py` Does Naive String Replacement

**File:** `scripts/apply_config.py:19-21`

```python
for key, value in config.items():
    placeholder = f"${{{key}}}"
    flow_content = flow_content.replace(placeholder, value)
```

This replaces `${KEY}` patterns in flow JSON using raw string replacement with no escaping. If a config value contains `${ANOTHER_KEY}`, double substitution occurs. If a config value contains JSON-special characters (`"`, `\`), the output JSON will be malformed. The function operates on raw text, not parsed JSON, so there's no structural validation that the output is even valid JSON.

---

## SEVERITY: MEDIUM

### M1. `node_modules/` Committed for holyfields Node

The holyfields node has `node_modules/` checked in (confirmed via glob results finding test files inside `node_modules/fast-uri/test/`). There's no `.gitignore` in the `nodes/node-red-contrib-33god-holyfields/` directory. `package-lock.json` is present (good), but vendoring `node_modules` into a monorepo submodule is non-idiomatic and bloats the repo.

---

### M2. Hardcoded Absolute Paths Everywhere

| File | Hardcoded Path |
|------|---------------|
| `start-subscribers.sh:6` | `/home/delorenj/code/33GOD/services/node-red-flow-orchestrator/scripts` |
| `.mise/scripts/deploy_flows.sh:4` | `/home/delorenj/.node-red` |
| `nodes/.../lib/holyfields.js:8` | `/home/delorenj/code/33GOD/holyfields/schemas` |
| `flows/fireflies-bloodbank.json` | `/home/delorenj/.node-red/bb/...` (in function nodes) |
| `flows/fireflies-bloodbank.config.json` | `/home/delorenj/code/33GOD/services/...` |

Some of these are mitigated by env vars (`mise.toml` defines `SCRIPTS_DIR`, etc.), but the defaults and fallbacks are all absolute paths to a specific user's home directory. If this service ever needs to run on a different machine, in a container, or by a different user, it will break in a dozen places.

---

### M3. No Tests Whatsoever

Zero test files exist in the entire service. No unit tests for the Python scripts. No unit tests for the Node-RED nodes. No integration tests. No smoke tests. The `lib/holyfields.js` schema resolver is 483 lines of complex `$ref` resolution, `allOf`/`oneOf` merging, and recursive schema walking with zero test coverage.

---

### M4. `start-subscribers.sh` Uses `pkill -f` With No Process Isolation

```bash
pkill -f "bloodbank_subscribe.py" || true
```

This kills **any** process on the system matching `bloodbank_subscribe.py`, not just the ones started by this script. If another service or dev session is running a subscriber, it gets killed.

---

### M5. Default RabbitMQ Credentials in Start Script

**File:** `start-subscribers.sh:8`

```bash
export RABBIT_URL="amqp://guest:guest@localhost:5672/"
```

Using `guest:guest` is standard for local dev, but this is the **only** place `RABBIT_URL` is set for the subscriber processes. It's hardcoded in a shell script, not pulled from env or a config file, and uses the default guest credentials that RabbitMQ disables for non-localhost connections.

---

### M6. `holyfields-in` Default Port Mismatch

The `holyfields-in.html` template defaults the RabbitMQ URL to `amqp://127.0.0.1:5673/` (port **5673**), while:

- `start-subscribers.sh` uses port **5672** (standard AMQP)
- `bloodbank_subscribe.py` reads from `RABBIT_URL` env var (which is set to port 5672)

Port 5673 is non-standard. If someone deploys a holyfields-in node without changing the default, it will fail to connect silently.

---

### M7. Documentation Claims Architecture That Doesn't Exist

The C4 dynamic diagram shows `split-silence` and `extract_audio.py` as part of the ingest pipeline. But the actual `flows/fireflies-bloodbank.json` flow does not include either of them. The flow goes directly from `delay_settle` to `prep_minio`.

The `AUDIO_EXTRACTION_INTEGRATION.md` is an **implementation plan** that was never executed. It describes manual steps for adding nodes in the Node-RED UI that were never done.

The docs describe a more complete system than what was built.

---

## SEVERITY: LOW

### L1. Duplicate `registerAdminRoutes` Guard is Fragile

Both `holyfields-in.js` and `holyfields-out.js` call `registerAdminRoutes(RED)`. The function uses a module-level `adminRoutesRegistered` boolean to prevent double registration. This works because both files import from the same `lib/holyfields.js` module instance. If the module were ever loaded from two different paths (e.g., symlink issues, npm deduplication), the guard would fail and Express would throw duplicate route errors.

### L2. `deploy_flows.sh` Subshell Variable Scope Bug

```bash
find ... -print0 | while IFS= read ...; do
    ...
done
```

The `while` loop runs in a subshell (due to the pipe). Any variables set inside the loop would be lost after the loop exits. Currently this doesn't cause a bug because the loop only writes files, but it's a landmine for future modifications.

### L3. Inconsistent Error Output Conventions

| Script | stderr | stdout |
|--------|--------|--------|
| `bloodbank_subscribe.py` | diagnostics | data (correct) |
| `minio_presign.py` | errors | JSON (correct) |
| `extract_audio.py` | nothing | both success and error JSON (inconsistent) |
| `split_silence.py` | progress | JSON (correct) |

`extract_audio.py` emits error JSON to stdout. If a downstream consumer checks exit code but reads stdout, it will parse an error object as valid data.

---

## Summary: Communication Breakdown Evidence

The audit confirms the communication breakdown hypothesis through several clear signals:

1. **The team built the right abstractions and then didn't use them.** `holyfields-out` and `holyfields-in` are well-engineered nodes for Bloodbank pub/sub. The actual production flow bypasses both, using curl exec nodes and a spawned Python subscriber instead. This suggests the node developers and flow developers were not coordinating.

2. **Documentation describes aspirational architecture, not reality.** The C4 diagrams show `split-silence` and `extract_audio` in the pipeline. The `AUDIO_EXTRACTION_INTEGRATION.md` is a plan that was never executed. The dynamic diagram claims `holyfields-out` publishes events. It doesn't.

3. **Duplicate implementations of the same logic** (Python `split_silence.py` vs JS `split-silence` node) suggest parallel work without awareness of what already exists.

4. **Known bugs documented but workarounds not standardized.** The IPv6 issue was documented in February. The flow was fixed to use `127.0.0.1`, but no architectural decision was made about which endpoint (`/publish` vs `/events/custom`) is canonical.

5. **No GOD.md** means cross-team consumers have no contract reference for this service's events, violating the core 33GOD documentation mandate.

---

## Recommended Remediation Priority

| Priority | Action | Effort |
|----------|--------|--------|
| P0 | Rotate MinIO credentials, add `.gitignore`, remove `.env` from tracking | S |
| P0 | Migrate flow JSON to use `holyfields-out` and `holyfields-in` nodes instead of curl/exec subscribers | L |
| P0 | Create `GOD.md` with event contracts | M |
| P1 | Remove `scripts/split_silence.py` (superseded by the Node-RED node) | S |
| P1 | Replace `Math.random()` UUID with `crypto.randomUUID()` in flow function nodes (or solve via P0 migration to holyfields-out) | S |
| P1 | Fix command injection in `generate_password_hash.sh` | S |
| P1 | Add `.gitignore` to `nodes/node-red-contrib-33god-holyfields/` excluding `node_modules/` | S |
| P2 | Write tests for `lib/holyfields.js` schema resolver | L |
| P2 | Replace hardcoded paths with env var lookups with sensible defaults | M |
| P2 | Fix `apply_config.py` to operate on parsed JSON, not raw text | M |
| P2 | Standardize AMQP port (5672 vs 5673) across all configs | S |
| P2 | Decide and document canonical Bloodbank publish endpoint (`/publish` vs `/events/custom`) | S |
| P3 | Remove `start-subscribers.sh` once flow uses `holyfields-in` | S |
| P3 | Standardize stdout/stderr conventions across Python scripts | S |
