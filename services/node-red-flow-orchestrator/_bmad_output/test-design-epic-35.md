---
stepsCompleted: ['step-01-detect-mode', 'step-02-load-context', 'step-03-risk-and-testability', 'step-04-coverage-plan', 'step-05-generate-output']
lastStep: 'step-05-generate-output'
lastSaved: '2026-04-03'
---

# Test Design: Epic GOD-35 - Add Tests for node-red-flow-orchestrator

**Date:** 2026-04-03
**Author:** Jarad DeLorenzo
**Status:** Draft

---

## Executive Summary

**Scope:** Epic-level test design for GOD-35 (node-red-flow-orchestrator)

**Risk Summary:**

- Total risks identified: 10
- High-priority risks (>=6): 6
- Critical categories: TECH (4), OPS (2), DATA (1)

**Coverage Summary:**

- P0 scenarios: 13
- P1 scenarios: 13
- P2/P3 scenarios: 9
- **Total**: 35 tests, effort M-L

---

## Not in Scope

| Item | Reasoning | Mitigation |
|------|-----------|------------|
| **Node-RED flow E2E tests** | Requires live Node-RED + RabbitMQ + MinIO + Fireflies. Too many external deps for first test pass. | Covered by P3-T35 as future smoke test. Manual validation via Node-RED UI. |
| **holyfields-in/out integration tests** | Require live RabbitMQ broker and HTTP mock server. Integration test infra not yet established. | Deferred to follow-up. Unit-testable logic in lib/holyfields.js is covered at P0. |
| **Performance/load testing** | No baseline exists. Premature before functional coverage. | Monitor via Node-RED status nodes and PM2 metrics. |

---

## Risk Assessment

### High-Priority Risks (Score >=6)

| Risk ID | Category | Description | P | I | Score | Mitigation | Owner | Timeline |
|---------|----------|-------------|---|---|-------|------------|-------|----------|
| R10 | OPS | `holyfields-in` uses `amqp.connect()` not robust; RabbitMQ restart = silent death | 3 | 3 | **9** | Document limitation; architectural fix to use `connect_robust` pattern | Node-RED team | Next sprint |
| R1 | TECH | `resolveSchema()` circular `$ref` could cause infinite recursion | 2 | 3 | **6** | Unit tests T01-T04 validate depth guard and seen-set | Node-RED team | GOD-35 |
| R2 | TECH | `deepMerge()` silently replaces arrays instead of merging | 3 | 2 | **6** | Unit tests T09-T10 document and validate behavior | Node-RED team | GOD-35 |
| R3 | TECH | `ensureEnvelopeCompat()` mutates input object | 2 | 3 | **6** | Unit tests T07-T08 validate mutation behavior | Node-RED team | GOD-35 |
| R5 | DATA | `buildDefaultValue()` picks first oneOf/anyOf variant arbitrarily; nullable types produce wrong defaults | 2 | 3 | **6** | Unit tests T05-T06 cover nullable union cases | Node-RED team | GOD-35 |
| R7 | OPS | `minio_presign.py` no upload timeout; hung MinIO blocks exec node | 2 | 3 | **6** | Unit tests T27-T29 cover error paths | Node-RED team | GOD-35 |

### Medium-Priority Risks (Score 3-4)

| Risk ID | Category | Description | P | I | Score | Mitigation | Owner |
|---------|----------|-------------|---|---|-------|------------|-------|
| R4 | PERF | `getValidator()` creates new AJV instance on cache miss | 2 | 2 | 4 | Unit tests T11-T13 validate caching |  Node-RED team |
| R9 | TECH | `holyfields-out` fetch timeout races with AbortController | 2 | 2 | 4 | Deferred to integration test phase | Node-RED team |
| R8 | OPS | `extract_audio.py` no ffmpeg existence check | 1 | 3 | 3 | Unit test T26 covers non-media rejection | Node-RED team |

### Low-Priority Risks (Score 1-2)

| Risk ID | Category | Description | P | I | Score | Action |
|---------|----------|-------------|---|---|-------|--------|
| R6 | DATA | `apply_config.py` substitution on non-string values | 1 | 2 | 2 | Monitor; unit tests T20-T23 cover edge cases |

---

## Entry Criteria

- [x] Audit complete with remediation branch (`audit/node-red-remediation`)
- [ ] Remediation branch merged to main
- [ ] vitest installed in holyfields node package
- [ ] pytest available in scripts/.venv
- [ ] Fixture schema files created in test directory

## Exit Criteria

