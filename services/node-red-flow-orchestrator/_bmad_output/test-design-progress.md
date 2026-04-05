---
stepsCompleted: ['step-01-detect-mode', 'step-02-load-context', 'step-03-risk-and-testability', 'step-04-coverage-plan', 'step-05-generate-output']
lastStep: 'step-05-generate-output'
lastSaved: '2026-04-03'
mode: epic-level
inputDocuments:
  - services/node-red-flow-orchestrator/AUDIT_REPORT.md
  - services/node-red-flow-orchestrator/GOD.md
  - services/node-red-flow-orchestrator/nodes/node-red-contrib-33god-holyfields/lib/holyfields.js
  - services/node-red-flow-orchestrator/nodes/node-red-contrib-33god-holyfields/holyfields-in.js
  - services/node-red-flow-orchestrator/nodes/node-red-contrib-33god-holyfields/holyfields-out.js
  - services/node-red-flow-orchestrator/scripts/apply_config.py
  - services/node-red-flow-orchestrator/scripts/minio_presign.py
  - services/node-red-flow-orchestrator/scripts/extract_audio.py
  - services/node-red-flow-orchestrator/flows/fireflies-bloodbank.json
  - _bmad/tea/agents/bmad-tea/resources/knowledge/risk-governance.md
  - _bmad/tea/agents/bmad-tea/resources/knowledge/probability-impact.md
  - _bmad/tea/agents/bmad-tea/resources/knowledge/test-levels-framework.md
  - _bmad/tea/agents/bmad-tea/resources/knowledge/test-priorities-matrix.md
---

# Test Design Progress - node-red-flow-orchestrator

## Step 1: Mode Detection

- **Mode:** Epic-Level
- **Epic:** GOD-35 (Add tests for node-red-flow-orchestrator)
- **Rationale:** Specific epic with acceptance criteria from audit. No PRD/ADR pair exists.

## Step 2: Context Loaded

### Configuration
- `tea_use_playwright_utils`: N/A (no browser UI testing)
- `tea_use_pactjs_utils`: N/A (no contract testing)
- `tea_pact_mcp`: N/A
- `tea_browser_automation`: N/A
- `test_stack_type`: backend (Node.js + Python, no frontend UI)
- `detected_stack`: backend

### Stack Detection
- **Node.js:** package.json with ajv, ajv-formats, amqplib dependencies
- **Python:** aio-pika, boto3 in venv
- **No frontend framework** (Node-RED is runtime, not a build target)
- **No existing test infrastructure** (zero test files, no test scripts in package.json)

### Existing Test Coverage
- **Test files found:** 0
- **Test scripts in package.json:** None
- **Test framework configured:** None
- **Coverage:** 0% across all modules

### Key Modules to Test (from audit)
1. `lib/holyfields.js` (483 lines) - Schema resolver, validator, default builder, envelope compat
2. `holyfields-in.js` (180 lines) - RabbitMQ consumer node
3. `holyfields-out.js` (176 lines) - HTTP publisher node
4. `apply_config.py` (46 lines) - JSON config templating
5. `minio_presign.py` (75 lines) - S3 upload + presign
6. `extract_audio.py` (119 lines) - Video-to-audio extraction

### Knowledge Fragments Loaded
- risk-governance.md (core)
- probability-impact.md (core)
- test-levels-framework.md (core)
- test-priorities-matrix.md (core)

## Step 3: Risk & Testability Assessment

### Risk Assessment Matrix

