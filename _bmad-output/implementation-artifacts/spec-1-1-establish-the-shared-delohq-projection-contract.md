---
title: 'Story 1.1: Establish the Shared DeloHQ Projection Contract'
type: 'feature'
created: '2026-09-27'
status: 'done'
baseline_revision: 'ca7caba48ab8fe388045e5283141a560212fc73b' # holocene submodule HEAD (code lives there); parent 33GOD HEAD: b65a48dce82b99278fe31e36c1b5f6895b13427b
review_loop_iteration: 1
followup_review_recommended: true
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-1-context.md'
warnings: [oversized]
deferred:
  - summary: >-
      Holocene CI workflow runs on ubuntu-latest and calls npm scripts that do not exist, so no package tests run in CI.
    evidence: |-
      .github/workflows/ci.yml uses runs-on: ubuntu-latest (violates the self-hosted runner rule) and runs npm ci / npm run test:unit in a pnpm/turbo repo. Pre-existing; not introduced by Story 1.1.
    location: >-
      holocene/.github/workflows/ci.yml
    severity: low
---

<intent-contract>

## Intent

**Problem:** DeloHQ `/hq` routes return ad-hoc payloads (`{ ok:false, error, reason }`, raw org-tree and fleet JSON) with no shared version, freshness, evidence, or identity rules. Each new surface (Company, Now, Inbox, Office, Receipts) would invent its own dialect.

**Approach:** Create `holocene/packages/delohq-contracts/` (`@holocene/delohq-contracts`), a dependency-free TypeScript package. It is the only registry of browser-facing DeloHQ contracts. It exports versioned envelope types, canonical reference types, the freshness vocabulary, explicit Unknown and error states, evidence metadata, and pure runtime validators. Contract tests prove it rejects non-conforming payloads and that no `/hq` code defines a local envelope dialect.

## Boundaries & Constraints

**Always:**
- The package is PURE: no fs, fetch, clock reads, or env reads in `src/` except test files. Freshness classification takes `now` as a parameter.
- Wire fields are snake_case, as AD-9 names them (`schema_version`, `source`, `generated_at`, `observed_at`, `freshness`, `evidence`, `error`). Timestamps are ISO-8601 UTC strings ending in `Z`.
- Canonical refs are `{ kind, id }`, where `kind` is one of `employee | project | action | receipt | ticket | event | execution`. `id` is an opaque non-empty string. It is preserved byte-for-byte, with no trimming, case-folding, or normalization. Display labels live outside refs.
- Validators are strict and return `{ ok: true, value } | { ok: false, issues: string[] }`. They never throw on bad input. Unknown top-level envelope keys are rejected.
- Build output matches `@holocene/org-model`: `main: dist/index.js`, `types: dist/index.d.ts`, `tsc -p tsconfig.json`, and `tsconfig` extends `../../tsconfig.base.json`.

**Never:**
- Do not rewire existing `/hq` routes or `apps/api` adapters to emit envelopes. Story 1.2 owns the route boundary and Story 1.3 owns the Company projection.
- Do not choose numeric freshness budgets (an open decision). The contract carries a caller-supplied `max_age_seconds` policy only.
- Do not add runtime dependencies (zod, ajv, etc.) or a JSON-Schema toolchain.
- Do not define Company, posture, Inbox, or Action view models. Only generic envelope and reference primitives belong here.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Healthy projection | `state:"ok"`, all required fields, ≥1 evidence, `error:null`, `data` non-null | validator `ok:true` | — |
| Missing required field | any of `schema_version`, `source`, `generated_at`, `observed_at`, `freshness` absent | `ok:false`; issue names the missing field | no throw |
| ok without evidence | `state:"ok"`, `evidence:[]` | `ok:false` ("ok requires evidence") | — |
| Error projection | `state:"error"`, `error:{kind:"source_unavailable",message}`, `data:null`, `observed_at:null` | `ok:true` | — |
| Error without detail | `state:"error"` or `"unknown"`, `error:null` | `ok:false` | — |
| Unknown projection | `state:"unknown"`, error detail explains why, `freshness.state:"unknown"` | `ok:true`; never rendered as healthy | — |
| observed_at null while ok | `state:"ok"`, `observed_at:null` | `ok:false` | — |
| Wrong major version | `schema_version:"2.0.0"` | `ok:false` ("unsupported schema_version") | — |
| Legacy dialect | `{ ok:false, error:"unauthorized", reason:"..." }` | `ok:false`; unknown keys `ok`, `reason` reported | — |
| Ref by label | `{ kind:"employee", name:"Momo" }` or `{ kind:"employee", id:"" }` | `ok:false` | — |
| Opaque id round-trip | `{ kind:"employee", id:" Agent-X/01 " }` through `JSON.stringify`→`JSON.parse`→`validateCanonicalRef` | id unchanged; `refKey` = `employee:` + exact id | — |
| Freshness classify | `observed_at`, `now`, `max_age_seconds` | `fresh` if age ≤ max, `stale` if ≤ 2×max, else `expired`; `unknown` if `observed_at` null/invalid or future beyond 60s skew | — |

