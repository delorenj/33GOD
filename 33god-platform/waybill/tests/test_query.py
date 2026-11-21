"""Tests for waybill.query (fixtures only: no database, no network, no live registry)."""
import gzip
import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from waybill import query as Q
from waybill.registry import Registry
from test_schema import SCHEMA, validate

REG = Registry.from_records(
    {
        "candybar": {"name": "Candybar", "first_party": True, "producers": ["candybar"]},
        "hook-hub": {"name": "Hook Hub", "first_party": True, "producers": ["hook-hub"]},
        "hermes-fleet": {"name": "Hermes Fleet", "first_party": True, "producers": ["hermes-agent"]},
        "agent-hooks": {"name": "Agent Hooks", "first_party": True, "producers": ["claude-code"]},
        "krebs": {"name": "Krebs", "first_party": True, "producers": ["krebs"]},
    },
    desks={"hermes-desk": {"owner": "hermes-fleet", "producer": "hermes-agent:", "bare": ["hermes-agent"], "near": "crew",
                           "name": "Hermes desk", "instance": "^[a-z0-9][a-z0-9-]*$", "malformed": [], "routes": []}},
    tenants=[{"producer": "tiller", "slug": "tiller"}],
)
SINCE = datetime(2026, 11, 20, 23, 2, tzinfo=timezone.utc).timestamp() * 1000.0     # 18:02 New York
UNTIL = datetime(2026, 11, 21, 12, 41, tzinfo=timezone.utc).timestamp() * 1000.0    # 07:41
HOUR = 3_600_000.0
_n = [0]


def uid() -> str:
    _n[0] += 1
    return f"00000000-0000-4000-8000-{_n[0]:012d}"


def row(t, producer, etype, failed=False, worker=None, source=None, rid=None):
    return Q.Row(rid or uid(), t, t + 5.0, producer, etype, source, failed, worker)


def fixture_rows():
    """A small, mixed night: a busy candybar, failures, rare events, a third-party desk, a tenant, a stranger."""
    rows = []
    for m in range(0, 300):                                           # candybar chatter, one per minute
        rows.append(row(SINCE + m * 60_000.0 + 1000, "candybar", "bloodbank.cron.candybar.invoked", worker="hindsight-turn"))
    for m in range(0, 40):                                            # failures of one job
        rows.append(row(SINCE + (200 + m) * 60_000.0, "candybar", "bloodbank.cron.candybar.failed", True, "hindsight-turn"))
    for m in range(0, 200):                                           # hook-hub mirrors, a few failed
        rows.append(row(SINCE + (400 + m) * 60_000.0, "hook-hub", "bloodbank.agent.hook.updated", failed=(m % 50 == 0)))
    for i in range(5):                                                # rare
        rows.append(row(SINCE + (30 + i) * 60_000.0, "krebs", "bloodbank.krebs.lease.granted"))
    for i in range(30):                                               # a client desk and its private messages
        rows.append(row(SINCE + (100 + i) * 60_000.0, "hermes-agent:acme-client-pm", "bloodbank.conversation.turn.completed"))
        rows.append(row(SINCE + (100 + i) * 60_000.0, "hermes-agent:acme-client-pm", "bloodbank.messaging.message.received"))
    for i in range(20):                                               # a first-party desk
        rows.append(row(SINCE + (500 + i) * 60_000.0, "hermes-agent:krebs-pm", "bloodbank.conversation.turn.completed"))
    for i in range(15):                                               # a tenant
        rows.append(row(SINCE + (600 + i) * 60_000.0, "tiller", "bloodbank.finance.projection.updated"))
    for i in range(14):                                               # a producer nothing resolves
        rows.append(row(SINCE + (50 + i) * 60_000.0, "mystery-box", "bloodbank.mystery.ping"))
    return rows


def envelopes_for(rows):
    def fetch(ids):
        by = {r.id: r for r in rows}
        return {i: {"id": i, "received_at": M_iso(by[i].ra),
                    "raw": {"id": i, "type": by[i].type, "producer": by[i].producer, "source": "urn:test",
                            "data": {"name": by[i].worker, "note": "hello", "outcome": "error" if by[i].failed else "ok"}}}
                for i in ids if i in by}
    return fetch


