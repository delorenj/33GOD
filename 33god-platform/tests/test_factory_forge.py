"""Factory forge (I-10): pick ranking, polish mode, scope check, glb validator, manifest, ledger, prompt."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import struct
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ff = _load("god_factory_forge", ROOT / "scripts" / "factory_forge.py")
glbcheck = _load("god_glbcheck", ROOT / "manual" / "sandbox" / "tools" / "forge" / "glbcheck.py")


def make_glb(path: Path, durations=None, seam=0.0, size=(2.0, 1.5, 2.0), sockets=("socket_in", "socket_hold", "socket_out"), tris_x=1):
    """A hand-built glb: a floor-standing box, three socket empties, four one-channel animations."""
    durations = durations or {"Idle": 4.0, "Accept": 1.0, "Work": 2.0, "Emit": 0.8}
    sx, sy, sz = size
    v = [(x * sx / 2, y * sy, z * sz / 2) for x in (-1, 1) for y in (0, 1) for z in (-1, 1)]
    idx = [0, 1, 2, 1, 3, 2, 4, 6, 5, 5, 6, 7, 0, 4, 1, 1, 4, 5, 2, 3, 6, 3, 7, 6, 0, 2, 4, 2, 6, 4, 1, 5, 3, 3, 5, 7] * tris_x
    blob = b""
    views, accs = [], []

    def add(data: bytes, comp, typ, count, mn=None, mx=None):
        nonlocal blob
        off = len(blob)
        blob += data + b"\0" * (-len(data) % 4)
        views.append({"buffer": 0, "byteOffset": off, "byteLength": len(data)})
        a = {"bufferView": len(views) - 1, "componentType": comp, "count": count, "type": typ}
        if mn is not None:
            a["min"], a["max"] = mn, mx
        accs.append(a)
        return len(accs) - 1

    pos = add(b"".join(struct.pack("<3f", *p) for p in v), 5126, "VEC3", len(v),
              [min(p[i] for p in v) for i in range(3)], [max(p[i] for p in v) for i in range(3)])
    ind = add(struct.pack(f"<{len(idx)}H", *idx), 5123, "SCALAR", len(idx))
    nodes = [{"name": "body", "mesh": 0}, {"name": "part"}] + [{"name": s} for s in sockets]
    anims = []
    for name, dur in durations.items():
        tin = add(struct.pack("<2f", 0.0, dur), 5126, "SCALAR", 2, [0.0], [dur])
        out = add(struct.pack("<6f", 0, 0, 0, 0, seam, 0), 5126, "VEC3", 2)
        anims.append({"name": name, "samplers": [{"input": tin, "output": out}], "channels": [{"sampler": 0, "target": {"node": 1, "path": "translation"}}]})
    g = {"asset": {"version": "2.0"}, "scene": 0, "scenes": [{"nodes": list(range(len(nodes)))}], "nodes": nodes,
         "meshes": [{"primitives": [{"attributes": {"POSITION": pos}, "indices": ind}]}], "accessors": accs, "bufferViews": views,
         "buffers": [{"byteLength": len(blob)}], "animations": anims}
    js = json.dumps(g).encode()
    js += b" " * (-len(js) % 4)
    total = 12 + 8 + len(js) + 8 + len(blob)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"glTF" + struct.pack("<II", 2, total) + struct.pack("<II", len(js), 0x4E4F534A) + js + struct.pack("<II", len(blob), 0x004E4942) + blob)


def manifest(cid="a", placement="station", score=8, **kw):
    m = {"format": "33god.factory-asset", "version": 1, "id": cid, "title": "The receiving dock", "placement": placement,
         "replaces": ["Dock"] if placement == "station" else [], "footprint": [2.0, 2.0] if placement == "station" else [1.2, 1.2],
         "height": 1.5, "scale": 1, "rotationY": 0, "handles": ["parcel"],
         "clips": {"idle": "Idle", "accept": "Accept", "work": "Work", "emit": "Emit"},
         "sockets": {"in": "socket_in", "hold": "socket_hold", "out": "socket_out"},
         "budget": {"tris": 15000, "glbKB": 600}, "forge": {"run": "2026-11-18T01:30-0500", "rounds": 2, "score": score}}
    m.update(kw)
    return m


class Tree(unittest.TestCase):
    """A throwaway platform tree with a registry, a night digest and a cast."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "plat"
        self.p = ff.Paths(self.root)
        for d in (self.p.registry, self.p.nights, self.p.assets, self.p.forge, self.p.tools):
            d.mkdir(parents=True)
        (self.p.forge / "PROMPT.md").write_text("# brief\n")
        (self.p.forge / "CONTRACT.md").write_text("# contract\n")

    def tearDown(self):
        self.tmp.cleanup()

    def comp(self, cid, first_party=True, relations=(), factory=None, summary="does a thing"):
        rec = {"id": cid, "name": cid.title(), "summary": summary, "first_party": first_party, "kind": "service", "domain": "G3",
               "relations": [{"to": t, "kind": "calls", "via": "x"} for t in relations]}
        if factory:
            rec["factory"] = factory
        (self.p.registry / f"{cid}.yaml").write_text(yaml.safe_dump(rec))

    def night(self, name="2026-11-16", **events):
        (self.p.nights / f"{name}.json").write_text(json.dumps({"components": [{"id": k, "events": v, "credited": 0} for k, v in events.items()]}))

    def cast(self, **stations):
        comps = {k: {"station": v, "near": None if v else "dock", "aliases": []} for k, v in stations.items()}
        self.p.cast.parent.mkdir(parents=True, exist_ok=True)
        self.p.cast.write_text(json.dumps({"format": "33god.factory-cast", "version": 1, "components": comps}))

    def asset(self, cid, score=None, run=None, **kw):
        d = self.p.asset_dir(cid)
        d.mkdir(parents=True, exist_ok=True)
        m = manifest(cid, **kw)
        m["forge"] = {"run": run or "2026-11-01T01:40-0500", "rounds": 1, "score": 8 if score is None else score}
        (d / "asset.json").write_text(json.dumps(m))


