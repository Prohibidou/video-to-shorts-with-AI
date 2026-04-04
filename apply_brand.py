import subprocess
from pathlib import Path

# Paths
BASE = Path(r"output\clips\Fenómenos paranormales_ Si haces esto_ puedes terminar poseído por el demonio\02_Poderes_Avengers_Demonios")
INPUT = BASE / "final_v2_fluid_trimmed.mp4"
TITLE_IMG = BASE / "titulo.png"
LOGO_IMG = Path(r"C:\Users\veram\OneDrive\Documentos\long to short\Logo\logo bueno, el otro borrarlo cuando se pueda.png")
END_CARD_IMG = BASE / "video completo.png"
OUTPUT = BASE / "CLIP_02_FINAL_BRANDED.mp4"

# Escaping and text
text_stage1 = "Avengers tienen poderes de endemoniados"
text_end = "Video Completo"

# Duration of video is approx 143s
# Last 5s starting at t=138
end_start = 138

filter_complex = (
    # --- STAGE 1: Avengers Overlay (0-50s) ---
    f"[1:v]scale=-1:220[hdr_img]; "
    f"[0:v][hdr_img]overlay=x=(W-w)/2:y=240:enable='lt(t,50)'[v1]; "
    f"[v1]drawtext=font='Arial':text='{text_stage1}':"
    f"fontcolor=white:fontsize=52:x=(w-tw)/2:y=490:"
    f"bordercolor=black:borderw=2:enable='lt(t,50)'[v2]; "
    
    # --- STAGE 2: Channel Logo (50s - 138s) ---
    f"[2:v]scale=-1:120[chan_logo]; "
    f"[v2][chan_logo]overlay=x=(W-w)/2:y=340:enable='between(t,50,{end_start})'[v3]; "
    
    # --- STAGE 3: End Card (Last 5s) ---
    # Black background box
    f"[v3]drawbox=x=0:y=0:w=iw:h=ih:color=black:t=fill:enable='gte(t,{end_start})'[v4]; "
    # Large Text
    f"[v4]drawtext=font='Arial':text='{text_end}':"
    f"fontcolor=white:fontsize=80:x=(w-tw)/2:y=600:"
    f"bordercolor=white:borderw=1:enable='gte(t,{end_start})'[v5]; "
    # Thumbnail Image
    f"[3:v]scale=900:-1[thumb]; "
    f"[v5][thumb]overlay=x=(W-w)/2:y=800:enable='gte(t,{end_start})'[outv]"
)

cmd = [
    "ffmpeg", "-y",
    "-i", str(INPUT),        # 0
    "-i", str(TITLE_IMG),    # 1
    "-i", str(LOGO_IMG),     # 2
    "-i", str(END_CARD_IMG), # 3
    "-filter_complex", filter_complex,
    "-map", "[outv]",
    "-map", "0:a",
    "-c:v", "libx264", "-crf", "18", "-preset", "fast",
    "-c:a", "copy",
    str(OUTPUT)
]

print(f"Running full branding & end-card command for {OUTPUT}...")
subprocess.run(cmd, check=True)
print(f"\n[OK] Video with end-card saved: {OUTPUT}")
