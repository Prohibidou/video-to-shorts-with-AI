"""
YouTube Shorts Extractor
========================
Tool to extract multiple clips from a YouTube video
based on specific timestamps, with automatic subtitles.

Usage:
    python shorts_extractor.py

Requirements:
    - yt-dlp (pip install yt-dlp)
    - ffmpeg (must be in system PATH)
"""

import subprocess
import os
import sys
import json
import tempfile
import re
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Tuple

# Database module for tracking
try:
    from database import save_video, save_short, init_db
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False


# Constants removed manually by user request to avoid heuristic bias
# All hooks must be defined manually in the SEGMENTS configuration

@dataclass
class Segment:
    """Represents a video segment to extract."""
    start: str          # Format: "MM:SS" or "HH:MM:SS"
    end: str            # Format: "MM:SS" or "HH:MM:SS"
    name: str           # Descriptive clip name
    hook_duration: float = 4.0  # Hook duration in seconds
    hook_text: str = None       # Hook text (optional, if None it's auto-generated)
    

def time_to_seconds(time_str: str) -> float:
    """Converts time in MM:SS or HH:MM:SS format to seconds."""
    parts = time_str.strip().split(":")
    if len(parts) == 2:
        minutes, seconds = parts
        return int(minutes) * 60 + float(seconds)
    elif len(parts) == 3:
        hours, minutes, seconds = parts
        return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    else:
        raise ValueError(f"Invalid time format: {time_str}")



