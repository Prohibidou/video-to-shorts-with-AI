"""
Script para reorganizar clips existentes en la nueva estructura de carpetas.

Estructura:
output/
└── clips/
    └── [Video Title - VideoID]/
        └── 01_Nombre_Short/
            ├── short.mp4           <- <1 min
            ├── extended/           <- 3 min (carpeta vacía por ahora)
            └── long/               <- 10+ min (carpeta vacía por ahora)
"""
import os
import shutil
from pathlib import Path
from database import get_all_videos, get_shorts_by_video, update_short_folder

OUTPUT_DIR = Path(__file__).parent / "output" / "clips"


def sanitize_folder_name(name: str) -> str:
    """Remove invalid characters for folder names."""
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        name = name.replace(char, '_')
    return name[:100]  # Limitar longitud


def get_video_id_from_url(url: str) -> str:
    """Extract video ID from YouTube URL."""
    if 'v=' in url:
        return url.split('v=')[1].split('&')[0]
    elif 'youtu.be/' in url:
        return url.split('youtu.be/')[1].split('?')[0]
    return url[-11:]


def reorganize_clips():
    """Reorganize existing clips into the new folder structure."""
    videos = get_all_videos()
    
    if not videos:
        print("No hay videos en la base de datos.")
        return
    
    for video in videos:
        video_id = video['id']
        url = video['url']
        title = video['title'] or 'Sin_Titulo'
        
        # Crear nombre de carpeta del video
        yt_id = get_video_id_from_url(url)
        video_folder_name = sanitize_folder_name(f"{title} - {yt_id}")
        video_folder = OUTPUT_DIR / video_folder_name
        
        print(f"\n📺 Procesando video: {title}")
        print(f"   Carpeta: {video_folder}")
        
        # Obtener shorts del video
        shorts = get_shorts_by_video(video_id)
        
        if not shorts:
            print("   ⚠️ No hay shorts para este video")
            continue
        
        for i, short in enumerate(shorts, 1):
            short_id = short['id']
            short_title = short['title'] or f'short_{i}'
            short_filename = short.get('output_filename', '')
            
            # Crear carpeta del short
            short_folder_name = f"{i:02d}_{sanitize_folder_name(short_title)}"
            short_folder = video_folder / short_folder_name
            
            # Crear estructura de subcarpetas
            short_folder.mkdir(parents=True, exist_ok=True)
            (short_folder / "extended").mkdir(exist_ok=True)
            (short_folder / "long").mkdir(exist_ok=True)
            
            print(f"   📁 {short_folder_name}/")
            
            # Buscar y mover el archivo del short
            if short_filename:
                # Buscar en la ubicación actual
                old_path = OUTPUT_DIR / short_filename
                if old_path.exists():
                    new_path = short_folder / "short.mp4"
                    if not new_path.exists():
                        shutil.copy2(old_path, new_path)
                        print(f"      ✓ Copiado: {short_filename} -> short.mp4")
                    else:
                        print(f"      ℹ Ya existe: short.mp4")
                else:
                    # Buscar en otras ubicaciones
                    for mp4 in OUTPUT_DIR.glob("*.mp4"):
                        if short_title.replace(' ', '_') in mp4.name or short_filename in mp4.name:
                            new_path = short_folder / "short.mp4"
                            if not new_path.exists():
                                shutil.copy2(mp4, new_path)
                                print(f"      ✓ Copiado: {mp4.name} -> short.mp4")
                            break
            
            # Actualizar ruta en la base de datos
            update_short_folder(short_id, str(short_folder))
        
        # Actualizar clips_folder del video
        from database import save_video
        save_video(url, clips_folder=str(video_folder))
    
    print("\n✅ Reorganización completada!")
    print("   Estructura de carpetas actualizada")
    print("   Base de datos actualizada con rutas")


if __name__ == "__main__":
    reorganize_clips()
