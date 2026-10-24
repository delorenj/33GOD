"""Bundle-specific invariants and real CPU adapter behavior (no inference mocks)."""
import hashlib
import importlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
import wave
from fastapi.testclient import TestClient
from runtime.espeak_engine import app
from app.engine_contract import EngineHealth, EngineSynthesizeResponse

class CpuEngineTest(unittest.TestCase):
    def test_contract_and_speech(self):
        client = TestClient(app)
        health = EngineHealth.model_validate(client.get("/healthz").json())
        self.assertTrue(health.ready)
        result = EngineSynthesizeResponse.model_validate(client.post("/v1/synthesize", json={"text": "Hello voice."}).json())
        import base64
        with wave.open(io.BytesIO(base64.b64decode(result.wav_b64))) as wav:
            self.assertGreater(wav.getnframes(), 1000)
    def test_empty_text_rejected(self):
        self.assertEqual(TestClient(app).post("/v1/synthesize", json={"text": ""}).status_code, 422)

class IntakeTest(unittest.TestCase):
    def setUp(self):
        import runtime.intake as intake
        self.intake = intake
        self.temp = tempfile.TemporaryDirectory()
        self.old = intake.ROOT
        intake.ROOT = Path(self.temp.name)
        for name in ("input", "inbox", "receipts"):
            (intake.ROOT / name).mkdir()
    def tearDown(self):
        self.intake.ROOT = self.old
        self.temp.cleanup()
    def test_pickup_hash_receipt_and_idempotence(self):
        raw = Path("/app/smoke/speech.wav").read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        for name in ("first.wav", "again.wav"):
            path = self.intake.ROOT / "inbox" / name
            path.write_bytes(raw)
            self.intake.publish(path)
            self.assertFalse(path.exists())
        self.assertEqual((self.intake.ROOT / "input" / (digest + ".wav")).read_bytes(), raw)
        self.assertEqual(len(list((self.intake.ROOT / "receipts").glob("*.json"))), 1)
    def test_invalid_wav_rejected(self):
        path = self.intake.ROOT / "inbox" / "bad.wav"
        path.write_bytes(b"not audio")
        with self.assertRaises((wave.Error, EOFError)):
            self.intake.publish(path)
        self.assertTrue(path.exists())
    def test_symlink_rejected(self):
        path = self.intake.ROOT / "inbox" / "link.wav"
        path.symlink_to("/app/smoke/speech.wav")
        with self.assertRaises(ValueError):
            self.intake.publish(path)
    def test_no_credentials_is_inert(self):
        from unittest.mock import patch
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(self.intake.configured())

if __name__ == "__main__":
    unittest.main(verbosity=2)
