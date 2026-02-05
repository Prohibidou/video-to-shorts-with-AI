"""
YouTube Shorts Extractor
========================
Tool to extract multiple clips from a YouTube video
based on specific timestamps, with automatic subtitles.

Usage:
    python shorts_extractor.py

Requirements:
    - yt-dlp (pip install yt-dlp)
    - faster-whisper (pip install faster-whisper)
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


# =============================================================================
# HOOK SELECTION CONSTANTS - Estrategia para capturar atención de evangélicos
# =============================================================================

# Palabras/frases que causan disonancia cognitiva en evangélicos/protestantes
# Ordenadas por impacto (las más disruptivas primero)
DISRUPTIVE_KEYWORDS = [
    # Contraataques directos (máximo impacto)
    "mentira", "mentiras", "engañado", "engaño", "falso", "error", "no es bíblico",
    "no es biblico", "anti-bíblico", "anti-biblico", "herejía", "herejia", "hereje",
    
    # Desafíos a autoridad protestante
    "lutero", "calvino", "reforma", "reformadores", "500 años", "1500",
    "inventaron", "inventó", "invento", "secta", "sectas", "división", "division",
    "dividido", "miles de denominaciones",
    
    # Autoridad histórica católica
    "padres de la iglesia", "padres apostólicos", "padres apostolicos", "primitivos",
    "primeros cristianos", "iglesia primitiva", "apóstoles", "apostoles", "discípulo de",
    "discipulo de", "año 100", "año 107", "siglo I", "siglo II", "ignacio", "policarpo",
    "clemente", "ireneo", "atanasio", "agustín", "agustin", "jerónimo", "jeronimo",
    
    # Sacramentos (ataque a sola scriptura)
    "eucaristía", "eucaristia", "cuerpo de cristo", "presencia real", "sangre de cristo",
    "transubstanciación", "transubstanciacion", "altar", "sacrificio", "misa",
    "confesión", "confesion", "sacerdote", "obispo", "sucesión apostólica",
    "sucesion apostolica",
    
    # María y Santos (puntos de fricción)
    "maría", "maria", "virgen", "madre de dios", "theotokos", "santos", "intercesión",
    "intercesion", "veneración", "veneracion",
    
    # Iglesia y Autoridad
    "católica", "catolica", "católico", "catolico", "una sola iglesia", "única iglesia",
    "unica iglesia", "fuera de la iglesia", "pedro", "roma", "papa", "papado",
    "tradición", "tradicion", "magisterio",
    
    # Frases de impacto
    "protestantes no saben", "evangélicos ignoran", "evangelicos ignoran",
    "la biblia dice", "pablo dice", "jesús dijo", "jesus dijo",
]

# Palabras de relleno que NO deben iniciar ni terminar un gancho
FILLER_WORDS_START = [
    "y", "e", "o", "u", "pero", "entonces", "pues", "bueno", "bien",
    "eh", "este", "esto", "eso", "ah", "oh", "mm", "mira", "oye",
    "digamos", "como", "así", "asi", "o sea", "osea", "porque",
    "también", "tambien", "además", "ademas", "sin embargo",
    "no obstante", "por lo tanto", "es decir", "en realidad",
    "de hecho", "la verdad", "verdad", "claro", "obviamente",
]

FILLER_WORDS_END = [
    "y", "e", "o", "u", "que", "de", "en", "a", "el", "la", "los", "las",
    "un", "una", "unos", "unas", "al", "del", "con", "para", "por",
    "como", "así", "asi", "muy", "más", "mas", "menos", "tan",
    "este", "esta", "estos", "estas", "ese", "esa", "esos", "esas",
    "su", "sus", "mi", "mis", "tu", "tus", "nuestro", "nuestra",
    "obispos", "sacerdotes", "diaconos",  # Contexto específico: suelen ser parte de listas
]

# Palabras que indican un inicio FUERTE (bonus de puntaje)
STRONG_SUBJECTS = [
    "la iglesia", "el apostol", "los apostoles", "maria", "maría", "jesus", "jesús",
    "cristo", "el señor", "san", "santa", "dios", "padre", "hijo", "espiritu",
    "pablo", "juan", "pedro", "ignacio", "timoteo", "onesimo", "onésimo",
    "nadie", "todo", "todos", "ninguno", "jamas", "nunca", "siempre",
    "lutero", "calvino", "la biblia", "las escrituras",
]

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


def seconds_to_srt_time(seconds: float) -> str:
    """Converts seconds to SRT format (HH:MM:SS,mmm)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


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


