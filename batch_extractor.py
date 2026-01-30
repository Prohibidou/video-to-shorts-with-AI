"""
Batch Shorts Extractor
======================
Lee segmentos desde un archivo JSON y extrae todos los clips
con subtítulos automáticos.

Uso:
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
    """Carga la configuración de segmentos desde un archivo JSON."""
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    url = data.get("video_url")
    if not url:
        raise ValueError("El archivo JSON debe tener 'video_url'")
    
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
        description="Extrae múltiples shorts de YouTube desde un archivo JSON"
    )
    parser.add_argument(
        "json_file",
        type=Path,
        help="Archivo JSON con la URL y los segmentos"
    )
    parser.add_argument(
        "--vertical",
        action="store_true",
        help="Convertir a formato vertical 9:16 para Shorts"
    )
    parser.add_argument(
        "--fast",
        action="store_true",
        help="Modo rápido (sin subtítulos, corte instantáneo)"
    )
    parser.add_argument(
        "--no-subtitles",
        action="store_true",
        help="Desactivar subtítulos automáticos"
    )
    parser.add_argument(
        "--style",
        type=str,
        default="modern",
        choices=["modern", "bold", "minimal"],
        help="Estilo de subtítulos (default: modern)"
    )
    parser.add_argument(
        "--lang",
        type=str,
        default="es",
        help="Idioma del video para transcripción (default: es)"
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=None,
        help="Directorio de salida (default: ./output)"
    )
    parser.add_argument(
        "--no-keep-source",
        action="store_true",
        help="Eliminar el video fuente después de extraer los clips"
    )
    
    args = parser.parse_args()
    
    if not args.json_file.exists():
        print(f"❌ No se encontró el archivo: {args.json_file}")
        sys.exit(1)
    
    # Cargar configuración
    url, segments = load_segments_from_json(args.json_file)
    
    print(f"📄 Cargados {len(segments)} segmentos desde {args.json_file.name}")
    
    # Determinar directorio de salida
    output_dir = args.output or Path("./output")
    
    # Determinar si agregar subtítulos
    add_subtitles = not args.no_subtitles and not args.fast
    
    # Procesar
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
