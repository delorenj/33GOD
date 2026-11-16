"""The assembler's output validates against schema/waybill.v1.schema.json (minimal built-in validator)."""
from __future__ import annotations

import copy
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_assemble import build  # noqa: E402

SCHEMA = json.loads((ROOT / "schema" / "waybill.v1.schema.json").read_text())

_TYPES = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "null": lambda v: v is None,
}
_SUPPORTED = {"$schema", "$id", "$defs", "$ref", "title", "description", "type", "enum", "const", "required",
              "properties", "additionalProperties", "items", "pattern", "format"}


def validate(inst, schema: dict, root: dict, path: str = "$") -> list[str]:
    """JSON Schema 2020-12 subset: $ref (local), type, enum, const, required, properties,
    additionalProperties, items, pattern. Unknown keywords are an error so the schema stays checkable."""
    errs: list[str] = []
    unknown = set(schema) - _SUPPORTED
    if unknown:
        return [f"{path}: schema uses unsupported keywords {sorted(unknown)}"]
    if "$ref" in schema:
        ref = schema["$ref"]
        assert ref.startswith("#/"), ref
        target = root
        for part in ref[2:].split("/"):
            target = target[part]
        return validate(inst, target, root, path)
    if "type" in schema:
        types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(_TYPES[t](inst) for t in types):
            return [f"{path}: expected {types}, got {type(inst).__name__} {str(inst)[:60]!r}"]
    if "const" in schema and inst != schema["const"]:
        errs.append(f"{path}: expected const {schema['const']!r}, got {inst!r}")
    if "enum" in schema and inst not in schema["enum"]:
        errs.append(f"{path}: {inst!r} not in {schema['enum']}")
    if "pattern" in schema and isinstance(inst, str) and not re.search(schema["pattern"], inst):
        errs.append(f"{path}: {inst!r} does not match {schema['pattern']}")
    if isinstance(inst, dict):
        for k in schema.get("required", []):
            if k not in inst:
                errs.append(f"{path}: missing required {k!r}")
        props = schema.get("properties", {})
        for k, v in inst.items():
            if k in props:
                errs += validate(v, props[k], root, f"{path}.{k}")
            else:
                ap = schema.get("additionalProperties", True)
                if ap is False:
                    errs.append(f"{path}: unexpected property {k!r}")
                elif isinstance(ap, dict):
                    errs += validate(v, ap, root, f"{path}.{k}")
    if isinstance(inst, list) and "items" in schema:
        for i, v in enumerate(inst):
            errs += validate(v, schema["items"], root, f"{path}[{i}]")
    return errs


class TestSchema(unittest.TestCase):
    def test_schema_is_2020_12(self) -> None:
        self.assertEqual(SCHEMA["$schema"], "https://json-schema.org/draft/2020-12/schema")
        self.assertTrue(SCHEMA["additionalProperties"])
        for name, d in SCHEMA["$defs"].items():
            self.assertTrue(d.get("additionalProperties", True), name)

    def test_full_waybill_validates(self) -> None:
        errs = validate(build("full"), SCHEMA, SCHEMA)
        self.assertEqual(errs, [], "\n".join(errs[:20]))

    def test_public_waybill_validates(self) -> None:
        errs = validate(build("public"), SCHEMA, SCHEMA)
        self.assertEqual(errs, [], "\n".join(errs[:20]))

    def test_validator_catches_breakage(self) -> None:
        wb = build("full")
        bad = copy.deepcopy(wb)
        del bad["spans"][0]["phase"]
        bad["spans"][1]["status"] = "exploded"
        bad["events"][0]["consumers"].append({"name": "x"})
        bad["version"] = 2
        errs = validate(bad, SCHEMA, SCHEMA)
        joined = "\n".join(errs)
        self.assertIn("missing required 'phase'", joined)
        self.assertIn("'exploded' not in", joined)
        self.assertIn("missing required 'kind'", joined)
        self.assertIn("expected const 1", joined)

    def test_spec_enums_match_assembler(self) -> None:
        from waybill import assemble as A
        d = SCHEMA["$defs"]
        self.assertEqual(tuple(d["Span"]["properties"]["phase"]["enum"]), A.PHASES)
        self.assertEqual(tuple(d["Span"]["properties"]["status"]["enum"]), A.STATUSES)
        self.assertEqual(tuple(d["Link"]["properties"]["kind"]["enum"]), A.LINK_KINDS)
        self.assertEqual(tuple(d["Consumer"]["properties"]["outcome"]["enum"]), A.OUTCOMES)
        self.assertEqual(tuple(d["Consumer"]["properties"]["kind"]["enum"]), A.CONSUMER_KINDS)
        self.assertEqual(tuple(d["Source"]["properties"]["status"]["enum"]), A.SOURCE_STATUSES)
        self.assertEqual(tuple(d["Gap"]["properties"]["severity"]["enum"]), A.SEVERITIES)


if __name__ == "__main__":
    unittest.main()
