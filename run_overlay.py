import subprocess
from pathlib import Path
import sys

# Import to reuse like_btn
sys.path.append(str(Path(".").absolute()))
from enhance_short import download_like_btn

clip = Path(r"output\clips\Fenómenos paranormales_ Si haces esto_ puedes terminar poseído por el demonio\01_Peligro_Cultos_Pentecostales\clip_01_Peligro_Cultos_Pentecostales_sub_v3.mp4")
screenshot = Path(r"C:\Users\veram\OneDrive\Documentos\long to short\output\clips\Fenómenos paranormales_ Si haces esto_ puedes terminar poseído por el demonio\01_Peligro_Cultos_Pentecostales\Captura de pantalla 2026-04-03 144917.png")
output = Path(r"output\clips\Fenómenos paranormales_ Si haces esto_ puedes terminar poseído por el demonio\01_Peligro_Cultos_Pentecostales\clip_01_final_overlay_v9.mp4")

cache_dir = Path("temp_analysis_output")
cache_dir.mkdir(parents=True, exist_ok=True)
like_btn = download_like_btn(cache_dir)

font_path = "C:/Windows/Fonts/arial.ttf"
escaped_font = font_path.replace(":", "\\:")

# The main 16:9 video is centered in 1080x1920
# Its Y offset is ~656 (1920-607)/2. X is 0. Width is 1080.
# The user wants to cover the top right corner of the centered video with a black block.
# Let's cover from x=680, y=650, width=400, height=350
fc = (
    f"[1:v]scale=380:-1[img]; " # screenshot width 380 height 213
    f"[2:v]scale=1000:-1,chromakey=0x00FF00:0.1:0.2,split=3[b1][b2][b3]; " # like
    f"[b1]setpts=PTS+20/TB[b1t]; "
    f"[b2]setpts=PTS+80/TB[b2t]; "
    f"[b3]setpts=PTS+140/TB[b3t]; "
    # Right panel starts at exactly 40%: x=648. Top half height adjusted to 340 to swallow the sliver.
    f"[0:v]drawbox=x=648:y=656:w=432:h=340:color=black:t=fill[v_box]; "
    # text 'video completo :' dynamically centered exactly at x=864 (which is 648 + 432/2)
    f"[v_box]drawtext=fontfile='{escaped_font}':text='video completo \\:':fontcolor=white:fontsize=36:x=864-(tw/2):y=680[v_txt]; "
    # Overlay screenshot at exact center: x=674 (864 - 190) with 380 width
    f"[v_txt][img]overlay=x=674:y=730[v_midt]; "
    # Like buttons
    f"[v_midt][b1t]overlay=x=(W-w)/2:y=1350:enable='between(t,20,29)'[v1_btn]; "
    f"[v1_btn][b2t]overlay=x=(W-w)/2:y=1350:enable='between(t,80,89)'[v2_btn]; "
    f"[v2_btn][b3t]overlay=x=(W-w)/2:y=1350:enable='between(t,140,149)'[outv]; "
    # Audio
    f"[2:a]asplit=3[a1][a2][a3]; "
    f"[a1]adelay=20000|20000[a1t]; "
    f"[a2]adelay=80000|80000[a2t]; "
    f"[a3]adelay=140000|140000[a3t]; "
    f"[0:a][a1t][a2t][a3t]amix=inputs=4:duration=first:normalize=0[outa]"
)

cmd = [
    "ffmpeg", "-y", "-i", str(clip), "-i", str(screenshot), "-i", str(like_btn),
    "-filter_complex", fc,
    "-map", "[outv]", "-map", "[outa]",
    "-c:v", "libx264", "-crf", "21", "-preset", "fast", "-c:a", "aac",
    str(output)
]
print("Running overlay...")
subprocess.run(cmd, check=True)
print(f"Saved: {output}")
