"""
Test de subtítulos usando el video ya descargado.
"""
from pathlib import Path
from shorts_extractor import (
    Segment, 
    time_to_seconds, 
    transcribe_audio, 
    create_srt_file,
    extract_clip_with_subtitles
)

# Usar el video ya descargado en output
source_video = Path("output/source_video.mp4")
output_dir = Path("output/clips_test")
output_dir.mkdir(parents=True, exist_ok=True)

segment = Segment("11:29", "11:43", "Test_Subtitulos_v2")

clip = extract_clip_with_subtitles(
    source_video=source_video,
    segment=segment,
    output_dir=output_dir,
    clip_index=1,
    make_vertical=False,
    add_subtitles=True,
    subtitle_style="modern",
    language="es"
)

print(f"\n✅ Clip generado: {clip}")
