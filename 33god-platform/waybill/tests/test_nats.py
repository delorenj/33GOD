import os
import sys
import unittest
from copy import deepcopy
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from waybill.collectors import nats
from waybill.model import ms

JSZ = {"now": "2026-11-16T04:30:00.000Z", "account_details": [{"name": "A", "stream_detail": [
    {"name": "BLOODBANK_EVENTS", "state": {"messages": 5, "last_seq": 9, "consumer_count": 3},
     "config": {"subjects": ["bloodbank.evt.>"], "storage": "file"},
     "consumer_detail": [
         {"name": "candystore-events", "push_bound": True,
          "config": {"durable_name": "candystore-events", "filter_subject": "bloodbank.evt.>", "deliver_subject": "d",
                     "ack_policy": "explicit"},
          "delivered": {"stream_seq": 9, "last_active": "2026-11-16T04:29:59.000Z"}, "ack_floor": {"stream_seq": 9},
          "num_pending": 0},
         {"name": "n8n-abc", "push_bound": False,
          "config": {"durable_name": "n8n-abc", "filter_subjects": ["bloodbank.evt.agent.invocation.completed"],
                     "deliver_subject": "d2"},
          "delivered": {"stream_seq": 1, "last_active": "2026-11-14T00:00:00.000Z"}, "num_pending": 1055},
         {"name": "weird", "config": {"filter_subject": "bloodbank.evt.agent.>", "name": "weird"},
          "delivered": {"stream_seq": 1, "last_active": "2026-11-16T04:29:00.000Z"}, "num_pending": 3}]},
    {"name": "OTHER", "state": {}, "config": {}, "consumer_detail": [{"name": "skip"}]}]}]}

CONNZ = {"connections": [
    {"cid": 1, "name": "bloodbank-ntfy-router", "lang": "python", "subscriptions_list_detail": [
        {"subject": "bloodbank.evt.>", "msgs": 10}, {"subject": "_INBOX.x"}]},
    {"cid": 2, "name": "waybill-probe", "subscriptions_list_detail": [{"subject": "bloodbank.evt.>"}]},
    {"cid": 3, "name": "deckard-attention", "subscriptions_list_detail": [{"subject": "deckard.evt.attention", "qgroup": "q"}]},
    {"cid": 4, "name": None, "subscriptions_list_detail": [{"subject": "bloodbank.evt.agent.>"}]}]}