- [ ] All P0 tests passing (13/13)
- [ ] All P1 tests passing or triaged (>=12/13)
- [ ] No open high-severity bugs in tested modules
- [ ] Line coverage >= 80% on `lib/holyfields.js`
- [ ] Branch coverage >= 70% on `lib/holyfields.js`

---

## Test Coverage Plan

### P0 (Critical) - Run on every PR

**Criteria**: Core schema engine functions + High risk (>=6) + No workaround

| Requirement | Test Level | Risk Link | Tests | Owner | Notes |
|-------------|-----------|-----------|-------|-------|-------|
| `resolveSchema()` resolves simple `$ref` across files | Unit | R1 | T01 | DEV | Fixture schemas with cross-file refs |
| `resolveSchema()` handles circular `$ref` without recursion | Unit | R1 | T02 | DEV | Validates depth=20 guard fires |
| `resolveSchema()` merges `allOf` schemas | Unit | R1 | T03 | DEV | Properties and required arrays merged |
| `resolveSchema()` picks first `oneOf`/`anyOf` | Unit | R5 | T04 | DEV | Verify deterministic selection |
| `buildDefaultValue()` produces valid object defaults | Unit | R5 | T05 | DEV | Required fields populated, optional skipped |
| `buildDefaultValue()` handles nullable unions | Unit | R5 | T06 | DEV | No crash on `["string", "null"]` type |
| `ensureEnvelopeCompat()` fills missing fields | Unit | R3 | T07 | DEV | event_id, timestamp, source auto-generated |
| `ensureEnvelopeCompat()` preserves existing fields | Unit | R3 | T08 | DEV | Pre-set event_id not overwritten |
| `deepMerge()` merges nested objects | Unit | R2 | T09 | DEV | Recursive object merge verified |
| `deepMerge()` replaces arrays entirely | Unit | R2 | T10 | DEV | Documents intentional array replacement |
| `getValidator()` returns cached validator | Unit | R4 | T11 | DEV | Second call same schemaPath = same instance |
| `getValidator()` validates correct envelope | Unit | R4 | T12 | DEV | Known-good envelope passes |
| `getValidator()` rejects invalid envelope | Unit | R4 | T13 | DEV | Missing required field fails |

**Total P0**: 13 tests

### P1 (High) - Run on PR to main

**Criteria**: Important catalog/utility functions + Medium risk + Common paths

| Requirement | Test Level | Risk Link | Tests | Owner | Notes |
|-------------|-----------|-----------|-------|-------|-------|
| `loadCatalog()` discovers all schemas from fixture dir | Unit | - | T14 | DEV | Temp dir with fixture .json files |
| `loadCatalog()` skips manifest.json and _common/ | Unit | - | T15 | DEV | Verify exclusion filters |
| `getSchemaCatalog("vetted")` returns only vetted | Unit | - | T16 | DEV | Assert filtered by VETTED_SCHEMA_PATHS |
| `getSchemaCatalog("all")` returns everything | Unit | - | T17 | DEV | Assert unfiltered count |
| `deriveEventType()` from schema const | Unit | - | T18 | DEV | event_type.const = "foo.bar" |
| `deriveEventType()` fallback to path | Unit | - | T19 | DEV | No const, path "foo/bar.v1.json" -> "foo.bar" |
| `apply_config()` substitutes ${KEY} in strings | Unit | R6 | T20 | DEV | pytest |
| `apply_config()` leaves non-string values alone | Unit | R6 | T21 | DEV | Numbers, booleans, nulls unchanged |
| `apply_config()` preserves unmatched ${UNKNOWN} | Unit | R6 | T22 | DEV | No KeyError, placeholder survives |
| `apply_config()` no recursive substitution | Unit | R6 | T23 | DEV | Value containing ${X} not re-expanded |
| `extract_audio.py` detects video -> extracted=true | Unit | R8 | T24 | DEV | Mock subprocess; check JSON output |
| `extract_audio.py` passes audio -> extracted=false | Unit | R8 | T25 | DEV | Audio file passthrough |
| `extract_audio.py` rejects non-media | Unit | R8 | T26 | DEV | .pdf -> success=false |

**Total P1**: 13 tests

### P2 (Medium) - Run nightly

**Criteria**: Secondary modules + Integration points + Error paths

| Requirement | Test Level | Risk Link | Tests | Owner | Notes |
|-------------|-----------|-----------|-------|-------|-------|
| `minio_presign.py` returns JSON output | Unit | R7 | T27 | DEV | Mock boto3 client |
| `minio_presign.py` exits 2 on missing credentials | Unit | R7 | T28 | DEV | Unset env vars |
| `minio_presign.py` exits 2 on missing file | Unit | R7 | T29 | DEV | Non-existent path |
| `bloodbank_subscribe.py` connects and prints | Integration | R10 | T30 | DEV | Requires test RabbitMQ or skip |
| Admin API `/holyfields/schemas` returns catalog | Integration | - | T31 | DEV | node-red-node-test-helper |
| Admin API `/holyfields/schema?path=...` returns details | Integration | - | T32 | DEV | node-red-node-test-helper |