class PickTest(Tree):
    def test_station_first_then_traffic_then_first_party_then_id(self):
        for c, fp in (("a-quiet", True), ("b-busy-nostation", True), ("c-busy", True), ("d-mid", True), ("e-third", False), ("f-third", True), ("g-third", True)):
            self.comp(c, first_party=fp)
        self.cast(**{"a-quiet": "dock", "b-busy-nostation": None, "c-busy": "belt", "d-mid": "clock", "e-third": "crew", "f-third": "archive", "g-third": "rules"})
        self.night(**{"a-quiet": 5, "b-busy-nostation": 9999, "c-busy": 900, "d-mid": 400, "e-third": 100, "f-third": 100, "g-third": 100})
        res = ff.pick(self.p)
        order = [r["id"] for r in res["ranked"]]
        self.assertEqual(order, ["c-busy", "d-mid", "f-third", "g-third", "e-third", "a-quiet", "b-busy-nostation"])
        self.assertEqual((res["id"], res["mode"]), ("c-busy", "build"))
        self.assertIn("station=belt", res["ranked"][0]["reasons"])

    def test_components_with_an_asset_are_not_candidates(self):
        self.comp("a"); self.comp("b"); self.cast(a="dock", b="belt"); self.night(a=500, b=10); self.asset("a")
        res = ff.pick(self.p)
        self.assertEqual([r["id"] for r in res["ranked"]], ["b"])
        self.assertEqual(res["assets"], 1)

    def test_a_station_with_a_body_hosts_no_second_one(self):
        self.comp("a"); self.comp("b"); self.comp("c"); self.cast(a="control", b="control", c="belt"); self.night(a=500, b=400, c=1); self.asset("a")
        self.assertEqual([r["id"] for r in ff.pick(self.p)["ranked"]], ["c"])
        with self.assertRaises(SystemExit):
            ff.pick(self.p, "b")
        self.assertEqual(ff.pick(self.p, "a")["mode"], "polish")

    def test_a_dir_without_asset_json_is_still_a_candidate(self):
        self.comp("a"); self.cast(a="dock"); (self.p.asset_dir("a")).mkdir(parents=True)
        self.assertEqual(ff.pick(self.p)["id"], "a")

    def test_newest_night_is_used(self):
        self.comp("a"); self.comp("b"); self.cast(a="dock", b="dock")
        self.night("2026-11-15", a=900, b=1); self.night("2026-11-16", a=1, b=900)
        self.assertEqual(ff.pick(self.p)["id"], "b")

    def test_credited_work_counts_as_traffic(self):
        self.comp("a"); self.comp("b"); self.cast(a="dock", b="dock")
        (self.p.nights / "2026-11-16.json").write_text(json.dumps({"components": [
            {"id": "a", "events": 10, "credited": 0}, {"id": "b", "events": 2, "credited": 50}]}))
        self.assertEqual(ff.pick(self.p)["id"], "b")

    def test_no_night_digest_falls_back_to_first_party_then_id(self):
        self.comp("b", first_party=False); self.comp("a", first_party=False); self.comp("c", first_party=True)
        self.cast(a="dock", b="dock", c="dock")
        self.assertEqual([r["id"] for r in ff.pick(self.p)["ranked"]], ["c", "a", "b"])

    def test_registry_factory_block_is_used_when_there_is_no_cast(self):
        self.comp("a", factory={"station": "dock"}); self.comp("b")
        res = ff.pick(self.p)
        self.assertEqual(res["id"], "a")
        self.assertEqual(res["cast_source"], "registry factory: blocks")

    def test_component_override_and_alias(self):
        self.comp("a"); self.comp("b"); self.cast(a="dock", b="dock")
        c = json.loads(self.p.cast.read_text()); c["components"]["b"]["aliases"] = ["b-old"]; self.p.cast.write_text(json.dumps(c))
        self.assertEqual(ff.pick(self.p, "b")["id"], "b")
        self.assertEqual(ff.pick(self.p, "b-old")["id"], "b")
        self.asset("a")
        self.assertEqual(ff.pick(self.p, "a")["mode"], "polish")
        with self.assertRaises(SystemExit):
            ff.pick(self.p, "nope")

    def test_cooling_off_after_two_failures(self):
        self.comp("a"); self.comp("b"); self.cast(a="dock", b="dock"); self.night(a=900, b=1)
        for _ in range(2):
            ff.ledger_add(self.p, {"id": "a", "mode": "build", "outcome": "failed"})
        res = ff.pick(self.p)
        self.assertEqual(res["id"], "b")
        self.assertTrue(any("cooling off" in r for r in res["ranked"][1]["reasons"]))
        self.assertEqual(ff.pick(self.p, "a")["id"], "a")          # an explicit override still wins
        ff.ledger_add(self.p, {"id": "a", "mode": "build", "outcome": "shipped"})
        self.assertEqual(ff.pick(self.p)["id"], "a")               # a success clears it
        ff.ledger_add(self.p, {"id": "b", "mode": "build", "outcome": "failed"})
        ff.ledger_add(self.p, {"id": "b", "mode": "build", "outcome": "error"})  # infra errors do not count
        self.assertEqual(ff.pick(self.p)["id"], "a")

    def test_polish_mode_lowest_score_then_oldest_run(self):
        for c in ("a", "b", "c", "d"):
            self.comp(c)
        self.cast(a="dock", b="dock", c="dock", d="dock")
        self.asset("a", score=8, run="2026-11-01T01:40-0500")
        self.asset("b", score=7, run="2026-11-10T01:40-0500")
        self.asset("c", score=7, run="2026-11-05T01:40-0500")
        self.asset("d", score=9, run="2026-10-01T01:40-0500")
        res = ff.pick(self.p)
        self.assertEqual((res["id"], res["mode"]), ("c", "polish"))
        self.assertEqual([r["id"] for r in res["ranked"]], ["c", "b", "a", "d"])
        self.assertIn("polish the weakest", res["ranked"][0]["reasons"][0])

    def test_explain_lists_ranked_rows(self):
        self.comp("a"); self.cast(a="dock"); self.night(a=7)
        text = ff.explain(ff.pick(self.p))
        self.assertIn("factory-forge pick: a (build mode)", text)
        self.assertIn("7 events in night 2026-11-16", text)


