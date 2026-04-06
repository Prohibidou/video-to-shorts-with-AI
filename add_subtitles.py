"""
Add Movie-Style Subtitles to a Video
=====================================
Uses faster-whisper (large-v3) for high-quality Spanish transcription,
then burns subtitles into the video with a classic movie aesthetic:
  - Black semi-transparent background box
  - Yellowish text (like classic cinema subtitles)

Usage:
    python add_subtitles.py <video_path> [--model large-v3] [--output <path>]

Example:
    python add_subtitles.py "output/clips/.../clip_01_final.mp4"
"""

import subprocess
import sys
import os
import json
from pathlib import Path


def get_video_resolution(video_path: Path) -> tuple:
    """Get video width and height using ffprobe."""
    cmd = [
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height", "-of", "json",
        str(video_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        data = json.loads(result.stdout)
        width = data['streams'][0]['width']
        height = data['streams'][0]['height']
        return width, height
    return 1080, 1920  # Default fallback


def transcribe_audio(video_path: Path, model_name: str = "large-v3") -> list:
    """Transcribe audio using faster-whisper for high accuracy."""
    from faster_whisper import WhisperModel

    print(f"   [INFO] Loading Whisper model: {model_name}")
    print(f"   [INFO] This may take a moment on first run (downloading model)...")

    model = WhisperModel(model_name, device="cpu", compute_type="int8")

    print(f"   [INFO] Transcribing audio...")
    segments_gen, info = model.transcribe(
        str(video_path),
        language="es",
        beam_size=5,
        word_timestamps=True,
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=500)
    )

    segments = []
    MAX_WORDS = 3

    for seg in segments_gen:
        if not seg.words:
            # Fallback if word timestamps are missing for some reason
            segments.append({
                "start": seg.start,
                "end": seg.end,
                "text": seg.text.strip()
            })
            continue

        current_chunk = []
        chunk_start = None

        for w in seg.words:
            if not current_chunk:
                chunk_start = w.start
            current_chunk.append(w.word.strip())

            if len(current_chunk) >= MAX_WORDS:
                segments.append({
                    "start": chunk_start,
                    "end": w.end,
                    "text": " ".join(current_chunk)
                })
                current_chunk = []
                chunk_start = None

        # Add any remaining words in the segment
        if current_chunk:
            segments.append({
                "start": chunk_start,
                "end": seg.words[-1].end,
                "text": " ".join(current_chunk)
            })

    # Optional: print summary of chunks
    print(f"   [INFO] Grouped into {len(segments)} subtitle chunks (Max {MAX_WORDS} words/chunk).")
    return segments


def format_time(seconds: float) -> str:
    """Format seconds as HH:MM:SS,mmm for SRT."""
    hours = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{mins:02d}:{secs:02d},{millis:03d}"


def generate_srt(segments: list, output_path: Path):
    """Generate SRT subtitle file from segments."""
    with open(output_path, "w", encoding="utf-8") as f:
        for i, seg in enumerate(segments, 1):
            f.write(f"{i}\n")
            f.write(f"{format_time(seg['start'])} --> {format_time(seg['end'])}\n")
            f.write(f"{seg['text']}\n\n")

    print(f"   [OK] SRT saved: {output_path.name}")


def generate_ass(segments: list, output_path: Path, width: int, height: int):
    """Generate ASS subtitle file with movie-style formatting adjusted for resolution."""
    # Scale font and margins based on height
    font_size = int(height * 0.05) if height > width else int(height * 0.07)
    margin_v = int(height * 0.1) # 10% from bottom

    ass_header = f"""[Script Info]
Title: Movie Subtitles
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709
PlayResX: {width}
PlayResY: {height}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: MovieSub,Arial,{font_size},&H0080FFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,3,2,0,2,40,40,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(ass_header)
        for seg in segments:
            start = format_ass_time(seg['start'])
            end = format_ass_time(seg['end'])
            text = seg['text'].replace("\n", "\\N")
            f.write(f"Dialogue: 0,{start},{end},MovieSub,,0,0,0,,{text}\n")

    print(f"   [OK] ASS saved: {output_path.name}")


def format_ass_time(seconds: float) -> str:
    """Format seconds as H:MM:SS.CC for ASS."""
    hours = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centis = int((seconds % 1) * 100)
    return f"{hours}:{mins:02d}:{secs:02d}.{centis:02d}"


def burn_subtitles(video_path: Path, ass_path: Path, output_path: Path):
    """Burn ASS subtitles into the video using FFmpeg."""
    # Escape path for FFmpeg on Windows (replace \ with / and : with \:)
    ass_escaped = str(ass_path).replace("\\", "/").replace(":", "\\:")

    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-vf", f"ass='{ass_escaped}'",
        "-c:v", "libx264",
        "-crf", "21",
        "-preset", "fast",
        "-c:a", "copy",
        str(output_path)
    ]

    print(f"   [INFO] Burning subtitles into video...")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        size_mb = output_path.stat().st_size / (1024 * 1024)
        print(f"   [OK] Subtitled video saved: {output_path.name} ({size_mb:.1f} MB)")
    else:
        print(f"   [ERROR] FFmpeg failed:")
        print(result.stderr[-800:])
        sys.exit(1)


def main():
    if len(sys.argv) < 2:
        print("=" * 60)
        print("ADD MOVIE-STYLE SUBTITLES")
        print("=" * 60)
        print()
        print("Usage: python add_subtitles.py <video_path> [options]")
        print()
        print("Options:")
        print("  --model NAME    Whisper model (default: large-v3)")
        print("                  Options: tiny, base, small, medium, large-v3")
        print("  --output PATH   Custom output path")
        print("  --srt-only      Only generate SRT, don't burn into video")
        print()
        print("Example:")
        print('  python add_subtitles.py "clip_01_final.mp4"')
        print('  python add_subtitles.py "clip_01_final.mp4" --model medium')
        sys.exit(1)

    video_path = Path(sys.argv[1])

    if not video_path.exists():
        print(f"[ERROR] Video not found: {video_path}")
        sys.exit(1)

    # Parse optional arguments
    model_name = "large-v3"
    output_path = None
    srt_only = False

    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == "--model" and i + 1 < len(sys.argv):
            model_name = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--output" and i + 1 < len(sys.argv):
            output_path = Path(sys.argv[i + 1])
            i += 2
        elif sys.argv[i] == "--srt-only":
            srt_only = True
            i += 1
        else:
            i += 1

    if output_path is None:
        output_path = video_path.with_name(video_path.stem + "_sub.mp4")

    srt_path = video_path.with_suffix(".srt")
    ass_path = video_path.with_suffix(".ass")

    print("=" * 60)
    print("ADD MOVIE-STYLE SUBTITLES")
    print("=" * 60)
    print(f"   Video:  {video_path.name}")
    print(f"   Model:  {model_name}")
    print(f"   Output: {output_path.name}")
    print()

    # Step 1: Transcribe
    segments = transcribe_audio(video_path, model_name)

    if not segments:
        print("[ERROR] No segments transcribed. Exiting.")
        sys.exit(1)

    # Step 2: Generate subtitle files
    width, height = get_video_resolution(video_path)
    print(f"   [INFO] Video resolution: {width}x{height}")
    generate_srt(segments, srt_path)
    generate_ass(segments, ass_path, width, height)

    if srt_only:
        print("\n[INFO] SRT-only mode. Skipping video burn-in.")
        return

    # Step 3: Burn subtitles into video
    burn_subtitles(video_path, ass_path, output_path)

    print()
    print("=" * 60)
    print("SUBTITLES COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    main()
