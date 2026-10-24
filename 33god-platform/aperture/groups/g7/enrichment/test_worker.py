"""Unit tests for the enrichment worker's extraction + derivation (no bus, no
HTTP). The smoke proves the live path; these pin the contract."""
import json
import unittest
import uuid

import worker


def source_event(etype="bloodbank.aperture.smoke.g7", data=None, **over):
    eid = str(uuid.uuid4())
    env = {
        "specversion": "1.0", "id": eid, "source": "urn:33god:aperture:g7-smoke",
        "type": etype, "subject": "bloodbank.evt." + etype.split(".", 1)[1],
        "time": "2026-10-24T12:00:00.000Z", "datacontenttype": "application/json",
        "correlationid": eid, "causationid": eid,
        "producer": "aperture-g7-smoke", "service": "smoke", "domain": etype.split(".")[1],
        "kind": "event", "ordering_key": "g7:smoke",
        "actor": {"type": "operator", "agent_id": "operator:smoke"},
        "data": data or {"ping": True},
    }
    env.update(over)
    return env


class ExtractionTests(unittest.TestCase):
    def test_extracts_new_fields(self):
        x = worker.extract(source_event(data={"project": "33GOD", "n": 1}))
        assert x is not None
        self.assertEqual(x["domain"], "aperture")
        self.assertEqual(x["entity"], "smoke")
        self.assertEqual(x["action"], "g7")
        self.assertEqual(x["payload_keys"], ["n", "project"])
        self.assertEqual(x["size_class"], "tiny")
        self.assertEqual(len(x["payload_sha256"]), 64)
        self.assertTrue(x["payload_bytes"] > 0)
        # derived id is deterministic on source id
        self.assertEqual(x["derived_id"],
                         str(uuid.uuid5(worker.NAMESPACE, x["source_id"])))

    def test_deterministic(self):
        env = source_event()
        a, b = worker.extract(env), worker.extract(env)
        self.assertEqual(a, b)

    def test_rejects_non_canonical(self):
        cases = [
            {},                                  # empty
            source_event(etype="bloodbank.a.b.c.d"),  # 5-token type
            source_event(etype="aperture.smoke.g7"),  # missing bloodbank prefix
            source_event(subject="wrong.subject.here"),  # subject/type disagree
            source_event(data="not-a-dict"),      # non-dict data
            source_event(etype="bloodbank.aperture.smoke.enriched"),  # derived loop
            source_event(id="not-a-uuid"),        # bad id
        ]
        for i, case in enumerate(cases):
            with self.subTest(case=i):
                self.assertIsNone(worker.extract(case))

    def test_rejects_own_source_urn(self):
        env = source_event(source="urn:33god:aperture:g7-enrichment")
        self.assertIsNone(worker.extract(env))


class DerivationTests(unittest.TestCase):
    def test_canonical_shape_and_chain(self):
        env = source_event()
        x = worker.extract(env)
        assert x is not None
        d = worker.derive(env, x)
        # canonical contract: type 4 tokens, subject 5 with evt marker, same triple
        self.assertEqual(d["type"].split("."), ["bloodbank", "aperture", "smoke", "enriched"])
        self.assertEqual(d["subject"], "bloodbank.evt.aperture.smoke.enriched")
        self.assertEqual(d["specversion"], "1.0")
        self.assertEqual(d["kind"], "event")
        self.assertEqual(d["domain"], "aperture")  # domain = type token 2
        self.assertIn("ordering_key", d)
        # THE CHAIN: causationid = source event id; correlationid carries through
        self.assertEqual(d["causationid"], env["id"])
        self.assertEqual(d["correlationid"], env["correlationid"])
        # payload is built from the extraction (the transform is visible)
        self.assertEqual(d["data"]["pass"], "typed-extraction-v1")
        self.assertEqual(d["data"]["extraction"]["source_id"], env["id"])
        self.assertEqual(d["data"]["extraction"]["payload_sha256"], x["payload_sha256"])
        # type is NOT the subject (the historical conflation bug)
        self.assertNotEqual(d["type"], d["subject"])
        # derived id is a uuid
        uuid.UUID(d["id"])


if __name__ == "__main__":
    unittest.main()
