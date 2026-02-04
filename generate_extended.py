"""
Generate Extended Videos from Shorts
====================================
Creates 3-minute extended versions of each short.
Same start timestamp, extended to ~3 minutes.
Extended in vertical format (3 min short).

Usage:
    python generate_extended.py
"""

from pathlib import Path
from database import (
    get_all_shorts, get_shorts_by_video, get_all_videos,
    save_extended_video, update_short_folder
)
from shorts_extractor import (
    Segment, download_video, extract_clip_with_subtitles,
    time_to_seconds
)


def seconds_to_time(seconds: int) -> str:
    """Convert seconds to MM:SS format."""
    minutes = seconds // 60
    secs = seconds % 60
    return f"{minutes}:{secs:02d}"


def add_minutes_to_time(time_str: str, minutes_to_add: int) -> str:
    """Add minutes to a MM:SS or HH:MM:SS timestamp."""
    seconds = time_to_seconds(time_str)
    new_seconds = int(seconds + (minutes_to_add * 60))
    
    hours = new_seconds // 3600
    remaining = new_seconds % 3600
    mins = remaining // 60
    secs = remaining % 60
    
    if hours > 0:
        return f"{hours}:{mins:02d}:{secs:02d}"
    else:
        return f"{mins}:{secs:02d}"


def extract_hook_from_script(script: str, max_words: int = 15) -> str:
    """
    Extracts the hook text from the short's script.
    The hook is approximately the first 15 words (~4 seconds of speech).
    """
    if not script:
        return None
    
    words = script.split()
    if len(words) <= max_words:
        return script.strip()
    
    return " ".join(words[:max_words]).strip()


def generate_extended_for_short(short: dict, video_url: str, source_video: Path, output_base: Path):
    """Generate extended version for a single short."""
    
    short_id = short['id']
    title = short['title']
    start_time = short['start_time']
    script = short.get('script', '')
    
    # Extended = start_time + 3 minutes
    extended_end = add_minutes_to_time(start_time, 3)
    
    print(f"\n📹 Generating Extended for: {title}")
    print(f"   Start: {start_time} → End: {extended_end} (3 min)")
    
    # Priority: Hook stored in DB > Hook extracted from script
    hook_text = short.get('hook_text')
    if not hook_text:
        hook_text = extract_hook_from_script(script)
        
    if hook_text:
        print(f"   🎣 Using hook from original short: \"{hook_text[:50]}...\"")
    
    # Create segment with the same hook_text as the original short
    segment = Segment(
        start=start_time,
        end=extended_end,
        name=f"{title}_EXTENDED",
        hook_duration=4.0,
        hook_text=hook_text  # Use the same hook as the original short
    )
    
    # Output directory for this short's extended version
    short_folder = short.get('folder_path', '')
    if short_folder:
        extended_dir = Path(short_folder) / "extended"
    else:
        extended_dir = output_base / title.replace(" ", "_") / "extended"
    
    extended_dir.mkdir(parents=True, exist_ok=True)
    
    # Extract the extended clip (with hook for extended as well)
    output_file, script, _ = extract_clip_with_subtitles(
        source_video=source_video,
        segment=segment,
        output_dir=extended_dir,
        clip_index=1,
        make_vertical=True,  # Extended in vertical format (3 min short)
        add_subtitles=True,
        subtitle_style="modern",
        language="es",
        add_hook=True  # Extended also uses hook like shorts
    )
    
    # Calculate duration
    duration = time_to_seconds(extended_end) - time_to_seconds(start_time)
    
    # Save to database
    extended_id = save_extended_video(
        short_id=short_id,
        title=f"{title} - Extended",
        summary=f"Extended version (3 min) of short '{title}'",
        script=script,
        duration_seconds=duration,
        output_filename=str(output_file)
    )
    
    print(f"   ✅ Extended saved: {output_file}")
    print(f"   📊 DB ID: {extended_id}")
    
    return extended_id


def main():
    print("=" * 60)
    print("🎬 EXTENDED VIDEO GENERATOR")
    print("=" * 60)
    
    # Get all videos and shorts
    videos = get_all_videos()
    
    if not videos:
        print("❌ No videos in database")
        return
    
    for video in videos:
        video_id = video['id']
        video_url = video['url']
        video_title = video.get('title', 'Video')
        clips_folder = video.get('clips_folder', '')
        
        print(f"\n📺 Processing video: {video_title}")
        print(f"   URL: {video_url}")
        
        shorts = get_shorts_by_video(video_id)
        
        if not shorts:
            print("   ⚠️ No shorts for this video")
            continue
        
        print(f"   📊 Shorts found: {len(shorts)}")
        
        # Find source video file
        if clips_folder:
            source_dir = Path(clips_folder).parent
        else:
            source_dir = Path("output")
        
        # Look for the source video
        source_video = None
        
        # First check for source_video.mp4 directly in output folder
        output_dir = Path("output")
        direct_source = output_dir / "source_video.mp4"
        if direct_source.exists():
            source_video = direct_source
        else:
            # Search in source_dir
            for ext in ["mp4", "webm", "mkv"]:
                candidates = list(source_dir.glob(f"source*.{ext}")) + list(source_dir.glob(f"*full*.{ext}"))
                if candidates:
                    source_video = candidates[0]
                    break
        
        if not source_video or not source_video.exists():
            print(f"   ⚠️ Source file not found in {source_dir}")
            print("   🔄 Downloading video...")
            
            download_dir = source_dir / "source"
            download_dir.mkdir(parents=True, exist_ok=True)
            source_video = download_video(video_url, download_dir)
        
        print(f"   📂 Source video: {source_video}")
        
        # Process each short
        output_base = Path(clips_folder) if clips_folder else Path("output/extended")
        
        for short in shorts:
            if short['title'] not in ["Sin Altar No Hay Pan", "Necesidad de Herejias"]:
                continue
            try:
                generate_extended_for_short(short, video_url, source_video, output_base)
            except Exception as e:
                print(f"   ❌ Error processing {short['title']}: {e}")
                continue
    
    print("\n" + "=" * 60)
    print("✅ EXTENDED GENERATION COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    main()
