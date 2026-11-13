# G1/G2 re-proof intake — source gate blocked

Observed by Rererere, 2026-10-23. No Damian changes made in this pass.

## Exact source state

HEAD `a6e49173d021cd6ed623653e2363a48a12a95a52` includes attached-mode overlay and seam. The three newly advertised corrections are still uncommitted working-tree changes:
- groups/g1/smoke/smoke.sh
- groups/g2/outbox/server.py
- groups/g2/workflows/01-smoke.json

Do not transfer a mixed HEAD-plus-uncommitted release. Existing deployed release `3d3c393cb06259fa39f885f0d7069096d1fb00ea` remains unchanged by this pass, including Damian's loopback Candystore access.

## Executed check and concrete remaining mismatches

`/usr/bin/python3 -m unittest discover -s outbox -v` in G2 returned exit1: seven tests passed, test_valid_cloud_event errored at server.validate with `ValueError: CloudEvent fields missing`. The positive fixture has not been updated for the new required canonical envelope. This is a failing test, not proof the new envelope itself is wrong.

G2 `smoke/check.py:75` still asserts `event['type'] == event['subject'] == ack['subject']`. The corrected workflow emits four-token type and five-token subject, so this assertion necessarily rejects the corrected output.

G1 `smoke/smoke.sh:169-175` still passes TOPIC as expected_type and asserts both type and subject equal it. The corrected emitted type is now CE_TYPE, so the round-trip assertion necessarily fails even when transport succeeds. Pass/compare expected type and subject separately.

README and SEAM-G1-G2.md still contain historical envelope and standalone-only prose; reconcile with canonical patch rather than treating an old successful run as proof of the new bytes.

## Requested owner handback before Damian re-test

Grolf to update unit fixture, both smoke assertions, and relevant proof text; run standalone, attached Candystore readback, portable G1 smoke on those exact bytes; commit/publish a clean release revision. Rererere will then stage the pinned release, preserve target-local keys/volumes and loopback overlay, verify actual saved workflow migration (first-boot importer marker otherwise keeps old workflow), and independently execute native ARM64 acceptance. Do not reset DBs or remove importer markers as a shortcut, and do not hand-edit live nodes.

No upstream code, remote workflows, resources, hooks or routing changed by Rererere in this re-proof intake.
