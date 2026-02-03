"""
Smart Shorts Regenerator
=========================
Analyzes transcripts using Gemini AI to determine if extending shorts
to 1 minute improves the argument without changing topic.

Usage:
    python regenerate_shorts_smart.py
"""

import os
import re
import json
from pathlib import Path
from database import (
    get_all_shorts, get_shorts_by_video, get_all_videos,
    get_connection
)
from shorts_extractor import (
    Segment, download_video, extract_clip_with_subtitles,
    time_to_seconds, transcribe_audio
)

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("⚠️ google-generativeai no instalado. Ejecuta: pip install google-generativeai")


def configure_gemini():
    """Configure Gemini API."""
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        # Try reading from .env file
        env_path = Path(".env")
        if env_path.exists():
            with open(env_path) as f:
                for line in f:
                    if line.startswith("GEMINI_API_KEY=") or line.startswith("GOOGLE_API_KEY="):
                        api_key = line.split("=", 1)[1].strip().strip('"\'')
                        break
    
    if not api_key:
        raise ValueError("No se encontró GEMINI_API_KEY. Configúrala como variable de entorno o en .env")
    
    genai.configure(api_key=api_key)
    return genai.GenerativeModel('gemini-2.0-flash')


def seconds_to_time(seconds: int) -> str:
    """Convert seconds to MM:SS format."""
    minutes = int(seconds) // 60
    secs = int(seconds) % 60
    return f"{minutes}:{secs:02d}"


def add_seconds_to_time(time_str: str, seconds_to_add: int) -> str:
    """Add seconds to a MM:SS or HH:MM:SS timestamp."""
    seconds = time_to_seconds(time_str)
    new_seconds = int(seconds + seconds_to_add)
    
    hours = new_seconds // 3600
    remaining = new_seconds % 3600
    mins = remaining // 60
    secs = remaining % 60
    
    if hours > 0:
        return f"{hours}:{mins:02d}:{secs:02d}"
    else:
        return f"{mins}:{secs:02d}"


def get_transcript_segment(full_transcript: list, start_sec: float, end_sec: float) -> str:
    """Extract text from transcript between start and end seconds."""
    text_parts = []
    for seg in full_transcript:
        seg_start = seg.get('start', 0)
        seg_end = seg.get('end', seg_start + 1)
        
        # Check if segment overlaps with our range
        if seg_start < end_sec and seg_end > start_sec:
            text_parts.append(seg.get('text', ''))
    
    return ' '.join(text_parts)


def analyze_extension_with_gemini(model, short_title: str, current_transcript: str, 
                                   extended_transcript: str, extra_transcript: str) -> dict:
    """
    Use Gemini to analyze if extending the short improves the argument.
    Returns dict with: should_extend (bool), reason (str), new_duration_suggestion (int seconds)
    """
    
    prompt = f"""Eres un analista de contenido de videos apologéticos católicos.

Tienes un SHORT de YouTube con el título: "{short_title}"

TRANSCRIPCIÓN ACTUAL DEL SHORT (~40 segundos):
{current_transcript}

TRANSCRIPCIÓN SI SE EXTIENDE A 1 MINUTO:
{extended_transcript}

CONTENIDO ADICIONAL (los ~20 segundos extras):
{extra_transcript}

ANALIZA:
1. ¿El contenido adicional PROFUNDIZA el mismo argumento del short original?
2. ¿O cambia de tema / se desvía / no aporta al argumento central?
3. ¿Hay un punto natural de cierre antes del minuto completo?

RESPONDE EN FORMATO JSON:
{{
    "should_extend": true/false,
    "reason": "Explicación breve de tu decisión",
    "recommended_duration_seconds": 60,  // o menos si hay un punto de cierre natural antes
    "argument_quality": "mejor" / "igual" / "peor"  // calidad del argumento si se extiende
}}

Solo responde el JSON, sin texto adicional."""

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        
        # Clean up response - extract JSON
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        
        result = json.loads(text)
        return result
    except Exception as e:
        print(f"   ⚠️ Error con Gemini: {e}")
        return {
            "should_extend": False,
            "reason": f"Error al analizar: {e}",
            "recommended_duration_seconds": 40,
            "argument_quality": "igual"
        }


