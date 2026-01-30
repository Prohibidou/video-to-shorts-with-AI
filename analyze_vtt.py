import re
from pathlib import Path

def time_to_seconds(time_str):
    h, m, s = time_str.split(':')
    return int(h) * 3600 + int(m) * 60 + float(s)

def seconds_to_time(seconds):
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m}:{s:02d}"

def parse_vtt(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Simple regex to capture timestamp and text
    # Pattern: HH:MM:SS.mmm --> HH:MM:SS.mmm ... \n Line 1 \n Line 2 ...
    pattern = re.compile(r'(\d{2}:\d{2}:\d{2}\.\d{3}) --> (\d{2}:\d{2}:\d{2}\.\d{3}).*?\n(.*?)(?=\n\d{2}:\d{2}:\d{2}|\Z)', re.DOTALL)
    
    matches = pattern.findall(content)
    segments = []
    
    for start, end, text in matches:
        # Clean text
        text = re.sub(r'<[^>]+>', '', text) # Remove tags like <c>
        text = text.replace('\n', ' ').strip()
        text = re.sub(r'\s+', ' ', text)
        segments.append({
            'start': start,
            'end': end,
            'start_sec': time_to_seconds(start),
            'text': text
        })
    return segments

def analyze_transcript():
    vtt_files = list(Path("temp_analysis_output").glob("*.vtt"))
    if not vtt_files:
        print("No VTT files found")
        return

    segments = parse_vtt(vtt_files[0])
    
    keywords = [
        "eucaristía", "carne", "sangre", "altar", 
        "obispo", "jerarquía", "autoridad", "someteos",
        "herejía", "división", "cisma", "unidad",
        "protestante", "evangélico", "biblia", "escritura",
        "ignacio", "107", "discípulo", "juan"
    ]
    
    print(f"Total segments: {len(segments)}\n")
    
    # Group segments into blocks of ~60 seconds to find dense areas
    
    found_highlights = []
    
    for i in range(len(segments)):
        seg = segments[i]
        text_lower = seg['text'].lower()
        
        # Check if segment contains keyword
        for kw in keywords:
            if kw in text_lower:
                # Get context (prev 5, next 10 segments)
                start_idx = max(0, i - 5)
                end_idx = min(len(segments), i + 15)
                
                context_block = segments[start_idx:end_idx]
                context_text = " ".join([s['text'] for s in context_block])
                
                start_time = context_block[0]['start']
                end_time = context_block[-1]['end']
                
                # Avoid duplicates (simple overlap check)
                is_duplicate = False
                for existing in found_highlights:
                    if abs(time_to_seconds(start_time) - time_to_seconds(existing['start'])) < 60:
                        is_duplicate = True
                        break
                

                if not is_duplicate:
                    found_highlights.append({
                        'start': start_time,
                        'end': end_time,
                        'keyword': kw,
                        'text': context_text
                    })
    
    with open("analysis_results.txt", "w", encoding="utf-8") as f:
        for item in found_highlights:
            f.write(f"[{item['start']} - {item['end']}] Keyword: {item['keyword']}\n")
            f.write(f"Context: {item['text']}\n")
            f.write("-" * 80 + "\n")
            
    print(f"Saved {len(found_highlights)} potential segments to analysis_results.txt")


if __name__ == "__main__":
    analyze_transcript()
