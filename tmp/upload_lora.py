#!/usr/bin/env python3
"""Upload the LoRA checkpoint to a Modal Volume."""
import modal
import os

LOCAL_LORA = "/home/delorenj/code/hot/output/delo_flux_captioned_20260505/delo_flux_captioned_20260505_000001750.safetensors"
VOLUME_NAME = "flux-lora"
REMOTE_PATH = "delo_flux_latest.safetensors"

def main():
    vol = modal.Volume.from_name(VOLUME_NAME, create_if_missing=True)
    if not os.path.exists(LOCAL_LORA):
        print(f"ERROR: {LOCAL_LORA} not found")
        return
    vol.put_file(LOCAL_LORA, REMOTE_PATH)
    print(f"Uploaded: {LOCAL_LORA} -> {VOLUME_NAME}:{REMOTE_PATH}")
    files = vol.listdir("/")
    print(f"Volume contents: {files}")

if __name__ == "__main__":
    main()
