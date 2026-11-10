"""verify-hooks-event-sink.py resolves Candystore per the 8683 port contract."""

import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "verify-hooks-event-sink.py"
spec = importlib.util.spec_from_file_location("verify_hooks_event_sink", SCRIPT)
sink = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sink)


class CandystoreDefaultTest(unittest.TestCase):
    def test_default_is_the_contract(self):
        self.assertEqual(sink.CANDYSTORE_DEFAULT_URL, "http://127.0.0.1:8683")
        self.assertEqual(sink.candystore_default({}), "http://127.0.0.1:8683")

    def test_candystore_url_is_honored(self):
        self.assertEqual(sink.candystore_default({"CANDYSTORE_URL": "http://127.0.0.1:3603/"}), "http://127.0.0.1:3603")

    def test_blank_falls_back(self):
        self.assertEqual(sink.candystore_default({"CANDYSTORE_URL": "  "}), sink.CANDYSTORE_DEFAULT_URL)


if __name__ == "__main__":
    unittest.main()
