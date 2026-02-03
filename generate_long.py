"""
Generate Long Videos from Shorts
================================
Creates 10-minute long versions of each short.
Same start timestamp, extended to ~10 minutes.
Format: vertical 9:16 (same as shorts).

Usage:
    python generate_long.py
"""

from pathlib import Path
from database import (
    get_all_videos, get_shorts_by_video, save_long_video,
    get_connection
)
from shorts_extractor import (
    Segment, extract_clip_with_subtitles, time_to_seconds
)


def add_minutes_to_time(time_str: str, minutes: int) -> str:
    """Add minutes to a MM:SS or HH:MM:SS timestamp."""
    seconds = time_to_seconds(time_str)
    new_seconds = int(seconds + (minutes * 60))
    
    hours = new_seconds // 3600
    remaining = new_seconds % 3600
    mins = remaining // 60
    secs = remaining % 60
    
    if hours > 0:
        return f"{hours}:{mins:02d}:{secs:02d}"
    else:
        return f"{mins}:{secs:02d}"


def generate_long_for_short(short: dict, source_video: Path, output_base: Path) -> Path:
    """Generate a 10-minute long video for a single short."""
    
    short_id = short['id']
    title = short['title']
    start_time = short['start_time']
    short_folder = short.get('folder_path', '')
    
    # Long = start_time + 10 minutes
    long_end = add_minutes_to_time(start_time, 10)
    
    print(f"\n📹 Generando Long para: {title}")
    print(f"   Start: {start_time} → End: {long_end} (10 min)")
    
    # Create output directory
    if short_folder:
        long_dir = Path(short_folder) / "long"
    else:
        long_dir = output_base / title.replace(" ", "_") / "long"
    
    long_dir.mkdir(parents=True, exist_ok=True)
    
    # Create segment
    segment = Segment(
        start=start_time,
        end=long_end,
        name=f"{title}_LONG"
    )
    
    # Extract clip with subtitles (vertical format)
    output_file, script = extract_clip_with_subtitles(
        source_video=source_video,
        segment=segment,
        output_dir=long_dir,
        clip_index=1,
        make_vertical=True,
        add_subtitles=True,
        subtitle_style="modern",
        language="es"
    )
    
    # Calculate duration
    start_sec = time_to_seconds(start_time)
    end_sec = time_to_seconds(long_end)
    duration = int(end_sec - start_sec)
    
    # Save to database
    long_id = save_long_video(
        short_id=short_id,
        title=f"{title} - Long",
        summary=f"Versión extendida (10 min) del short '{title}'",
        script=script,
        duration_seconds=duration,
        output_filename=str(output_file)
    )
    
    print(f"   ✅ Long guardado: {output_file}")
    print(f"   📊 ID en BD: {long_id}")
    
    return output_file


def main():
    print("=" * 60)
    print("🎬 GENERADOR DE VIDEOS LONG (10 min)")
    print("=" * 60)
    
    videos = get_all_videos()
    
    if not videos:
        print("❌ No hay videos en la base de datos")
        return
    
    for video in videos:
        video_id = video['id']
        video_title = video.get('title', 'Video')
        clips_folder = video.get('clips_folder', '')
        
        print(f"\n📺 Procesando video: {video_title}")
        
        shorts = get_shorts_by_video(video_id)
        
        if not shorts:
            print("   ⚠️ No hay shorts para este video")
            continue
        
        print(f"   📊 Shorts encontrados: {len(shorts)}")
        
        # Find source video
        source_video = Path("output/source_video.mp4")
        if not source_video.exists() and clips_folder:
            possible_source = Path(clips_folder).parent / "source_video.mp4"
            if possible_source.exists():
                source_video = possible_source
        
        if not source_video.exists():
            print(f"   ⚠️ No se encontró el video fuente en: {source_video}")
            continue
        
        print(f"   📂 Video fuente: {source_video}")
        
        output_base = Path(clips_folder) if clips_folder else Path("output/clips")
        
        # Generate long for each short
        for short in shorts:
            try:
                generate_long_for_short(short, source_video, output_base)
            except Exception as e:
                print(f"   ❌ Error generando Long para {short['title']}: {e}")
    
    print("\n" + "=" * 60)
    print("✅ GENERACIÓN DE LONG VIDEOS COMPLETADA")
    print("=" * 60)


if __name__ == "__main__":
    main()
