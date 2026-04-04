"""
Brand Video - Post-production branding overlay tool
====================================================
Applies branding overlays to an ALREADY RENDERED video.
Never re-renders subtitles or the base video — only adds overlays on top.

3 optional stages:
  1. INTRO  (0 → intro_end):  Title image + hook text
  2. MIDDLE (intro_end → end-card start):  Channel logo
  3. END CARD (last N seconds):  Black screen + text + thumbnail

Usage:
    python brand_video.py <input_video> [options]

Example:
    python brand_video.py "output/clips/.../final.mp4" ^
        --intro-img "titulo.png" ^
        --intro-text "Avengers tienen poderes de endemoniados" ^
        --logo "Logo/logo bueno.png" ^
        --endcard-img "video completo.png" ^
        --output "CLIP_FINAL.mp4"
"""

import argparse
import subprocess
import sys
from pathlib import Path


def get_duration(path: Path) -> float:
    """Get video duration in seconds via ffprobe."""
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True
    )
    return float(result.stdout.strip())


def build_filter(args, duration: float):
    """Build the FFmpeg filter_complex string and input list."""
    inputs = ["-i", str(args.input)]
    filters = []
    input_idx = 1  # next available input index
    current_v = "[0:v]"

    has_intro = args.intro_img is not None
    has_logo = args.logo is not None
    has_endcard = args.endcard_img is not None

    end_card_start = duration - args.end_duration

    # ── STAGE 1: INTRO (0 → intro_end) ──────────────────────────
    if has_intro:
        inputs.extend(["-i", str(args.intro_img)])
        idx = input_idx
        input_idx += 1

        filters.append(f"[{idx}:v]scale=-1:{args.intro_img_h}[hdr_img]")
        filters.append(
            f"{current_v}[hdr_img]overlay=x=(W-w)/2:y={args.intro_img_y}"
            f":enable='lt(t,{args.intro_end})'[v_intro_img]"
        )
        current_v = "[v_intro_img]"

        if args.intro_text:
            safe_text = args.intro_text.replace("'", "'\\''")
            filters.append(
                f"{current_v}drawtext=font='Arial':text='{safe_text}':"
                f"fontcolor=white:fontsize={args.intro_text_size}:"
                f"x=(w-tw)/2:y={args.intro_text_y}:"
                f"bordercolor=black:borderw=2:"
                f"enable='lt(t,{args.intro_end})'[v_intro_txt]"
            )
            current_v = "[v_intro_txt]"

    # ── STAGE 2: CHANNEL LOGO (intro_end → end-card start) ──────
    if has_logo:
        inputs.extend(["-i", str(args.logo)])
        idx = input_idx
        input_idx += 1

        filters.append(f"[{idx}:v]scale=-1:{args.logo_h}[chan_logo]")

        if has_endcard:
            logo_end = end_card_start
            filters.append(
                f"{current_v}[chan_logo]overlay=x=(W-w)/2:y={args.logo_y}"
                f":enable='between(t,{args.intro_end},{logo_end:.2f})'[v_logo]"
            )
        else:
            filters.append(
                f"{current_v}[chan_logo]overlay=x=(W-w)/2:y={args.logo_y}"
                f":enable='gte(t,{args.intro_end})'[v_logo]"
            )
        current_v = "[v_logo]"

    # ── STAGE 3: END CARD (last N seconds) ──────────────────────
    if has_endcard:
        inputs.extend(["-i", str(args.endcard_img)])
        idx = input_idx
        input_idx += 1

        # Black box covering entire frame
        filters.append(
            f"{current_v}drawbox=x=0:y=0:w=iw:h=ih:color=black:t=fill"
            f":enable='gte(t,{end_card_start:.2f})'[v_endbox]"
        )
        current_v = "[v_endbox]"

        # End card text
        safe_end_text = args.endcard_text.replace("'", "'\\''")
        filters.append(
            f"{current_v}drawtext=font='Arial':text='{safe_end_text}':"
            f"fontcolor=white:fontsize={args.endcard_text_size}:"
            f"x=(w-tw)/2:y={args.endcard_text_y}:"
            f"bordercolor=white:borderw=1:"
            f"enable='gte(t,{end_card_start:.2f})'[v_endtxt]"
        )
        current_v = "[v_endtxt]"

        # Thumbnail image
        filters.append(f"[{idx}:v]scale={args.endcard_img_w}:-1[thumb]")
        filters.append(
            f"{current_v}[thumb]overlay=x=(W-w)/2:y={args.endcard_img_y}"
            f":enable='gte(t,{end_card_start:.2f})'[v_endimg]"
        )
        current_v = "[v_endimg]"

    # Final output label
    final_label = current_v.strip("[]")
    if final_label != "0:v":
        # Rename last label to [outv]
        last_filter = filters[-1]
        filters[-1] = last_filter.rsplit("[", 1)[0] + "[outv]"
    else:
        # No filters applied at all — just copy
        filters.append(f"{current_v}null[outv]")

    return inputs, "; ".join(filters)