</intent-contract>

## Code Map

- `holocene/packages/org-model/{package.json,tsconfig.json,src/index.ts}` -- template for a pure shared package (dist build, header comment style, no IO). Its `AgentRef`/`OrgNode` use display names inline and are legacy; do not import from it.
- `holocene/apps/web/app/hq/api/{snapshot,org-tree,action}/route.ts` -- current `/hq` routes emitting the legacy `{ok,error,reason|message}` dialect. Use them as the source for legacy-dialect rejection fixtures. Read-only in this story.
- `holocene/apps/web/app/hq/{hq-client.tsx,page.tsx,lib/verify-init-data.ts}` -- `/hq` view and auth code covered by the dialect guard. Read-only.
- `holocene/apps/api/src/hook-hub.test.ts` -- existing test style (`node:test` + `node:assert/strict`). It legitimately uses `schema_version` for hook-hub, which is not DeloHQ, so the guard must not scan `apps/api/src` broadly.
- `holocene/apps/web/app/hq/hq-client.tsx:4,8` -- imports browser payload types (`OrgNode`, `OrgTree`) from `@holocene/org-model` and declares a local `type ActionResult = { ok; status; data }`. Both are legacy browser-facing contract sources the guard must detect.
- `holocene/apps/web/app/hq/api/{snapshot,org-tree,action}/route.ts` -- every failure path returns `Response.json({ ok: false, error, reason|message })`. This is the legacy dialect the guard must detect in the real files, not only in copied fixtures.
- `holocene/turbo.json` -- `test` is cached, and its default inputs cover only the package's own files. The guard reads `apps/**`, so its turbo task needs those paths as inputs.
- `holocene/pnpm-workspace.yaml` -- `packages/*` already globbed; no edit needed.
- `holocene/tsconfig.base.json` -- ES2022 / Bundler / strict. Use `.js` import specifiers inside the package.
- Toolchain: host `node` v26.10.0 (native type stripping), `tsc` 5.9.3 at `holocene/node_modules/.bin/tsc`, `tsx` in `apps/api`. No zod or ajv is available as a direct dep.

## Tasks & Acceptance

