"""
Script para procesar clips uno a uno con el modelo small de Whisper.
Esto evita problemas de RAM al liberar memoria después de cada clip.
"""
import subprocess
import sys
import gc

# Lista de segmentos a procesar
segments = [
    {"index": 1, "start": "10:37", "end": "11:20", "name": "Iglesia_Catolica_Primitiva"},
    {"index": 2, "start": "12:58", "end": "13:45", "name": "Doctrinas_Apostolicas_Son_Catolicas"},
    {"index": 3, "start": "21:43", "end": "22:25", "name": "Ignacio_Contra_Herejes"},
    {"index": 4, "start": "24:26", "end": "25:05", "name": "No_Herejia_Entre_Ustedes"},
    {"index": 5, "start": "27:37", "end": "28:20", "name": "Herejia_Merece_Infierno"},
    {"index": 6, "start": "31:53", "end": "32:35", "name": "Herejes_No_Heredan_Reino"},
    {"index": 7, "start": "43:07", "end": "43:50", "name": "Fe_Y_Caridad_Para_Salvarse"},
    {"index": 8, "start": "55:22", "end": "56:05", "name": "Fuera_Altar_Sin_Pan_De_Dios"},
]

VIDEO_URL = "https://www.youtube.com/watch?v=JxAdV9YVbsY"

def process_single_clip(segment):
    """Procesa un solo clip en un subproceso separado para liberar memoria después."""
    
    script = f'''
import sys
sys.path.insert(0, ".")
from shorts_extractor import Segment, process_video
from pathlib import Path

segment = Segment("{segment['start']}", "{segment['end']}", "{segment['name']}")
process_video(
    url="{VIDEO_URL}",
    segments=[segment],
    output_dir=Path("output"),
    make_vertical=True,
    fast_mode=False,
    add_subtitles=True,
    subtitle_style="bold",
    language="es",
    keep_source=True
)
'''
    
    print(f"\n{'='*60}")
    print(f"📹 PROCESANDO CLIP {segment['index']}/8: {segment['name']}")
    print(f"{'='*60}")
    
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=False,
        text=True
    )
    
    # Forzar recolección de basura
    gc.collect()
    
    return result.returncode == 0

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=1, help="Clip inicial (1-8)")
    parser.add_argument("--end", type=int, default=8, help="Clip final (1-8)")
    args = parser.parse_args()
    
    print(f"\n🎬 Procesando clips {args.start} a {args.end} con modelo Whisper 'small'")
    print(f"   Cada clip se procesa por separado para evitar problemas de RAM\n")
    
    for seg in segments:
        if args.start <= seg['index'] <= args.end:
            success = process_single_clip(seg)
            if not success:
                print(f"❌ Error en clip {seg['index']}")
            else:
                print(f"✅ Clip {seg['index']} completado\n")
    
    print("\n" + "="*60)
    print("✅ PROCESO FINALIZADO")
    print("="*60)