| # | Risk | Cat | P | I | Score | Mitigation |
|---|------|-----|---|---|-------|------------|
| R1 | `resolveSchema()` infinite recursion on circular `$ref` | TECH | 2 | 3 | **6** | Unit test circular refs; validate depth guard |
| R2 | `deepMerge()` silently replaces arrays | TECH | 3 | 2 | **6** | Unit test array merge; document behavior |
| R3 | `ensureEnvelopeCompat()` mutates input object | TECH | 2 | 3 | **6** | Unit test mutation; verify callers don't reuse |
| R4 | `getValidator()` creates new AJV per call (cache miss path) | PERF | 2 | 2 | 4 | Unit test cache hit/miss |
| R5 | `buildDefaultValue()` wrong types for nullable unions | DATA | 2 | 3 | **6** | Unit test oneOf/anyOf with nullable |
| R6 | `apply_config.py` substitution on non-string values | DATA | 1 | 2 | 2 | Unit test mixed-type JSON |
| R7 | `minio_presign.py` no upload timeout | OPS | 2 | 3 | **6** | Unit test error paths |
| R8 | `extract_audio.py` no ffmpeg existence check | OPS | 1 | 3 | 3 | Unit test missing-binary path |
| R9 | `holyfields-out` fetch/abort race | TECH | 2 | 2 | 4 | Integration test slow endpoint |
| R10 | `holyfields-in` no reconnect on RabbitMQ restart | OPS | 3 | 3 | **9** | Integration test + arch fix |

### High Risks (Score >= 6)

- **R10 (9):** `holyfields-in` uses `amqp.connect()` not robust. RabbitMQ restart = silent death.
- **R1 (6):** Circular `$ref` depth guard untested.
- **R2 (6):** Array replacement in `deepMerge()` undocumented and surprising.
- **R3 (6):** Input mutation in `ensureEnvelopeCompat()` risks cross-contamination.
- **R5 (6):** Nullable union handling picks `oneOf[0]` arbitrarily.
- **R7 (6):** No upload timeout in `minio_presign.py`.

### Testability Assessment

**Controllability:** High. JS functions are pure/near-pure. Python scripts are CLI tools. Node-RED nodes testable via `node-test-helper`.

**Observability:** High. JS returns values. Python outputs JSON stdout. Nodes emit status/warn/error.

**Isolation Concerns:**
- `holyfields-in`: needs live RabbitMQ or mock
- `holyfields-out`: needs mock HTTP server
- `minio_presign.py`: needs moto or boto3 mock
- `loadCatalog()`: needs fixture schema files on disk

## Step 4: Coverage Plan & Execution Strategy

### Coverage Matrix

#### P0: Critical (13 tests)
- T01-T04: `resolveSchema()` - $ref resolution, circular guard, allOf merge, oneOf pick
- T05-T06: `buildDefaultValue()` - object defaults, nullable unions
- T07-T08: `ensureEnvelopeCompat()` - fill missing, preserve existing
- T09-T10: `deepMerge()` - recursive merge, array replacement
- T11-T13: `getValidator()` - cache hit, valid envelope, invalid envelope

#### P1: High (13 tests)
- T14-T19: `loadCatalog()`, `getSchemaCatalog()`, `deriveEventType()`
- T20-T23: `apply_config.py` - substitution, non-string, unmatched, no recursion
- T24-T26: `extract_audio.py` - video detect, audio passthrough, non-media reject

#### P2: Medium (6 tests)
- T27-T29: `minio_presign.py` - JSON output, missing creds, missing file
- T30: `bloodbank_subscribe.py` integration test
- T31-T32: Admin API integration tests

#### P3: Nice-to-have (3 tests)
- T33-T34: `pickDefaultString()`, `normalizeSourceType()`
- T35: Full pipeline E2E smoke test

### Execution Strategy
- **PR:** All P0+P1 unit tests (<30s). Gate: 100% P0, >=95% P1.
- **Nightly:** P0+P1+P2 including integration. Gate: all P0/P1 pass, >=90% P2.
- **Weekly:** Full suite + P3 + E2E smoke. Informational.

### Effort Estimates
- P0: S-M | P1: M | P2: M (integration setup) | P3: S
- Total: M-L

### Quality Gates
- P0 pass rate: 100% (merge blocker)
- P1 pass rate: >= 95%
- High-risk mitigations (R1-R3, R5, R7, R10) covered before release
- Line coverage: >= 80% on lib/holyfields.js
- Branch coverage: >= 70% on lib/holyfields.js

### Test Frameworks
- JS: vitest + node-red-node-test-helper
- Python: pytest (via uv)