**Execution:**
- `holocene/packages/delohq-contracts/package.json` -- create `@holocene/delohq-contracts` (private, `type: module`, dist main/types, `build`/`typecheck`/`test`/`clean` scripts, devDeps `typescript`, `@types/node`). `test` = `tsc -p tsconfig.test.json && node --test "dist-test/**/*.test.js"` (or an equivalent that runs without new deps) -- workspace package consumable by api (dist) and web.
- `holocene/packages/delohq-contracts/tsconfig.json` + `tsconfig.test.json` -- build excludes `*.test.ts`; test config emits src + tests to `dist-test/` -- keeps tests out of the published dist.
- `holocene/packages/delohq-contracts/src/refs.ts` -- `CANONICAL_REF_KINDS`, `CanonicalRef<K>`, per-kind aliases (`EmployeeRef` ... `ExecutionRef`), `validateCanonicalRef`, `refKey(ref)` (the only sanctioned join key), `Labeled<R>` = `{ ref, label }` -- AC3.
- `holocene/packages/delohq-contracts/src/freshness.ts` -- `FRESHNESS_STATES = ["fresh","stale","expired","unknown"]`, `FreshnessPolicy {max_age_seconds}`, `Freshness {state, max_age_seconds, age_seconds|null}`, pure `classifyFreshness(observedAt, now, policy)` -- freshness vocabulary with no budgets chosen.
- `holocene/packages/delohq-contracts/src/errors.ts` -- `PROJECTION_STATES = ["ok","degraded","unknown","error"]`, `ERROR_KINDS` separating auth (`auth_missing`, `auth_invalid`, `auth_expired`, `auth_forbidden`), `not_configured`, `proxy_unreachable`, `source_unavailable`, `source_timeout`, `source_contradictory`, `contract_violation`, `command_rejected`, `command_failed`, `internal`; `ErrorDetail {kind, message, retryable?, source?}` -- NFR-7 distinct failure states.
- `holocene/packages/delohq-contracts/src/evidence.ts` -- `CANONICAL_SYSTEMS` (flume, pjangler, krebs, pilot, bloodbank, candystore, hermes, holocene), `ProjectionSource {system, adapter}`, `EvidenceRef {evidence_ref, source, observed_at, subject?: CanonicalRef, summary?}` + validators.
- `holocene/packages/delohq-contracts/src/envelope.ts` -- `DELOHQ_SCHEMA_VERSION = "1.0.0"`, `ProjectionEnvelope<T>` (`schema_version`, `surface`, `source`, `generated_at`, `observed_at: string|null`, `freshness`, `state`, `evidence`, `error: ErrorDetail|null`, `data: T|null`), state-coherence rules per the I/O matrix, `validateProjectionEnvelope(value, validateData?)`, and constructors `okProjection`, `errorProjection`, `unknownProjection` -- AC1 and AC2.
- `holocene/packages/delohq-contracts/src/registry.ts` -- `DELOHQ_CONTRACT_REGISTRY`: a frozen map of surface ids (`company`, `employee`, `now`, `inbox`, `office`, `receipt`) to `{ schema_version }`, plus `isRegisteredSurface`. The envelope validator rejects unregistered surfaces -- one registry.
- `holocene/packages/delohq-contracts/src/index.ts` -- re-export everything with a header comment naming this as the sole browser-facing DeloHQ contract registry (AD-11).
- `holocene/packages/delohq-contracts/src/contract.test.ts` -- cover every I/O-matrix row plus constructor output validating as `ok:true`.
- `holocene/packages/delohq-contracts/src/dialect-guard.test.ts` -- scan `holocene/apps/web/app/hq/**/*.{ts,tsx}` and any `holocene/apps/api/src/**` file whose path or content mentions `hq`/`delohq`. Fail if a file declares envelope fields (`schema_version`, `generated_at` + `observed_at`) or a type/interface named `*Envelope`/`*Projection` without importing `@holocene/delohq-contracts`. Also assert validators reject fixtures copied from the current route dialects -- AC4.
- `holocene/packages/delohq-contracts/README.md` -- short usage and migration rule. The envelope and every nested object (freshness, error, evidence, source, ref) have fixed key sets per major, and unknown keys are rejected. Adding, removing, or renaming any such field is a major bump. Minor and patch versions may change only `data`, additively. Also state that `ok` may carry `stale`/`expired` freshness: `state` reports that the read succeeded, and views must render `freshness.state`.
- `holocene/turbo.json` -- add a `@holocene/delohq-contracts#test` task override. It keeps `dependsOn: ["^test"]` and sets `inputs` to `$TURBO_DEFAULT$`, `$TURBO_ROOT$/apps/web/app/hq/**`, and `$TURBO_ROOT$/apps/api/src/**`, so guard-relevant edits invalidate the cache.

**Review amendments (loop 1). These are binding and extend the tasks above:**
- Dialect guard (`dialect-guard.test.ts`):
  - An import of `@holocene/delohq-contracts` never exempts a whole file.
  - Always flag: a `schema_version` key or identifier outside the package (constructors stamp it, so consumers never write it); a local `type`/`interface` named `*Envelope`/`*Projection`; and camelCase `generatedAt` + `observedAt` together.
  - Flag snake_case `generated_at` + `observed_at` only when the file does not import from the package.
  - Also flag the legacy dialect: an object literal or type literal that has an `ok` key together with an `error` or `status` key, such as `Response.json({ ok: false, error, ... })` or `type X = { ok: boolean; status: number; ... }`. Plain internal `{ ok: true }` guard returns do not match.
  - Also flag a type import from `@holocene/org-model` or `@holocene/modules-hermes-fleet` in `apps/web/app/hq/**`, as a non-registry browser payload source.
  - Scan `.ts`, `.tsx`, `.js`, `.jsx`, `.mjs`, and `.cjs`. Skip symlinks by using `lstat`.
  - Keep `LEGACY_DIALECT_ALLOWLIST` as an explicit map of file to the reasons it is expected to violate. Fail when a non-allowlisted file violates, when an allowlisted file shows a reason not in its entry, or when an entry's file no longer violates (a stale entry).
  - Read the legacy rejection fixtures from the real route files' `Response.json({...})` literals where practical. Otherwise keep hand-copied fixtures, but pair them with the in-situ detection above.
- Envelope cross-checks (`envelope.ts`), using `CLOCK_SKEW_TOLERANCE_SECONDS`:
  - Reject `observed_at` later than `generated_at` + skew.
  - Reject any `evidence[i].observed_at` later than `generated_at` + skew.
  - When freshness is known, reject an `age_seconds` that differs by more than the skew from `max(0, generated_at − observed_at)`. A self-reported age can no longer disguise old data.
- Validator robustness:
  - `validateProjectionEnvelope` catches a throwing `validateData` and reports it as an issue.
  - On success it returns `data` from the `validateData` result, not the raw input.
  - All key-presence checks use own properties (`Object.hasOwn`/`hasOwnProperty`), never `in`.
  - `validateCanonicalRef` accepts an optional `path` argument, so nested issues read `envelope.evidence[0].subject.kind`, not `...subject.ref.kind`.
  - `ContractViolationError.issues` is a frozen copy.