**Total P2**: 6 tests

### P3 (Low) - Run on-demand

**Criteria**: Nice-to-have + Exploratory

| Requirement | Test Level | Tests | Owner | Notes |
|-------------|-----------|-------|-------|-------|
| `pickDefaultString()` generates UUID for _id fields | Unit | T33 | DEV | Regex match UUID format |
| `normalizeSourceType()` maps "watcher" to "file_watch" | Unit | T34 | DEV | Alias mapping |
| Full ingest pipeline smoke test | E2E | T35 | DEV | Requires live infra; deferred |

**Total P3**: 3 tests

---

## Execution Order

### Smoke Tests (<5s)

- [ ] T09: `deepMerge()` nested objects (instant)
- [ ] T10: `deepMerge()` array replacement (instant)
- [ ] T07: `ensureEnvelopeCompat()` fills missing (instant)

**Total**: 3 scenarios

### P0 Tests (<15s)

- [ ] T01-T04: Schema resolution suite
- [ ] T05-T06: Default value builder suite
- [ ] T07-T08: Envelope compat suite
- [ ] T09-T10: Deep merge suite
- [ ] T11-T13: Validator cache suite

**Total**: 13 scenarios

### P1 Tests (<30s)

- [ ] T14-T19: Catalog and event type suite (JS)
- [ ] T20-T23: apply_config suite (Python)
- [ ] T24-T26: extract_audio suite (Python)

**Total**: 13 scenarios

### P2/P3 Tests (<60s)

- [ ] T27-T29: minio_presign suite (Python)
- [ ] T30: bloodbank_subscribe integration (Python, skip if no RabbitMQ)
- [ ] T31-T32: Admin API integration (JS, node-test-helper)
- [ ] T33-T35: Low-priority and exploratory

**Total**: 9 scenarios

---

## Resource Estimates

### Test Development Effort

| Priority | Count | Effort/Test | Total Effort | Notes |
|----------|-------|-------------|--------------|-------|
| P0 | 13 | S | S-M | Pure function tests, fixture schemas needed |
| P1 | 13 | S | M | Mix of JS and Python, mock setup |
| P2 | 6 | M | M | Integration test infrastructure setup |
| P3 | 3 | S | S | Deferred, minimal effort |
| **Total** | **35** | - | **M-L** | - |

### Prerequisites

**Test Data:**

- Fixture schema directory with 3-5 minimal JSON schemas (simple, $ref, allOf, oneOf, circular)
- Fixture flow JSON for apply_config tests

**Tooling:**

- `vitest` for JS unit tests (add to holyfields package.json devDependencies)
- `pytest` for Python unit tests (add to scripts/.venv via `uv pip install pytest`)
- `node-red-node-test-helper` for Node-RED integration tests (add to holyfields devDependencies)

**Environment:**

- Node.js >= 18 (already satisfied)
- Python 3.12+ with uv (already satisfied)
- ffmpeg on PATH (already installed for split-silence)
- RabbitMQ accessible at localhost:5672 (for P2 integration tests only; skip if unavailable)

---

## Quality Gate Criteria

### Pass/Fail Thresholds

- **P0 pass rate**: 100% (no exceptions, merge blocker)
- **P1 pass rate**: >=95% (waivers required for failures)
- **P2/P3 pass rate**: >=90% (informational)
- **High-risk mitigations**: 100% complete or approved waivers

### Coverage Targets

- **lib/holyfields.js line coverage**: >= 80%
- **lib/holyfields.js branch coverage**: >= 70%
- **Python scripts line coverage**: >= 60% (lower bar, simpler code)

### Non-Negotiable Requirements

- [ ] All P0 tests pass
- [ ] No high-risk (>=6) items unmitigated
- [ ] `resolveSchema()` circular ref guard verified (R1)
- [ ] `ensureEnvelopeCompat()` mutation behavior documented (R3)

---

## Mitigation Plans

### R10: holyfields-in silent death on RabbitMQ restart (Score: 9)