def transcribe_audio(video_path: Path, language: str = "es", max_words_per_line: int = 4) -> list[dict]:
    """
    Transcribes the video audio using faster-whisper.
    Returns a list of short segments (maximum max_words_per_line words each).
    """
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        print("   ⚠️  faster-whisper not installed. Installing...")
        subprocess.run([sys.executable, "-m", "pip", "install", "faster-whisper"], 
                      capture_output=True)
        from faster_whisper import WhisperModel
    
    print(f"   🎤 Transcribing audio...")
    
    # IMPORTANT: Use 'small' model for better quality (NEVER use 'tiny')
    # Process videos one by one to avoid RAM issues
    model = WhisperModel("small", device="cpu", compute_type="int8")
    
    segments, info = model.transcribe(
        str(video_path),
        language=language,
        word_timestamps=True,
        vad_filter=True
    )
    
    # Collect all words with their timestamps
    all_words = []
    for segment in segments:
        if segment.words:
            for word in segment.words:
                all_words.append({
                    "start": word.start,
                    "end": word.end,
                    "text": word.word.strip()
                })
    
    # Group words in small chunks (maximum max_words_per_line words)
    result = []
    current_chunk = []
    chunk_start = None
    
    for word in all_words:
        if chunk_start is None:
            chunk_start = word["start"]
        
        current_chunk.append(word["text"])
        
        # Create new segment when we reach the word limit
        if len(current_chunk) >= max_words_per_line:
            result.append({
                "start": chunk_start,
                "end": word["end"],
                "text": " ".join(current_chunk)
            })
            current_chunk = []
            chunk_start = None
    
    # Add the last chunk if anything remains
    if current_chunk:
        result.append({
            "start": chunk_start,
            "end": all_words[-1]["end"],
            "text": " ".join(current_chunk)
        })
    
    print(f"   ✅ Transcription completed ({len(result)} fragments)")

    # Replace "protestante/protestantes" with "protestantes (Evangelicos)" in subtitles
    # and remove accents
    import unicodedata
    import re
    
    def remove_accents(text):
        return ''.join(
            c for c in unicodedata.normalize('NFD', text)
            if unicodedata.category(c) != 'Mn'
        )
    
    for segment in result:
        # If text contains "protestante" or "protestantes", replace ALL the text
        # with just "protestantes (Evangelicos)" - no other words
        if re.search(r'\bprotestantes?\b', segment["text"], flags=re.IGNORECASE):
            segment["text"] = "protestantes (Evangelicos)"
        else:
            segment["text"] = remove_accents(segment["text"])

    return result


# Lista de nombres propios comunes en apologética que necesitan comas
PROPER_NAMES = [
    "maria", "maría", "pablo", "pedro", "juan", "santiago", "mateo", "marcos", "lucas",
    "ignacio", "policarpo", "clemente", "ireneo", "atanasio", "agustin", "agustín",
    "jeronimo", "jerónimo", "ambrosio", "crisostomo", "crisóstomo", "basilio",
    "gregorio", "cipriano", "tertuliano", "origenes", "orígenes", "justino",
    "lutero", "calvino", "zuinglio", "wesley", "knox",
]


def format_hook_with_commas(text: str) -> str:
    """
    Agrega comas entre nombres propios consecutivos para mejor legibilidad.
    Ejemplo: "Maria Pablo Juan" -> "Maria, Pablo, Juan"
    """
    if not text:
        return text
    
    words = text.split()
    if len(words) < 2:
        return text
    
    result = []
    i = 0
    while i < len(words):
        word = words[i]
        word_clean = word.lower().rstrip(".,;:!?")
        
        # Si es un nombre propio
        if word_clean in PROPER_NAMES:
            result.append(word.rstrip(","))  # Quitar coma existente si hay
            
            # Verificar si la siguiente palabra también es nombre propio
            if i + 1 < len(words):
                next_word_clean = words[i + 1].lower().rstrip(".,;:!?")
                if next_word_clean in PROPER_NAMES:
                    # Agregar coma después del nombre actual
                    result[-1] = result[-1] + ","
        else:
            result.append(word)
        
        i += 1
    
    return " ".join(result)