def get_video_title(url: str) -> str:
    """Gets the real YouTube video title using yt-dlp."""
    try:
        result = subprocess.run(
            ["yt-dlp", "--get-title", url],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception as e:
        print(f"   ⚠️ Could not get title: {e}")
    return None


def download_video(url: str, output_dir: Path) -> Path:
    """Downloads the YouTube video."""
    target_file = output_dir / "source_video.mp4"
    if target_file.exists() and target_file.stat().st_size > 0:
        print(f"\n   ✅ Video already exists: {target_file.name}")
        return target_file

    output_template = str(output_dir / "source_video.%(ext)s")
    
    print(f"\n📥 Downloading video...")
    print(f"   URL: {url}")
    
    cmd = [
        "yt-dlp",
        "-f", "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
        "--merge-output-format", "mp4",
        "-o", output_template,
        "--no-playlist",
        url
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ Download error: {result.stderr}")
        sys.exit(1)
    
    # Find the downloaded file
    for file in output_dir.glob("source_video.*"):
        print(f"   ✅ Downloaded: {file.name}")
        return file
    
    raise FileNotFoundError("Downloaded video not found")


def extract_clip(
    source_video: Path,
    segment: Segment,
    output_dir: Path,
    clip_index: int,
    make_vertical: bool = False,
    add_hook: bool = True,  # Add fixed hook text in the first seconds (unused but kept for signature comp)
    preview_mode: bool = False # If True, only extracts script, no video rendering (deprecated logic)
) -> Tuple[Optional[Path], str, Optional[str]]:
    """Extracts a clip from the source video.
    Returns (file_path, script_text, hook_text).
    Script text and hook text will be empty/None as transcription is removed.
    """
    
    start_seconds = time_to_seconds(segment.start)
    end_seconds = time_to_seconds(segment.end)
    duration = end_seconds - start_seconds
    
    # Sanitize filename
    safe_name = "".join(c if c.isalnum() or c in "- _" else "_" for c in segment.name)
    temp_clip = output_dir / f"temp_clip_{clip_index:02d}.mp4"
    output_file = output_dir / f"clip_{clip_index:02d}_{safe_name}.mp4"
    
    print(f"\n🎬 Extracting clip {clip_index}: {segment.name}")
    print(f"   ⏱️  {segment.start} → {segment.end} (duration: {duration:.1f}s)")
    
    # Step 1: Extract temporary clip (or audio if in preview mode)
    if preview_mode:
        # Extract audio only for faster processing
        temp_clip = output_dir / f"temp_audio_{clip_index:02d}.m4a"
        cmd_extract = [
            "ffmpeg", "-y",
            "-ss", str(start_seconds),
            "-i", str(source_video),
            "-t", str(duration),
            "-vn",          # No video
            "-c:a", "aac",
            "-b:a", "128k",
            str(temp_clip)
        ]
    else:
        # Extract video + audio
        cmd_extract = [
            "ffmpeg", "-y",
            "-ss", str(start_seconds),
            "-i", str(source_video),
            "-t", str(duration),
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "128k",
            str(temp_clip)
        ]
    
    # FFmpeg writes to stderr even on successful runs, so we check the file
    result = subprocess.run(cmd_extract, capture_output=True, text=True)
    
    if not temp_clip.exists():
        print(f"   ❌ Error: Could not create temporary clip")
        print(f"   ℹ️ FFmpeg stderr: {result.stderr[:500]}")
        return None, "", None
        
    if temp_clip.stat().st_size == 0:
        print(f"   ❌ Error: Temporary clip is 0 bytes (corrupted)")
        print(f"   ℹ️ FFmpeg stderr: {result.stderr[:500]}")
        temp_clip.unlink()
        return None, "", None

    # Step 1.5: Remove silence (dead air) if requested
    # Robust method: Detect silence -> Split -> Concat (preserves sync)
    # IMPORTANT: The first hook_duration seconds are PROTECTED and never cut
    hook_protection_seconds = segment.hook_duration if segment.hook_duration else 4.0
    try:
        print("   ✂️  Analyzing silence patterns...")
        print(f"   🛡️  Hook protection zone: first {hook_protection_seconds:.1f}s are untouchable")
        silence_thresh = "-35dB"
        silence_duration = "0.5" # Minimum duration (seconds) to consider silence
        
        # 1. Detect silences
        cmd_detect = [
            "ffmpeg", "-i", str(temp_clip),
            "-af", f"silencedetect=noise={silence_thresh}:d={silence_duration}",
            "-f", "null", "-"
        ]
        result_detect = subprocess.run(cmd_detect, capture_output=True, text=True)
        
        # 2. Parse silence info
        # Output format: [silencedetect @ ...] silence_start: 12.345
        #                [silencedetect @ ...] silence_end: 14.567
        silence_starts = []
        silence_ends = []
        for line in result_detect.stderr.splitlines():
            if "silence_start" in line:
                try:
                    silence_starts.append(float(line.split("silence_start: ")[1]))
                except: pass
            elif "silence_end" in line:
                try:
                    silence_ends.append(float(line.split("silence_end: ")[1].split(" ")[0]))
                except: pass
        
        # 3. Filter out silences that overlap with the hook protection zone
        # Any silence that starts OR ends within the first hook_protection_seconds is SKIPPED
        filtered_starts = []
        filtered_ends = []
        skipped_count = 0
        for i in range(len(silence_starts)):
            s_start = silence_starts[i]
            s_end = silence_ends[i] if i < len(silence_ends) else None
            
            # Skip if silence starts within the hook protection zone
            if s_start < hook_protection_seconds:
                skipped_count += 1
                continue
            # Skip if silence ends within the hook protection zone (overlapping silence)
            if s_end is not None and s_end < hook_protection_seconds:
                skipped_count += 1
                continue
            
            filtered_starts.append(s_start)
            if s_end is not None:
                filtered_ends.append(s_end)
        
        if skipped_count > 0:
            print(f"   🛡️  Skipped {skipped_count} silence(s) inside hook protection zone")
        
        silence_starts = filtered_starts
        silence_ends = filtered_ends
        
        if not silence_starts:
            print("   ℹ️  No significant silence found (outside hook zone). Skipping cut.")
        else:
            # Construct keep segments
            # Keep: [0, start[0]], [end[0], start[1]], [end[1], end_of_video]
            
            # Get video duration
            cmd_dur = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(temp_clip)]
            res_dur = subprocess.run(cmd_dur, capture_output=True, text=True)
            total_duration = float(res_dur.stdout.strip())
            
            keep_segments = []
            last_pos = 0.0
            
            # Safest iteration
            num_silences = len(silence_starts)
            for i in range(num_silences):
                s_start = silence_starts[i]
                
                # Keep segment from last_pos to s_start
                if s_start > last_pos + 0.1: # Keep if segment > 0.1s
                    keep_segments.append((last_pos, s_start))
                
                # Update last_pos to end of this silence
                if i < len(silence_ends):
                     # Adjust end to skip the silence
                     # Add a small buffer (0.1s) to avoid clipping words
                    last_pos = silence_ends[i] - 0.1 # Overlap slightly into silence to be safe
                else:
                    last_pos = total_duration # Silence goes to end
            
            # Add final segment
            if last_pos < total_duration - 0.1:
                keep_segments.append((last_pos, total_duration))
            
            if len(keep_segments) < 1:
                print("   ⚠️  All content detected as silence? Skipping cut.")
            elif len(keep_segments) == 1 and keep_segments[0][0] == 0.0 and keep_segments[0][1] == total_duration:
                 print("   ℹ️  Silence detected but effectively full video. Skipping.")
            else:
                print(f"   ✂️  Cutting {len(keep_segments)} active segments...")
                
                # 3. Extract segments
                segment_files = []
                for i, (start, end) in enumerate(keep_segments):
                    seg_file = output_dir / f"temp_seg_{clip_index}_{i}.mp4"
                    cmd_seg = [
                        "ffmpeg", "-y",
                        "-i", str(temp_clip),
                        "-ss", f"{start:.3f}",
                        "-to", f"{end:.3f}",
                        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                        "-c:a", "aac",
                        str(seg_file)
                    ]
                    subprocess.run(cmd_seg, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    if seg_file.exists():
                        segment_files.append(seg_file)
                
                # 4. Concat
                if segment_files:
                    concat_list = output_dir / f"concat_list_{clip_index}.txt"
                    with open(concat_list, "w") as f:
                        for sf in segment_files:
                            f.write(f"file '{sf.name}'\n")
                    
                    processed_clip = output_dir / f"processed_{clip_index:02d}.mp4"
                    cmd_concat = [
                        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                        "-i", str(concat_list),
                        "-c", "copy",
                        str(processed_clip)
                    ]
                    subprocess.run(cmd_concat, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    
                    # Cleanup segments
                    concat_list.unlink()
                    for sf in segment_files:
                        try: sf.unlink()
                        except: pass
                        
                    if processed_clip.exists() and processed_clip.stat().st_size > 0:
                        temp_clip.unlink()
                        processed_clip.rename(temp_clip)
                        print("   ✅ Silence removed successfully (Synced Audio/Video)")
                    else:
                        print("   ⚠️  Concat failed. Using original.")
                        
    except Exception as e:
        print(f"   ⚠️  Error in silence removal: {e}") 
    
    if preview_mode:
        print(f"   ⚠️ Preview mode is deprecated as transcription is removed.")
        return None, "", None

    
    # Step 4: Finalize video
    
    if make_vertical:
        # Vertical 9:16 format (without subtitles)
        filter_complex = (
            f"[0:v]scale=1080:1920:force_original_aspect_ratio=increase,"
            f"crop=1080:1920,boxblur=20:5[bg];"
            f"[0:v]scale=1080:-2:force_original_aspect_ratio=decrease[fg];"
            f"[bg][fg]overlay=(W-w)/2:(H-h)/2[v]"
        )
        cmd_final = [
            "ffmpeg", "-y",
            "-i", temp_clip.name,
            "-filter_complex", filter_complex,
            "-map", "[v]",
            "-map", "0:a",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "128k",
            output_file.name
        ]
    else:
        # Keep original format
        # Just rename/copy temp clip as we don't have burn-in anymore
        # But to be safe and consistent with previous behavior (re-encoding), let's keep it simple
        # Actually, if not vertical, we can just move the temp clip
        temp_clip.rename(output_file)
        print(f"   ✅ Saved: {output_file.name}")
        return output_file, "", None
    
    # Run FFmpeg from the clip directory to avoid path issues
    # Fix: redirect to log file to prevent pipe buffer deadlock on long FFmpeg output
    log_file = output_dir / f"ffmpeg_log_{clip_index}.txt"
    with open(log_file, "w") as f_log:
        result = subprocess.run(cmd_final, stdout=f_log, stderr=f_log, cwd=str(output_dir))
    
    # Check if FFmpeg failed
    if result.returncode != 0:
        print(f"   ❌ Error: FFmpeg failed (exit code {result.returncode}).")
        try:
            with open(log_file, "r") as f_read:
                print(f"   ℹ️ Log: {f_read.read()[:500]}")
        except: pass
        return None, "", None
    
    # Clean up log file on success
    if log_file.exists():
        log_file.unlink()
    
    # Clean up temporary files
    if temp_clip.exists():
        temp_clip.unlink()
    
    # ROBUST VALIDATION: Check if output file exists AND is not 0 bytes (corrupted)
    if not output_file.exists():
        print(f"   ❌ Error: Could not create video")
        return None, "", None
    
    # Check for corrupted (0-byte) file - indicates FFmpeg failure (memory error, etc.)
    if output_file.stat().st_size == 0:
        print(f"   ❌ Error: Output file is 0 bytes (corrupted). FFmpeg may have failed due to memory.")
        output_file.unlink()  # Delete corrupted file
        return None, "", None
    
    # Additional validation: Check if file is at least 100KB (reasonable minimum for 1min video)
    min_size = 100 * 1024  # 100KB
    if output_file.stat().st_size < min_size:
        print(f"   ⚠️  Warning: Output file is unusually small ({output_file.stat().st_size} bytes)")
    
    print(f"   ✅ Saved: {output_file.name}")
    return output_file, "", None


def extract_clip_fast(
    source_video: Path,
    segment: Segment,
    output_dir: Path,
    clip_index: int
) -> Path:
    """
    Extracts a clip WITHOUT re-encoding (instant).
    Note: Cuts may not be frame-exact.
    Does not support subtitles.
    """
    
    start_seconds = time_to_seconds(segment.start)
    end_seconds = time_to_seconds(segment.end)
    duration = end_seconds - start_seconds
    
    safe_name = "".join(c if c.isalnum() or c in "- _" else "_" for c in segment.name)
    output_file = output_dir / f"clip_{clip_index:02d}_{safe_name}.mp4"
    
    print(f"\n⚡ Extracting clip {clip_index} (fast mode, no subtitles): {segment.name}")
    print(f"   ⏱️  {segment.start} → {segment.end}")
    
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start_seconds),
        "-i", str(source_video),
        "-t", str(duration),
        "-c", "copy",  # Without re-encoding
        str(output_file)
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"   ❌ Error: {result.stderr[:200]}")
        return None
    
    print(f"   ✅ Saved: {output_file.name}")
    return output_file


def process_video(
    url: str,
    segments: list[Segment],
    output_dir: Path,
    make_vertical: bool = False,
    fast_mode: bool = False,
    keep_source: bool = True,
    preview_mode: bool = False,
    resume_mode: bool = False
):
    """Processes a complete video extracting all segments."""
    
    print("=" * 60)
    print("🎥 YOUTUBE SHORTS EXTRACTOR")
    if preview_mode:
        print("   👀 PREVIEW MODE (No video rendering)")
    if resume_mode:
        print("   ⏯️  RESUME MODE (Skipping existing clips)")
    print("=" * 60)
    
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Download video
    source_video = download_video(url, output_dir)
    
    # Get real YouTube video title
    video_title = get_video_title(url)
    if not video_title:
        video_title = "Untitled Video"
    if video_title:
        print(f"   📺 Title: {video_title}")
    
    # Create folder for video using the title
    safe_video_title = "".join(c if c.isalnum() or c in "- _" else "_" for c in (video_title or "Video"))
    video_clips_dir = output_dir / "clips" / safe_video_title
    video_clips_dir.mkdir(parents=True, exist_ok=True)
    
    # Save video in database
    video_id = None
    if DB_AVAILABLE:
        try:
            video_id = save_video(url=url, title=video_title, transcript=None)
            print(f"   💾 Video registered in DB (ID: {video_id})")
        except Exception as e:
            print(f"   ⚠️ Error saving video to DB: {e}")
    
    # Extract each segment
    print(f"\n📋 Processing {len(segments)} segments...")
    if preview_mode:
        print("   👀 PREVIEW MODE (Logic deprecated, will skip extraction)")
    
    extracted_clips = []
    all_scripts = []  # To save complete video transcription
    
    for i, segment in enumerate(segments, 1):
        # Create individual folder for this short
        safe_segment_name = "".join(c if c.isalnum() or c in "- _" else "_" for c in segment.name)
        short_folder = video_clips_dir / f"{i:02d}_{safe_segment_name}"
        short_folder.mkdir(parents=True, exist_ok=True)
        
        # Check for existing clip in resume mode
        final_clip_name = f"clip_{i:02d}_{safe_segment_name}.mp4"
        final_clip_path = short_folder / final_clip_name
        
        if resume_mode and final_clip_path.exists() and final_clip_path.stat().st_size > 100000:
            print(f"\n✅ Clip {i} {segment.name} already exists. Skipping.")
            extracted_clips.append(final_clip_path)
            continue

        if fast_mode:
            clip = extract_clip_fast(source_video, segment, short_folder, i)
            script_text = ""
            final_hook_text = None
        else:
            # Retry logic: attempt up to 2 times if extraction fails (memory errors, etc.)
            max_attempts = 2
            for attempt in range(1, max_attempts + 1):
                clip, script_text, final_hook_text = extract_clip(
                    source_video, segment, short_folder, i,
                    make_vertical=make_vertical,
                    preview_mode=preview_mode
                )
                if clip:
                    break  # Success, exit retry loop
                elif attempt < max_attempts:
                    print(f"   🔄 Retrying extraction (attempt {attempt + 1}/{max_attempts})...")
                    import time
                    time.sleep(2)  # Brief pause to allow memory recovery
        
        if clip or (preview_mode and script_text):
            if clip:
                extracted_clips.append(clip)
            
            all_scripts.append(script_text)
            
            # Save short in database with folder_path
            # In Preview Mode clip is None, but we have script_text
            if DB_AVAILABLE and video_id and not preview_mode:
                try:
                    # Use segment.hook_text as fallback when extract_clip doesn't return hook
                    db_hook_text = final_hook_text or segment.hook_text
                    
                    short_id = save_short(
                        video_id=video_id,
                        title=segment.name,
                        summary=f"Short extracted from {segment.start} to {segment.end}",
                        script=script_text,
                        start_time=segment.start,
                        end_time=segment.end,
                        output_filename=str(clip),
                        folder_path=str(short_folder),
                        hook_text=db_hook_text
                    )
                    print(f"   💾 Short saved to DB (ID: {short_id})")
                except Exception as e:
                    print(f"   ⚠️ Error saving short to DB: {e}")
    
    # Update complete video transcription in DB
    if DB_AVAILABLE and video_id and all_scripts:
        try:
            full_transcript = "\n\n".join(all_scripts)
            save_video(url=url, title=None, transcript=full_transcript)
        except Exception as e:
            print(f"   ⚠️ Error updating transcript in DB: {e}")
    
    # Clean up source video if not keeping
    if not keep_source:
        source_video.unlink()
        print(f"\n🗑️  Source video deleted")
    
    # Summary
    print("\n" + "=" * 60)
    print("✅ PROCESS COMPLETED")
    print("=" * 60)
    print(f"   📂 Clips saved to: {video_clips_dir}")
    if preview_mode:
         print(f"   👀 Preview completed for {len(all_scripts)} scripts.")
         
         # Interactive selection loop
         while True:
            print("\n" + "="*60)
            print("👇 SELECTION MENU")
            print("Enter the numbers of the shorts to render (comma-separated, e.g., 1,3)")
            print("Or type 'all' to render all, or 'q' to quit.")
            choice = input("👉 Your choice: ").strip().lower()
            
            if choice == 'q' or choice == 'quit' or not choice:
                print("👋 Exiting without rendering.")
                return extracted_clips
            
            selected_indices = []
            if choice == 'all':
                selected_indices = range(len(segments))
            else:
                try:
                    parts = choice.split(',')
                    for p in parts:
                        idx = int(p.strip()) - 1
                        if 0 <= idx < len(segments):
                            selected_indices.append(idx)
                        else:
                            print(f"⚠️  Invalid index ignored: {p}")
                except ValueError:
                    print("❌ Invalid input format. Please try again.")
                    continue
            
            if not selected_indices:
                print("⚠️  No valid shorts selected.")
                continue
                
            # Filter segments based on selection
            selected_segments = [segments[i] for i in selected_indices]
            print(f"\n🚀 Rendering {len(selected_segments)} selected shorts...")
            
            # Recursive call with preview_mode=False
            return process_video(
                url=url,
                segments=selected_segments,
                output_dir=output_dir,
                make_vertical=make_vertical,
                fast_mode=fast_mode,
                keep_source=keep_source,
                preview_mode=False # RENDER NOW
            )

    print(f"   📊 Clips extracted: {len(extracted_clips)}/{len(segments)}")
    if DB_AVAILABLE:
        print(f"   💾 Data saved to database")
    
    return extracted_clips


# =============================================================================
# CLI - Reads configuration from a JSON file
# =============================================================================

if __name__ == "__main__":
    
    if len(sys.argv) < 2:
        print("=" * 60)
        print("🎥 YOUTUBE SHORTS EXTRACTOR")
        print("=" * 60)
        print()
        print("Usage: python shorts_extractor.py <config.json>")
        print()
        print("JSON format:")
        print('  {')
        print('    "url": "https://www.youtube.com/watch?v=...",')
        print('    "segments": [')
        print('      {')
        print('        "name": "Title for DB and filename",')
        print('        "start": "MM:SS or HH:MM:SS",')
        print('        "end": "MM:SS or HH:MM:SS",')
        print('        "hook_text": "Opening hook text",')
        print('        "hook_duration": 4.0')
        print('      }')
        print('    ],')
        print('    "make_vertical": true,')
        print('    "fast_mode": false,')
        print('    "keep_source": true')
        print('  }')
        sys.exit(1)
    
    config_path = Path(sys.argv[1])
    if not config_path.exists():
        print(f"❌ Config file not found: {config_path}")
        sys.exit(1)
    
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    
    VIDEO_URL = config["url"]
    SEGMENTS = [
        Segment(
            name=seg["name"],
            start=seg["start"],
            end=seg["end"],
            hook_text=seg.get("hook_text"),
            hook_duration=seg.get("hook_duration", 4.0)
        )
        for seg in config["segments"]
    ]
    
    OUTPUT_DIR = Path(config.get("output_dir", str(Path(__file__).parent / "output")))
    MAKE_VERTICAL = config.get("make_vertical", True)
    FAST_MODE = config.get("fast_mode", False)
    KEEP_SOURCE = config.get("keep_source", True)
    PREVIEW_MODE = config.get("preview_mode", False)
    RESUME_MODE = config.get("resume_mode", False)
    
    print(f"📄 Loaded {len(SEGMENTS)} segments from: {config_path.name}")
    
    process_video(
        url=VIDEO_URL,
        segments=SEGMENTS,
        output_dir=OUTPUT_DIR,
        make_vertical=MAKE_VERTICAL,
        fast_mode=FAST_MODE,
        keep_source=KEEP_SOURCE,
        preview_mode=PREVIEW_MODE,
        resume_mode=RESUME_MODE
    )

