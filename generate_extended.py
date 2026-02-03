"""
Generate Extended Videos from Shorts
====================================
Creates 3-minute extended versions of each short.
Same start timestamp, extended to ~3 minutes.
Extended en formato vertical (short de 3 min).

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


def generate_extended_for_short(short: dict, video_url: str, source_video: Path, output_base: Path):
    """Generate extended version for a single short."""
    
    short_id = short['id']
    title = short['title']
    start_time = short['start_time']
    
    # Extended = start_time + 3 minutes
    extended_end = add_minutes_to_time(start_time, 3)
    
    print(f"\n📹 Generando Extended para: {title}")
    print(f"   Start: {start_time} → End: {extended_end} (3 min)")
    
    # Create segment
    segment = Segment(
        start=start_time,
        end=extended_end,
        name=f"{title}_EXTENDED"
    )
    
    # Output directory for this short's extended version
    short_folder = short.get('folder_path', '')
    if short_folder:
        extended_dir = Path(short_folder) / "extended"
    else:
        extended_dir = output_base / title.replace(" ", "_") / "extended"
    
    extended_dir.mkdir(parents=True, exist_ok=True)
    
    # Extract the extended clip
    output_file, script = extract_clip_with_subtitles(
        source_video=source_video,
        segment=segment,
        output_dir=extended_dir,
        clip_index=1,
        make_vertical=True,  # Extended en formato vertical (short de 3 min)
        add_subtitles=True,
        subtitle_style="modern",
        language="es"
    )
    
    # Calculate duration
    duration = time_to_seconds(extended_end) - time_to_seconds(start_time)
    
    # Save to database
    extended_id = save_extended_video(
        short_id=short_id,
        title=f"{title} - Extended",
        summary=f"Versión extendida (3 min) del short '{title}'",
        script=script,
        duration_seconds=duration,
        output_filename=str(output_file)
    )
    
    print(f"   ✅ Extended guardado: {output_file}")
    print(f"   📊 ID en BD: {extended_id}")
    
    return extended_id


def main():
    print("=" * 60)
    print("🎬 GENERADOR DE VIDEOS EXTENDED")
    print("=" * 60)
    
    # Get all videos and shorts
    videos = get_all_videos()
    
    if not videos:
        print("❌ No hay videos en la base de datos")
        return
    
    for video in videos:
        video_id = video['id']
        video_url = video['url']
        video_title = video.get('title', 'Video')
        clips_folder = video.get('clips_folder', '')
        
        print(f"\n📺 Procesando video: {video_title}")
        print(f"   URL: {video_url}")
        
        shorts = get_shorts_by_video(video_id)
        
        if not shorts:
            print("   ⚠️ No hay shorts para este video")
            continue
        
        print(f"   📊 Shorts encontrados: {len(shorts)}")
        
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
            print(f"   ⚠️ Archivo fuente no encontrado en {source_dir}")
            print("   🔄 Descargando video...")
            
            download_dir = source_dir / "source"
            download_dir.mkdir(parents=True, exist_ok=True)
            source_video = download_video(video_url, download_dir)
        
        print(f"   📂 Video fuente: {source_video}")
        
        # Process each short
        output_base = Path(clips_folder) if clips_folder else Path("output/extended")
        
        for short in shorts:
            try:
                generate_extended_for_short(short, video_url, source_video, output_base)
            except Exception as e:
                print(f"   ❌ Error procesando {short['title']}: {e}")
                continue
    
    print("\n" + "=" * 60)
    print("✅ GENERACIÓN DE EXTENDED COMPLETADA")
    print("=" * 60)


if __name__ == "__main__":
    main()
