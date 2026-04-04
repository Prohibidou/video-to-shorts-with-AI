"""
Enhance Short - Add visual overlays to a rendered short
========================================================
Adds:
  1. "video completo :" text + screenshot thumbnail (top-right corner)
  2. Animated "Like & Subscribe" green-screen button (bottom center, 3 times)

Usage:
    python enhance_short.py <clip_path> <screenshot_path> [--like-btn <path>] [--output <path>]

Example:
    python enhance_short.py "output/clips/.../clip_01.mp4" "thumbnail.png"
"""

import subprocess
import sys
from pathlib import Path

DEFAULT_LIKE_BTN_URL = "https://www.youtube.com/watch?v=4bDBhs6eG-o"


def download_like_btn(output_dir: Path) -> Path:
    """Download the Like & Subscribe green screen animation."""
    btn_path = output_dir / "like_btn.webm"
    if btn_path.exists() and btn_path.stat().st_size > 0:
        print(f"   [OK] Like button already cached: {btn_path.name}")
        return btn_path

    print("   [INFO] Downloading Like & Subscribe animation...")
    cmd = [
        "yt-dlp", "-o", str(btn_path), DEFAULT_LIKE_BTN_URL
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"   [ERROR] Download failed: {result.stderr[:200]}")
        sys.exit(1)

    print(f"   [OK] Downloaded: {btn_path.name}")
    return btn_path


def get_duration(path: Path) -> float:
    """Get video duration in seconds using ffprobe."""
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True
    )
    return float(result.stdout.strip())


def enhance_video(clip_path: Path, screenshot_path: Path, like_btn_path: Path, output_path: Path, 
                  header_img_path: Path = None, header_text: str = None):
    """Apply all visual enhancements using FFmpeg."""
    font_path = "C:/Windows/Fonts/arial.ttf"
    escaped_font = font_path.replace(":", "\\:")

    # Get duration to place end-card in the last 5 seconds
    dur = get_duration(clip_path)
    end_start = max(0, dur - 5)
    print(f"   [INFO] Video duration: {dur:.1f}s, end-card from {end_start:.1f}s")

    inputs = [
        "-i", str(clip_path),
        "-i", str(screenshot_path),
        "-i", str(like_btn_path)
    ]
    
    # Filter Complex Building
    # 1. Process screenshot - scaled to 500px wide for the end-card
    filters = [f"[1:v]scale=500:-1[img]"]
    
    # 2. Process like button (v) - 1000px wide, chroma-keyed
    filters.append(f"[2:v]scale=1000:-1,chromakey=0x00FF00:0.1:0.2,split=3[b1][b2][b3]")
    filters.append(f"[b1]setpts=PTS+20/TB[b1t]")
    filters.append(f"[b2]setpts=PTS+80/TB[b2t]")
    filters.append(f"[b3]setpts=PTS+140/TB[b3t]")
    
    # Base video processing
    current_v = "[0:v]"
    
    # HEADER (Optional) - First 50 seconds
    if header_img_path and header_img_path.exists():
        inputs.extend(["-i", str(header_img_path)])
        idx = len(inputs) // 2 - 1 # Current index of header_img
        
        # Scale header image to 220px height
        filters.append(f"[{idx}:v]scale=-1:220[hdr_img]")
        
        # Overlay header image centered at y=200
        filters.append(f"{current_v}[hdr_img]overlay=x=(W-w)/2:y=200:enable='lt(t,50)'[v_hdr_img]")
        current_v = "[v_hdr_img]"
        
        if header_text:
            # Place text centered below the image (image y=200 + height=220 + 30 spacer = 450)
            filters.append(f"{current_v}drawtext=fontfile='{escaped_font}':text='{header_text}':"
                           f"fontcolor=white:fontsize=52:x=(w-tw)/2:y=450:"
                           f"bordercolor=black:borderw=2:enable='lt(t,50)'[v_hdr_full]")
            current_v = "[v_hdr_full]"

    # END CARD: black box covering the ENTIRE frame in the last 5 seconds
    filters.append(f"{current_v}drawbox=x=0:y=0:w=1080:h=1920:color=black:t=fill"
                   f":enable='gte(t,{end_start:.2f})'[v_endbox]")
    
    # 'video completo :' text centered, only visible in the end card
    filters.append(f"[v_endbox]drawtext=fontfile='{escaped_font}':text='video completo \\:'"
                   f":fontcolor=white:fontsize=52:x=(w-tw)/2:y=700"
                   f":enable='gte(t,{end_start:.2f})'[v_txt]")
    
    # Screenshot centered below the text, only in end card
    filters.append(f"[v_txt][img]overlay=x=(W-w)/2:y=800"
                   f":enable='gte(t,{end_start:.2f})'[v_midt]")
    
    # Overlay like button at y=1500, centered, at 20s/80s/140s
    filters.append(f"[v_midt][b1t]overlay=x=(W-w)/2:y=1500:enable='between(t,20,29)'[v1_btn]")
    filters.append(f"[v1_btn][b2t]overlay=x=(W-w)/2:y=1500:enable='between(t,80,89)'[v2_btn]")
    filters.append(f"[v2_btn][b3t]overlay=x=(W-w)/2:y=1500:enable='between(t,140,149)'[outv]")
    
    # Audio processing remains same
    filters.append(f"[2:a]asplit=3[a1][a2][a3]")
    filters.append(f"[a1]adelay=20000|20000[a1t]")
    filters.append(f"[a2]adelay=80000|80000[a2t]")
    filters.append(f"[a3]adelay=140000|140000[a3t]")
    filters.append(f"[0:a][a1t][a2t][a3t]amix=inputs=4:duration=first:normalize=0[outa]")

    filter_complex = "; ".join(filters)

    cmd = ["ffmpeg", "-y"] + inputs + [
        "-filter_complex", filter_complex,
        "-map", "[outv]",
        "-map", "[outa]",
        "-c:v", "libx264", "-crf", "21", "-preset", "fast",
        "-c:a", "aac", "-b:a", "128k",
        str(output_path)
    ]

    print(f"   [INFO] Rendering enhanced video...")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        size_mb = output_path.stat().st_size / (1024 * 1024)
        print(f"   [OK] Enhanced video saved: {output_path.name} ({size_mb:.1f} MB)")
    else:
        print(f"   [ERROR] FFmpeg failed:")
        print(result.stderr[-500:])
        sys.exit(1)



