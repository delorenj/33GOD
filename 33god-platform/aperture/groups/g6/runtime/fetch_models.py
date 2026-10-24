"""Network preseed/first-boot fetch; every artifact must match models.lock.json."""
import hashlib
import json
import os
from pathlib import Path
import urllib.request

ROOT = Path(os.environ.get("GOD_MODEL_DIR", "/models"))
LOCK = json.loads((Path(__file__).resolve().parents[1] / "models.lock.json").read_text())

def fetch():
    ROOT.mkdir(parents=True, exist_ok=True)
    for name, digest in LOCK["sha256"].items():
        dest = ROOT / name
        if dest.exists() and hashlib.sha256(dest.read_bytes()).hexdigest() == digest:
            print("model cached", name, flush=True)
            continue
        if os.environ.get("GOD_MODEL_OFFLINE", "0") == "1":
            raise RuntimeError("offline model absent or checksum mismatch: " + name)
        url = ("https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/silero_vad.onnx"
               if name == "silero_vad.onnx" else
               f'https://huggingface.co/{LOCK["repository"]}/resolve/{LOCK["revision"]}/{name}')
        print("WARNING: first boot downloading verified model:", name, flush=True)
        temp = dest.with_suffix(dest.suffix + ".partial")
        try:
            with urllib.request.urlopen(url, timeout=120) as response, temp.open("wb") as out:
                while chunk := response.read(1024 * 1024):
                    out.write(chunk)
            if hashlib.sha256(temp.read_bytes()).hexdigest() != digest:
                raise RuntimeError("model checksum mismatch: " + name)
            temp.replace(dest)
        finally:
            temp.unlink(missing_ok=True)

if __name__ == "__main__":
    fetch()