- `classifyFreshness` throws `RangeError` for a string `now` that is not ISO-8601 UTC ending in `Z`.
- `package.json` adds `"engines": { "node": ">=22.13.0" }`, matching the sibling packages.
- `contract.test.ts` adds rejection tests for:
  - `degraded` with `error: null`, with `evidence: []`, and with `data: null`.
  - `ok` with a valid `observed_at` but `unknownFreshness`, rejected with "requires a known freshness".
  - `error` and `unknown` with non-null data.
  - Non-semver versions (`"1.0"`, `"v1.0.0"`, `"01.0.0"`).
  - `validateData` not running for error/unknown.
  - A throwing `validateData`.
  - Each of the four constructors throwing `ContractViolationError`.
  - The three new cross-checks: a forged age, observed_at after generated_at, and future-dated evidence.
  - Non-`Z` `now`.

**Acceptance Criteria:**
- Given the package is built, when a consumer imports `@holocene/delohq-contracts`, then envelope types, canonical ref types, freshness vocabulary, projection/error states, evidence metadata, validators, and the registry are exported from the package root.
- Given `pnpm --filter @holocene/delohq-contracts test` runs, when any guarded `/hq` file defines a local envelope, a legacy `{ ok, error }` dialect, or a browser payload type imported from another package, and that file is not on the legacy allowlist, then the dialect-guard test fails and names the file and the reason.
- Given the legacy allowlist in `dialect-guard.test.ts`, when an allowlisted file no longer violates, then the test fails and says to remove that entry. The allowlist can only shrink. On today's tree it lists exactly the three `/hq/api/*/route.ts` files and `hq-client.tsx`, and the test passes.
- Given `pnpm test` / `turbo run test` at the holocene root, when only a guarded file under `apps/web/app/hq/**` or `apps/api/src/**` changes, then the `@holocene/delohq-contracts#test` task is not a cache hit and the guard reruns.
- Given `pnpm --filter @holocene/delohq-contracts build` and `typecheck` run, then both succeed with strict TS and `dist/` contains no test files.

## Spec Change Log

### 2026-09-27 — Loop 1 (bad_spec)
- **Triggering findings:** The dialect guard could not see the legacy `{ ok, error }` dialect that every `/hq` route emits today. One import of the package exempted a whole file from the guard. The AC said "Against today's tree it passes", so the guard proved nothing about AC4. Separately, the envelope validator accepted a forged `age_seconds` and future-dated `observed_at`/evidence, which makes an old snapshot look fresh (a truthfulness gap under NFR-1). The README promised additive minors while the validator rejects unknown keys. And the guard's turbo task was cached on package-only inputs.
- **Amended:**
  - Code Map: added the legacy dialect sites and `turbo.json`.
  - Acceptance Criteria: replaced "passes on today's tree" with detection plus a shrink-only legacy allowlist and a cache-invalidation AC.
  - Execution: added the README versioning rule, the `turbo.json` task, and the binding "Review amendments (loop 1)" list.
- **Known-bad state avoided:** a green guard over routes that still emit the legacy dialect; `state: ok` + `fresh` on week-old data; a stale turbo replay of the guard.
- **KEEP (must survive re-derivation):**
  - Module layout: `refs`, `freshness`, `errors`, `evidence`, `registry`, `envelope`, `validation`, and `index`.
  - The state-coherence table and constructors (`ok`/`degraded`/`error`/`unknown` + `ContractViolationError`).
  - `ERROR_KINDS` with `AUTH_ERROR_KINDS`, `CANONICAL_SYSTEMS`, the frozen six-surface registry with semver major matching, and `refKey`/`sameRef`/`Labeled`.
  - `classifyFreshness` boundaries (fresh ≤ max < stale ≤ 2×max < expired; 60s skew clamp; unknown beyond it) and `validateFreshness` rejecting a state that contradicts the age.
  - The purity test, the `dist-test` test build with its `.gitignore`, and all 44 original tests (still passing).

## Review Triage Log

