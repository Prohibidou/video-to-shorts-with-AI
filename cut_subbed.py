import subprocess
from pathlib import Path

# Paths
subbed_vid = Path("output/clips/Fenómenos paranormales_ Si haces esto_ puedes terminar poseído por el demonio/01_Peligro_Cultos_Pentecostales/clip_01_Peligro_Cultos_Pentecostales_sub.mp4")
part1 = "output/clips/part1_cut.mp4"
part2 = "output/clips/part2_cut.mp4"
concat_txt = "output/clips/concat_cut.txt"
final_cut = "output/clips/clip_01_final_cut.mp4"

def run(cmd):
    print(" ".join(cmd))
    subprocess.run(cmd, check=True)

# Try cutting at 6.3s to 8.0s
# "Salís de ahí poseído" finishes around 6.0-6.2s
run(["ffmpeg", "-y", "-i", str(subbed_vid), "-to", "6.2", "-c:v", "libx264", "-preset", "superfast", "-crf", "21", "-c:a", "aac", part1])

# Resume at 7.9s "Entonces todas estas..."
run(["ffmpeg", "-y", "-i", str(subbed_vid), "-ss", "7.9", "-c:v", "libx264", "-preset", "superfast", "-crf", "21", "-c:a", "aac", part2])

with open(concat_txt, "w") as f:
    f.write(f"file 'part1_cut.mp4'\n")
    f.write(f"file 'part2_cut.mp4'\n")

run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_txt, "-c", "copy", final_cut])

print(f"DONE! Merged perfectly to {final_cut}")
