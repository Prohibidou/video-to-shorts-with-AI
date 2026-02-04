"""
Batch Shorts Extractor
======================
Reads segments from a JSON file and extracts all clips
with automatic subtitles.

Usage:
    python batch_extractor.py segments.json
    python batch_extractor.py segments.json --vertical --subtitles
    python batch_extractor.py segments.json --style bold
"""

import argparse
import json
import sys
from pathlib import Path
from shorts_extractor import Segment, process_video


def load_segments_from_json(json_path: Path) -> tuple[str, list[Segment]]:
    """Loads segment configuration from a JSON file."""
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    url = data.get("video_url")
    if not url:
        raise ValueError("JSON file must have 'video_url'")
    
    segments = []
    for seg in data.get("segments", []):
        segments.append(Segment(
            start=seg["start"],
            end=seg["end"],
            name=seg.get("name", f"clip_{len(segments)+1}")
        ))
    
    return url, segments


def main():
    parser = argparse.ArgumentParser(
        description="Extract multiple YouTube shorts from a JSON file"
    )
    parser.add_argument(
        "json_file",
        type=Path,
        help="JSON file with URL and segments"
    )
    parser.add_argument(
        "--vertical",
        action="store_true",
        help="Convert to vertical 9:16 format for Shorts"
    )
    parser.add_argument(
        "--fast",
        action="store_true",
        help="Fast mode (no subtitles, instant cut)"
    )
    parser.add_argument(
        "--no-subtitles",
        action="store_true",
        help="Disable automatic subtitles"
    )
    parser.add_argument(
        "--style",
        type=str,
        default="modern",
        choices=["modern", "bold", "minimal"],
        help="Subtitle style (default: modern)"
    )
    parser.add_argument(
        "--lang",
        type=str,
        default="es",
        help="Video language for transcription (default: es)"
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=None,
        help="Output directory (default: ./output)"
    )
    parser.add_argument(
        "--no-keep-source",
        action="store_true",
        help="Delete source video after extracting clips"
    )
    
    args = parser.parse_args()
    
    if not args.json_file.exists():
        print(f"❌ File not found: {args.json_file}")
        sys.exit(1)
    
    # Load configuration
    url, segments = load_segments_from_json(args.json_file)
    
    print(f"📄 Loaded {len(segments)} segments from {args.json_file.name}")
    
    # Determine output directory
    output_dir = args.output or Path("./output")
    
    # Determine if adding subtitles
    add_subtitles = not args.no_subtitles and not args.fast
    
    # Process
    process_video(
        url=url,
        segments=segments,
        output_dir=output_dir,
        make_vertical=args.vertical,
        fast_mode=args.fast,
        add_subtitles=add_subtitles,
        subtitle_style=args.style,
        language=args.lang,
        keep_source=not args.no_keep_source
    )


if __name__ == "__main__":
    main()