def main():
    if len(sys.argv) < 3:
        print("=" * 60)
        print("ENHANCE SHORT - Video Overlay Tool")
        print("=" * 60)
        print()
        print("Usage: python enhance_short.py <clip_path> <screenshot_path> [options]")
        print()
        print("Arguments:")
        print("  clip_path        Path to the rendered short (.mp4)")
        print("  screenshot_path  Path to the screenshot/thumbnail image")
        print()
        print("Options:")
        print("  --like-btn PATH  Path to a custom Like button animation (.webm)")
        print("  --output PATH    Custom output path (default: <clip>_final.mp4)")
        print()
        print("Example:")
        print('  python enhance_short.py "output/clips/.../clip_01.mp4" "thumbnail.png"')
        sys.exit(1)

    clip_path = Path(sys.argv[1])
    screenshot_path = Path(sys.argv[2])

    if not clip_path.exists():
        print(f"[ERROR] Clip not found: {clip_path}")
        sys.exit(1)

    if not screenshot_path.exists():
        print(f"[ERROR] Screenshot not found: {screenshot_path}")
        sys.exit(1)

    # Parse optional arguments
    like_btn_path = None
    output_path = None
    header_img_path = None
    header_text = None

    i = 3
    while i < len(sys.argv):
        if sys.argv[i] == "--like-btn" and i + 1 < len(sys.argv):
            like_btn_path = Path(sys.argv[i + 1])
            i += 2
        elif sys.argv[i] == "--output" and i + 1 < len(sys.argv):
            output_path = Path(sys.argv[i + 1])
            i += 2
        elif sys.argv[i] == "--header-img" and i + 1 < len(sys.argv):
            header_img_path = Path(sys.argv[i + 1])
            i += 2
        elif sys.argv[i] == "--header-text" and i + 1 < len(sys.argv):
            header_text = sys.argv[i + 1]
            i += 2
        else:
            i += 1

    # Default output path
    if output_path is None:
        output_path = clip_path.with_name(clip_path.stem + "_final.mp4")

    # Download like button if not provided
    if like_btn_path is None or not like_btn_path.exists():
        cache_dir = Path(__file__).parent / "temp_analysis_output"
        cache_dir.mkdir(parents=True, exist_ok=True)
        like_btn_path = download_like_btn(cache_dir)

    print("=" * 60)
    print("ENHANCE SHORT")
    print("=" * 60)
    print(f"   Clip:       {clip_path.name}")
    print(f"   Header Img: {header_img_path.name if header_img_path else 'None'}")
    print(f"   Header Txt: {header_text}")
    print()

    enhance_video(clip_path, screenshot_path, like_btn_path, output_path, header_img_path, header_text)

    print()
    print("=" * 60)
    print("ENHANCEMENT COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    main()