class GitTree(Tree):
    def setUp(self):
        super().setUp()
        git = lambda *a: subprocess.run(["git", "-C", str(self.root), *a], check=True, capture_output=True)   # noqa: E731
        git("init", "-q"); git("config", "user.email", "t@t"); git("config", "user.name", "t")
        (self.root / "keep.txt").write_text("v1\n")
        self.comp("a"); self.cast(a="dock")
        git("add", "-A"); git("commit", "-q", "-m", "init")


class ScopeTest(GitTree):
    def snap(self):
        return ff.snapshot(self.p)

    def test_changes_inside_the_asset_dir_are_in_scope(self):
        before = self.snap()
        (self.p.asset_dir("a")).mkdir(parents=True)
        (self.p.asset_dir("a") / "build.py").write_text("print(1)\n")
        (self.p.asset_dir("a") / "sub").mkdir()
        (self.p.asset_dir("a") / "sub" / "x.json").write_text("{}")
        ok, detail, stray = ff.scope_check(self.p, "a", before)
        self.assertTrue(ok, detail)
        self.assertEqual(stray, [])

    def test_a_change_outside_fails_and_is_named(self):
        before = self.snap()
        (self.root / "keep.txt").write_text("v2\n")
        (self.p.sandbox / "src").mkdir(parents=True, exist_ok=True)
        (self.p.sandbox / "src" / "Props.tsx").write_text("x")
        ok, detail, stray = ff.scope_check(self.p, "a", before)
        self.assertFalse(ok)
        self.assertEqual(sorted(stray), ["keep.txt", "manual/sandbox/src/Props.tsx"])
        self.assertIn("OUTSIDE", detail)

    def test_a_sibling_asset_dir_is_outside(self):
        before = self.snap()
        (self.p.asset_dir("b")).mkdir(parents=True)
        (self.p.asset_dir("b") / "asset.json").write_text("{}")
        self.assertFalse(ff.scope_check(self.p, "a", before)[0])

    def test_dirt_that_was_already_there_is_not_blamed(self):
        (self.root / "keep.txt").write_text("someone else's edit\n")
        (self.root / "stray-new.txt").write_text("x")
        before = self.snap()
        (self.p.asset_dir("a")).mkdir(parents=True)
        (self.p.asset_dir("a") / "asset.json").write_text("{}")
        self.assertTrue(ff.scope_check(self.p, "a", before)[0])

    def test_editing_already_dirty_file_again_is_caught(self):
        (self.root / "keep.txt").write_text("someone else's edit\n")
        before = self.snap()
        (self.root / "keep.txt").write_text("the agent touched it\n")
        ok, _, stray = ff.scope_check(self.p, "a", before)
        self.assertFalse(ok)
        self.assertEqual(stray, ["keep.txt"])

    def test_deleting_a_tracked_file_is_caught(self):
        before = self.snap()
        (self.root / "keep.txt").unlink()
        self.assertEqual(ff.scope_check(self.p, "a", before)[2], ["keep.txt"])

    def test_no_baseline_means_the_tree_must_have_been_clean(self):
        (self.root / "keep.txt").write_text("dirty\n")
        self.assertFalse(ff.scope_check(self.p, "a", None)[0])

    def test_head_moving_is_reported(self):
        before = self.snap()
        (self.root / "keep.txt").write_text("v3\n")
        subprocess.run(["git", "-C", str(self.root), "commit", "-qam", "other"], check=True, capture_output=True)
        self.assertIn("HEAD moved", ff.scope_check(self.p, "a", before)[1])


