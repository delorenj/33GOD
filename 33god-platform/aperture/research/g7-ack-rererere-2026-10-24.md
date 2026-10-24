# G7 acknowledgment — Rererere → Grolf, 2026-10-24

**Status: independently checked research + acceptance direction, NOT deployment authorization or ARM64 acceptance.** Charter at this checkout loaded. Input: handoff `792f3e178d54856c389cad59f85becffd5072348`, merged bundle `9babbbda436325e4ca2a0453a456da01c9adc4ad`. No Damian operations, board changes, or internal implementation edits performed in this review.

## Confirmed independently

- Both commits exist in the local repository; review HEAD was the handoff revision above. Unrelated dirty submodules and untracked earlier acceptance notes were left untouched.
- All **32 shipped upstream files** under `candystore-src/` (excluding PROVENANCE itself) are byte-identical to Candystore `767ebb5eb8351b43b43bb6406aa1882ef3912713`; no vendored `tests/` directory. Dockerfile delta = NONE. Did not open or redistribute the excluded production fixture corpus.
- `python3 -m unittest discover -s enrichment -p 'test_*.py' -v`: **5/5 passed**.
- `python3 -m unittest test_services -v` from smoke/: **7/7 passed**, including the positive payload-word search test and isolated backend failure. These are local unit tests, NOT real-bus or target execution evidence.
- `docker compose config --quiet` and the same command with compose.attach.yml: **both exit 0**. No containers started for this review.
- Code confirms exact empty-config degraded reason: `degraded: no embeddings/rerank (GOD_LLM_BASE_URL and GOD_LLM_API_KEY empty); keyword search only`; /embed returns 503 unconfigured; /query labels keyword mode without reranking. readiness alone does NOT prove bus/backend delivery: /healthz sets ready=true independently of bus status.
- Reference backend is real SQLite FTS5. Payload searching is field-specific: data.name / data.prompt_text / data.project and the other listed keys are indexed; arbitrary data.decision / data.note is not part of its explicit text allowlist. Full data JSON is also an FTS column, but the kit should use the documented allowlist rather than depend on incidental JSON tokenization.
- Source confirms the enrichment deterministic ID and causation chain, profiled-out attach nats-init, two worker durable defaults, empty LLM defaults, and backend HTTP contract. PROOF.md records build-host standalone/attach outputs, not Studio execution. I have NOT rerun full cold smoke, upstream DB suite, manifests, or runtime capacity measurements.

## Gate-kit shape: adopted with concrete requirements

Deliver `accept/` in the deployable bundle, runnable with the Studio's Docker Compose + bundled runtime only. No upstream checkout, px/pj, PM-host API/board/Candystore, external credentials, or LLM needed.

1. **Preflight without mutation:** show selected project/bus/backend and revision; verify connected bus and reachable backend separately from green healthz. Assert both LLM vars empty and exact D1 reason; /embed 503; keyword query succeeds. Do not print env secret values.
2. **Damian supplies history:** prompt for at least two real decisions/notes from his own day, not canned demos. Put the searchable human text in a documented indexed field such as data.name or data.prompt_text and retain the full original text. Generate canonical envelope/UUID fields for him. Display IDs and transport acknowledgments.
3. **Recall through the actual pipeline:** publish only through the selected bus, then poll with a bounded deadline; query through hindsight-bridge, NOT direct /ingest or SQLite. Damian chooses a distinguishing word from his own text (not a generated marker/producer), and sees the matching event_id plus his exact stored values. Query a second record and a chosen absent term to avoid blanket-hit success.
4. **Auditable enrichment:** read the source and derived events from the explicitly selected local Candystore; verify exact original data, derived.causationid == source.id, preserved correlationid, four-token type / five-token subject, expected extraction/hash and bounded completion. Never treat publish ack or bridge tailed counter as successful recall.
5. **Persistence without deletion:** restart ONLY owned G7 services, then rerun identical readback/queries and compare IDs/text. No cold smoke, down -v, volume deletion, shared-bus restart, consumer deletion, or automatic cleanup of Damian's history. G1 full-stack persistence belongs to the separate G1 gate.
6. **Negative and replay evidence:** malformed input must not produce a derived record; report failures clearly. Record replay duplicate behavior, and distinguish retained bus delivery from confirmed backend storage. No exactly-once or outage recovery guarantee from the current ack-on-backend-failure policy.
7. **Evidence artifact:** local timestamp/revision/mode, source+derived IDs, keyword choices, HTTP statuses and individual PASS/FAIL with nonzero failure exit. Real history stays local; any shared report defaults to IDs/statuses/redacted content. Separate `studio` technical acceptance from Damian's `gate` completion.

The kit must be non-destructive by default and explicitly identify the Candystore it reads. The build-host smoke scripts are destructive and are NOT the acceptance entrypoints on his retained deployment.

## Sequencing decision

**Standalone first**, as a fresh isolated `god-g7` deployment when scheduled, using owned storage and bus; optional notify profile off and no LLM. Measure native ARM64 runtime and target-VM coexistence before attach. This is a sequencing decision, not an instruction to deploy now. Do NOT run the shipped cold smoke against retained history.

**Attached second**, only to Damian's parallel `god-g1` bus, never Jarad's native stack or Damian's unrelated native systems. No changes to G1 stream initialization. Preserve his existing G1 Candystore and loopback :8683. I will not choose a replacement-store architecture unilaterally.

Before attached deployment, Grolf must resolve/prove **Candystore consumer ownership**: both g1/dapr/pubsub.yaml and g7/dapr/pubsub.yaml currently specify durableName=candystore-events and queueGroupName=candystore on BLOODBANK_EVENTS. An empty-bus seam with only G7 does not prove coexistence with G1's active subscriber. Decide whether G7 uses G1's store or an independent subscriber with a distinct durable/queue; demonstrate each intended store receives the same source+derived IDs while G1 remains running. This is an attach-specific acceptance gate, not a rejection of standalone readiness.

## Corrections / bounded follow-ups for the owner

- **PROVENANCE re-vendor instructions contradict the corrected policy:** lines 30–38 still copy `tests` and expect a Dockerfile build-arg change. Fix those instructions before a future re-vendor; current shipped corpus is excluded and byte-identical as confirmed above.
- **Idempotency claim is narrower than prose:** enrichment UUID/upsert and Candystore conflict handling exist; memory-reference.ingest inserts every occurrence into FTS without event_id uniqueness. Thus replay can duplicate query results. Choose/document intended user-visible semantics; do not promise deduplicated memory results yet.
- **Backend-loss boundary:** bridge acknowledges after per-backend ingest failures; backend_errors is incremented internally but is NOT included by the current /healthz response. The README's visible counter claim is inaccurate. An acknowledged failed backend write is not automatically recovered by durable bus redelivery. Gate must distinguish successful ingestion from merely counted/acked traffic.
- **Real Hindsight remains deferred:** a backend implementing the shipped /ingest and /query HTTP contract can be configured by URL. A specific real Hindsight server is not proven wire-compatible merely by changing the URL. Require a compatible adapter or separately executed contract proof before claiming that swap works.

These are owner follow-ups, not permission for Rererere to rewrite internal code. No demand to interrupt active workers; incorporate at the relevant handoff/attach gate.

## Board and communication

No studio/gate state advances during research. Existing pending entries remain truthful. Prefer the existing field conventions and revisioned note/provenance; I am not adopting a new board taxonomy or publishing any Damian-facing link. Deployment status and operator-completed acceptance will be updated independently when evidenced.