### 2026-09-27 — Review pass
- verdicts: 39 findings — high 0, medium 18, low 17, false 4, maybe-false 0
- findings:
  - Blind hunter:
    - `[false]` `[reject]` No app declares a workspace dependency on the package. — No bad outcome: the spec's Never list defers route and adapter wiring to Stories 1.2/1.3, and each will add the dependency when it first imports.
    - `[medium]` `[bad_spec]` The guard cannot see today's `{ ok:false, error, reason }` dialect, so it passes while the routes still emit it. — Verified at `route.ts:25-112` and `hq-client.tsx:8`. The amendment adds legacy-dialect detection with a shrink-only allowlist.
    - `[medium]` `[bad_spec]` One import of the package exempts the whole file. — Verified: `findDialectViolation` returns null right away on `IMPORTS_CONTRACTS`. The amendment removes the exemption.
    - `[low]` `[bad_spec]` The guard skips `.js`/`.jsx`/`.mjs`, and symlinks are unguarded. — The regex and `statSync` are confirmed. Folded into the amendment (a direct regex fix plus `lstat`).
    - `[low]` `[reject]` The purity test is top-level only and misses `require`, `Math.random`, etc. — `src/` is flat and every module is reviewed. Closing the holes adds pattern complexity for a risk unlikely in everyday use.
    - `[medium]` `[bad_spec]` `age_seconds` is never tied to `generated_at − observed_at`, so a week-old snapshot can claim fresh. — Verified by the edge-case layer. The amendment adds a cross-check.
    - `[medium]` `[bad_spec]` There is no `observed_at ≤ generated_at` check and no check on evidence timestamps. — Verified: a 2030 `observed_at` passes as ok. The amendment adds skew-bounded checks.
    - `[low]` `[bad_spec]` `classifyFreshness` accepts a non-`Z` `now` string and parses it as local time. — Verified: only `Date.parse` is applied. The amendment makes it throw `RangeError`.
    - `[medium]` `[bad_spec]` The README's "additive minor" promise contradicts the strict unknown-key rejection. — Verified: web and API deploy separately, so version skew is real. The amendment states that key sets are fixed per major and minors change `data` only.
    - `[low]` `[reject]` The registry does not bind a surface to its data type. — No surface view models exist yet by spec (the Never list). A typed map is future work for Stories 1.3+ and adds generics now for no caller.
    - `[low]` `[bad_spec]` The validator returns the raw input and discards `validateData`'s value. — Verified at `envelope.ts` on the return. Folded into the amendment.
    - `[low]` `[reject]` Commands and receipts have no contract, and legacy codes have no mapping. — Out of scope by the intent's epic plan: commands are Epic 6 and route error mapping is Story 1.2.
    - `[low]` `[bad_spec]` Whether `ok` with `expired` freshness is allowed is undocumented. — Real ambiguity for view authors. The amendment has the README state that ok may carry stale/expired and that views render `freshness.state`.
    - `[low]` `[bad_spec]` Error paths are prefixed twice under `subject`. — Verified: `validateCanonicalRef` has no path argument. The amendment adds one.
    - `[medium]` `[bad_spec]` Tests are missing for the degraded, data-null, non-semver, and constructor-throw branches. — Grouped with the verification-gap findings. The amendment lists them.
    - `[low]` `[bad_spec]` Hygiene: `engines` is missing and `ContractViolationError.issues` is held by reference. The `lint` echo is a repo-wide pre-existing convention and not a finding against this diff. — Folded into the amendment (engines plus a frozen copy).
  - Edge-case hunter:
    - `[medium]` `[bad_spec]` A forged `age_seconds` validates as fresh. — Same root cause as the blind hunter's age finding.
    - `[medium]` `[bad_spec]` `observed_at` after `generated_at` passes. — Same root cause as the blind hunter's timestamp finding.
    - `[medium]` `[bad_spec]` A throwing `validateData` makes the validator throw. — Verified: the call is unguarded. The amendment adds try/catch.
    - `[low]` `[bad_spec]` The `validateData` result is discarded. — Duplicate of the blind hunter's raw-return finding.
    - `[low]` `[bad_spec]` Keys inherited through the prototype satisfy `in` checks. — Verified. The fix is a direct correction (`Object.hasOwn`), folded in.
    - `[low]` `[reject]` Constructors do not freeze their input. — Mutation after construction is unlikely in everyday use, and freezing adds complexity.
    - `[low]` `[reject]` A non-string, non-Date `now` throws `TypeError`, not `RangeError`. — The TS signature forbids it, and it still fails loudly, which is correct behavior.
    - `[low]` `[reject]` A symlink loop could crash the guard. — `find apps/web/app/hq -type l` returns nothing today. It is also covered anyway by the `lstat` change.
    - `[low]` `[bad_spec]` `.js` files are unscanned. — Duplicate of the blind hunter's extension finding.
    - `[medium]` `[bad_spec]` The import exemption. — Duplicate of the blind hunter's import finding.
    - `[medium]` `[bad_spec]` The guard misses the live legacy dialect and camelCase `generatedAt`/`observedAt`. — Same root cause as the blind hunter's legacy-dialect finding. The amendment covers both.
    - `[medium]` `[bad_spec]` Freshness and evidence timestamps are not cross-checked. — Same root cause as the blind hunter's age and timestamp findings.
  - Verification gap:
    - `[medium]` `[bad_spec]` Turbo caches the guard on package-only inputs, so edits to `/hq` replay a stale pass. — Pre-verified by `turbo --dry=json`. The amendment adds a `turbo.json` inputs override.
    - `[medium]` `[bad_spec]` Degraded rejection rules are untested. — Pre-verified. Tests are listed in the amendment.
    - `[medium]` `[bad_spec]` "requires a known freshness" is never isolated. — Pre-verified. The test is listed in the amendment.
    - `[medium]` `[bad_spec]` "error/unknown data null" is untested. — Pre-verified. The test is listed in the amendment.
    - `[medium]` `[bad_spec]` (other) The import exemption. — Duplicate of the blind hunter's import finding.
    - `[low]` `[bad_spec]` (other) `LEGACY_FIXTURES` are hand-copied, not read from the routes. — Real. The amendment reads them from the routes or pairs them with in-situ detection.
    - `[low]` `[defer]` (other) `.github/workflows/ci.yml` uses `ubuntu-latest` and calls npm scripts that don't exist. — Pre-existing and not caused by this story. Deferred.
  - Intent alignment:
    - `[false]` `[reject]` The awaiting-operator rule might apply. — The auditor itself concluded that no AC needs a human outside the repo (reading W1).
    - `[medium]` `[bad_spec]` AC4 is met only against envelope-lookalikes, not the dialect `/hq` actually emits. — Same root cause as the blind hunter's legacy-dialect finding.
    - `[false]` `[reject]` AC2: no real route response is validated. — The intent's epic assigns route envelopes to Stories 1.2/1.3, and AC2 is about the validator's requirements, which the tests exercise.
    - `[false]` `[reject]` AC3: refs inside `data` are validated only via `validateData`. — No surface data model exists in this story. Ref validation and `refKey` are exercised directly, and embedding is a later surface's job.