class MonorepoScopeTest(Tree):
    """The platform lives inside a bigger repo with other writers: their edits during a run are not the agent's."""

    def setUp(self):
        super().setUp()
        top = self.root.parent
        git = lambda *a: subprocess.run(["git", "-C", str(top), *a], check=True, capture_output=True)   # noqa: E731
        git("init", "-q"); git("config", "user.email", "t@t"); git("config", "user.name", "t")
        (top / "_bmad-output").mkdir()
        (top / "_bmad-output" / "events.jsonl").write_text("1\n")
        (self.root / "keep.txt").write_text("v1\n")
        self.comp("a"); self.cast(a="dock")
        git("add", "-A"); git("commit", "-q", "-m", "init")

    def test_a_parallel_writer_outside_the_platform_is_ignored_but_reported(self):
        before = ff.snapshot(self.p)
        (self.root.parent / "_bmad-output" / "events.jsonl").write_text("1\n2\n")
        self.p.asset_dir("a").mkdir(parents=True)
        (self.p.asset_dir("a") / "asset.json").write_text("{}")
        ok, detail, stray = ff.scope_check(self.p, "a", before)
        self.assertTrue(ok, detail)
        self.assertEqual(stray, [])
        self.assertIn("_bmad-output/events.jsonl", detail)
        self.assertIn("ignored", detail)

    def test_a_change_inside_the_platform_but_outside_the_asset_still_fails(self):
        before = ff.snapshot(self.p)
        (self.root / "keep.txt").write_text("v2\n")
        ok, _, stray = ff.scope_check(self.p, "a", before)
        self.assertFalse(ok)
        self.assertEqual(stray, ["plat/keep.txt"])