def main():
    parser = argparse.ArgumentParser(
        description="Brand Video — Post-production overlay tool. "
                    "Applies branding overlays WITHOUT re-rendering the base video.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Full branding (intro + logo + end-card):
    python brand_video.py final.mp4 --intro-img titulo.png --intro-text "Hook text" --logo logo.png --endcard-img thumb.png

  Logo only:
    python brand_video.py final.mp4 --logo logo.png

  End-card only:
    python brand_video.py final.mp4 --endcard-img thumb.png --endcard-text "Ver video completo"
        """
    )

    # Required
    parser.add_argument("input", type=Path, help="Input video file (already rendered)")

    # Output
    parser.add_argument("--output", "-o", type=Path, default=None,
                        help="Output path (default: <input>_branded.mp4)")

    # Intro Stage
    intro = parser.add_argument_group("Intro Stage (0 -> intro-end)")
    intro.add_argument("--intro-img", type=Path, default=None,
                       help="Title/hook image (e.g. Avengers logo)")
    intro.add_argument("--intro-text", type=str, default=None,
                       help="Hook text below the image")
    intro.add_argument("--intro-end", type=float, default=50,
                       help="When intro ends in seconds (default: 50)")
    intro.add_argument("--intro-img-y", type=int, default=240,
                       help="Y position of intro image (default: 240)")
    intro.add_argument("--intro-img-h", type=int, default=220,
                       help="Height to scale intro image to (default: 220)")
    intro.add_argument("--intro-text-y", type=int, default=490,
                       help="Y position of intro text (default: 490)")
    intro.add_argument("--intro-text-size", type=int, default=52,
                       help="Font size of intro text (default: 52)")

    # Middle Stage (Channel Logo)
    mid = parser.add_argument_group("Channel Logo Stage (intro-end -> end-card)")
    mid.add_argument("--logo", type=Path, default=None,
                     help="Channel logo image")
    mid.add_argument("--logo-y", type=int, default=340,
                     help="Y position of logo (default: 340)")
    mid.add_argument("--logo-h", type=int, default=120,
                     help="Height to scale logo to (default: 120)")

    # End Card
    end = parser.add_argument_group("End Card Stage (last N seconds)")
    end.add_argument("--endcard-img", type=Path, default=None,
                     help="Thumbnail image for end card")
    end.add_argument("--endcard-text", type=str, default="Video Completo",
                     help='End card text (default: "Video Completo")')
    end.add_argument("--endcard-text-size", type=int, default=80,
                     help="Font size of end card text (default: 80)")
    end.add_argument("--endcard-text-y", type=int, default=600,
                     help="Y position of end card text (default: 600)")
    end.add_argument("--endcard-img-w", type=int, default=900,
                     help="Width to scale end card thumbnail (default: 900)")
    end.add_argument("--endcard-img-y", type=int, default=800,
                     help="Y position of end card thumbnail (default: 800)")
    end.add_argument("--end-duration", type=float, default=5,
                     help="Duration of end card in seconds (default: 5)")

    # Encoding
    enc = parser.add_argument_group("Encoding")
    enc.add_argument("--crf", type=int, default=18,
                     help="CRF quality (default: 18, lower = better)")
    enc.add_argument("--preset", type=str, default="fast",
                     help="x264 preset (default: fast)")

    args = parser.parse_args()

    # ── Validation ──────────────────────────────────────────────
    if not args.input.exists():
        print(f"[ERROR] Input video not found: {args.input}")
        sys.exit(1)

    for label, path in [("--intro-img", args.intro_img), ("--logo", args.logo),
                        ("--endcard-img", args.endcard_img)]:
        if path and not path.exists():
            print(f"[ERROR] {label} not found: {path}")
            sys.exit(1)

    if not any([args.intro_img, args.logo, args.endcard_img]):
        print("[ERROR] No branding specified. Use at least one of: --intro-img, --logo, --endcard-img")
        sys.exit(1)

    # Default output
    if args.output is None:
        args.output = args.input.with_name(args.input.stem + "_branded.mp4")

    # ── Build & Run ─────────────────────────────────────────────
    duration = get_duration(args.input)
    print("=" * 60)
    print("BRAND VIDEO — Post-Production Overlay")
    print("=" * 60)
    print(f"  Input:    {args.input.name}")
    print(f"  Duration: {duration:.1f}s")
    print(f"  Output:   {args.output}")
    print()

    if args.intro_img:
        print(f"  [INTRO]    Image: {args.intro_img.name}")
        print(f"             Text:  {args.intro_text or '(none)'}")
        print(f"             Range: 0s -> {args.intro_end}s")
    if args.logo:
        print(f"  [LOGO]     Image: {args.logo.name}")
        end_card_start = duration - args.end_duration if args.endcard_img else duration
        print(f"             Range: {args.intro_end}s -> {end_card_start:.0f}s")
    if args.endcard_img:
        end_card_start = duration - args.end_duration
        print(f"  [ENDCARD]  Image: {args.endcard_img.name}")
        print(f"             Text:  {args.endcard_text}")
        print(f"             Range: {end_card_start:.0f}s -> {duration:.0f}s")
    print()

    inputs, filter_complex = build_filter(args, duration)

    cmd = ["ffmpeg", "-y"] + inputs + [
        "-filter_complex", filter_complex,
        "-map", "[outv]",
        "-map", "0:a",
        "-c:v", "libx264", "-crf", str(args.crf), "-preset", args.preset,
        "-c:a", "copy",
        str(args.output)
    ]

    print("  [INFO] Applying branding overlays...")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        size_mb = args.output.stat().st_size / (1024 * 1024)
        print(f"\n  [OK] Branded video saved: {args.output} ({size_mb:.1f} MB)")
    else:
        print(f"\n  [ERROR] FFmpeg failed:")
        print(result.stderr[-800:])
        sys.exit(1)

    print()
    print("=" * 60)
    print("BRANDING COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    main()
