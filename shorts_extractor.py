"""
YouTube Shorts Extractor
========================
Herramienta para extraer múltiples clips de un video de YouTube
basándose en timestamps específicos, con subtítulos automáticos.

Uso:
    python shorts_extractor.py

Requisitos:
    - yt-dlp (pip install yt-dlp)
    - faster-whisper (pip install faster-whisper)
    - ffmpeg (debe estar en el PATH del sistema)
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


@dataclass
class Segment:
    """Representa un segmento de video a extraer."""
    start: str          # Formato: "MM:SS" o "HH:MM:SS"
    end: str            # Formato: "MM:SS" o "HH:MM:SS"
    name: str           # Nombre descriptivo del clip
    hook_duration: float = 4.0  # Duración del gancho en segundos
    hook_text: str = None       # Texto del gancho (opcional, si None se genera automáticamente)
    

def time_to_seconds(time_str: str) -> float:
    """Convierte tiempo en formato MM:SS o HH:MM:SS a segundos."""
    parts = time_str.strip().split(":")
    if len(parts) == 2:
        minutes, seconds = parts
        return int(minutes) * 60 + float(seconds)
    elif len(parts) == 3:
        hours, minutes, seconds = parts
        return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    else:
        raise ValueError(f"Formato de tiempo inválido: {time_str}")


def seconds_to_srt_time(seconds: float) -> str:
    """Convierte segundos a formato SRT (HH:MM:SS,mmm)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def get_video_title(url: str) -> str:
    """Obtiene el título real del video de YouTube usando yt-dlp."""
    try:
        result = subprocess.run(
            ["yt-dlp", "--get-title", url],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception as e:
        print(f"   ⚠️ No se pudo obtener título: {e}")
    return None


def download_video(url: str, output_dir: Path) -> Path:
    """Descarga el video de YouTube."""
    output_template = str(output_dir / "source_video.%(ext)s")
    
    print(f"\n📥 Descargando video...")
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
        print(f"❌ Error descargando: {result.stderr}")
        sys.exit(1)
    
    # Encontrar el archivo descargado
    for file in output_dir.glob("source_video.*"):
        print(f"   ✅ Descargado: {file.name}")
        return file
    
    raise FileNotFoundError("No se encontró el video descargado")


def transcribe_audio(video_path: Path, language: str = "es", max_words_per_line: int = 4) -> list[dict]:
    """
    Transcribe el audio del video usando faster-whisper.
    Retorna una lista de segmentos cortos (máximo max_words_per_line palabras cada uno).
    """
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        print("   ⚠️  faster-whisper no instalado. Instalando...")
        subprocess.run([sys.executable, "-m", "pip", "install", "faster-whisper"], 
                      capture_output=True)
        from faster_whisper import WhisperModel
    
    print(f"   🎤 Transcribiendo audio...")
    
    # Usar modelo tiny para reducir uso de memoria
    model = WhisperModel("tiny", device="cpu", compute_type="int8")
    
    segments, info = model.transcribe(
        str(video_path),
        language=language,
        word_timestamps=True,
        vad_filter=True
    )
    
    # Recopilar todas las palabras con sus timestamps
    all_words = []
    for segment in segments:
        if segment.words:
            for word in segment.words:
                all_words.append({
                    "start": word.start,
                    "end": word.end,
                    "text": word.word.strip()
                })
    
    # Agrupar palabras en chunks pequeños (máximo max_words_per_line palabras)
    result = []
    current_chunk = []
    chunk_start = None
    
    for word in all_words:
        if chunk_start is None:
            chunk_start = word["start"]
        
        current_chunk.append(word["text"])
        
        # Crear nuevo segmento cuando alcanzamos el límite de palabras
        if len(current_chunk) >= max_words_per_line:
            result.append({
                "start": chunk_start,
                "end": word["end"],
                "text": " ".join(current_chunk)
            })
            current_chunk = []
            chunk_start = None
    
    # Añadir el último chunk si queda algo
    if current_chunk:
        result.append({
            "start": chunk_start,
            "end": all_words[-1]["end"],
            "text": " ".join(current_chunk)
        })
    
    print(f"   ✅ Transcripción completada ({len(result)} fragmentos)")

    # Reemplazar "protestante/protestantes" por "protestantes (Evangelicos)" en los subtítulos
    # y eliminar acentos
    import unicodedata
    import re
    
    def remove_accents(text):
        return ''.join(
            c for c in unicodedata.normalize('NFD', text)
            if unicodedata.category(c) != 'Mn'
        )
    
    for segment in result:
        # Si el texto contiene "protestante" o "protestantes", reemplazar TODO el texto
        # con solo "protestantes (Evangelicos)" - sin ninguna otra palabra
        if re.search(r'\bprotestantes?\b', segment["text"], flags=re.IGNORECASE):
            segment["text"] = "protestantes (Evangelicos)"
        else:
            segment["text"] = remove_accents(segment["text"])

    return result


def extract_hook_text(transcription: list[dict], hook_duration: float) -> tuple[str, float]:
    """
    Extrae el texto de los primeros segundos para usar como gancho.
    Retorna (texto_del_gancho, tiempo_final_del_gancho).
    El tiempo final es el end del último segmento incluido en el gancho.
    """
    hook_words = []
    hook_end_time = hook_duration
    
    for seg in transcription:
        # Incluir segmentos que empiezan antes del hook_duration
        if seg["start"] < hook_duration:
            hook_words.append(seg["text"])
            hook_end_time = max(hook_end_time, seg["end"])
        else:
            break
    
    return " ".join(hook_words), hook_end_time



def create_srt_file(transcription: list[dict], output_path: Path) -> Path:
    """Crea un archivo SRT a partir de la transcripción."""
    with open(output_path, 'w', encoding='utf-8') as f:
        for i, segment in enumerate(transcription, 1):
            start_time = seconds_to_srt_time(segment["start"])
            end_time = seconds_to_srt_time(segment["end"])
            text = segment["text"]
            
            f.write(f"{i}\n")
            f.write(f"{start_time} --> {end_time}\n")
            f.write(f"{text}\n\n")
    
    return output_path


def create_ass_file(transcription: list[dict], output_path: Path, 
                    font_size: int = 18, style: str = "modern") -> Path:
    """
    Crea un archivo ASS con estilo de subtítulos para Shorts.
    Estilos disponibles: "modern", "bold", "minimal"
    """
    
    # Definir estilos
    styles = {
        "modern": {
            "font": "Arial",
            "size": font_size,
            "primary_color": "&H00FFFFFF",  # Blanco
            "outline_color": "&H00000000",   # Negro
            "back_color": "&H80000000",      # Negro semi-transparente
            "bold": 1,
            "outline": 2,
            "shadow": 1,
            "margin_v": 50
        },
        "bold": {
            "font": "Impact",
            "size": font_size + 4,
            "primary_color": "&H00FFFFFF",
            "outline_color": "&H00000000",
            "back_color": "&H00000000",
            "bold": 1,
            "outline": 3,
            "shadow": 0,
            "margin_v": 60
        },
        "minimal": {
            "font": "Helvetica",
            "size": font_size,
            "primary_color": "&H00FFFFFF",
            "outline_color": "&H00000000",
            "back_color": "&H00000000",
            "bold": 0,
            "outline": 1,
            "shadow": 2,
            "margin_v": 40
        }
    }
    
    s = styles.get(style, styles["modern"])
    
    # Cabecera ASS
    header = f"""[Script Info]
Title: Auto Subtitles
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{s['font']},{s['size']},{s['primary_color']},&H000000FF,{s['outline_color']},{s['back_color']},{s['bold']},0,0,0,100,100,0,0,1,{s['outline']},{s['shadow']},2,20,20,{s['margin_v']},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    
    def seconds_to_ass_time(seconds: float) -> str:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours}:{minutes:02d}:{secs:05.2f}"
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(header)
        
        for segment in transcription:
            start = seconds_to_ass_time(segment["start"])
            end = seconds_to_ass_time(segment["end"])
            text = segment["text"].replace("\n", "\\N")
            
            f.write(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}\n")
    
    return output_path


def extract_clip_with_subtitles(
    source_video: Path,
    segment: Segment,
    output_dir: Path,
    clip_index: int,
    make_vertical: bool = False,
    add_subtitles: bool = True,
    subtitle_style: str = "modern",
    language: str = "es",
    add_hook: bool = True  # Agregar texto de gancho fijo en los primeros segundos
) -> Tuple[Optional[Path], str]:
    """Extrae un clip del video fuente con subtítulos automáticos.
    Retorna (path_archivo, script_texto).
    """
    
    start_seconds = time_to_seconds(segment.start)
    end_seconds = time_to_seconds(segment.end)
    duration = end_seconds - start_seconds
    
    # Sanitizar nombre del archivo
    safe_name = "".join(c if c.isalnum() or c in "- _" else "_" for c in segment.name)
    temp_clip = output_dir / f"temp_clip_{clip_index:02d}.mp4"
    output_file = output_dir / f"clip_{clip_index:02d}_{safe_name}.mp4"
    
    print(f"\n🎬 Extrayendo clip {clip_index}: {segment.name}")
    print(f"   ⏱️  {segment.start} → {segment.end} (duración: {duration:.1f}s)")
    
    # Paso 1: Extraer clip temporal (sin subtítulos)
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
    
    # FFmpeg escribe a stderr incluso en ejecuciones exitosas, así que verificamos el archivo
    subprocess.run(cmd_extract, capture_output=True, text=True)
    if not temp_clip.exists():
        print(f"   ❌ Error: No se pudo crear el clip temporal")
        return None
    
    if not add_subtitles:
        # Si no queremos subtítulos, renombrar y retornar
        temp_clip.rename(output_file)
        print(f"   ✅ Guardado: {output_file.name}")
        return output_file, ""
    
    # Paso 2: Transcribir el clip (máximo 2 palabras por fragmento = 1 sola línea)
    transcription = transcribe_audio(temp_clip, language, max_words_per_line=2)
    
    if not transcription:
        print(f"   ⚠️  No se detectó audio/voz. Guardando sin subtítulos.")
        temp_clip.rename(output_file)
        return output_file, ""
    
    # Determinar hook (gancho) para los primeros segundos
    hook_duration = getattr(segment, 'hook_duration', 4.0)
    hook_text = getattr(segment, 'hook_text', None)
    hook_end_time = hook_duration
    
    if add_hook and not hook_text:
        # Extraer texto del gancho automáticamente de la transcripción
        hook_text, hook_end_time = extract_hook_text(transcription, hook_duration)
        print(f"   🎣 Gancho detectado: \"{hook_text[:50]}...\" (0-{hook_end_time:.1f}s)")
    elif add_hook and hook_text:
        print(f"   🎣 Gancho manual: \"{hook_text[:50]}...\"")
    
    
    # Paso 3: Crear archivo SRT con gancho incluido como primer subtítulo
    subs_file = output_dir / f"subs_{clip_index:02d}.srt"
    
    with open(subs_file, 'w', encoding='utf-8') as f:
        subtitle_index = 1
        
        # Agregar gancho como primer subtítulo (texto completo, fijo durante ~4 segundos)
        if add_hook and hook_text:
            # Dividir en líneas si es muy largo (máximo ~35 caracteres por línea)
            words = hook_text.split()
            lines = []
            current_line = []
            for word in words:
                current_line.append(word)
                if len(" ".join(current_line)) > 35:
                    lines.append(" ".join(current_line))
                    current_line = []
            if current_line:
                lines.append(" ".join(current_line))
            formatted_hook = "\n".join(lines)
            
            f.write(f"{subtitle_index}\n")
            f.write(f"00:00:00,000 --> {seconds_to_srt_time(hook_end_time)}\n")
            f.write(f"{formatted_hook}\n\n")
            subtitle_index += 1
        
        # Agregar subtítulos normales (después del gancho)
        for seg in transcription:
            # Skipear los que están dentro del período del gancho
            if add_hook and hook_text and seg["start"] < hook_end_time:
                continue
            
            start_time = seconds_to_srt_time(seg["start"])
            end_time = seconds_to_srt_time(seg["end"])
            text = seg["text"]
            
            f.write(f"{subtitle_index}\n")
            f.write(f"{start_time} --> {end_time}\n")
            f.write(f"{text}\n\n")
            subtitle_index += 1
    
    # Paso 4: Quemar subtítulos en el video
    print(f"   📝 Agregando subtítulos al video...")
    
    # Estilo de subtítulos para Shorts
    subtitle_style = (
        "FontName=Arial,"
        "FontSize=18,"
        "Bold=1,"
        "PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&H00000000,"
        "Outline=2,"
        "Shadow=1,"
        "MarginV=75,"
        "MarginL=30,"
        "MarginR=30,"
        "Alignment=2"
    )
    
    if make_vertical:
        # Formato vertical 9:16 con subtítulos
        filter_complex = (
            f"[0:v]scale=1080:1920:force_original_aspect_ratio=increase,"
            f"crop=1080:1920,boxblur=20:5[bg];"
            f"[0:v]scale=1080:-2:force_original_aspect_ratio=decrease[fg];"
            f"[bg][fg]overlay=(W-w)/2:(H-h)/2[v];"
            f"[v]subtitles='{subs_file.name}':force_style='{subtitle_style}'[outv]"
        )
        cmd_subs = [
            "ffmpeg", "-y",
            "-i", temp_clip.name,
            "-filter_complex", filter_complex,
            "-map", "[outv]",
            "-map", "0:a",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "128k",
            output_file.name
        ]
    else:
        # Mantener formato original con subtítulos quemados
        subtitle_filter = f"subtitles='{subs_file.name}':force_style='{subtitle_style}'"
        cmd_subs = [
            "ffmpeg", "-y",
            "-i", temp_clip.name,
            "-vf", subtitle_filter,
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "128k",
            output_file.name
        ]
    
    # Ejecutar FFmpeg desde el directorio del clip para evitar problemas con paths
    subprocess.run(cmd_subs, capture_output=True, text=True, cwd=str(output_dir))
    
    # Limpiar archivos temporales
    if temp_clip.exists():
        temp_clip.unlink()
    if subs_file.exists():
        subs_file.unlink()
    
    # Verificar si el archivo de salida se creó correctamente
    if not output_file.exists():
        print(f"   ❌ Error: No se pudo crear el video con subtítulos")
        return None, ""
    
    # Extraer texto completo del script
    script_text = " ".join([seg["text"] for seg in transcription])
    
    print(f"   ✅ Guardado: {output_file.name} (con subtítulos)")
    return output_file, script_text


def extract_clip_fast(
    source_video: Path,
    segment: Segment,
    output_dir: Path,
    clip_index: int
) -> Path:
    """
    Extrae un clip SIN re-encoding (instantáneo).
    Nota: Los cortes pueden no ser exactos al frame.
    No soporta subtítulos.
    """
    
    start_seconds = time_to_seconds(segment.start)
    end_seconds = time_to_seconds(segment.end)
    duration = end_seconds - start_seconds
    
    safe_name = "".join(c if c.isalnum() or c in "- _" else "_" for c in segment.name)
    output_file = output_dir / f"clip_{clip_index:02d}_{safe_name}.mp4"
    
    print(f"\n⚡ Extrayendo clip {clip_index} (modo rápido, sin subtítulos): {segment.name}")
    print(f"   ⏱️  {segment.start} → {segment.end}")
    
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start_seconds),
        "-i", str(source_video),
        "-t", str(duration),
        "-c", "copy",  # Sin re-encoding
        str(output_file)
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"   ❌ Error: {result.stderr[:200]}")
        return None
    
    print(f"   ✅ Guardado: {output_file.name}")
    return output_file


def process_video(
    url: str,
    segments: list[Segment],
    output_dir: Path,
    make_vertical: bool = False,
    fast_mode: bool = False,
    add_subtitles: bool = True,
    subtitle_style: str = "modern",
    language: str = "es",
    keep_source: bool = True
):
    """Procesa un video completo extrayendo todos los segmentos."""
    
    print("=" * 60)
    print("🎥 YOUTUBE SHORTS EXTRACTOR")
    print("=" * 60)
    
    if add_subtitles and fast_mode:
        print("⚠️  Nota: fast_mode desactiva subtítulos. Usando modo normal.")
        fast_mode = False
    
    # Crear directorio de salida
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Descargar video
    source_video = download_video(url, output_dir)
    
    # Obtener título real del video de YouTube
    video_title = get_video_title(url)
    if video_title:
        print(f"   📺 Título: {video_title}")
    
    # Crear carpeta para el video usando el título
    safe_video_title = "".join(c if c.isalnum() or c in "- _" else "_" for c in (video_title or "Video"))
    video_clips_dir = output_dir / "clips" / safe_video_title
    video_clips_dir.mkdir(parents=True, exist_ok=True)
    
    # Guardar video en base de datos
    video_id = None
    if DB_AVAILABLE:
        try:
            video_id = save_video(url=url, title=video_title, transcript=None)
            print(f"   💾 Video registrado en BD (ID: {video_id})")
        except Exception as e:
            print(f"   ⚠️ Error guardando video en BD: {e}")
    
    # Extraer cada segmento
    print(f"\n📋 Procesando {len(segments)} segmentos...")
    if add_subtitles:
        print(f"   📝 Subtítulos automáticos: ACTIVADOS (estilo: {subtitle_style})")
    
    extracted_clips = []
    all_scripts = []  # Para guardar transcripción completa del video
    
    for i, segment in enumerate(segments, 1):
        # Crear carpeta individual para este short
        safe_segment_name = "".join(c if c.isalnum() or c in "- _" else "_" for c in segment.name)
        short_folder = video_clips_dir / f"{i:02d}_{safe_segment_name}"
        short_folder.mkdir(parents=True, exist_ok=True)
        
        if fast_mode:
            clip = extract_clip_fast(source_video, segment, short_folder, i)
            script_text = ""
        else:
            clip, script_text = extract_clip_with_subtitles(
                source_video, segment, short_folder, i,
                make_vertical=make_vertical,
                add_subtitles=add_subtitles,
                subtitle_style=subtitle_style,
                language=language
            )
        
        if clip:
            extracted_clips.append(clip)
            all_scripts.append(script_text)
            
            # Guardar short en base de datos con folder_path
            if DB_AVAILABLE and video_id:
                try:
                    short_id = save_short(
                        video_id=video_id,
                        title=segment.name,
                        summary=f"Short extraído de {segment.start} a {segment.end}",
                        script=script_text,
                        start_time=segment.start,
                        end_time=segment.end,
                        output_filename=str(clip),
                        folder_path=str(short_folder)
                    )
                    print(f"   💾 Short guardado en BD (ID: {short_id})")
                except Exception as e:
                    print(f"   ⚠️ Error guardando short en BD: {e}")
    
    # Actualizar transcripción completa del video en BD
    if DB_AVAILABLE and video_id and all_scripts:
        try:
            full_transcript = "\n\n".join(all_scripts)
            save_video(url=url, title=None, transcript=full_transcript)
        except Exception as e:
            print(f"   ⚠️ Error actualizando transcript en BD: {e}")
    
    # Limpiar video fuente si no se quiere conservar
    if not keep_source:
        source_video.unlink()
        print(f"\n🗑️  Video fuente eliminado")
    
    # Resumen
    print("\n" + "=" * 60)
    print("✅ PROCESO COMPLETADO")
    print("=" * 60)
    print(f"   📂 Clips guardados en: {video_clips_dir}")
    print(f"   📊 Clips extraídos: {len(extracted_clips)}/{len(segments)}")
    if add_subtitles:
        print(f"   📝 Archivos SRT también guardados para cada clip")
    if DB_AVAILABLE:
        print(f"   💾 Datos guardados en base de datos")
    
    return extracted_clips


# =============================================================================
# CONFIGURACIÓN - EDITA ESTO CON TUS DATOS
# =============================================================================

if __name__ == "__main__":
    
    # URL del video de YouTube
    VIDEO_URL = "https://www.youtube.com/watch?v=JxAdV9YVbsY"
    
    # Lista de segmentos a extraer (1 short para prueba completa)
    SEGMENTS = [
        # Los protestantes que no les mientan - argumento nuclear
        Segment("12:58", "14:00", "A Los Protestantes No Les Mientan"),
    ]
    
    # Configuración
    OUTPUT_DIR = Path(__file__).parent / "output"  # Carpeta de salida
    MAKE_VERTICAL = True   # True = formato 9:16 para YouTube Shorts/TikTok/Reels
    FAST_MODE = False      # True = sin subtítulos, corte instantáneo
    ADD_SUBTITLES = True   # True = generar subtítulos automáticos
    SUBTITLE_STYLE = "modern"  # Opciones: "modern", "bold", "minimal"
    LANGUAGE = "es"        # Idioma del video para transcripción
    KEEP_SOURCE = True     # True = conservar video original descargado
    
    # Ejecutar
    process_video(
        url=VIDEO_URL,
        segments=SEGMENTS,
        output_dir=OUTPUT_DIR,
        make_vertical=MAKE_VERTICAL,
        fast_mode=FAST_MODE,
        add_subtitles=ADD_SUBTITLES,
        subtitle_style=SUBTITLE_STYLE,
        language=LANGUAGE,
        keep_source=KEEP_SOURCE
    )
