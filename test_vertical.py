"""
Test de formato vertical para YouTube Shorts (9:16, 1080x1920).
"""
from pathlib import Path
from shorts_extractor import Segment, extract_clip_with_subtitles

# Usar el video ya descargado
source_video = Path("output/source_video.mp4")
output_dir = Path("output/shorts_vertical")
output_dir.mkdir(parents=True, exist_ok=True)

segment = Segment("11:29", "11:43", "Short_Vertical_Test")

print("🎬 Generando SHORT en formato VERTICAL (9:16)...")

clip = extract_clip_with_subtitles(
    source_video=source_video,
    segment=segment,
    output_dir=output_dir,
    clip_index=1,
    make_vertical=True,  # Formato 9:16 para Shorts
    add_subtitles=True,
    subtitle_style="modern",
    language="es"
)

if clip:
    print(f"\n✅ Short generado: {clip}")
    print(f"📐 Formato: 1080x1920 (9:16 vertical)")
else:
    print("\n❌ Error generando el short")
