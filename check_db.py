import sqlite3
conn = sqlite3.connect('shorts_tracker.db')
c = conn.cursor()
# Use video_id column
c.execute("SELECT id, title, start_time, end_time, status, hook_text FROM shorts WHERE video_id LIKE '%JxAdV9YVbsY%'")
rows = c.fetchall()
for r in rows:
    print(f"  ID={r[0]} | {r[2]}-{r[3]} | {r[4]} | {r[1]} | hook: {r[5][:60] if r[5] else 'N/A'}...")
if not rows:
    print("No existing shorts for this URL")
conn.close()
