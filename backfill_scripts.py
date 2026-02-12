"""Backfill script text into DB shorts from VTT subtitles (clean, deduplicated).

VTT format has alternating blocks:
  - Transition blocks (10ms duration like 05.070→05.080): just clean previous text
  - Active blocks (~2-3s duration): old clean text + new tagged text
  
We skip transition blocks entirely and only take the FIRST (clean) line from active blocks.
"""
import sqlite3
import re

# Read VTT
with open('subs.es.vtt', 'r', encoding='utf-8') as f:
    vtt = f.read()

def clean_vtt_text(text):
    """Remove VTT formatting tags and timestamps from text."""
    text = re.sub(r'<\d{2}:\d{2}:\d{2}\.\d+>', '', text)
    text = re.sub(r'</?c>', '', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'  +', ' ', text)
    return text.strip()

# Parse VTT — skip transition blocks (duration < 50ms)
blocks = re.split(r'\n\n+', vtt)
entries = []
seen_texts = set()  # deduplicate

for b in blocks:
    m = re.search(r'(\d{2}):(\d{2}):(\d{2})\.(\d+) --> (\d{2}):(\d{2}):(\d{2})\.(\d+)', b)
    if not m:
        continue
    
    start_ms = (int(m.group(1))*3600 + int(m.group(2))*60 + int(m.group(3))) * 1000 + int(m.group(4))
    end_ms = (int(m.group(5))*3600 + int(m.group(6))*60 + int(m.group(7))) * 1000 + int(m.group(8))
    duration_ms = end_ms - start_ms
    
    # Skip transition blocks (very short duration, typically 10ms)
    if duration_ms < 50:
        continue
    
    start_sec = start_ms // 1000
    end_sec = end_ms // 1000
    
    lines = b.strip().split('\n')
    # Get text lines (skip timestamp line)
    text_lines = []
    for l in lines:
        if '-->' in l or re.match(r'^\d+$', l.strip()):
            continue
        cleaned = clean_vtt_text(l)
        if cleaned:
            text_lines.append(cleaned)
    
    # The first line is usually a repeat of the previous block's text
    # The second line is the NEW text for this block
    # Take only the LAST unique text line (the new content)
    if text_lines:
        new_text = text_lines[-1]  # Last line is the new content
        if new_text and new_text not in seen_texts:
            seen_texts.add(new_text)
            entries.append((start_sec, end_sec, new_text))

print(f"Parsed {len(entries)} unique VTT entries")

# Get ALL shorts
conn = sqlite3.connect('shorts_tracker.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()
c.execute("SELECT id, start_time, end_time FROM shorts")
shorts = c.fetchall()
print(f"Found {len(shorts)} shorts total")

def time_to_sec(t):
    parts = t.split(':')
    return int(parts[0]) * 60 + int(parts[1])

updated = 0
for s in shorts:
    st = time_to_sec(s['start_time'])
    et = time_to_sec(s['end_time'])
    script_parts = [e[2] for e in entries if e[0] >= st - 2 and e[1] <= et + 2]
    script = '\n'.join(script_parts)
    if script:
        c.execute('UPDATE shorts SET script = ? WHERE id = ?', (script, s['id']))
        updated += 1
        print(f"  Updated short {s['id']} ({s['start_time']}-{s['end_time']}): {len(script)} chars")

conn.commit()
conn.close()
print(f"\nDone! Updated {updated} shorts with clean deduplicated script text")
