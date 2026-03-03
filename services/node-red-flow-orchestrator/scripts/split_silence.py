#!/usr/bin/env python3
"""
Detect silence gaps in audio and split into activity-only chunks.

Uses ffmpeg silencedetect filter to find long silence regions, then extracts
each activity segment as a separate MP3.

Usage:
  split_silence.py <input_file> [--output-dir DIR] [--watch-dir DIR]
                   [--min-silence SEC] [--threshold DB] [--min-activity SEC]
                   [--dry-run]

Output JSON array of produced files:
  [{"file": "/path/to/chunk_001.mp3", "start": 0.0, "end": 1234.5, "duration": 1234.5}, ...]
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


def detect_silence(
    file_path: str,
    min_silence: float = 120.0,
    threshold: float = -40.0,
) -> list[dict]:
    """Run ffmpeg silencedetect and parse silence intervals."""
    cmd = [
        "ffmpeg",
        "-i", file_path,
        "-af", f"silencedetect=noise={threshold}dB:d={min_silence}",
        "-f", "null", "-",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    stderr = result.stderr

    # Parse silence_start / silence_end pairs from ffmpeg stderr
    starts = re.findall(r"silence_start:\s*([\d.]+)", stderr)
    ends = re.findall(r"silence_end:\s*([\d.]+)", stderr)

    silences = []
    for i, start in enumerate(starts):
        end = ends[i] if i < len(ends) else None
        silences.append({
            "start": float(start),
            "end": float(end) if end else None,
        })
    return silences


def get_duration(file_path: str) -> float:
    """Get total duration via ffprobe."""
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_format", file_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(result.stdout)
    return float(data["format"]["duration"])


def invert_silences(
    silences: list[dict],
    total_duration: float,
) -> list[dict]:
    """Convert silence intervals into activity intervals."""
    activities = []
    cursor = 0.0

    for s in silences:
        if s["start"] > cursor:
            activities.append({"start": cursor, "end": s["start"]})
        cursor = s["end"] if s["end"] else total_duration

    # Trailing activity after last silence
    if cursor < total_duration:
        activities.append({"start": cursor, "end": total_duration})

    return activities


def extract_chunk(
    input_file: str,
    output_file: str,
    start: float,
    duration: float,
) -> None:
    """Extract a time range from the input file as MP3."""
    cmd = [
        "ffmpeg",
        "-ss", str(start),
        "-i", input_file,
        "-t", str(duration),
        "-acodec", "libmp3lame",
        "-q:a", "2",
        "-y",
        output_file,
    ]
    subprocess.run(cmd, capture_output=True, text=True, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Split audio on silence gaps")
    parser.add_argument("input_file", help="Path to audio file")
    parser.add_argument("--output-dir", help="Directory for output chunks (default: same as input)")
    parser.add_argument("--watch-dir", help="Copy chunks here to trigger ingest pipeline")
    parser.add_argument("--min-silence", type=float, default=120.0,
                        help="Minimum silence duration in seconds to split on (default: 120)")
    parser.add_argument("--threshold", type=float, default=-40.0,
                        help="Silence threshold in dB (default: -40)")
    parser.add_argument("--min-activity", type=float, default=60.0,
                        help="Discard activity chunks shorter than this (seconds, default: 60)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Detect and report chunks without extracting")
    args = parser.parse_args()

    input_path = Path(args.input_file).expanduser().resolve()
    if not input_path.exists():
        print(json.dumps({"error": f"File not found: {input_path}"}))
        return 1

    output_dir = Path(args.output_dir).resolve() if args.output_dir else input_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: detect silence regions
    print(f"Detecting silence (threshold={args.threshold}dB, min_duration={args.min_silence}s)...",
          file=sys.stderr)
    total_duration = get_duration(str(input_path))
    silences = detect_silence(str(input_path), args.min_silence, args.threshold)
    print(f"Found {len(silences)} silence region(s) in {total_duration:.0f}s total", file=sys.stderr)

    # Step 2: invert to activity regions
    activities = invert_silences(silences, total_duration)

    # Filter out short activity regions
    activities = [a for a in activities if (a["end"] - a["start"]) >= args.min_activity]
    print(f"Found {len(activities)} activity chunk(s) after filtering (min={args.min_activity}s)",
          file=sys.stderr)

    if not activities:
        print(json.dumps([]))
        return 0

    # Report what we found
    for i, a in enumerate(activities):
        dur = a["end"] - a["start"]
        print(f"  Chunk {i+1}: {a['start']:.1f}s - {a['end']:.1f}s ({dur/60:.1f} min)",
              file=sys.stderr)

    if args.dry_run:
        results = []
        for i, a in enumerate(activities):
            dur = a["end"] - a["start"]
            results.append({
                "chunk": i + 1,
                "start": a["start"],
                "end": a["end"],
                "duration": dur,
            })
        print(json.dumps(results, indent=2))
        return 0

    # Step 3: extract each chunk
    results = []
    for i, a in enumerate(activities):
        dur = a["end"] - a["start"]
        chunk_name = f"{input_path.stem}_chunk_{i+1:03d}.mp3"
        chunk_path = output_dir / chunk_name

        print(f"Extracting chunk {i+1}/{len(activities)}: {chunk_name} ({dur/60:.1f} min)...",
              file=sys.stderr)
        extract_chunk(str(input_path), str(chunk_path), a["start"], dur)

        result = {
            "file": str(chunk_path),
            "start": a["start"],
            "end": a["end"],
            "duration": dur,
        }
        results.append(result)

        # Copy to watch dir if specified (triggers ingest pipeline)
        if args.watch_dir:
            import shutil
            watch_path = Path(args.watch_dir).resolve()
            watch_path.mkdir(parents=True, exist_ok=True)
            dest = watch_path / chunk_name
            shutil.copy2(str(chunk_path), str(dest))
            result["queued"] = str(dest)
            print(f"  Queued for transcription: {dest}", file=sys.stderr)

    print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
