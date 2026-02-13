#!/usr/bin/env python3
"""
Clone a voice from audio samples using Qwen3-TTS.
Usage: uv run clone_voice.py --reference <audio.wav> --text "Hello world" --output output.wav
"""
import argparse
import sys
import torch

def main():
    parser = argparse.ArgumentParser(description="Clone a voice using Qwen3-TTS")
    parser.add_argument("--reference", "-r", required=True, help="Reference audio file (WAV, 3+ seconds)")
    parser.add_argument("--text", "-t", required=True, help="Text to synthesize")
    parser.add_argument("--output", "-o", default="output.wav", help="Output WAV file")
    parser.add_argument("--model", "-m", default="Qwen/Qwen3-TTS-12Hz-1.7B-Base", help="Model name")
    parser.add_argument("--tokenizer", default="Qwen/Qwen3-TTS-Tokenizer-12Hz", help="Tokenizer name")
    args = parser.parse_args()

    print(f"Loading model: {args.model}")
    print(f"Device: {'cuda' if torch.cuda.is_available() else 'cpu'}")

    from qwen_tts import Qwen3TTSModel
    model = Qwen3TTSModel(args.model, args.tokenizer)

    print(f"Cloning voice from: {args.reference}")
    print(f"Text: {args.text}")

    # Voice clone: provide reference audio
    wav = model.synthesize(
        text=args.text,
        ref_audio=args.reference,
    )

    # Save output
    import soundfile as sf
    sf.write(args.output, wav, 24000)
    print(f"Saved to: {args.output}")

if __name__ == "__main__":
    main()