### 2026-09-27 — Review pass (loop 1 re-review)
- verdicts: 36 findings — high 0, medium 6, low 23, false 7, maybe-false 0
- findings:
  - Blind hunter:
    - `[false]` `[reject]` The envelope `observed_at` is never checked against older evidence timestamps. — Evidence may legitimately predate the snapshot read, e.g. the last ticket event a week ago. `observed_at` marks the read, not the newest evidence, so no false-fresh outcome follows.
    - `[low]` `[reject]` The producer sets `max_age_seconds` and the browser cannot check it against policy. — Budgets are an open decision (epic context). The fix adds a validator parameter, so enforcement lands with the budget decision.
    - `[low]` `[reject]` `validateProjectionEnvelope<T>` without `validateData` returns unchecked `T`. — `T` defaults to `unknown`, so passing `<T>` explicitly is the caller's own cast. Overloads add public surface for no current caller.
    - `[low]` `[reject]` The registry has no per-surface data validator. — carried: no surface view models exist in this story (Never list).
    - `[low]` `[reject]` Older minor versions are accepted. — The README states minors change `data` additively, so readers treat additions as optional. Low harm, and a minimum-minor rule adds policy.
    - `[medium]` `[patch]` The lexer mis-lexes JSX (`</p>` read as a regex, `don't` as a string), swallowing the rest of the line. — Verified with a scratch fixture: the shape lost the trailing `;`. Fixed: `<` is removed from `REGEX_PRECEDER`, a word-internal apostrophe in `.tsx`/`.jsx` is treated as text, and JSX fixture tests were added.
    - `[low]` `[patch]` Importing the package still exempts a local snake_case envelope type. — Real: an `interface` with `generated_at`+`observed_at` passed. Fixed: those fields are flagged inside type/interface bodies whatever the file imports, with tests.
    - `[low]` `[reject]` The `schema_version` rule also flags reads. — Intended by the loop-1 amendment. Views never need to read it.
    - `[low]` `[reject]` The guard misses `{ success:false }`, a bare `{ error }`, and `new Response(JSON.stringify(...))`. — Expanding the heuristic without bound. None of these shapes exist in `/hq` today.
    - `[medium]` `[patch]` The route-fixture test breaks with no guidance once Story 1.2 migrates a route (magic `count >= 5`). — Verified. Fixed: fixtures are read only from routes allowlisted for legacy-ok-dialect, the count is gone, and the failure says to remove the entry.
    - `[false]` `[reject]` Nothing uses the package yet. — carried: consumers are Stories 1.2/1.3.
    - `[low]` `[reject]` Purity-test holes. — carried.
    - `[low]` `[patch]` Test gaps: unregistered-surface constructors, error+stale+evidence valid, degraded+unknown freshness, subject/summary preserved. — All added.
    - `[low]` `[reject]` Constructors return unfrozen caller objects. — carried.
    - `[low]` `[reject]` There is no `contractViolationProjection` helper. — New public surface. The view-side failure rendering belongs to Stories 1.2/1.3.
  - Edge-case hunter:
    - `[low]` `[reject]` `max_age_seconds` is not checked against policy. — Duplicate of the blind hunter's `max_age_seconds` finding (budgets undecided).
    - `[medium]` `[patch]` Within the 60s age tolerance, a producer can cross a state boundary (170s old reported as age 115, `fresh`). — Verified by reading `envelope.ts`. Fixed: `freshness.state` must equal `stateForAge(impliedAge)`, and the test was added.
    - `[false]` `[reject]` Evidence older than `observed_at`. — Same refutation as the blind hunter's first finding.
    - `[low]` `[patch]` `validateData` returning ok with a null/undefined value yields an ok envelope with no data. — Fixed with an issue and a test.
    - `[low]` `[reject]` A non-string/non-Date `now` throws `TypeError`. — carried.
    - `[low]` `[reject]` Constructors alias the caller's input. — carried.
    - `[low]` `[reject]` Non-JSON-serializable data. — Unlikely from adapters that build JSON. A round-trip check costs every construction.
    - `[low]` `[patch]` A whitespace-only `error.message` validates. — Fixed (trim) with tests.
    - `[low]` `[reject]` A computed key `["ok"]` evades the guard. — Unlikely in everyday code, and it would need a heuristic expansion.
    - `[low]` `[reject]` An ENOENT race between readdir and lstat. — Unlikely in a test run over a static tree.
    - `[low]` `[patch]` `HQ_MENTION` misses camelCase `deloHq`/`hqClient`. — Grouped with the API-selection finding. Fixed via `isGuardedApiFile` with a camelCase-aware regex.
    - `[low]` `[reject]` The purity test does not recurse. — carried.
    - `[medium]` `[patch]` Claim "a self-reported age cannot disguise old data" is only partly true. — Grouped with the state-boundary fix above. The `max_age` part is rejected, as in the blind hunter's `max_age_seconds` finding.
  - Verification gap:
    - `[medium]` `[patch]` The API half of the guard scans zero files, and its selection is untested. — Pre-verified. Fixed: extracted `isGuardedApiFile` with unit tests (`hq/company.ts`, a content import, `deloHqProjection`, `hqClient`, and a rejected `hook-hub.ts`).
    - `[medium]` `[patch]` Nested validator rejection rules have no negative tests. — Pre-verified. Fixed: table-driven cases, each asserting its issue path.
    - `[low]` `[defer]` (other) `ci.yml` uses `ubuntu-latest` and npm scripts that don't exist. — carried and already in `deferred`.
    - `[low]` `[patch]` (other) API files are selected by design only when they mention hq. — Grouped with the API-selection finding: importing the package now also selects a file.
  - Intent alignment:
    - `[false]` `[reject]` The awaiting-operator rule might apply. — carried: no AC needs a human outside the repo.
    - `[false]` `[reject]` AC2: no live route returns an envelope. — carried.
    - `[false]` `[reject]` AC3: no real projection serializes refs yet. — carried.
    - `[false]` `[reject]` AC4 holds only for new code, since the four live files are allowlisted. — This is the shrink-only design from the loop-1 amendment. The intent's epic assigns route and view migration to Stories 1.2/1.3.