**Mitigation Strategy:** Document as known limitation in GOD.md. Architectural fix: replace `amqp.connect()` with a reconnection wrapper that catches connection close events and re-establishes the channel. Consider `amqplib`'s `createConnection` with heartbeats + error handler that calls `startConsumer()` again.
**Owner:** Node-RED team
**Timeline:** Next sprint (separate ticket from GOD-35)
**Status:** Planned
**Verification:** Integration test with RabbitMQ restart during active consumption

### R1: resolveSchema() circular $ref recursion (Score: 6)

**Mitigation Strategy:** Unit tests T01-T04 with fixture schemas containing direct and indirect circular references. Validate that depth=20 guard and `seen` set prevent infinite loops.
**Owner:** Node-RED team (GOD-35)
**Timeline:** This epic
**Status:** Planned
**Verification:** Tests T02 passes with circular fixture schema; function returns without hang

### R2: deepMerge() array replacement (Score: 6)

**Mitigation Strategy:** Unit tests T09-T10 document and validate the intentional behavior. Add inline comment in source code clarifying arrays are replaced, not concatenated.
**Owner:** Node-RED team (GOD-35)
**Timeline:** This epic
**Status:** Planned
**Verification:** Test T10 asserts `deepMerge({a:[1]}, {a:[2]})` returns `{a:[2]}`

### R3: ensureEnvelopeCompat() input mutation (Score: 6)

**Mitigation Strategy:** Unit tests T07-T08 verify mutation behavior. If callers reuse input objects, consider adding a shallow clone at the top of the function.
**Owner:** Node-RED team (GOD-35)
**Timeline:** This epic
**Status:** Planned
**Verification:** Test passes confirming original object is modified (documenting current behavior)

### R5: buildDefaultValue() nullable union handling (Score: 6)

**Mitigation Strategy:** Unit tests T05-T06 with schemas using `oneOf: [{type: "null"}, {type: "string"}]` and `anyOf` variants. Verify non-null variant is selected.
**Owner:** Node-RED team (GOD-35)
**Timeline:** This epic
**Status:** Planned
**Verification:** Test T06 confirms non-null default returned for nullable union

### R7: minio_presign.py no upload timeout (Score: 6)

**Mitigation Strategy:** Unit tests T27-T29 cover error paths. Future enhancement: add `connect_timeout` and `read_timeout` to boto3 Config.
**Owner:** Node-RED team (GOD-35)
**Timeline:** This epic (tests); next sprint (timeout fix)
**Status:** Planned
**Verification:** Tests T28-T29 verify clean exit on error conditions

---

## Assumptions and Dependencies

### Assumptions

1. The `audit/node-red-remediation` branch will be merged before test implementation begins
2. Fixture schemas can be minimal (3-5 fields) and don't need to mirror production schemas exactly
3. Python tests can run in the existing `scripts/.venv` with pytest added
4. RabbitMQ may not be available in CI; integration tests (T30-T32) should be skippable

### Dependencies

1. `vitest` added to holyfields `package.json` devDependencies
2. `node-red-node-test-helper` added to holyfields `package.json` devDependencies
3. `pytest` installed in `scripts/.venv`
4. Fixture schema directory created at `nodes/node-red-contrib-33god-holyfields/test/fixtures/schemas/`

### Risks to Plan

- **Risk:** Audit branch not merged, tests written against stale code
  - **Impact:** Tests may need rework after merge
  - **Contingency:** Write tests against the audit branch directly

---

## Interworking & Regression

| Service/Component | Impact | Regression Scope |
|-------------------|--------|------------------|
| **Bloodbank** | holyfields nodes publish to /events/custom | Verify envelope format matches Bloodbank API contract |
| **Holyfields schemas** | Schema resolver reads from filesystem | Fixture schemas must match real schema structure |
| **Node-RED runtime** | Nodes register with RED API | node-test-helper simulates RED runtime |

---

## Follow-on Workflows (Manual)

- Run `*atdd` to generate failing P0 tests (TDD red phase)
- Run `*automate` for broader coverage once P0/P1 pass

---

## Appendix

### Knowledge Base References

- `risk-governance.md` - Risk classification framework
- `probability-impact.md` - Risk scoring methodology
- `test-levels-framework.md` - Test level selection
- `test-priorities-matrix.md` - P0-P3 prioritization

### Related Documents

- Audit Report: `services/node-red-flow-orchestrator/AUDIT_REPORT.md`
- GOD.md: `services/node-red-flow-orchestrator/GOD.md`
- C4 Architecture: `services/node-red-flow-orchestrator/docs/architecture/`
- Plane Ticket: GOD-35 (33GOD Infrastructure board)

---

**Generated by**: BMad TEA Agent - Test Architect Module
**Workflow**: `bmad-testarch-test-design`
**Mode**: Epic-Level, Sequential execution