def clean_hook_text(text: str) -> str:
    """
    Limpia el texto del gancho eliminando palabras de relleno del inicio y final.
    Asegura que el gancho termine correctamente (sin palabras sueltas).
    Agrega comas entre nombres propios para mejor legibilidad.
    También elimina palabras PARCIALES (muy cortas) que indican que se cortó a mitad.
    """
    if not text:
        return ""
    
    words = text.split()
    if not words:
        return ""
    
    # Eliminar palabras de relleno del inicio
    while words and words[0].lower().rstrip(".,;:!?") in FILLER_WORDS_START:
        words.pop(0)
    
    # Eliminar palabras de relleno del final (oraciones que quedan abiertas)
    while words and words[-1].lower().rstrip(".,;:!?") in FILLER_WORDS_END:
        words.pop()
    
    # NUEVO: Eliminar palabras PARCIALES del final (1-2 caracteres que no son palabras válidas)
    # Esto detecta cortes como "Juan era c" donde "c" es fragmento de "católico"
    MIN_WORD_LENGTH = 3  # Palabras válidas tienen al menos 3 letras
    # Excepciones: palabras muy cortas que SÍ son válidas
    SHORT_VALID_WORDS = ["la", "el", "y", "e", "o", "a", "de", "en", "es", "no", "si", "sí", "un"]
    while words:
        last_word_clean = words[-1].lower().rstrip(".,;:!?")
        if len(last_word_clean) < MIN_WORD_LENGTH and last_word_clean not in SHORT_VALID_WORDS:
            words.pop()  # Eliminar palabra parcial
        else:
            break
    
    if not words:
        return ""
    
    result = " ".join(words)
    
    # Agregar comas entre nombres propios
    result = format_hook_with_commas(result)
    
    # Si termina con carácter incompleto, intentar cerrar elegantemente
    if result and result[-1] not in ".!?":
        # Si la última palabra es sustantiva (no es artículo/preposición), agregar puntos suspensivos
        last_word = words[-1].lower().rstrip(".,;:!?")
        if last_word not in FILLER_WORDS_END:
            result = result.rstrip(".,;:") + "..."
    
    return result