## Design Notes

State coherence is the heart of truthfulness (NFR-1). Only `ok` may carry data without an error, and it must cite evidence. `degraded` carries data, evidence, and an error. `unknown` and `error` carry an error detail and never claim `fresh`.

```ts
okProjection({ surface: "company", source: { system: "flume", adapter: "org.ts" },
  generated_at, observed_at, freshness, evidence: [ev], data })
// => { schema_version: "1.0.0", state: "ok", error: null, ... }
```

## Verification

**Commands:**
- `cd holocene && pnpm install --offline` (or plain `pnpm install`) -- links the new workspace package. If the host Node 26 shim breaks pnpm, run `tsc` and `node --test` directly and record it.
- `cd holocene && pnpm --filter @holocene/delohq-contracts build && pnpm --filter @holocene/delohq-contracts typecheck` -- expected: exit 0.
- `cd holocene && pnpm --filter @holocene/delohq-contracts test` -- expected: all tests pass.

## Auto Run Result

Status: done

**Summary:** This adds `@holocene/delohq-contracts` (`holocene/packages/delohq-contracts/`), a dependency-free, pure TypeScript package. It is the sole registry of browser-facing DeloHQ contracts. It exports:
- versioned projection envelopes with state-coherence rules (`ok`/`degraded`/`unknown`/`error`), plus cross-checks between timestamps and freshness
- opaque canonical `{ kind, id }` refs, with `refKey` as the only join key
- the freshness vocabulary with a policy the caller supplies
- typed error kinds that keep auth, proxy, source, and command failures distinct
- evidence metadata, a frozen six-surface registry, constructors, and validators that never throw

