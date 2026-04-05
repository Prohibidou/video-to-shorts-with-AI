import subprocess
from pathlib import Path

# Paths
source_video = Path("output/source_video.mp4")
output_dir = Path("output/clips/Fenómenos paranormales_ Si haces esto_ puedes terminar poseído por el demonio/01_Peligro_Cultos_Pentecostales")
part1_file = output_dir / "part1.mp4"
part2_file = output_dir / "part2.mp4"
concat_list = output_dir / "concat.txt"
merged_file = output_dir / "merged.mp4"
final_file = output_dir / "clip_01_Peligro_Cultos_Pentecostales.mp4"

def run(cmd):
    print(" ".join(cmd))
    subprocess.run(cmd, check=True)

# 1. Extract Part A (31:49.230 to 31:58.500)
# This ends exactly after "mucho cuidado con eso"
run([
    "ffmpeg", "-y", "-ss", "1909.2", "-i", str(source_video), "-to", "9.3",
    "-c:v", "libx264", "-preset", "fast", "-crf", "23", "-c:a", "aac", str(part1_file)
])

# 2. Extract Part B (32:06.500 to 34:45.000)
# This starts at "Entonces, todas estas sesiones..."
run([
    "ffmpeg", "-y", "-ss", "1926.5", "-i", str(source_video), "-to", "158.5",
    "-c:v", "libx264", "-preset", "fast", "-crf", "23", "-c:a", "aac", str(part2_file)
])

# 3. Concat Part A and Part B
with open(concat_list, "w") as f:
    f.write(f"file 'part1.mp4'\n")
    f.write(f"file 'part2.mp4'\n")

run([
    "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list),
    "-c", "copy", str(merged_file)
])

# 4. Aggressive silence removal
silence_thresh = "-30dB"
silence_duration = "0.2"  # very aggressive
print("Analyzing aggressive silences...")
res = subprocess.run([
    "ffmpeg", "-i", str(merged_file),
    "-af", f"silencedetect=noise={silence_thresh}:d={silence_duration}",
    "-f", "null", "-"
], capture_output=True, text=True)

silences = []
for line in res.stderr.splitlines():
    if "silence_start" in line:
        try: silences.append({"start": float(line.split("silence_start: ")[1])})
        except: pass
    elif "silence_end" in line:
        try: silences[-1]["end"] = float(line.split("silence_end: ")[1].split(" ")[0])
        except: pass

cmd_dur = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(merged_file)]
dur_res = subprocess.run(cmd_dur, capture_output=True, text=True)
total_duration = float(dur_res.stdout.strip())

keep_segments = []
last_pos = 0.0

for s in silences:
    if "end" not in s: continue
    s_start = s["start"]
    s_end = s["end"]
    
    # Shield first 5 seconds
    if s_start < 5.0 and s_end < 5.0:
        continue
    if s_start < 5.0:
        s_start = 5.0
        
    if s_start > last_pos + 0.1:
        keep_segments.append((last_pos, s_start))
    
    last_pos = s_end - 0.05  # tiny overlap

if last_pos < total_duration - 0.1:
    keep_segments.append((last_pos, total_duration))

print(f"Cutting into {len(keep_segments)} fluent segments!")

seg_files = []
for i, (start, end) in enumerate(keep_segments):
    sf = output_dir / f"flu_{i}.mp4"
    run([
        "ffmpeg", "-y", "-i", str(merged_file), "-ss", f"{start:.3f}", "-to", f"{end:.3f}",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23", "-c:a", "aac", str(sf)
    ])
    seg_files.append(sf)

fluent_concat = output_dir / "fluent_concat.txt"
with open(fluent_concat, "w") as f:
    for sf in seg_files:
        f.write(f"file '{sf.name}'\n")

fluent_merged = output_dir / "fluent_merged.mp4"
run([
    "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(fluent_concat),
    "-c", "copy", str(fluent_merged)
])

# 5. Apply Vertical Black format
filter_complex = (
    f"[0:v]scale=1080:1920:force_original_aspect_ratio=increase,"
    f"crop=1080:1920,drawbox=x=0:y=0:w=1080:h=1920:color=black:t=fill[bg];"
    f"[0:v]scale=1080:-2:force_original_aspect_ratio=decrease[fg];"
    f"[bg][fg]overlay=(W-w)/2:(H-h)/2[v]"
)

run([
    "ffmpeg", "-y", "-i", str(fluent_merged),
    "-filter_complex", filter_complex,
    "-map", "[v]", "-map", "0:a",
    "-c:v", "libx264", "-preset", "fast", "-crf", "23", "-c:a", "aac",
    str(final_file)
])

# 6. Burn Subtitles
print("Burning subtitles using small model...")
run(["python", "add_subtitles.py", str(final_file), "--model", "small"])

print("ALL DONE. Result is in _sub.mp4.")
