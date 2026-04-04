"""
Parse VTT transcript into clean timestamped text.
"""
import re
from pathlib import Path

def time_to_seconds(time_str):
    h, m, s = time_str.split(':')
    return int(h) * 3600 + int(m) * 60 + float(s)

def seconds_to_mmss(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"

def main():
    vtt_path = Path("temp_analysis_output/transcript.es.vtt")
    content = vtt_path.read_text(encoding="utf-8")
    
    pattern = re.compile(
        r'(\d{2}:\d{2}:\d{2}\.\d{3}) --> (\d{2}:\d{2}:\d{2}\.\d{3}).*?\n(.*?)(?=\n\d{2}:\d{2}:\d{2}|\Z)',
        re.DOTALL
    )
    matches = pattern.findall(content)
    
    segments = []
    seen_texts = set()
    for start, end, text in matches:
        text = re.sub(r'<[^>]+>', '', text).replace('\n', ' ').strip()
        text = re.sub(r'\s+', ' ', text)
        if text and text not in seen_texts:
            seen_texts.add(text)
            segments.append({
                'start': start,
                'start_sec': time_to_seconds(start),
                'end': end,
                'end_sec': time_to_seconds(end),
                'text': text
            })
    
    # Write clean transcript with timestamps
    output = Path("temp_analysis_output/clean_transcript.txt")
    with open(output, "w", encoding="utf-8") as f:
        for seg in segments:
            ts = seconds_to_mmss(seg['start_sec'])
            f.write(f"[{ts}] {seg['text']}\n")
    
    total_duration = time_to_seconds(matches[-1][1]) if matches else 0
    print(f"Total segments: {len(segments)}")
    print(f"Total duration: {seconds_to_mmss(total_duration)}")
    print(f"Clean transcript saved to: {output}")

if __name__ == "__main__":
    main()