def M_iso(ms_):
    return datetime.fromtimestamp(ms_ / 1000.0, timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def build(rows=None, profile="public", dead=None, spec_kw=None, until=UNTIL, total=None):
    rows = fixture_rows() if rows is None else rows
    spec = Q.QuerySpec(since=SINCE, until=until, profile=profile, label="Last night, 18:02 to 07:41",
                       when="last night, 18:02 to 07:41", **(spec_kw or {}))
    b = Q.Builder(spec, REG, manifests={})
    wb = b.build(rows, len(rows) if total is None else total, dead or [], envelopes_for(rows), None, UNTIL)
    return wb, rows


class TestChapters(unittest.TestCase):
    def test_night_is_twelve_chapters_starting_at_1802_to_1910(self):
        b = Q.chapter_bounds(SINCE, UNTIL)
        self.assertEqual(len(b) - 1, 12)
        self.assertEqual(b[0], SINCE)
        self.assertEqual(b[-1], UNTIL)
        self.assertEqual(Q._hm(b[0], "America/New_York"), "18:02")
        self.assertEqual(Q._hm(b[1], "America/New_York"), "19:10")
        self.assertTrue(all((b[i] - SINCE) % 60_000.0 == 0 for i in range(12)))      # whole minutes

    def test_short_windows_get_fewer_chapters_and_budget_caps(self):
        self.assertEqual(len(Q.chapter_bounds(SINCE, SINCE + 20 * 60_000.0)) - 1, 4)
        self.assertEqual(len(Q.chapter_bounds(SINCE, SINCE + 30_000.0)) - 1, 1)
        self.assertEqual(len(Q.chapter_bounds(SINCE, UNTIL, budget_stops=20)) - 1, 4)
        self.assertEqual(len(Q.chapter_bounds(SINCE, UNTIL, budget_stops=500)) - 1, 12)

    def test_every_chapter_is_a_span_with_a_title(self):
        wb, _ = build()
        ch = [s for s in wb["spans"] if s["kind"] == "chapter"]
        self.assertEqual([s["id"] for s in ch], [f"chapter:{i}" for i in range(1, 13)])
        self.assertTrue(ch[0]["name"].startswith("18:02-19:10 · "), ch[0]["name"])
        self.assertEqual(sum(s["attrs"]["events"] for s in ch), wb["stats"]["query_total"])
        for s in ch:
            self.assertEqual(set(("index", "events", "kept", "batches")) - set(s["attrs"]), set())
        self.assertEqual(ch[0]["t0"], 0.0)
        self.assertEqual(ch[-1]["t1"], UNTIL - SINCE)

    def test_empty_chapter_is_quiet(self):
        wb, _ = build([row(SINCE + 1000, "candybar", "bloodbank.cron.candybar.invoked")])
        quiet = [s for s in wb["spans"] if s["kind"] == "chapter" and s["attrs"]["events"] == 0]
        self.assertTrue(quiet)
        self.assertTrue(all(s["name"].endswith("· quiet") for s in quiet))

    def test_title_names_the_dominant_components(self):
        wb, _ = build()
        names = " ".join(s["name"] for s in wb["spans"] if s["kind"] == "chapter")
        self.assertIn("Candybar", names)
        self.assertIn("the PM desks", names)


class TestConservation(unittest.TestCase):
    def test_kept_plus_batched_is_the_total(self):
        wb, rows = build()
        st = wb["stats"]
        self.assertEqual(st["query_total"], len(rows))
        self.assertEqual(st["kept_events"] + st["batched_events"], st["query_total"] + st["dead_letters"])
        self.assertTrue(st["conservation_ok"])
        self.assertEqual(st["kept_events"], len(wb["events"]))
        self.assertEqual(sum(s["attrs"]["count"] for s in wb["spans"] if s["kind"] == "batch"), st["batched_events"])

    def test_a_count_mismatch_is_broken_and_loud(self):
        wb, rows = build(total=len(fixture_rows()) + 7)
        self.assertFalse(wb["stats"]["conservation_ok"])
        self.assertTrue(any(g["severity"] == "broken" and "conservation" in g["what"] for g in wb["gaps"]))
        self.assertTrue(any(f["severity"] == "broken" and "conservation" in f["title"] for f in wb["findings"]))

    def test_dead_letters_count_on_the_dead_side(self):
        dead = [{"id": 1, "event_id": "dead-1", "topic": "bloodbank.evt.x.y", "reason": "malformed", "error": "bad json",
                 "received_at": M_iso(SINCE + 90 * 60_000.0), "raw_b64": "", "_env": {"id": "dead-1", "type": "bloodbank.x.y",
                                                                                         "producer": "krebs"}}]
        wb, rows = build(dead=dead)
        st = wb["stats"]
        self.assertEqual(st["dead_letters"], 1)
        self.assertEqual(st["kept_events"] + st["batched_events"], len(rows) + 1)
        self.assertTrue(st["conservation_ok"])
        ev = next(e for e in wb["events"] if e["id"] == "dead-1")
        self.assertEqual(ev["consumers"][0]["name"], "candystore-events")
        self.assertEqual(ev["consumers"][0]["outcome"], "dropped")
        self.assertTrue(any(g["severity"] == "warn" and "dead-lettered" in g["what"] for g in wb["gaps"]))
        self.assertTrue(any(f["severity"] == "broken" and "dead-lettered" in f["title"] for f in wb["findings"]))
        span = next(s for s in wb["spans"] if s["id"] == "publish:dead-1")
        self.assertEqual(span["status"], "dropped")

    def test_a_dead_letter_already_archived_is_not_counted_twice(self):
        rows = fixture_rows()
        dead = [{"id": 2, "event_id": rows[0].id, "topic": "t", "reason": "malformed", "error": "", "received_at": M_iso(SINCE),
                 "raw_b64": "", "_env": {"id": rows[0].id, "type": "bloodbank.x"}}]
        wb, _ = build(rows, dead=dead)
        self.assertEqual(wb["stats"]["dead_letters"], 0)
        self.assertTrue(wb["stats"]["conservation_ok"])


class TestKeepAndBatchRules(unittest.TestCase):
    def setUp(self):
        self.wb, self.rows = build()
        self.pub = {s["id"]: s for s in self.wb["spans"] if s["kind"] == "publish"}

    def test_small_queries_keep_everything_but_private(self):
        rows = [row(SINCE + i * 60_000.0, "krebs", "bloodbank.krebs.lease.granted") for i in range(50)]
        wb, _ = build(rows)
        self.assertEqual(wb["stats"]["kept_events"], 50)
        self.assertEqual(wb["stats"]["batches"], 0)
        self.assertTrue(all(s["attrs"]["keep"] == "all" for s in wb["spans"] if s["kind"] == "publish"))

    def test_rare_events_are_kept(self):
        rare = [s for s in self.pub.values() if s["attrs"]["type"] == "bloodbank.krebs.lease.granted"]
        self.assertEqual(len(rare), 5)
        self.assertTrue(all(s["attrs"]["keep"] == "rare" and s["component"] == "krebs" for s in rare))

    def test_failures_are_kept_or_counted_in_a_failed_batch(self):
        failed_kept = [s for s in self.pub.values() if s["status"] == "failed"]
        failed_batch = sum(s["attrs"]["failed"] for s in self.wb["spans"] if s["kind"] == "batch")
        self.assertEqual(len(failed_kept) + failed_batch, self.wb["stats"]["failures"])
        self.assertGreater(len(failed_kept), 0)
        for s in self.wb["spans"]:
            if s["kind"] == "batch":
                self.assertEqual(s["status"], "failed" if s["attrs"]["failed"] else "ok")

    def test_cap_is_400_with_a_warn_gap(self):
        rows = [row(SINCE + i * 1000.0, "candybar", "bloodbank.cron.candybar.failed", True, f"job-{i % 40}") for i in range(900)]
        wb, _ = build(rows)
        self.assertEqual(wb["stats"]["kept_events"], Q.KEEP_MAX)
        self.assertTrue(wb["stats"]["conservation_ok"])
        gap = next(g for g in wb["gaps"] if "keep rule" in g["what"])
        self.assertEqual(gap["severity"], "warn")
        self.assertIn("500 failure", gap["why"])

    def test_failures_and_rare_share_the_cap(self):
        rows = [row(SINCE + i * 1000.0, "candybar", "bloodbank.cron.candybar.failed", True, f"job-{i % 40}") for i in range(900)]
        rows += [row(SINCE + (2000 + i) * 1000.0, "krebs", f"bloodbank.krebs.odd{i}") for i in range(300)]
        wb, _ = build(rows)
        keeps = {s["attrs"]["keep"] for s in wb["spans"] if s["kind"] == "publish"}
        self.assertTrue({"failure", "rare"} <= keeps, keeps)

    def test_batch_math(self):
        batches = [s for s in self.wb["spans"] if s["kind"] == "batch"]
        self.assertTrue(batches)
        bounds = Q.chapter_bounds(SINCE, UNTIL)
        for s in batches:
            a = s["attrs"]
            mins = -(-int(bounds[a["chapter"]] - bounds[a["chapter"] - 1]) // 60_000)
            self.assertEqual(len(a["per_minute"]), mins)
            self.assertEqual(sum(a["per_minute"]), a["count"])
            self.assertLessEqual(len(a["exemplars"]), 3)
            self.assertEqual(s["summary"], f"{a['count']} × {s['name']}")
            self.assertEqual(s["parent"], f"chapter:{a['chapter']}")
            self.assertEqual(s["id"], f"batch:{s['component']}:{s['name']}:{a['chapter']}")
            self.assertLessEqual(s["t0"], s["t1"])
        big = next(s for s in batches if s["name"] == "cron.candybar.invoked" and s["attrs"]["chapter"] == 1)
        self.assertEqual(big["attrs"]["count"], sum(big["attrs"]["per_minute"]))
        self.assertEqual(big["attrs"]["producers"], ["candybar"])

    def test_candybar_job_credit(self):
        spec = Q.QuerySpec(since=SINCE, until=UNTIL, label="x")
        reg = Registry.from_records({**REG.records, "hindsight": {"name": "Hindsight", "first_party": True, "producers": []}})
        b = Q.Builder(spec, reg, manifests={})
        rows = fixture_rows()
        wb = b.build(rows, len(rows), [], envelopes_for(rows), None, UNTIL)
        credit = [s["attrs"]["credit"] for s in wb["spans"] if s["kind"] == "batch" and "credit" in s["attrs"]]
        self.assertTrue(credit)
        self.assertTrue(all("hindsight" in c for c in credit))

    def test_kept_event_carries_a_publish_span_at_its_component(self):
        ev = next(e for e in self.wb["events"] if e["type"] == "bloodbank.krebs.lease.granted")
        span = self.pub[ev["publisher_span"]]
        self.assertEqual(span["component"], "krebs")
        self.assertEqual(span["phase"], "async_after")
        self.assertTrue(span["parent"].startswith("chapter:"))
        self.assertEqual(ev["consumers"][0]["name"], "candystore-events")
        self.assertEqual(ev["consumers"][0]["outcome"], "archived")
        self.assertEqual(ev["stream"], "BLOODBANK_EVENTS")

    def test_is_failure_rule(self):
        self.assertTrue(Q.is_failure("bloodbank.cron.candybar.failed", {}))
        self.assertTrue(Q.is_failure("bloodbank.x.exhausted", None))
        self.assertTrue(Q.is_failure("bloodbank.x.denied", None))
        self.assertTrue(Q.is_failure("bloodbank.x.breached", None))
        self.assertTrue(Q.is_failure("bloodbank.llm.usage.recorded", {"outcome": "failed"}))
        self.assertTrue(Q.is_failure("bloodbank.agent.tool.completed", {"outcome": "error"}))
        self.assertTrue(Q.is_failure("bloodbank.agent.hook.updated", {"invocation": {"status": "succeeded", "executions": [
            {"status": "succeeded"}, {"status": "timed_out"}]}}))
        self.assertFalse(Q.is_failure("bloodbank.agent.hook.updated", {"invocation": {"status": "succeeded", "executions": [
            {"status": "skipped"}]}}))
        self.assertFalse(Q.is_failure("bloodbank.llm.usage.recorded", {"outcome": "completed"}))
        self.assertFalse(Q.is_failure("bloodbank.x.y", "nope"))

    def test_unresolved_producers_go_to_unknown_and_a_finding(self):
        st = self.wb["stats"]
        self.assertEqual(st["unresolved_producers"], 1)
        self.assertIn("unknown", self.wb["components"])
        self.assertFalse(self.wb["components"]["unknown"]["registry"])
        f = next(f for f in self.wb["findings"] if "resolve to no component" in f["title"])
        self.assertEqual(f["component"], "unknown")
        unknown = [s for s in self.wb["spans"] if s["component"] == "unknown" and s["kind"] in ("batch", "publish")]
        self.assertEqual(sum(s["attrs"].get("count", 1) for s in unknown), 14)       # none dropped

    def test_every_resolved_component_once_with_registry_flag(self):
        comps = self.wb["components"]
        self.assertTrue(comps["candybar"]["registry"])
        self.assertTrue(comps["hook-hub"]["registry"])
        for s in self.wb["spans"]:
            self.assertIn(s["component"], comps, s["id"])


class TestPublicProfile(unittest.TestCase):
    def test_private_types_are_counted_never_named(self):
        wb, rows = build()
        n_private = sum(1 for r in rows if r.type.startswith("bloodbank.messaging."))
        text = json.dumps(wb)
        self.assertNotIn("messaging", text)
        priv = [s for s in wb["spans"] if s["kind"] == "batch" and s["name"] == "private"]
        self.assertEqual(sum(s["attrs"]["count"] for s in priv), n_private)
        self.assertTrue(all(s["attrs"]["type"] == "private" and s["attrs"]["exemplars"] == [] for s in priv))
        self.assertTrue(wb["stats"]["conservation_ok"])

    def test_private_events_are_never_kept(self):
        rows = [row(SINCE + i * 1000.0, "hermes-agent:krebs-pm", "bloodbank.telephony.call.completed") for i in range(5)]
        wb, _ = build(rows)
        self.assertEqual(wb["stats"]["kept_events"], 0)
        self.assertEqual(wb["stats"]["batched_events"], 5)

    def test_third_party_desks_and_tenants_are_aliased(self):
        wb, _ = build()
        text = json.dumps(wb)
        self.assertNotIn("acme-client", text)
        self.assertNotIn("mystery-box", text)
        self.assertNotIn("tiller", text)
        self.assertIn("hermes-desk:desk-1", wb["components"])
        self.assertIn("tenant:tenant-1", wb["components"])
        self.assertIn("hermes-desk:krebs-pm", wb["components"])         # first party keeps its name

    def test_aliased_payloads_are_withheld(self):
        wb, _ = build()
        aliased = {e["id"] for e in wb["events"] if e["producer"].startswith(("hermes-agent:desk-", "producer-", "tenant-"))}
        for e in wb["events"]:
            if e["id"] in aliased:
                self.assertNotIn("payload", e)

    def test_full_profile_keeps_names(self):
        wb, _ = build(profile="full")
        text = json.dumps(wb)
        self.assertIn("acme-client-pm", text)
        self.assertIn("messaging", text)
        self.assertEqual(wb["recorder"]["profile"], "full")

    def test_a_credential_in_a_payload_never_survives(self):
        rows = [row(SINCE + 1000, "krebs", "bloodbank.krebs.lease.granted", rid="00000000-0000-4000-8000-0000000000aa")]

        def fetch(ids):
            return {i: {"id": i, "received_at": M_iso(SINCE), "raw": {"id": i, "type": "bloodbank.krebs.lease.granted",
                                                                         "producer": "krebs", "data": {"k": "ghp_" + "a" * 36}}}
                    for i in ids}
        spec = Q.QuerySpec(since=SINCE, until=UNTIL, label="x")
        wb = Q.Builder(spec, REG, manifests={}).build(rows, 1, [], fetch, None, UNTIL)
        self.assertNotIn("ghp_" + "a" * 36, json.dumps(wb))


EMAIL_RE = Q._EMAIL
LEAK_KEYS = ("tool_input", "transcript_text", "stderr_tail", "working_directory")


def _walk_keys(o):
    if isinstance(o, dict):
        for k, v in o.items():
            yield k
            yield from _walk_keys(v)
    elif isinstance(o, list):
        for v in o:
            yield from _walk_keys(v)


class TestPublicAllowList(unittest.TestCase):
    """The public profile is an allow-list: nothing a payload carries leaks by being forgotten in a deny-list."""

    def leaky(self):
        t = SINCE + 10 * 60_000.0
        recs = [
            ("hermes-agent:krebs-pm", "bloodbank.agent.tool.requested",
             {"tool_name": "terminal", "tool_call_id": "c1", "cwd": "/home/x/code/acme-client",
              "payload": {"tool_input": {"command": "px identity verify --key-ref op://DeLoSecrets/abc/credential"}},
              "result": "ok from ~/code/acme-client", "outcome": "ok"}),
            ("krebs", "bloodbank.audio.memo.transcribed", {"transcript_text": "Where'd we land with acme-client?", "status": "ok"}),
            ("candybar", "bloodbank.cron.candybar.failed",
             {"name": "crank-beat", "exit_code": 2, "stderr_tail": "mail jane.doe@example.com and bob@acme.io failed",
              "error": {"message": "jane.doe@example.com bounced"}}),
            ("krebs", "bloodbank.repo.task.created",
             {"name": "Put the privacy policy link in the footer", "title": "ACME-161", "description": "client words",
              "working_directory": "/srv/acme-client", "status": "todo"}),
            ("hermes-agent:acme-client-pm", "bloodbank.conversation.turn.completed", {"status": "ok"}),
        ]
        rows, data = [], {}
        for i, (prod, typ, d) in enumerate(recs):
            r = row(t + i * 1000.0, prod, typ, failed=Q.is_failure(typ, d), worker=d.get("name") if "candybar" in typ else None)
            rows.append(r)
            data[r.id] = d

        def fetch(ids):
            by = {r.id: r for r in rows}
            return {i: {"id": i, "received_at": M_iso(by[i].ra),
                        "raw": {"id": i, "type": by[i].type, "producer": by[i].producer, "source": "urn:test",
                                "time": M_iso(by[i].t), "extra_header": "secret header", "data": data[i]}}
                    for i in ids if i in by}
        return rows, fetch

    def build_leaky(self, filters=None, profile="public"):
        rows, fetch = self.leaky()
        spec = Q.QuerySpec(since=SINCE, until=SINCE + HOUR, label="x", profile=profile, filters=filters or {})
        return Q.Builder(spec, REG, manifests={}).build(rows, len(rows), [], fetch, None, SINCE + HOUR), rows

    def test_no_payload_text_keys_or_mail_survive_public(self):
        wb, _ = self.build_leaky()
        text = json.dumps(wb, ensure_ascii=False)
        for needle in ("acme", "op://", "privacy policy", "client words", "Where'd", "secret header", "ACME-161"):
            self.assertNotIn(needle.lower(), text.lower(), needle)
        self.assertIsNone(EMAIL_RE.search(text), EMAIL_RE.search(text))
        keys = set(_walk_keys(wb))
        for k in LEAK_KEYS:
            self.assertNotIn(k, keys)
            self.assertNotIn(f'"{k}"', text)
        self.assertEqual(validate(wb, SCHEMA, SCHEMA)[:5], [])

    def test_public_keeps_the_header_and_status_fields(self):
        wb, _ = self.build_leaky()
        arts = [a["json"] for a in wb["artifacts"].values() if isinstance(a.get("json"), dict)]
        tool = next(a for a in arts if a.get("type") == "bloodbank.agent.tool.requested")
        self.assertEqual(tool["data"]["tool_name"], "terminal")
        self.assertEqual(tool["data"]["outcome"], "ok")
        self.assertEqual(tool["data"]["tool_call_id"], "«dropped»")       # the key name stays, its value does not
        self.assertEqual(tool["producer"], "hermes-agent:krebs-pm")
        job = next(a for a in arts if a.get("type") == "bloodbank.cron.candybar.failed")
        self.assertEqual(job["data"]["name"], "crank-beat")
        self.assertEqual(job["data"]["exit_code"], 2)
        task = next(a for a in arts if a.get("type") == "bloodbank.repo.task.created")
        self.assertEqual(task["data"]["name"], "«dropped»")              # a sentence is not a slug

    def test_full_profile_keeps_the_payload(self):
        wb, _ = self.build_leaky(profile="full")
        self.assertIn("tool_input", json.dumps(wb))

    def test_filters_are_aliased_like_the_events(self):
        rows, fetch = self.leaky()
        for flt in ({"producer": "hermes-agent:acme-client-pm"}, {"project": "acme-client"}, {"q": "acme-client"},
                    {"type": "bloodbank.messaging.sms.received"}):
            spec = Q.QuerySpec(since=SINCE, until=SINCE + HOUR, label="x", filters=flt)
            wb = Q.Builder(spec, REG, manifests={}).build(rows, len(rows), [], fetch, None, SINCE + HOUR)
            text = json.dumps(wb)
            self.assertNotIn("acme", text.lower(), flt)
            self.assertNotIn("messaging", text, flt)
        spec = Q.QuerySpec(since=SINCE, until=SINCE + HOUR, label="x", filters={"producer": "hermes-agent:acme-client-pm"})
        wb = Q.Builder(spec, REG, manifests={}).build(rows, len(rows), [], fetch, None, SINCE + HOUR)
        self.assertEqual(wb["origin"]["query"]["filters"]["producer"], "hermes-agent:desk-1")
        self.assertIn("producer hermes-agent:desk-1", wb["prompt"]["text"])
        self.assertIn("hermes-desk:desk-1", wb["components"])          # the filter and the events agree on the alias

    def test_events_derived_from_private_ones_are_private(self):
        rows = [row(SINCE + 1000, "target-watch", "bloodbank.watch.target.detected"),
                Q.Row(uid(), SINCE + 2000, SINCE + 2005, "krebs", "bloodbank.krebs.digest.ready", None, False, None,
                      "messaging.email.received")]
        wb, _ = build(rows)
        self.assertEqual(wb["stats"]["kept_events"], 0)
        self.assertNotIn("watch.target", json.dumps(wb))
        self.assertEqual(sum(s["attrs"]["count"] for s in wb["spans"] if s["kind"] == "batch" and s["name"] == "private"), 2)

    def test_batches_carry_per_producer_counts(self):
        rows = [row(SINCE + i * 1000.0, "claude-code" if i % 3 else "hook-hub", "bloodbank.agent.tool.requested") for i in range(450)]
        wb, _ = build(rows, profile="full")
        batches = [x for x in wb["spans"] if x["kind"] == "batch"]
        self.assertTrue(batches)
        for s in batches:
            self.assertEqual(sum(s["attrs"]["producer_counts"].values()), s["attrs"]["count"])
            self.assertEqual(list(s["attrs"]["producer_counts"]), s["attrs"]["producers"])


class TestContract(unittest.TestCase):
    def setUp(self):
        self.wb, self.rows = build()

    def test_validates_against_the_schema(self):
        errs = validate(self.wb, SCHEMA, SCHEMA)
        self.assertEqual(errs, [], errs[:5])

    def test_full_profile_validates_too(self):
        wb, _ = build(profile="full")
        self.assertEqual(validate(wb, SCHEMA, SCHEMA)[:5], [])

    def test_origin_prompt_and_clock(self):
        wb = self.wb
        self.assertEqual(wb["recorder"]["mode"], "query")
        o = wb["origin"]
        self.assertEqual((o["cli"], o["surface"], o["turn_id"], o["turn_index"], o["cwd"], o["model"]),
                         ("candystore", "query", None, None, None, None))
        self.assertRegex(o["session_id"], r"^q_[0-9a-f]{12}$")
        q = o["query"]
        self.assertEqual(q["total"], len(self.rows))
        self.assertEqual(q["clock"], "time")
        self.assertEqual(q["label"], "Last night, 18:02 to 07:41")
        self.assertEqual(wb["prompt"]["text"], "You asked the archive: everything the company did last night, 18:02 to 07:41")
        self.assertFalse(wb["prompt"]["truncated"])
        self.assertEqual(wb["prompt"]["chars"], len(wb["prompt"]["text"]))
        self.assertEqual(wb["spans"][0]["kind"], "prompt")
        self.assertEqual(wb["clock"]["t0"], q["since"])
        self.assertEqual(wb["clock"]["t_end"], q["until"])
        self.assertEqual(wb["clock"]["duration_ms"], UNTIL - SINCE)

    def test_query_id_is_deterministic_and_filter_sensitive(self):
        a = Q.QuerySpec(SINCE, UNTIL)
        b = Q.QuerySpec(SINCE, UNTIL, filters={"project": "flume"})
        self.assertEqual(a.query_id(), Q.QuerySpec(SINCE, UNTIL, label="other label").query_id())
        self.assertNotEqual(a.query_id(), b.query_id())
        wb, _ = build(spec_kw={"filters": {"project": "krebs"}})          # a first-party project keeps its name
        self.assertEqual(wb["origin"]["project"], "krebs")
        self.assertIn("project krebs", wb["prompt"]["text"])
        wb, _ = build(spec_kw={"filters": {"project": "flume"}}, profile="full")
        self.assertEqual(wb["origin"]["project"], "flume")

    def test_spans_reference_real_parents_and_unique_ids(self):
        ids = [s["id"] for s in self.wb["spans"]]
        self.assertEqual(len(ids), len(set(ids)))
        for s in self.wb["spans"]:
            if s.get("parent"):
                self.assertIn(s["parent"], ids)

    def test_stats_keys(self):
        for k in ("query_total", "kept_events", "batched_events", "batches", "chapters", "dead_letters",
                  "conservation_ok", "unresolved_producers"):
            self.assertIn(k, self.wb["stats"])
        self.assertIsInstance(self.wb["stats"]["conservation_ok"], bool)

    def test_commands_gap(self):
        self.assertTrue(any("commands" in g["what"] for g in self.wb["gaps"]))


class TestSynthesizedSpans(unittest.TestCase):
    def test_tool_llm_and_hook_spans(self):
        t = SINCE + 5 * 60_000.0
        recs = {
            "t1": (t, "claude-code", "bloodbank.agent.tool.requested", {"tool_name": "Bash", "tool_call_id": "toolu_1"}),
            "t2": (t + 900, "claude-code", "bloodbank.agent.tool.completed", {"tool_name": "Bash", "tool_call_id": "toolu_1", "outcome": "error"}),
            "l1": (t + 100, "aai-llm-observability", "bloodbank.llm.usage.recorded",
                   {"request_id": "bg-abc", "outcome": "completed", "latency_ms": 500, "occurred_at": M_iso(t + 600),
                    "returned_model": "m", "usage": {"input_tokens": 3, "output_tokens": 4}}),
            "l2": (t + 200, "aai-llm-observability", "bloodbank.llm.usage.recorded",
                   {"request_id": "12345", "outcome": "failed", "latency_ms": 100, "occurred_at": M_iso(t + 300)}),
            "h1": (t + 300, "hook-hub", "bloodbank.agent.hook.updated",
                   {"revision": 2, "invocation": {"invocation_id": "inv-1", "native": "Stop", "cli": "claude", "role": "stop",
                                                    "status": "succeeded", "received_at": M_iso(t + 300),
                                                    "updated_at": M_iso(t + 400),
                                                    "executions": [{"handler_id": "hindsight-turn", "mode": "async",
                                                                    "status": "failed", "event_id": None},
                                                                   {"handler_id": "x", "mode": "sync", "status": "succeeded"}]}}),
            "h0": (t + 250, "hook-hub", "bloodbank.agent.hook.updated",
                   {"revision": 1, "invocation": {"invocation_id": "inv-1", "native": "Stop", "status": "received"}}),
        }
        rows, payload = [], {}
        for key, (tt, prod, typ, data) in recs.items():
            r = row(tt, prod, typ, failed=Q.is_failure(typ, data), rid=f"00000000-0000-4000-8000-00000000{ord(key[0]):02x}{key[1]}0")
            rows.append(r)
            payload[r.id] = data

        def fetch(ids):
            by = {r.id: r for r in rows}
            return {i: {"id": i, "received_at": M_iso(by[i].ra), "raw": {"id": i, "type": by[i].type, "producer": by[i].producer,
                                                                          "correlationid": "inv-1", "data": payload[i]}} for i in ids}
        spec = Q.QuerySpec(since=SINCE, until=SINCE + HOUR, label="x")
        wb = Q.Builder(spec, REG, manifests={}).build(rows, len(rows), [], fetch, None, SINCE + HOUR)
        by = {s["id"]: s for s in wb["spans"]}
        self.assertEqual(by["tool:toolu_1"]["status"], "failed")
        self.assertEqual(by["tool:toolu_1"]["name"], "Bash")
        self.assertAlmostEqual(by["tool:toolu_1"]["t1"] - by["tool:toolu_1"]["t0"], 900)
        self.assertEqual(by["llm:bg-abc"]["component"], "aai-gateway")
        self.assertEqual(by["llm:bg-abc"]["status"], "ok")
        self.assertEqual(by["llm:req-12345"]["status"], "failed")
        self.assertAlmostEqual(by["llm:bg-abc"]["t1"] - by["llm:bg-abc"]["t0"], 500)
        self.assertEqual(by["hook:inv-1"]["component"], "hook-hub")
        self.assertEqual(by["hook:inv-1"]["status"], "ok")
        self.assertEqual(by["handler:inv-1:hindsight-turn"]["status"], "failed")
        self.assertFalse(by["handler:inv-1:hindsight-turn"]["sync"])
        self.assertTrue(by["handler:inv-1:x"]["sync"])
        self.assertEqual(validate(wb, SCHEMA, SCHEMA)[:5], [])

    def test_system_hook_updated_is_not_a_mirror(self):
        rows = [row(SINCE + 1000, "hook-hub", "bloodbank.system.hook.updated")]
        wb, _ = build(rows)
        self.assertFalse([s for s in wb["spans"] if s["kind"] == "hook"])


class TestSizeBound(unittest.TestCase):
    def test_gzip_is_far_smaller_than_the_json(self):
        wb, _ = build()
        raw, gz = Q.encode(wb, False), Q.encode(wb, True)
        self.assertLess(len(gz), len(raw) / 3)
        self.assertEqual(json.loads(gzip.decompress(gz))["id"], wb["id"])

    def test_fit_budget_drops_payloads_then_handlers_never_batches(self):
        wb, _ = build()
        before_batches = [s["id"] for s in wb["spans"] if s["kind"] == "batch"]
        before_stats = {k: wb["stats"][k] for k in ("query_total", "kept_events", "batched_events", "conservation_ok")}
        full = len(Q.encode(wb, False))
        wb, size = Q.fit_budget(wb, full // 2, False)
        self.assertFalse(wb["artifacts"])
        self.assertEqual(before_batches, [s["id"] for s in wb["spans"] if s["kind"] == "batch"])
        self.assertEqual(before_stats, {k: wb["stats"][k] for k in before_stats})
        self.assertTrue(any("max-kb" in f["title"] for f in wb["findings"]))

    def test_over_budget_after_dropping_is_a_warn_gap(self):
        wb, _ = build()
        wb, size = Q.fit_budget(wb, 2000, False)
        self.assertGreater(size, 2000)
        self.assertTrue(any(g["severity"] == "warn" and "over --max-kb" in g["what"] for g in wb["gaps"]))

    def test_in_budget_is_untouched(self):
        wb, _ = build()
        n = len(wb["artifacts"])
        wb, size = Q.fit_budget(wb, 10 * 1024 * 1024, True)
        self.assertEqual(len(wb["artifacts"]), n)

    def test_a_night_of_many_events_stays_small(self):
        rows = []
        for i in range(30000):
            rows.append(row(SINCE + i * 1500.0, ["candybar", "hook-hub", "claude-code", "hermes-agent:krebs-pm"][i % 4],
                            ["bloodbank.a.b", "bloodbank.c.d", "bloodbank.e.f"][i % 3]))
        wb, _ = build(rows)
        self.assertTrue(wb["stats"]["conservation_ok"])
        self.assertLess(len(Q.encode(wb, True)), 2 * 1024 * 1024)
        self.assertLessEqual(wb["stats"]["kept_events"], Q.KEEP_MAX)


class TestWindowsAndUrls(unittest.TestCase):
    def test_last_night_is_1802_to_0741_in_new_york(self):
        now = datetime(2026, 11, 21, 12, 48, tzinfo=timezone.utc).timestamp() * 1000.0
        lo, hi = Q.last_night(now)
        self.assertEqual(lo, SINCE)
        self.assertEqual(hi, UNTIL)

    def test_parse_duration(self):
        self.assertEqual(Q.parse_duration("2h"), 7_200_000.0)
        self.assertEqual(Q.parse_duration("30m"), 1_800_000.0)
        self.assertEqual(Q.parse_duration("1d"), 86_400_000.0)
        with self.assertRaises(ValueError):
            Q.parse_duration("soon")

    def test_labels(self):
        self.assertEqual(Q.window_label("last-night", SINCE, UNTIL, "America/New_York")[0], "Last night, 18:02 to 07:41")
        self.assertEqual(Q.window_label("last-night", SINCE, UNTIL, "America/New_York")[1], "last night, 18:02 to 07:41")
        self.assertTrue(Q.window_label("last", UNTIL - 2 * HOUR, UNTIL, "America/New_York")[0].startswith("The last 2 hours"))
        self.assertIn("so far", Q.window_label("last-night", SINCE, UNTIL, "America/New_York", True)[0])
        # a session that crosses midnight names its end date (13:32 on the 20th to 07:08 on the 21st, New York)
        a = datetime(2026, 11, 20, 18, 32, tzinfo=timezone.utc).timestamp() * 1000.0
        b = datetime(2026, 11, 21, 12, 8, tzinfo=timezone.utc).timestamp() * 1000.0
        self.assertEqual(Q.window_label("session", a, b, "America/New_York", extra="c5f80064-aaaa")[0],
                         "Session c5f80064, 20 Nov 13:32 to 21 Nov 07:08")

    def test_candystore_ui_urls(self):
        u = Q.parse_candystore_url("https://candystore.delo.sh/projects/flume?lens=errors&class=prompt&tools=0&from=2026-11-20T18:00&q=boom")
        self.assertEqual(u["filters"], {"project": "flume", "lens": "errors", "class": "prompt", "q": "boom"})
        self.assertEqual(u["from"], "2026-11-20T18:00")
        s = Q.parse_candystore_url("http://x/sessions/5b0c2f6e-0000-4000-8000-000000000001")
        self.assertEqual(s["filters"], {"correlation": "5b0c2f6e-0000-4000-8000-000000000001"})
        e = Q.parse_candystore_url("http://x/events/5b0c2f6e-0000-4000-8000-000000000002")
        self.assertEqual(e["event"], "5b0c2f6e-0000-4000-8000-000000000002")
        a = Q.parse_candystore_url("http://x/events?type=bloodbank.a.b&correlationid=abc&producer=krebs")
        self.assertEqual(a["filters"], {"type": "bloodbank.a.b", "correlation": "abc", "producer": "krebs"})


class FakeReader:
    kind = "fake"
    locator = "fixture"

    def __init__(self, rows, dead=None, fail_where=False):
        self.rows_, self.dead_ = rows, dead or []
        self.fail_where = fail_where
        self.seen = {}

    def now_ms(self):
        return UNTIL + 60_000.0

    def where(self, filters):
        if self.fail_where:
            raise RuntimeError("Candystore could not render the filters: boom")
        self.seen["filters"] = filters
        return "true"

    def count(self, spec, where, as_of):
        return len(self.rows_)

    def rows(self, spec, where, as_of):
        yield from self.rows_

    def envelopes(self, ids):
        return envelopes_for(self.rows_)(ids)

    def dead_letters(self, spec, as_of):
        return self.dead_


class TestRun(unittest.TestCase):
    def test_run_end_to_end_with_a_fake_reader(self):
        rows = fixture_rows()
        spec = Q.QuerySpec(SINCE, UNTIL, label="Last night, 18:02 to 07:41", filters={"project": "flume"})
        r = FakeReader(rows)
        wb = Q.run(spec, r, REG, manifests={}, holocene=False)
        self.assertEqual(r.seen["filters"], {"project": "flume"})
        self.assertTrue(wb["stats"]["conservation_ok"])
        self.assertEqual(wb["stats"]["query_total"], len(rows))
        self.assertIn("wall_ms", wb["stats"])
        self.assertEqual({s["id"] for s in wb["sources"]} >= {"candystore", "candystore-envelopes"}, True)
        self.assertEqual(validate(wb, SCHEMA, SCHEMA)[:5], [])

    def test_unmatchable_filters_skip_dead_letters_with_a_gap(self):
        spec = Q.QuerySpec(SINCE, UNTIL, filters={"lens": "errors"})
        wb = Q.run(spec, FakeReader(fixture_rows(), dead=[{"id": 1}]), REG, manifests={}, holocene=False)
        self.assertEqual(wb["stats"]["dead_letters"], 0)
        self.assertTrue(any("dead letters left out" in g["what"] for g in wb["gaps"]))

    def test_dead_letters_matched_in_python(self):
        import base64
        env = {"id": "d-1", "type": "bloodbank.krebs.lease.granted", "producer": "krebs"}
        dead = [{"id": 1, "event_id": "d-1", "topic": "t", "reason": "malformed", "error": "x", "received_at": M_iso(SINCE + 1000),
                 "raw_b64": base64.b64encode(json.dumps(env).encode()).decode()},
                {"id": 2, "event_id": "d-2", "topic": "t", "reason": "malformed", "error": "x", "received_at": M_iso(SINCE + 2000),
                 "raw_b64": base64.b64encode(json.dumps({"id": "d-2", "type": "bloodbank.other.thing", "producer": "krebs"}).encode()).decode()}]
        spec = Q.QuerySpec(SINCE, UNTIL, filters={"type": "bloodbank.krebs.lease.granted"})
        wb = Q.run(spec, FakeReader([], dead=dead), REG, manifests={}, holocene=False)
        self.assertEqual(wb["stats"]["dead_letters"], 1)
        self.assertEqual([e["id"] for e in wb["events"]], ["d-1"])

    def test_dead_letters_can_be_turned_off(self):
        spec = Q.QuerySpec(SINCE, UNTIL, include_dead_letters=False)
        wb = Q.run(spec, FakeReader(fixture_rows(), dead=[{"id": 1}]), REG, manifests={}, holocene=False)
        self.assertEqual(wb["stats"]["dead_letters"], 0)

    def test_filter_render_failure_is_raised(self):
        with self.assertRaises(RuntimeError):
            Q.run(Q.QuerySpec(SINCE, UNTIL, filters={"lens": "errors"}), FakeReader([], fail_where=True), REG,
                  manifests={}, holocene=False)

    def test_sql_is_read_only_windowed_and_keyset_paged(self):
        spec = Q.QuerySpec(SINCE, UNTIL)
        r = Q.PsqlReader()
        sql = r.page_sql(spec, "true", UNTIL, ("2026-11-21T00:00:00Z", "00000000-0000-4000-8000-000000000001"))
        self.assertIn("order by time, id limit", sql)
        self.assertIn("(time, id) >", sql)
        self.assertRegex(sql, r"time >= '2026-11-20T23:02:00")
        self.assertIn("received_at <=", sql)
        rec = Q.PsqlReader.window_sql(Q.QuerySpec(SINCE, UNTIL, clock="received_at"), UNTIL)
        self.assertIn("received_at >=", rec)
        self.assertIn("time >=", rec)       # received_at queries are still time-bounded (the indexed column)


class TestPublishQuery(unittest.TestCase):
    URL = "https://s3.delo.sh/projects/33god/2026-11-21/q/wb.waybill.json.gz"

    def _run(self, wb, name="in.waybill.json.gz", **kw):
        import tempfile
        from waybill import publish as pub

        class P:
            returncode = 0
            stdout = json.dumps({"ok": True, "entry_url": self.URL}) + "\n" + self.URL
            stderr = ""
        seen = {}

        def runner(cmd, **k):
            d = Path(cmd[2])
            f = next(d.iterdir())
            seen["name"], seen["bytes"] = f.name, f.read_bytes()
            return P()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / name
            path.write_bytes(Q.encode(wb, True))
            res = pub.publish(str(path), runner=runner, **kw)
        return res, seen

    def test_gz_query_waybill_publishes_as_gz_and_is_public(self):
        wb, _ = build()
        res, seen = self._run(wb)
        self.assertTrue(seen["name"].endswith(".waybill.json.gz"))
        self.assertEqual(seen["bytes"][:2], b"\x1f\x8b")
        doc = json.loads(gzip.decompress(seen["bytes"]))
        self.assertEqual(doc["recorder"]["mode"], "query")
        self.assertTrue(res["json_url"].endswith(".waybill.json.gz"))
        self.assertIn("waybill=", res["factory_url"])

    def test_full_profile_query_waybill_is_refused(self):
        wb, _ = build(profile="full")
        with self.assertRaises(ValueError):
            self._run(wb)

    def test_cli_load_waybill_reads_gzip(self):
        import tempfile
        from waybill import cli
        wb, _ = build()
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "x.waybill.json.gz"
            cli.write_waybill(wb, str(p), compact=True)
            self.assertEqual(p.read_bytes()[:2], b"\x1f\x8b")
            self.assertEqual(cli.load_waybill(str(p))["id"], wb["id"])

    def test_query_parser_and_usage_spec(self):
        from waybill import cli
        a = cli.build_parser().parse_args(["query", "--last-night", "--project", "flume", "--no-include-dead-letters",
                                           "--max-kb", "100", "-o", "x.waybill.json.gz", "--publish"])
        self.assertTrue(a.last_night and a.publish and not a.include_dead_letters)
        self.assertEqual((a.profile, a.budget_stops, a.clock), ("public", 60, "time"))
        kdl = (ROOT / "waybill" / "waybill.usage.kdl").read_text()
        self.assertIn("cmd query", kdl)
        self.assertIn("--last-night", kdl)


if __name__ == "__main__":
    unittest.main()
