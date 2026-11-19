import csv
import hashlib
import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import bmb_help_registration as reg

REPO = Path(__file__).resolve().parents[1]
LIVE = Path(subprocess.check_output(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"], cwd=REPO, text=True).strip()).parent
SKILLS = LIVE / ".agents/skills"


def rows(text):
    return list(csv.reader(io.StringIO(text)))


class BmbRegistrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in reg.TARGETS:
            dest = self.root / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            source = (LIVE / name).read_bytes()
            # Simulate an old installer rerun reintroducing a stale conversion entry.
            obsolete = b'BMad Builder,bmad-workflow-builder,Convert a Skill,CW,Unsupported,convert-process,--convert,anytime,,,false,,\n'
            dest.write_bytes(source + obsolete)

    def test_overlay_routes_and_action_boundaries(self):
        overlay = reg.OVERLAY.read_text()
        reg.validate(SKILLS, overlay)
        self.assertEqual([r[3] for r in rows(overlay)[2:]], list(reg.ROUTES))
        for row in rows(overlay)[2:]:
            code = row[3]
            self.assertEqual(row[6], reg.ARGS[code], code)
            self.assertEqual((row[1], row[5]), reg.ROUTES[code][:2], code)
        self.assertNotIn("-H", rows(overlay)[-1][6])
        self.assertIn("If `--headless` or `-H` is passed, route to CM",
                      (SKILLS / "bmad-module-builder/SKILL.md").read_text())
        self.assertNotIn("--convert", overlay)
        self.assertNotIn("convert-process", overlay)
        self.assertTrue((SKILLS / "bmad-help/SKILL.md").is_file())
        self.assertIn("_bmad/_config/bmad-help.csv", (SKILLS / "bmad-help/SKILL.md").read_text())

    def test_scoped_apply_rerun_and_foreign_bytes(self):
        before = {name: (self.root / name).read_bytes() for name in reg.TARGETS}
        self.assertEqual(reg.run(self.root, True, SKILLS), 0)
        first = {name: (self.root / name).read_bytes() for name in reg.TARGETS}
        for name in reg.TARGETS:
            original = before[name].decode()
            revised = first[name].decode()
            foreign = lambda text: [line for line in text.splitlines(keepends=True)
                                    if line.startswith("module,") or rows(line)[0][0] != reg.MODULE]
            self.assertEqual(foreign(original), foreign(revised))
            registered = [r for r in rows(revised)[1:] if r[0] == reg.MODULE]
            self.assertEqual(registered[0][1], "_meta")
            self.assertEqual([r[3] for r in registered[1:]], list(reg.ROUTES))
            self.assertEqual(len({(r[1], r[5]) for r in registered[1:]}), 8)
            self.assertNotIn("convert-process", revised)
        self.assertEqual(reg.run(self.root, False, SKILLS), 0)
        self.assertEqual(reg.run(self.root, True, SKILLS), 0)
        self.assertEqual(first, {name: (self.root / name).read_bytes() for name in reg.TARGETS})
        self.assertNotEqual(before, first)

    def test_unterminated_foreign_eof_survives_apply_and_check(self):
        header = reg.OVERLAY.read_text().splitlines()[0]
        for ending in ("\n", "\r\n"):
            with self.subTest(ending=repr(ending)):
                foreign = "Other,foreign,Unrelated,ZZ,Keep,foreign-action,,anytime,,,false,,last-row-no-newline"
                original = (header + ending + foreign).encode()
                for name in reg.TARGETS:
                    (self.root / name).write_bytes(original)
                self.assertEqual(reg.run(self.root, True, SKILLS), 0)
                for name in reg.TARGETS:
                    result = (self.root / name).read_bytes()
                    self.assertTrue(result.endswith(foreign.encode()))
                    self.assertEqual(rows(result.decode())[-1][0], "Other")
                    self.assertEqual(len(rows(result.decode())), len(reg.ROUTES) + 3)
                    self.assertEqual([line for line in result.decode().splitlines(keepends=True)
                                      if line.startswith("Other,")], [foreign])
                self.assertEqual(reg.run(self.root, False, SKILLS), 0)
                snapshot = {(self.root / name).read_bytes() for name in reg.TARGETS}
                self.assertEqual(reg.run(self.root, True, SKILLS), 0)
                self.assertEqual(snapshot, {(self.root / name).read_bytes() for name in reg.TARGETS})

    def test_refuse_wrong_header_and_missing_reference(self):
        first = self.root / reg.TARGETS[0]
        before = first.read_bytes()
        path = self.root / reg.TARGETS[1]
        path.write_text("bad,header\n")
        with self.assertRaisesRegex(AssertionError, "schema"):
            reg.run(self.root, True, SKILLS)
        self.assertEqual(path.read_text(), "bad,header\n")
        self.assertEqual(first.read_bytes(), before)
        with self.assertRaises((AssertionError, FileNotFoundError)):
            reg.validate(self.root, reg.OVERLAY.read_text())

    def test_unsupported_duplicate_action_rejected(self):
        overlay = reg.OVERLAY.read_text()
        with self.assertRaisesRegex(AssertionError, "exactly eight"):
            reg.validate(SKILLS, overlay + rows(overlay)[-1][0] + "\n")


if __name__ == "__main__":
    unittest.main()