def score_hook_window(text: str) -> int:
    """
    Puntúa una ventana de texto según su potencial como gancho disruptivo.
    Mayor puntaje = más disruptivo y atractivo para evangélicos/protestantes.
    """
    if not text:
        return 0
    
    score = 0
    text_lower = text.lower()
    
    # Puntaje por palabras disruptivas (más impacto = más puntos)
    for i, keyword in enumerate(DISRUPTIVE_KEYWORDS):
        if keyword in text_lower:
            # Las primeras keywords son más disruptivas (tienen más peso)
            weight = max(1, 15 - (i // 5))  # De 15 a 1 según posición
            score += weight
    
    # Bonus si es una oración que parece completa
    if text.strip().endswith((".", "!", "?", "...")):
        score += 5
    
    # Bonus si NO empieza con palabra de relleno
    words = text.split()
    if words and words[0].lower() not in FILLER_WORDS_START:
        score += 3
    
    # Bonus si NO termina con palabra de relleno
    if words and words[-1].lower().rstrip(".,;:!?") not in FILLER_WORDS_END:
        score += 3
    
    # NUEVA LÓGICA: Penalizar longitud EXCESIVA (usuario reportó que 15+ palabras es demasiado)
    word_count = len(words)
    if word_count < 5:
        score -= 20  # Muy corto, inútil
    elif word_count > 12:
        score -= 20  # Demasiado largo - PENALIZACIÓN FUERTE
    elif 6 <= word_count <= 10:
        score += 10  # Longitud IDEAL (punch line corto)
    elif word_count <= 12:
        score += 5   # Aceptable
    
    # NUEVA LÓGICA: Bonus por Sujeto Fuerte al inicio
    for subject in STRONG_SUBJECTS:
        if text.lower().startswith(subject):
            score += 15
            break
    
    # NUEVA LÓGICA: Penalización MASIVA si empieza con "Y" u otros conectores dependientes
    if words[0].lower() in ["y", "e", "o", "pero", "porque", "pues", "que", "cual"]:
        score -= 50  # Esto rompe completamente la gramática
    
    # NUEVA LÓGICA: Penalizar "Sustantivo + Y" (ej: "Obispos y todos...")
    # Indica que es continuación de una lista anterior
    if len(words) > 1 and words[1].lower() == "y":
        first_word_lower = words[0].lower().rstrip(".,;:!?")
        # Si la primera palabra NO es un nombre propio conocido, penalizar
        if first_word_lower not in [name.lower() for name in PROPER_NAMES]:
            score -= 30  # Penalización fuerte por patrón "Sustantivo + y"
    
    # NUEVA LÓGICA: Detectar patrones de LISTA/CONTINUACIÓN INTERNOS
    # Frases como "Maria, Pablo y todos ellos..." tienen "y todos" que indica continuación
    text_lower = text.lower()
    bad_internal_patterns = [
        " y todos ", " y cada ", " y los demás ", " y las demás ",
        " y ellos ", " y muchos ", " y otros ", " y otras ",
        " como obispos ", " como sacerdotes ",  # "X como obispos y todos" es lista
    ]
    for pattern in bad_internal_patterns:
        if pattern in text_lower:
            score -= 40  # Penalización muy fuerte - esto es continuación de lista
            break
    
    return max(0, score)


def find_best_hook_window(transcription: list[dict], hook_duration: float, 
                          search_window: float = 15.0) -> tuple[str, float, float]:
    """
    Busca el MEJOR gancho posible dentro de los primeros segundos del video.
    NO usa una duración fija - prueba múltiples duraciones y elige la que
    produzca el gancho más disruptivo para capturar la atención.
    
    La duración del gancho se determina por el contenido, no por un tiempo fijo.
    
    Returns: (hook_text, hook_start_time, hook_end_time)
    """
    if not transcription:
        return "", 0.0, hook_duration
    
    best_score = -1
    best_text = ""
    best_start = 0.0
    best_end = hook_duration
    
    # Probar múltiples duraciones de ventana - LIMITADO a máximo 8s
    # El usuario reportó que ganchos largos son inaceptables
    DURATIONS_TO_TRY = [4.0, 5.0, 6.0, 7.0, 8.0]  # Eliminados 10s y 12s
    
    for try_duration in DURATIONS_TO_TRY:
        # Para cada duración, probar diferentes puntos de inicio
        for i, start_seg in enumerate(transcription):
            # Solo buscar en los primeros search_window segundos
            if start_seg["start"] >= search_window:
                break
            
            window_start = start_seg["start"]
            window_words = []
            window_end = window_start
            
            # Acumular palabras hasta la duración objetivo
            # IMPORTANTE: Aumentamos tolerancia a 2s para evitar cortar palabras a la mitad
            # Es mejor tener una frase completa que una cortada
            for seg in transcription[i:]:
                if seg["start"] < window_start + try_duration + 2.0:  # +2s tolerancia para completar palabras
                    window_words.append(seg["text"])
                    window_end = max(window_end, seg["end"])
                else:
                    break
            
            if not window_words:
                continue
            
            window_text = clean_hook_text(" ".join(window_words))
            if not window_text:
                continue
                
            window_score = score_hook_window(window_text)
            
            # Penalizar ventanas que empiezan tarde (preferimos empezar cerca de 0)
            # Penalización más suave para permitir encontrar mejor contenido
            time_penalty = int(window_start)  # 1 punto por segundo de retraso
            
            # Pequeño bonus si la duración está en el rango "ideal" (6-10 segundos)
            if 6.0 <= try_duration <= 10.0:
                window_score += 2
            
            adjusted_score = window_score - time_penalty
            
            if adjusted_score > best_score and window_text:
                best_score = adjusted_score
                best_text = window_text
                best_start = window_start
                best_end = window_end
    
    # Si no encontramos nada bueno, usar los primeros segundos disponibles
    if not best_text and transcription:
        fallback_words = []
        fallback_end = 0.0
        for seg in transcription[:10]:  # Primeros 10 segmentos
            fallback_words.append(seg["text"])
            fallback_end = seg["end"]
        best_text = clean_hook_text(" ".join(fallback_words))
        best_end = fallback_end
    
    return best_text, best_start, best_end


def extract_hook_text(transcription: list[dict], hook_duration: float) -> tuple[str, float]:
    """
    Extrae el mejor texto de gancho del video usando búsqueda inteligente.
    Busca la ventana más disruptiva dentro de los primeros 15 segundos.
    Returns (hook_text, hook_end_time).
    
    El gancho elegido:
    - Contiene palabras que causan disonancia cognitiva
    - No tiene palabras de relleno al inicio/final
    - Es una oración lo más completa posible
    
    IMPORTANTE: El hook_end_time es la duración VISUAL del texto en pantalla,
    NO el tiempo que toma decir las palabras. El texto es estático (no subtítulo
    en tiempo real), así que debe ser breve (~4-6 segundos para completar oraciones).
    """
    hook_text, hook_start, hook_end = find_best_hook_window(transcription, hook_duration)
    
    # DURACIÓN VISUAL FLEXIBLE: El texto del gancho es estático. Debe aparecer
    # aproximadamente 4-6 segundos para no tener tiempos muertos PERO también
    # para no cortar oraciones a mitad de palabra.
    # Usamos hasta 6 segundos para permitir completar frases.
    MAX_VISUAL_DURATION = 6.0
    MIN_VISUAL_DURATION = 4.0
    
    # Usar duración flexible: preferimos 4s pero permitimos hasta 6s
    visual_duration = max(MIN_VISUAL_DURATION, min(hook_duration, MAX_VISUAL_DURATION))
    
    return hook_text, visual_duration



def create_srt_file(transcription: list[dict], output_path: Path) -> Path:
    """Creates an SRT file from the transcription."""
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
    Creates an ASS file with subtitle styling for Shorts.
    Available styles: "modern", "bold", "minimal"
    """
    
    # Define styles
    styles = {
        "modern": {
            "font": "Arial",
            "size": font_size,
            "primary_color": "&H00FFFFFF",  # White
            "outline_color": "&H00000000",   # Black
            "back_color": "&H80000000",      # Semi-transparent black
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
    
    # ASS header
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
    add_hook: bool = True  # Add fixed hook text in the first seconds
) -> Tuple[Optional[Path], str, Optional[str]]:
    """Extracts a clip from the source video with automatic subtitles.
    Returns (file_path, script_text, hook_text).
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
    
    # Step 1: Extract temporary clip (without subtitles)
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
    subprocess.run(cmd_extract, capture_output=True, text=True)
    if not temp_clip.exists():
        print(f"   ❌ Error: Could not create temporary clip")
        return None, "", None
    
    if not add_subtitles:
        # If we don't want subtitles, rename and return
        temp_clip.rename(output_file)
        print(f"   ✅ Saved: {output_file.name}")
        return output_file, "", None
    
    # Step 2: Transcribe the clip (maximum 2 words per fragment = 1 single line)
    transcription = transcribe_audio(temp_clip, language, max_words_per_line=2)
    
    if not transcription:
        print(f"   ⚠️  No audio/voice detected. Saving without subtitles.")
        temp_clip.rename(output_file)
        return output_file, "", None
    
    # Determine hook for the first seconds
    hook_duration = getattr(segment, 'hook_duration', 4.0)
    hook_text = getattr(segment, 'hook_text', None)
    hook_end_time = hook_duration
    
    if add_hook and not hook_text:
        # Extract hook text automatically from transcription
        hook_text, hook_end_time = extract_hook_text(transcription, hook_duration)
        print(f"   🎣 Hook detected: \"{hook_text[:50]}...\" (0-{hook_end_time:.1f}s)")
    elif add_hook and hook_text:
        print(f"   🎣 Manual hook: \"{hook_text[:50]}...\"")
    
    
    # Step 3: Create SRT file with hook included as first subtitle
    subs_file = output_dir / f"subs_{clip_index:02d}.srt"
    
    with open(subs_file, 'w', encoding='utf-8') as f:
        subtitle_index = 1
        
        # Add hook as first subtitle (complete text, fixed for ~4 seconds)
        if add_hook and hook_text:
            # Split into lines if too long (maximum ~35 characters per line)
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
        
        # Add normal subtitles (after the hook)
        for seg in transcription:
            # Skip those within the hook period
            if add_hook and hook_text and seg["start"] < hook_end_time:
                continue
            
            start_time = seconds_to_srt_time(seg["start"])
            end_time = seconds_to_srt_time(seg["end"])
            text = seg["text"]
            
            f.write(f"{subtitle_index}\n")
            f.write(f"{start_time} --> {end_time}\n")
            f.write(f"{text}\n\n")
            subtitle_index += 1
    
    # Step 4: Burn subtitles into the video
    print(f"   📝 Adding subtitles to video...")
    
    # Subtitle style for Shorts
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
        # Vertical 9:16 format with subtitles
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
        # Keep original format with burned-in subtitles
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
    
    # Run FFmpeg from the clip directory to avoid path issues
    subprocess.run(cmd_subs, capture_output=True, text=True, cwd=str(output_dir))
    
    # Clean up temporary files
    if temp_clip.exists():
        temp_clip.unlink()
    if subs_file.exists():
        subs_file.unlink()
    
    # Verify if output file was created correctly
    if not output_file.exists():
        print(f"   ❌ Error: Could not create video with subtitles")
        return None, "", None
    
    # Extract complete script text
    script_text = " ".join([seg["text"] for seg in transcription])
    
    print(f"   ✅ Saved: {output_file.name} (with subtitles)")
    return output_file, script_text, hook_text


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
    add_subtitles: bool = True,
    subtitle_style: str = "modern",
    language: str = "es",
    keep_source: bool = True
):
    """Processes a complete video extracting all segments."""
    
    print("=" * 60)
    print("🎥 YOUTUBE SHORTS EXTRACTOR")
    print("=" * 60)
    
    if add_subtitles and fast_mode:
        print("⚠️  Note: fast_mode disables subtitles. Using normal mode.")
        fast_mode = False
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Download video
    source_video = download_video(url, output_dir)
    
    # Get real YouTube video title
    video_title = get_video_title(url)
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
    if add_subtitles:
        print(f"   📝 Automatic subtitles: ENABLED (style: {subtitle_style})")
    
    extracted_clips = []
    all_scripts = []  # To save complete video transcription
    
    for i, segment in enumerate(segments, 1):
        # Create individual folder for this short
        safe_segment_name = "".join(c if c.isalnum() or c in "- _" else "_" for c in segment.name)
        short_folder = video_clips_dir / f"{i:02d}_{safe_segment_name}"
        short_folder.mkdir(parents=True, exist_ok=True)
        
        if fast_mode:
            clip = extract_clip_fast(source_video, segment, short_folder, i)
            script_text = ""
            final_hook_text = None
        else:
            clip, script_text, final_hook_text = extract_clip_with_subtitles(
                source_video, segment, short_folder, i,
                make_vertical=make_vertical,
                add_subtitles=add_subtitles,
                subtitle_style=subtitle_style,
                language=language
            )
        
        if clip:
            extracted_clips.append(clip)
            all_scripts.append(script_text)
            
            # Save short in database with folder_path
            if DB_AVAILABLE and video_id:
                try:
                    short_id = save_short(
                        video_id=video_id,
                        title=segment.name,
                        summary=f"Short extracted from {segment.start} to {segment.end}",
                        script=script_text,
                        start_time=segment.start,
                        end_time=segment.end,
                        output_filename=str(clip),
                        folder_path=str(short_folder),
                        hook_text=final_hook_text
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
    print(f"   📊 Clips extracted: {len(extracted_clips)}/{len(segments)}")
    if add_subtitles:
        print(f"   📝 SRT files also saved for each clip")
    if DB_AVAILABLE:
        print(f"   💾 Data saved to database")
    
    return extracted_clips


# =============================================================================
# CONFIGURATION - EDIT THIS WITH YOUR DATA
# =============================================================================

if __name__ == "__main__":
    
    # YouTube video URL
    VIDEO_URL = "https://www.youtube.com/watch?v=JxAdV9YVbsY"
    
    # List of segments to extract (apologetic shorts about St. Ignatius and the early Church)
    SEGMENTS = [
        # María, Pablo, Juan, Ignacio, Timoteo, Onésimo - todos católicos
        # El video DEBE empezar en 11:29 donde empieza "María era católica..."
        Segment("11:29", "12:29", "Maria Pablo Juan Todos Catolicos"),
    ]
    
    # Configuration
    OUTPUT_DIR = Path(__file__).parent / "output"  # Output folder
    MAKE_VERTICAL = True   # True = 9:16 format for YouTube Shorts/TikTok/Reels
    FAST_MODE = False      # True = no subtitles, instant cut
    ADD_SUBTITLES = True   # True = generate automatic subtitles
    SUBTITLE_STYLE = "modern"  # Options: "modern", "bold", "minimal"
    LANGUAGE = "es"        # Video language for transcription
    KEEP_SOURCE = True     # True = keep original downloaded video
    
    # Execute
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
