"""
Trim a video without re-encoding (fast cut using -c copy).
Keeps video, audio, and burned-in subtitles exactly as they are.

Usage:
    python trim_video.py <input_video> <end_time> [--start <start_time>] [--output <path>]

Examples:
    python trim_video.py video.mp4 02:23
    python trim_video.py video.mp4 02:23 --start 00:10
    python trim_video.py video.mp4 02:23 -o trimmed.mp4
"""
import subprocess
import sys
from pathlib import Path


def trim_video(input_path, end_time, start_time="00:00", output_path=None):
    input_path = Path(input_path)
    if output_path is None:
        output_path = input_path.parent / f"{input_path.stem}_trimmed{input_path.suffix}"
    else:
        output_path = Path(output_path)

    print(f"   Trimming: {input_path.name}")
    print(f"   Range:    {start_time} -> {end_time}")

    subprocess.run([
        "ffmpeg", "-y",
        "-ss", start_time,
        "-to", end_time,
        "-i", str(input_path),
        "-c", "copy",
        "-avoid_negative_ts", "make_zero",
        str(output_path)
    ], check=True)

    print(f"   [OK] Output: {output_path}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Trim video without re-encoding")
    parser.add_argument("input", help="Input video file")
    parser.add_argument("end", help="End time (e.g. 02:23 or 00:02:23)")
    parser.add_argument("--start", "-s", default="00:00", help="Start time (default: 00:00)")
    parser.add_argument("--output", "-o", help="Output path")
    args = parser.parse_args()

    trim_video(args.input, args.end, args.start, args.output)