class Tests(unittest.TestCase):
    def test_consumer_component(self):
        self.assertEqual(nats.consumer_component("candystore-events"), "candystore")
        self.assertEqual(nats.consumer_component("holocene_ab12"), "holocene")
        self.assertEqual(nats.consumer_component("n8n-l0J53"), "n8n")
        self.assertEqual(nats.consumer_component("bloodbank-hermes-gateway-x"), "hermes-gw")
        self.assertEqual(nats.consumer_component("mystery"), "ext:mystery")

    def test_client_component(self):
        self.assertEqual(nats.client_component("bloodbank-ntfy-router"), "ntfy-router")
        self.assertEqual(nats.client_component("deckard-attention"), "deckard")
        self.assertEqual(nats.client_component(None), "ext:unnamed")

    def test_parse_jsz(self):
        consumers, streams = nats.parse_jsz(JSZ)
        names = [c["name"] for c in consumers]
        self.assertEqual(names, ["candystore-events", "n8n-abc", "weird"])      # OTHER stream ignored
        self.assertIn("OTHER", streams)
        c0 = consumers[0]
        self.assertEqual(c0["filter_subjects"], ["bloodbank.evt.>"])
        self.assertEqual((c0["kind"], c0["component"], c0["delivered"], c0["push_bound"]), ("durable", "candystore", 9, True))
        self.assertEqual(consumers[2]["kind"], "ephemeral")
        self.assertEqual(streams["BLOODBANK_EVENTS"]["messages"], 5)

    def test_parse_connz(self):
        subs = nats.parse_connz(CONNZ)
        self.assertEqual([(s["client"], s["subject"]) for s in subs],
                         [("bloodbank-ntfy-router", "bloodbank.evt.>"), ("deckard-attention", "deckard.evt.attention"),
                          (None, "bloodbank.evt.agent.>")])
        self.assertEqual(subs[0]["component"], "ntfy-router")
        self.assertEqual(subs[1]["queue"], "q")

    def test_idle_consumers(self):
        consumers, _ = nats.parse_jsz(JSZ)
        now = ms(JSZ["now"])
        idle = nats.idle_consumers(consumers, ["bloodbank.evt.agent.invocation.completed"], now)
        self.assertEqual([c["name"] for c in idle], ["n8n-abc"])               # unbound + stale + pending
        self.assertEqual(idle[0]["subjects_hit"], ["bloodbank.evt.agent.invocation.completed"])
        # a subject the consumer does not filter on is not its business
        self.assertEqual(nats.idle_consumers(consumers, ["bloodbank.evt.conversation.turn.started"], now), [])

    def test_n8n_pull_waiting_and_idle_boundaries(self):
        subject = "bloodbank.evt.agent.invocation.completed"
        now = ms(JSZ["now"])
        assert now is not None
        base = {"name": "n8n-active", "stream": "BLOODBANK_EVENTS", "kind": "durable", "component": "n8n",
                "filter_subjects": [subject], "push": False, "push_bound": False, "num_pending": 1732,
                "num_waiting": 0, "last_active": "2026-11-14T00:00:00Z"}
        self.assertEqual(nats.idle_consumers([dict(base, num_waiting=1)], [subject], now), [])
        self.assertEqual(nats.idle_consumers([dict(base, num_pending=0)], [subject], now), [])
        self.assertEqual(nats.idle_consumers([dict(base, num_waiting=1, num_pending=0)], [subject], now), [])
        self.assertEqual(nats.idle_consumers([dict(base, last_active="2026-11-15T05:00:00Z")], [subject], now), [])
        self.assertEqual(nats.idle_consumers([dict(base, last_active=None)], [subject], now), [])
        candidate = nats.idle_consumers([base], [subject], now)
        self.assertEqual(candidate[0]["idle_diagnosis"], "orphan_candidate")
        self.assertEqual(candidate[0]["subjects_hit"], [subject])
        self.assertEqual(nats.idle_consumers([dict(base, push=True, push_bound=True)], [subject], now), [])
        self.assertEqual(nats.idle_consumers([dict(base, name="other", component="other", num_waiting=1)],
                                             [subject], now)[0]["name"], "other")

    def test_exact_retirement_evidence_not_prefix_or_activation_claim(self):
        subject = "bloodbank.evt.agent.invocation.completed"
        now = ms(JSZ["now"])
        assert now is not None
        base = {"stream": "BLOODBANK_EVENTS", "kind": "durable", "component": "n8n",
                "filter_subjects": [subject], "push": False, "num_waiting": 0, "num_pending": 1,
                "last_active": "2026-11-14T00:00:00Z"}
        for name in nats.RETIRED_DELEGATION_DURABLES:
            with self.subTest(name=name):
                self.assertEqual(nats.idle_consumers([dict(base, name=name)], [subject], now)[0]["idle_diagnosis"],
                                 "retired_lane_residual")
                self.assertEqual(nats.idle_consumers([dict(base, name=name + "-new")], [subject], now)[0]["idle_diagnosis"],
                                 "orphan_candidate")
                self.assertEqual(nats.idle_consumers([dict(base, name=name, num_waiting=2)], [subject], now), [])

    def test_collect_reports_candidate_and_retired_residual_without_false_outage(self):
        from waybill.model import Ctx, TurnWindow
        subject = "bloodbank.evt.agent.invocation.completed"
        jsz = deepcopy(JSZ)
        retired = next(iter(sorted(nats.RETIRED_DELEGATION_DURABLES)))
        detail = jsz["account_details"][0]["stream_detail"][0]["consumer_detail"]
        detail[1].update(name=retired, push_bound=False, num_waiting=0)
        detail[1]["config"]["durable_name"] = retired
        detail[1]["config"].pop("deliver_subject")
        active = deepcopy(detail[1])
        active["name"] = "n8n-current-workflow"
        active["config"]["durable_name"] = active["name"]
        detail.append(active)
        for name, changes in (("n8n-waiting", {"num_waiting": 2}),
                              ("n8n-short", {"delivered": {"last_active": "2026-11-16T04:00:00Z"}}),
                              ("n8n-no-backlog", {"num_pending": 0})):
            row = deepcopy(active)
            row.update(name=name, **changes)
            row["config"]["durable_name"] = name
            detail.append(row)
        ctx = Ctx(window=TurnWindow(cli="claude", surface="claude-code", session_id="s", t0=1.0, t_end=2.0),
                  timeout_s=1.0)
        def response(path, timeout):
            return jsz if path.startswith("/jsz") else {"connections": []}
        with mock.patch.object(nats, "http_json", side_effect=response), mock.patch.object(
                nats.hookhub, "published_events", return_value=[{"subject": subject}]):
            frag = nats.collect(ctx)
        self.assertEqual(frag.source.status, "ok")
        self.assertEqual(len(frag.findings), 2)
        titles = {f.title for f in frag.findings}
        self.assertIn(f"JetStream consumer {retired} has a retired-lane residual backlog", titles)
        self.assertIn("JetStream consumer n8n-current-workflow is an idle backlog candidate", titles)
        self.assertTrue(any("current workflow state is not verified" in f.detail for f in frag.findings))
        self.assertTrue(any("one snapshot does not prove a continuous outage" in f.detail for f in frag.findings))
        self.assertEqual(len(frag.facts["consumers"]), 7)

    def test_collect_fails_soft(self):
        from waybill.model import Ctx, TurnWindow
        old = nats.MONITOR_URL
        nats.MONITOR_URL = "http://127.0.0.1:9"
        try:
            c = Ctx(window=TurnWindow(cli="claude", surface="claude-code", session_id="s", t0=1.0, t_end=2.0), timeout_s=1.0)
            fr = nats.collect(c)
            self.assertEqual(fr.source.status, "error")
            self.assertTrue(fr.gaps)
        finally:
            nats.MONITOR_URL = old


if __name__ == "__main__":
    unittest.main()
