"""The hub-skill standard, structurally, for every skill 33god-platform owns (scripts/platform.py validate_skills)."""

import importlib.util
import tempfile
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "scripts" / "platform.py"
spec = importlib.util.spec_from_file_location("platform_skills", MODULE)
platform = importlib.util.module_from_spec(spec)
spec.loader.exec_module(platform)


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class ValidateSkillsTests(unittest.TestCase):
    def hub(self, root: Path) -> Path:
        hub = root / "hub"
        write(hub / "SKILL.md", "[a](references/a.md) [f](subskills/feat/SUBSKILL.md) `other-skill`\n")
        write(hub / "references/a.md", "# a\n")
        write(hub / "subskills/feat/SUBSKILL.md", "[r](references/r.md) [up](../../references/a.md)\n")
        write(hub / "subskills/feat/references/r.md", "[sib](health.md#x)\n")
        write(hub / "subskills/feat/references/health.md", "# health\n")
        return hub

    def test_a_well_formed_hub_with_a_sub_skill_passes(self):
        with tempfile.TemporaryDirectory() as temp:
            self.hub(Path(temp))
            self.assertEqual(platform.validate_skills(Path(temp)), [])

    def test_an_orphan_reference_or_sub_skill_file_is_an_error(self):
        with tempfile.TemporaryDirectory() as temp:
            hub = self.hub(Path(temp))
            write(hub / "subskills/feat/references/forgotten.md", "# nobody links me\n")
            errors = platform.validate_skills(Path(temp))
            self.assertEqual(len(errors), 1)
            self.assertIn("forgotten.md: orphan", errors[0])

    def test_a_link_out_of_the_skill_or_to_nothing_is_an_error(self):
        with tempfile.TemporaryDirectory() as temp:
            hub = self.hub(Path(temp))
            write(hub / "references/a.md", "[sibling](../../other/SKILL.md) [gone](missing.md) [web](https://x.y/z)\n")
            errors = platform.validate_skills(Path(temp))
            self.assertTrue(any("leaves hub/" in e for e in errors), errors)
            self.assertTrue(any("'missing.md' does not resolve" in e for e in errors), errors)
            self.assertEqual(len(errors), 2, errors)

    def test_a_nested_skill_md_is_an_error(self):
        with tempfile.TemporaryDirectory() as temp:
            hub = self.hub(Path(temp))
            write(hub / "subskills/feat/SKILL.md", "# would be auto-listed\n")
            errors = platform.validate_skills(Path(temp))
            self.assertTrue(any("nested SKILL.md" in e for e in errors), errors)

    def test_the_real_skills_tree_is_clean(self):
        self.assertEqual(platform.validate_skills(), [])


if __name__ == "__main__":
    unittest.main()
