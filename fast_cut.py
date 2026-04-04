import subprocess
from pathlib import Path

# Paths
subbed_vid = Path("output/clips/Fenómenos paranormales_ Si haces esto_ puedes terminar poseído por el demonio/01_Peligro_Cultos_Pentecostales/clip_01_Peligro_Cultos_Pentecostales_sub.mp4")
part1 = "output/clips/part1_fast.mp4"
part2 = "output/clips/part2_fast.mp4"
concat_txt = "output/clips/concat_fast.txt"
final_cut = "output/clips/clip_01_final_fast.mp4"

def run(cmd):
    print(" ".join(cmd))
    subprocess.run(cmd, check=True)

# Cut exactly at 4.9 seconds, which is BEFORE the 5.0s mark where the bad subtitle starts
# and happens right after the FIRST "poseído."
run(["ffmpeg", "-y", "-i", str(subbed_vid), "-to", "4.9", "-c:v", "libx264", "-preset", "superfast", "-crf", "21", "-c:a", "aac", part1])

# Resume exactly at 8.0 seconds, which is exactly where the NEXT subtitle block starts
# "Entonces todas estas sesiones mediúmnicas..."
run(["ffmpeg", "-y", "-i", str(subbed_vid), "-ss", "8.0", "-c:v", "libx264", "-preset", "superfast", "-crf", "21", "-c:a", "aac", part2])

with open(concat_txt, "w") as f:
    f.write(f"file 'part1_fast.mp4'\n")
    f.write(f"file 'part2_fast.mp4'\n")

run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_txt, "-c", "copy", final_cut])

print(f"DONE! Merged perfectly to {final_cut}")
