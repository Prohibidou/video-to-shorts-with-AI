"""
Remove dead times (silences) from an ALREADY RENDERED video.
Uses FFmpeg silencedetect to find pauses, then builds a single
filter_complex that trims+concats all kept segments in one pass.

Re-encodes with -c:v libx264 -crf 18 -preset veryfast for frame-accurate cuts.
This is fast because veryfast preset is used and the video is already short (~3 min).

Usage:
    python remove_silence.py <input_video> [--output <path>] [--threshold -30] [--min-silence 0.4]
"""
import subprocess
import re
import sys
from pathlib import Path


def get_silence_intervals(video_path, noise_db=-30, min_duration=0.4):
    """Detect silence intervals using FFmpeg silencedetect filter."""
    cmd = [
        "ffmpeg", "-i", str(video_path),
        "-af", f"silencedetect=noise={noise_db}dB:d={min_duration}",
        "-f", "null", "-"
    ]
    result = subprocess.run(cmd, stderr=subprocess.PIPE, text=True, encoding="utf-8")

    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", result.stderr)]
    ends   = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", result.stderr)]
    return list(zip(starts, ends))


def get_duration(video_path):
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(video_path)
    ]
    return float(subprocess.run(cmd, stdout=subprocess.PIPE, text=True).stdout.strip())


def remove_silence(input_path, output_path, noise_db=-30, min_duration=0.4, pad=0.05):
    """
    Cut silences from a video using a single filter_complex pass.
    Uses trim/atrim to extract kept segments and concat to join them.
    """
    input_path = Path(input_path)
    output_path = Path(output_path)

    print(f"\n{'='*60}")
    print("REMOVE DEAD TIMES (Jump Cuts)")
    print(f"{'='*60}")
    print(f"   Input:     {input_path.name}")
    print(f"   Threshold: {noise_db}dB")
    print(f"   Min Pause: {min_duration}s")

    silences = get_silence_intervals(input_path, noise_db, min_duration)
    duration = get_duration(input_path)

    if not silences:
        print("   [INFO] No significant silence detected. Nothing to cut.")
        subprocess.run(["ffmpeg", "-y", "-i", str(input_path), "-c", "copy", str(output_path)], check=True)
        return

    # Build keep intervals
    keeps = []
    pos = 0.0
    for s_start, s_end in silences:
        keep_end = max(pos, s_start + pad)
        if keep_end > pos + 0.05:  # skip tiny segments
            keeps.append((pos, keep_end))
        pos = max(pos, s_end - pad)

    if pos < duration:
        keeps.append((pos, duration))

    total_silence = sum(e - s for s, e in silences)
    print(f"   [INFO] Found {len(silences)} silences ({total_silence:.1f}s total)")
    print(f"   [INFO] Keeping {len(keeps)} segments...")

    # Build filter_complex with trim+concat
    filters = []
    concat_inputs = []
    for i, (start, end) in enumerate(keeps):
        filters.append(f"[0:v]trim=start={start:.3f}:end={end:.3f},setpts=PTS-STARTPTS[v{i}];")
        filters.append(f"[0:a]atrim=start={start:.3f}:end={end:.3f},asetpts=PTS-STARTPTS[a{i}];")
        concat_inputs.append(f"[v{i}][a{i}]")

    filter_str = "".join(filters) + "".join(concat_inputs) + f"concat=n={len(keeps)}:v=1:a=1[outv][outa]"

    cmd = [
        "ffmpeg", "-y", "-i", str(input_path),
        "-filter_complex", filter_str,
        "-map", "[outv]", "-map", "[outa]",
        "-c:v", "libx264", "-crf", "18", "-preset", "veryfast",
        "-c:a", "aac", "-b:a", "192k",
        str(output_path)
    ]

    print(f"   [INFO] Processing cuts...")
    subprocess.run(cmd, check=True, capture_output=True)

    new_dur = get_duration(output_path)
    saved = duration - new_dur
    print(f"   [OK] Original: {duration:.1f}s -> Fluid: {new_dur:.1f}s (saved {saved:.1f}s)")
    print(f"   [OK] Output: {output_path}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Remove dead times from a rendered video")
    parser.add_argument("input", help="Input video file")
    parser.add_argument("--output", "-o", help="Output path (default: <input>_fluid.mp4)")
    parser.add_argument("--threshold", type=int, default=-30, help="Silence threshold in dB (default: -30)")
    parser.add_argument("--min-silence", type=float, default=0.4, help="Min silence duration in seconds (default: 0.4)")
    args = parser.parse_args()

    inp = Path(args.input)
    out = Path(args.output) if args.output else inp.parent / f"{inp.stem}_fluid{inp.suffix}"
    remove_silence(inp, out, noise_db=args.threshold, min_duration=args.min_silence)
