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
import json
import time
from pathlib import Path

# =====================================================================
# FIX: Force UTF-8 output on Windows to prevent UnicodeEncodeError
# =====================================================================
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')


def safe_delete(path: Path, retries=3, wait=2):
    """Delete a file safely, retrying if it's locked by another process."""
    for attempt in range(retries):
        try:
            if path.exists():
                path.unlink()
            return True
        except PermissionError:
            if attempt < retries - 1:
                print(f"   [WARN] '{path.name}' is locked. Retrying in {wait}s... ({attempt+1}/{retries})")
                time.sleep(wait)
            else:
                print(f"   [ERROR] Cannot overwrite '{path.name}'. Close it and retry.")
                return False
    return True


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
    return 1080, 1920

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

    # Detect resolution
    width, height = get_video_resolution(clip_path)
    print(f"   [INFO] Video resolution: {width}x{height}")

    inputs = [
        "-i", str(clip_path),
        "-i", str(screenshot_path),
        "-i", str(like_btn_path)
    ]
    
    # Filter Complex Building
    # 1. Process screenshot - scaled to 25% of height or fixed width
    img_width = int(width * 0.8)
    filters = [f"[1:v]scale={img_width}:-1[img]"]
    
    # 2. Process like button (v) - scaled to 80% of width
    like_width = int(width * 0.8)
    filters.append(f"[2:v]scale={like_width}:-1,chromakey=0x00FF00:0.1:0.2,split=3[b1][b2][b3]")
    filters.append(f"[b1]setpts=PTS+20/TB[b1t]")
    filters.append(f"[b2]setpts=PTS+80/TB[b2t]")
    filters.append(f"[b3]setpts=PTS+140/TB[b3t]")
    
    # Base video processing
    current_v = "[0:v]"
    
    # END CARD: black box covering the ENTIRE frame in the last 5 seconds
    filters.append(f"{current_v}drawbox=x=0:y=0:w={width}:h={height}:color=black:t=fill"
                   f":enable='gte(t,{end_start:.2f})'[v_endbox]")
    
    # 'video completo :' text centered above image
    txt_y = int(height * 0.28)
    filters.append(f"[v_endbox]drawtext=fontfile='{escaped_font}':text='video completo \\:'"
                   f":fontcolor=white:fontsize=52:x=(w-tw)/2:y={txt_y}"
                   f":enable='gte(t,{end_start:.2f})'[v_txt]")
    
    # Screenshot centered in the middle of the screen
    img_y_str = f"(H-h)/2"
    filters.append(f"[v_txt][img]overlay=x=(W-w)/2:y={img_y_str}"
                   f":enable='gte(t,{end_start:.2f})'[v_midt]")
    
    # Overlay like button at bottom center
    btn_y = int(height * 0.80)
    filters.append(f"[v_midt][b1t]overlay=x=(W-w)/2:y={btn_y}:enable='between(t,20,29)'[v1_btn]")
    filters.append(f"[v1_btn][b2t]overlay=x=(W-w)/2:y={btn_y}:enable='between(t,80,89)'[v2_btn]")
    filters.append(f"[v2_btn][b3t]overlay=x=(W-w)/2:y={btn_y}:enable='between(t,140,149)'[outv]")
    
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
        "-c:v", "libx264", "-crf", "21", "-preset", "fast", "-g", "30",
        "-c:a", "aac", "-b:a", "128k",
        str(output_path)
    ]

    print(f"   [INFO] Rendering enhanced video...")
    if not safe_delete(output_path):
        output_path = output_path.with_stem(output_path.stem + "_new")
        print(f"   [FALLBACK] Writing to: {output_path.name}")
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
