"""
Extracts truly clean scripts by aggressively deduplicating subtitle overlaps.
"""

import re
from pathlib import Path


def time_to_seconds(time_str: str) -> float:
    parts = time_str.strip("[] ").split(":")
    if len(parts) == 2:
        return int(parts[0]) * 60 + int(parts[1])
    elif len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    return 0


def extract_clean_script(transcript_lines: list[str], start_sec: float, end_sec: float) -> str:
    """Extracts clean script, aggressively removing overlapping subtitle fragments."""
    raw_texts = []
    for line in transcript_lines:
        line = line.strip()
        if not line:
            continue
        match = re.match(r'\[(\d+:\d+(?::\d+)?)\]\s*(.*)', line)
        if not match:
            continue
        time_str = match.group(1)
        text = match.group(2).strip()
        if not text:
            continue
        line_sec = time_to_seconds(time_str)
        if start_sec <= line_sec < end_sec:
            raw_texts.append(text)
    
    # Aggressive deduplication: remove lines that are substrings of adjacent lines
    deduped = []
    for t in raw_texts:
        if not deduped:
            deduped.append(t)
            continue
        prev = deduped[-1]
        # If current text is contained in previous, skip
        if t in prev:
            continue
        # If previous text is contained in current, replace
        if prev in t:
            deduped[-1] = t
            continue
        # Check suffix/prefix overlap (subtitle continuation)
        # If the end of prev overlaps with the start of current
        overlap_found = False
        min_overlap = min(len(prev), len(t), 10)
        for ol in range(min(len(prev), len(t)), min_overlap - 1, -1):
            if prev[-ol:] == t[:ol]:
                # Merge: keep prev + non-overlapping part of current
                deduped[-1] = prev + t[ol:]
                overlap_found = True
                break
        if not overlap_found:
            deduped.append(t)
    
    # Now join into paragraphs, creating breaks at sentence ends
    full_text = " ".join(deduped)
    
    # Clean up multiple spaces
    full_text = re.sub(r'\s+', ' ', full_text).strip()
    
    # Add paragraph breaks after sentences that end a thought
    # (every ~3-4 sentences for readability)
    sentences = re.split(r'(?<=[.?!])\s+', full_text)
    
    paragraphs = []
    current_para = []
    for i, s in enumerate(sentences):
        current_para.append(s)
        if len(current_para) >= 4:
            paragraphs.append(" ".join(current_para))
            current_para = []
    if current_para:
        paragraphs.append(" ".join(current_para))
    
    return "\n\n".join(paragraphs)


def main():
    transcript_path = Path("temp_analysis_output/clean_transcript.txt")
    lines = transcript_path.read_text(encoding="utf-8").splitlines()
    
    segments = [
        {"number": 1, "title": "¿Qué es la Renovación Carismática y por qué genera dudas?",
         "start": 0, "end": 600},
        {"number": 2, "title": "San Pablo ya condenó estos abusos: 1 Corintios 14 y el orden litúrgico",
         "start": 600, "end": 1200},
        {"number": 3, "title": "El Montanismo: la herejía antigua que se repite hoy en la Renovación Carismática",
         "start": 1200, "end": 1860},
        {"number": 4, "title": "La respuesta del sacerdote: 'Dios no produce desmayos'",
         "start": 2280, "end": 3120},
        {"number": 5, "title": "'Es un completo disparate': El veredicto final del sacerdote",
         "start": 3300, "end": 4020}
    ]
    
    output_dir = Path("segment_scripts")
    output_dir.mkdir(exist_ok=True)
    
    for seg in segments:
        script = extract_clean_script(lines, seg["start"], seg["end"])
        
        start_m, start_s = divmod(seg["start"], 60)
        end_m, end_s = divmod(seg["end"], 60)
        
        header = f"{'='*60}\n"
        header += f"SEGMENTO {seg['number']}: {seg['title']}\n"
        header += f"Timestamps: {start_m}:{start_s:02d} - {end_m}:{end_s:02d}\n"
        header += f"{'='*60}\n\n"
        
        filepath = output_dir / f"segmento_{seg['number']}.txt"
        filepath.write_text(header + script, encoding="utf-8")
        
        word_count = len(script.split())
        print(f"Segmento {seg['number']}: {word_count} palabras")
    
    print(f"\nGuardados en: {output_dir}/")


if __name__ == "__main__":
    main()
