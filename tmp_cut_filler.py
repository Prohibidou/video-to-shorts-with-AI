import subprocess
import sys
from pathlib import Path

# Paths
base = Path(r"c:\Users\veram\OneDrive\Documentos\long to short\output\clips\descenso_cristo\01_Se salvaron Platon Socrates y Aristoteles")
in_vid = base / "clip_01_Se salvaron Platon Socrates y Aristoteles_sub.mp4"
out_vid = base / "clip_01_Se salvaron Platon Socrates y Aristoteles_sub_no_filler.mp4"

# We found 4 extremely noticeable filler segments in the script:
# 1. 00:04:58.5 - 00:05:07.8 ("Bueno, habría que conocer... no quiero opinar")
# 2. 00:06:42.9 - 00:06:53.3 ("y acá un poco como que habría que venir leyendo... no tengo eso")
# 3. 00:07:15.0 - 00:07:22.0 ("Habría que ver el contexto... yo lo desconozco")
# 4. 00:10:07.0 - 00:10:31.5 ("Venga a ver, no no no, perdón acá yo estoy confundido, me corrijo")

keep_segments = [
    (0.0, 298.5),
    (307.8, 402.9),
    (413.3, 435.0),
    (442.0, 607.0),
    (631.5, 9999.0) # To the end
]

print("=== REMOVIENDO RELLENO Y COMENTARIOS INNECESARIOS ===")

filters = []
concat_inputs = []
# Create video and audio fragments
for i, (start, end) in enumerate(keep_segments):
    filters.append(f"[0:v]trim=start={start}:end={end},setpts=PTS-STARTPTS[v{i}];")
    filters.append(f"[0:a]atrim=start={start}:end={end},asetpts=PTS-STARTPTS[a{i}];")
    concat_inputs.append(f"[v{i}][a{i}]")

# We don't know exact duration, so end=9999.0 is fine, trim will just stop at file end.
filter_str = "".join(filters) + "".join(concat_inputs) + f"concat=n={len(keep_segments)}:v=1:a=1[outv][outa]"

cmd = [
    "ffmpeg", "-y",
    "-i", str(in_vid),
    "-filter_complex", filter_str,
    "-map", "[outv]", "-map", "[outa]",
    "-c:v", "libx264", "-preset", "fast", "-crf", "18",
    "-c:a", "aac", "-b:a", "192k",
    str(out_vid)
]

print(f"Executing surgical cuts to remove meta-commentary...")
r = subprocess.run(cmd, capture_output=True, text=True)
if r.returncode != 0:
    print(f"Error: {r.stderr[-1000:]}")
    sys.exit(1)

print(f"Cortes limpios. Video sin relleno guardado: {out_vid.name}")

# Now remove silence on top of this nicely trimmed video
silence_py = Path(r"c:\Users\veram\OneDrive\Documentos\long to short\remove_silence.py")
fluid_vid = base / "clip_01_Se salvaron Platon Socrates y Aristoteles_sub_fluid.mp4"
print("\nRe-aplicando Fluididad (cortando silencios muertos)...")
subprocess.run(["python", str(silence_py), str(out_vid), "--output", str(fluid_vid)])

# Re-build hook
build_hook = Path(r"c:\Users\veram\OneDrive\Documentos\long to short\build_10min_hook.py")
raw_vid = base / "clip_01_Se salvaron Platon Socrates y Aristoteles.mp4"
ass_path = base / "clip_01_Se salvaron Platon Socrates y Aristoteles.ass"
final_vid = base / "Video_03_Final_Horizontal_Custom.mp4"

print("\nRe-generando video final...")
cmd_hook = [
    "python", str(build_hook),
    "--raw-video", str(raw_vid),
    "--ass-file", str(ass_path),
    "--sub-fluid-video", str(fluid_vid),
    "--screenshot", r"C:\Users\veram\OneDrive\Documentos\k.png",
    "--hook-start", "154",
    "--hook-end", "169.3",
    "--crop-coords", "760:490:1100:590",
    "--output", str(final_vid)
]
subprocess.run(cmd_hook)
print("\n=== FLUJO COMPLETADO ===")