class ManifestTest(unittest.TestCase):
    def run_checks(self, m, cid="a", cast=None):
        return {n: (o, d) for n, o, d in ff.check_manifest(m, cid, cast if cast is not None else {"station": "dock"})}

    def test_good_station_manifest_passes_everything(self):
        res = self.run_checks(manifest())
        self.assertTrue(all(o for o, _ in res.values()), {k: v for k, v in res.items() if not v[0]})

    def test_good_kiosk_manifest_passes(self):
        res = self.run_checks(manifest(placement="kiosk"), cast={"station": None, "near": "dock"})
        self.assertTrue(all(o for o, _ in res.values()), {k: v for k, v in res.items() if not v[0]})

    def test_placement_must_agree_with_the_cast(self):
        self.assertFalse(self.run_checks(manifest(placement="kiosk"))["placement-matches-cast"][0])
        self.assertFalse(self.run_checks(manifest(), cast={"station": None, "near": "dock"})["placement-matches-cast"][0])

    def test_a_kiosk_must_fit_its_slot(self):
        self.assertFalse(self.run_checks(manifest(placement="kiosk", footprint=[1.6, 1.2]), cast={"near": "dock"})["manifest-footprint"][0])

    def test_score_below_seven_does_not_ship(self):
        res = self.run_checks(manifest(score=6))
        self.assertFalse(res["ship-score"][0])
        self.assertTrue(res["manifest-forge"][0])

    def test_schema_violations(self):
        bad = manifest(id="other"); self.assertFalse(self.run_checks(bad)["manifest-id"][0])
        bad = manifest(); bad["clips"].pop("emit"); self.assertFalse(self.run_checks(bad)["manifest-clips"][0])
        bad = manifest(); bad["sockets"]["out"] = ""; self.assertFalse(self.run_checks(bad)["manifest-sockets"][0])
        bad = manifest(budget={"tris": 90000, "glbKB": 600}); self.assertFalse(self.run_checks(bad)["manifest-budget"][0])
        bad = manifest(handles=["telepathy"]); self.assertFalse(self.run_checks(bad)["manifest-handles"][0])
        bad = manifest(); bad["forge"]["rounds"] = 4; self.assertFalse(self.run_checks(bad)["manifest-forge"][0])
        bad = manifest(replaces=[]); self.assertFalse(self.run_checks(bad)["manifest-replaces"][0])
        bad = manifest(); bad["format"] = "nope"; self.assertFalse(self.run_checks(bad)["manifest-format"][0])


class GlbTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.glb = Path(self.tmp.name) / "model.glb"

    def tearDown(self):
        self.tmp.cleanup()

    def res(self, asset=None, **kw):
        make_glb(self.glb, **kw)
        return {n: (o, d) for n, o, d in glbcheck.check(self.glb, asset or manifest())}

    def test_a_good_glb_passes(self):
        res = self.res()
        self.assertTrue(all(o for o, _ in res.values()), {k: v for k, v in res.items() if not v[0]})
        self.assertIn("12 tris", res["glb-has-geometry"][1])

    def test_not_a_glb(self):
        self.glb.write_bytes(b"hello world, definitely not a glb")
        self.assertFalse(glbcheck.check(self.glb, manifest())[0][1])

    def test_clip_lengths_are_enforced(self):
        res = self.res(durations={"Idle": 1.0, "Accept": 1.0, "Work": 2.0, "Emit": 0.8})
        self.assertFalse(res["clip-idle"][0])
        res = self.res(durations={"Idle": 4.0, "Accept": 1.0, "Work": 9.0, "Emit": 0.8})
        self.assertFalse(res["clip-work"][0])

    def test_a_missing_clip_is_named(self):
        res = self.res(durations={"Idle": 4.0, "Accept": 1.0, "Work": 2.0})
        self.assertFalse(res["clip-emit"][0])
        self.assertIn("Emit", res["clip-emit"][1])

    def test_idle_must_loop_seamlessly(self):
        res = self.res(seam=0.2)
        self.assertFalse(res["idle-seamless"][0])

    def test_missing_socket(self):
        res = self.res(sockets=("socket_in", "socket_hold"))
        self.assertFalse(res["socket-out"][0])

    def test_footprint_and_height_and_kiosk_slot(self):
        res = self.res(size=(4.0, 1.5, 2.0))
        self.assertFalse(res["fits-footprint"][0])
        res = self.res(size=(2.0, 3.5, 2.0))
        self.assertFalse(res["fits-height"][0])
        k = manifest(placement="kiosk", footprint=[1.6, 1.2])
        res = self.res(asset=k, size=(1.6, 1.5, 1.2))
        self.assertFalse(res["kiosk-slot"][0])

    def test_triangle_budget(self):
        res = self.res(asset=manifest(budget={"tris": 100, "glbKB": 600}), tris_x=20)
        self.assertFalse(res["glb-tris"][0])

    def test_size_budget(self):
        res = self.res(asset=manifest(budget={"tris": 15000, "glbKB": 600}), tris_x=1)
        self.assertTrue(res["glb-size"][0])


class LedgerTest(Tree):
    def test_add_and_read(self):
        self.assertEqual(ff.ledger_read(self.p)["runs"], [])
        row = ff.ledger_add(self.p, {"id": "a", "mode": "build", "outcome": "shipped", "score": 8.0, "commit": "abc1234",
                                     "tokens": {"total": 5}, "showcase_url": "https://s3.delo.sh/x", "duration_s": 61.2})
        self.assertTrue(row["run"])
        d = json.loads(self.p.ledger.read_text())
        self.assertEqual(d["format"], "33god.factory-forge-ledger")
        self.assertEqual(d["runs"][0]["commit"], "abc1234")
        ff.ledger_add(self.p, {"id": "b", "mode": "build", "outcome": "failed", "failed": ["tsc"], "note": "n"})
        d = ff.ledger_read(self.p)
        self.assertEqual([r["id"] for r in d["runs"]], ["a", "b"])
        self.assertEqual(d["runs"][1]["failed"], ["tsc"])

    def test_cli_round_trip(self):
        with contextlib.redirect_stdout(io.StringIO()):
            rc = ff.main(["--root", str(self.root), "ledger", "add", "--id", "a", "--mode", "build", "--outcome", "shipped", "--score", "8", "--tokens", '{"total": 3}', "--duration-s", "5"])
        self.assertEqual(rc, 0)
        self.assertEqual(ff.ledger_read(self.p)["runs"][0]["tokens"], {"total": 3})