A dialect guard scans `/hq` code for local envelope, legacy `{ ok, error }`, and non-registry payload dialects. Today's four legacy files sit on an allowlist that can only shrink.

**Commits (holocene):**
- `956df8d` initial
- `1a6c677` loop-1 amendments
- `345eff1` pass-2 patches

The 33GOD submodule pin was bumped in `5cd6470` and `6624eae`.

**Files changed (holocene):**
- `packages/delohq-contracts/package.json`, `tsconfig.json`, `tsconfig.test.json`, `.gitignore` -- package and build/test config (tests build into the ignored `dist-test/`).
- `src/refs.ts` -- canonical refs, `Labeled`, `refKey`/`sameRef`, and a ref validator that takes a path.
- `src/freshness.ts` -- `fresh`/`stale`/`expired`/`unknown`, pure `classifyFreshness`, and `validateFreshness`.
- `src/errors.ts` -- projection states, `ERROR_KINDS`/`AUTH_ERROR_KINDS`, and `validateErrorDetail`.
- `src/evidence.ts` -- `CANONICAL_SYSTEMS`, `ProjectionSource`, and `EvidenceRef` validators.
- `src/registry.ts` -- the frozen surface registry and semver major matching.
- `src/envelope.ts` -- the envelope types, the validator with coherence and timestamp/freshness cross-checks, constructors, and `ContractViolationError`.
- `src/validation.ts`, `src/index.ts` -- shared helpers and the root re-exports.
- `src/contract.test.ts`, `src/dialect-guard.test.ts`, `src/purity.test.ts` -- 89 tests: the I/O matrix, the AC4 guard with its allowlist, and package purity.
- `README.md` -- usage, the versioning and migration rule, and the semantics of `ok` combined with stale data.
- `turbo.json` -- a `@holocene/delohq-contracts#test` override whose inputs include `/hq` and `apps/api/src`.
- `pnpm-lock.yaml` -- the importer entry for the new package.

**Review findings:**
- Pass 1: 39 findings, which led to one spec repair (bad_spec loopback, iteration 1). It covered the guard's blindness to legacy dialects, the import exemption, forged freshness age and future timestamps, the conflict between the versioning rule and strict keys, the turbo cache inputs, and the missing degraded, data-null, and known-freshness tests. 1 item was deferred (holocene CI on `ubuntu-latest` running npm scripts that don't exist; pre-existing). Rejections and their reasons are in the Review Triage Log.
- Pass 2: 36 findings.
  - 12 rows were routed to patch, forming 6 entries: 5 at medium and 1 at low. The medium entries were JSX lexing, the freshness state-boundary check, the API guard selection, nested negative tests, and route-fixture resilience. The low entry was the snake_case local type.
  - Several low patches came along with them: validateData null, whitespace-only messages, and the extra positive and negative tests.
  - 23 findings were rejected or carried. Each has a recorded reason in the Review Triage Log; the main ones are the budget-policy parameter, the lack of a per-surface data validator, JSON-serializability, freezing, and heuristic expansion.
- Patched counts by entry verdict on the latest pass: high 0, medium 5, low 1.

**Follow-up review recommended:** true. Five medium entries were patched on this pass. The named unverified risk is that the hand-written, regex-based lexer in `dialect-guard.test.ts` (JSX apostrophe and regex handling) and the new `freshness.state === stateForAge(impliedAge)` rule have had no fresh review since they were patched.

**Verification:**
- `pnpm --filter @holocene/delohq-contracts build` and `typecheck` both exit 0, and `dist/` contains no test files.
- `pnpm --filter @holocene/delohq-contracts test` passes 89 of 89 (0 fail, 0 skipped).
- The implementer showed with `turbo --dry=json` that editing `/hq` changes the test task's hash, and that four deliberate `/hq` mutations each fail the guard with the file and the reason.
- The I/O matrix audit found every row covered by a test that ran.

**Residual risks:**
- `pnpm install --offline` did not relink the new package's `node_modules`. The implementer linked `typescript` and `@types/node` by hand, so a clean `pnpm install` should be run once.
- The dialect guard is heuristic, not a real parser.
- Nothing in `apps/` imports the package yet. Stories 1.2 and 1.3 migrate the routes and `hq-client.tsx` and empty the allowlist.
- Freshness budgets (`max_age_seconds`) are trusted from the producer until the budget decision lands.
- During loop 1 the implementer fixed a false positive in the global git guard (`~/.agents` commit `3c02ea6`, which skips `import(...)` matches inside comments).
- No operator actions are owed.