def update_short_times(short_id: int, new_end_time: str):
    """Update the end time of a short in the database."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE shorts SET end_time = ? WHERE id = ?", (new_end_time, short_id))
    conn.commit()
    conn.close()


def regenerate_short(short: dict, source_video: Path, new_end_time: str):
    """Regenerate the short video with new end time."""
    
    title = short['title']
    start_time = short['start_time']
    folder_path = short.get('folder_path', '')
    
    if not folder_path:
        print(f"   ⚠️ No hay folder_path para el short")
        return None
    
    output_dir = Path(folder_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create segment with new duration
    segment = Segment(
        start=start_time,
        end=new_end_time,
        name=title
    )
    
    # Extract with subtitles
    output_file, script = extract_clip_with_subtitles(
        source_video=source_video,
        segment=segment,
        output_dir=output_dir,
        clip_index=1,
        make_vertical=True,
        add_subtitles=True,
        subtitle_style="modern",
        language="es"
    )
    
    return output_file


def main():
    print("=" * 60)
    print("🧠 REGENERADOR INTELIGENTE DE SHORTS")
    print("    Usando Gemini AI para análisis de contenido")
    print("=" * 60)
    
    if not GEMINI_AVAILABLE:
        print("❌ Instala google-generativeai: pip install google-generativeai")
        return
    
    # Configure Gemini
    try:
        model = configure_gemini()
        print("✅ Gemini configurado correctamente")
    except Exception as e:
        print(f"❌ Error configurando Gemini: {e}")
        return
    
    # Get videos and shorts
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
        
        shorts = get_shorts_by_video(video_id)
        
        if not shorts:
            print("   ⚠️ No hay shorts para este video")
            continue
        
        print(f"   📊 Shorts encontrados: {len(shorts)}")
        
        # Find source video
        source_video = Path("output/source_video.mp4")
        if not source_video.exists():
            print(f"   ⚠️ No se encontró el video fuente")
            continue
        
        print(f"   📂 Video fuente: {source_video}")
        print("   🎤 Transcribiendo video completo...")
        
        # Get full transcript
        full_transcript = transcribe_audio(source_video, language="es")
        print(f"   ✅ Transcripción completada ({len(full_transcript)} fragmentos)")
        
        # Process each short
        results = []
        
        for short in shorts:
            short_id = short['id']
            title = short['title']
            start_time = short['start_time']
            end_time = short['end_time']
            
            start_sec = time_to_seconds(start_time)
            end_sec = time_to_seconds(end_time)
            current_duration = end_sec - start_sec
            
            # Skip if already ~60 seconds
            if current_duration >= 55:
                print(f"\n   ⏭️ {title}: Ya dura {current_duration:.0f}s, saltando")
                continue
            
            # Calculate extended end (60 seconds total)
            extended_end_sec = start_sec + 60
            extended_end_time = add_seconds_to_time(start_time, 60 - int(current_duration))
            
            print(f"\n   🔍 Analizando: {title}")
            print(f"      Actual: {start_time} → {end_time} ({current_duration:.0f}s)")
            print(f"      Extendido: {start_time} → {extended_end_time} (60s)")
            
            # Get transcripts
            current_transcript = get_transcript_segment(full_transcript, start_sec, end_sec)
            extended_transcript = get_transcript_segment(full_transcript, start_sec, extended_end_sec)
            extra_transcript = get_transcript_segment(full_transcript, end_sec, extended_end_sec)
            
            # Analyze with Gemini
            print("      🧠 Consultando Gemini...")
            analysis = analyze_extension_with_gemini(
                model, title, current_transcript, extended_transcript, extra_transcript
            )
            
            should_extend = analysis.get('should_extend', False)
            reason = analysis.get('reason', 'Sin razón')
            recommended_duration = analysis.get('recommended_duration_seconds', 40)
            quality = analysis.get('argument_quality', 'igual')
            
            print(f"      📊 Resultado: {'✅ EXTENDER' if should_extend else '❌ MANTENER'}")
            print(f"      💡 Razón: {reason}")
            print(f"      ⭐ Calidad argumento: {quality}")
            
            results.append({
                'short_id': short_id,
                'title': title,
                'should_extend': should_extend,
                'reason': reason,
                'current_duration': current_duration,
                'recommended_duration': recommended_duration,
                'quality': quality
            })
            
            # If should extend, regenerate
            if should_extend:
                new_end = add_seconds_to_time(start_time, recommended_duration - int(current_duration))
                print(f"      🎬 Regenerando video hasta {new_end}...")
                
                try:
                    output_file = regenerate_short(short, source_video, new_end)
                    if output_file:
                        # Update database
                        update_short_times(short_id, new_end)
                        print(f"      ✅ Video regenerado: {output_file}")
                except Exception as e:
                    print(f"      ❌ Error regenerando: {e}")
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 RESUMEN DE ANÁLISIS")
        print("=" * 60)
        
        extended_count = sum(1 for r in results if r['should_extend'])
        kept_count = len(results) - extended_count
        
        print(f"   ✅ Shorts extendidos: {extended_count}")
        print(f"   ⏸️ Shorts mantenidos: {kept_count}")
        
        for r in results:
            status = "✅ EXTENDIDO" if r['should_extend'] else "⏸️ MANTENIDO"
            print(f"   {status}: {r['title']} ({r['current_duration']:.0f}s → {r['recommended_duration']}s)")
    
    print("\n" + "=" * 60)
    print("✅ ANÁLISIS COMPLETADO")
    print("=" * 60)


if __name__ == "__main__":
    main()
