"""Run the upstream server with its persistent token and model-free HTTP recognizer."""
from pathlib import Path
from vinyl import server, vad
vad.DEFAULT_VAD_MODEL = Path("/models/silero_vad.onnx")
server.make_vad = lambda: vad.make_vad(Path("/models/silero_vad.onnx"))
raise SystemExit(server.serve())