class UsageTest(unittest.TestCase):
    def test_claude_json_result(self):
        u = ff.parse_usage(json.dumps({"type": "result", "subtype": "success", "is_error": False, "num_turns": 40, "total_cost_usd": 3.2,
                                       "usage": {"input_tokens": 1000, "output_tokens": 500, "cache_read_input_tokens": 9000, "cache_creation_input_tokens": 200}}))
        self.assertEqual((u["input"], u["output"], u["total"], u["cache_read"], u["subtype"]), (1000, 500, 1500, 9000, "success"))

    def test_event_list_and_garbage(self):
        u = ff.parse_usage(json.dumps([{"type": "system"}, {"type": "result", "subtype": "error_max_turns", "usage": {"input_tokens": 7, "output_tokens": 3}}]))
        self.assertEqual((u["total"], u["subtype"]), (10, "error_max_turns"))
        self.assertEqual(ff.parse_usage("not json")["total"], 0)


class PromptTest(Tree):
    def test_build_prompt_has_the_record_neighbours_and_station(self):
        self.comp("a", relations=["b"], factory={"station": "dock"}, summary="alpha summary")
        self.comp("b", summary="bravo summary"); self.comp("c", relations=["a"], summary="charlie summary")
        self.cast(a="dock", b="belt", c=None)
        text = ff.render_prompt(self.p, "a")
        self.assertIn("# brief", text)
        self.assertIn("# This run: build `a`", text)
        self.assertIn("id: a", text)                                   # the full registry record
        self.assertIn("bravo summary", text); self.assertIn("charlie summary", text)
        self.assertIn("kiosk near dock", text)                         # c's place, from the cast
        self.assertIn("it IS station `dock`", text)
        self.assertIn(str(self.p.forge / "CONTRACT.md"), text)
        self.assertIn("No finished asset exists yet", text)

    def test_polish_prompt_carries_the_previous_notes_score_and_exemplar(self):
        self.comp("a", factory={"station": "dock"}); self.comp("b"); self.cast(a="dock", b="belt")
        self.asset("a", score=7); (self.p.asset_dir("a") / "NOTES.md").write_text("PREVIOUS NOTES TEXT\n")
        self.asset("b", score=9)
        ff.ledger_add(self.p, {"id": "a", "mode": "build", "outcome": "shipped", "score": 7})
        text = ff.render_prompt(self.p, "a")
        self.assertIn("# This run: polish `a`", text)
        self.assertIn("PREVIOUS NOTES TEXT", text)
        self.assertIn('"score": 7', text)
        self.assertIn("The best existing asset is `b`", text)
        self.assertIn('"outcome": "shipped"', text)

    def test_unknown_id_is_refused(self):
        with self.assertRaises(SystemExit):
            ff.render_prompt(self.p, "ghost")


class ShowcaseTest(Tree):
    def test_page_links_the_live_floor_and_embeds_frames(self):
        self.comp("a"); self.cast(a="dock"); self.asset("a")
        (self.p.asset_dir("a") / "NOTES.md").write_text("# Dock\n\nIt <stamps> parcels.\n\n- Idle\n- Work\n")
        shots = Path(self.tmp.name) / "shots"; shots.mkdir()
        for n in ("work-1", "emit-1", "accept-1", "turn-000", "idle-1", "visit-0", "situ", "contact-sheet"):
            (shots / f"{n}.png").write_bytes(b"\x89PNG")
        out = Path(self.tmp.name) / "show"
        page = ff.render_showcase(self.p, "a", shots, out, {"total": 12345}, commit="abcdef1234").read_text()
        self.assertIn("https://manual.delo.sh/sandbox/?at=a", page)
        self.assertIn('src="turn-000.png"', page)
        self.assertLess(page.index('src="idle-1.png"'), page.index('src="accept-1.png"'))   # clips in cycle order, not alphabetical
        self.assertLess(page.index('src="work-1.png"'), page.index('src="emit-1.png"'))
        self.assertIn("12,345 tokens", page)
        self.assertIn("It &lt;stamps&gt; parcels.", page)               # the excerpt is escaped
        self.assertTrue((out / "idle-1.png").exists())


if __name__ == "__main__":
    unittest.main()
