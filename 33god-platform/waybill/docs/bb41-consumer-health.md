# BB-41 Waybill consumer health diagnostic

Waybill reads the existing NATS monitoring snapshot on demand; it does not check n8n workflow activation. A pull consumer with `num_waiting > 0` is polling even if its last delivery was days ago. The absence of `push_bound` for a pull consumer is not a disconnect signal.

For an n8n durable matching an event in the captured turn, Waybill emits an idle backlog **candidate** only when it has pending messages, no current waiting pull (or no bound push), and its last delivery is over 24 hours old. This does not prove that polling was continuously absent for 24 hours. Missing last-delivery time is insufficient for this n8n diagnosis. Other consumers retain the existing one-hour/unbound diagnostic.

The two exact BB-41 legacy delegation durable names receive a distinct `retired-lane residual backlog` finding instead of being suppressed or reported as a failed active lane. The historical inactive-workflow classification comes from the BB-41 read-only report; Waybill's NATS snapshot cannot confirm present activation or authorize deletion. Recheck workflow ownership and replacement dispatch before retiring those durables; do not reactivate the legacy dispatcher or replay its backlog. A different durable with a similar name remains an ordinary candidate.

Verification: `python3 -m unittest discover -s tests -q` in `33god-platform/waybill`. The `tests/test_nats.py` cases exercise the real `parse_jsz` → `collect` finding path with mocked monitoring GETs and published subjects, plus idle boundaries and exact-name discrimination. No live NATS or n8n mutation is part of this change.
