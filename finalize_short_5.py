import subprocess
import sys
from pathlib import Path

def finalize_short_5_fix_layout(video_path, screenshot_path, like_btn_path, logo_path, output_path):
    # Font path for Windows
    font_path = "C:/Windows/Fonts/arial.ttf"
    escaped_font = font_path.replace(":", "\\:")

    # We want exactly 175 seconds (trimmed last 5 seconds total)
    target_duration = 175.0
    end_card_duration = 5.0
    end_start = target_duration - end_card_duration

    # Header Lines
    line1 = "Los Catolicos se inventan doctrinas !"
    line2 = "Dicen los evangelicos"
    
    # Timestamps for the Like & Subscribe button
    like_times = [
        {"start": 15, "end": 24},
        {"start": 100, "end": 109}
    ]

    # Positions
    title_y1 = 400
    title_y2 = 510
    logo_y = 400
    like_y = 1350 # Moved up to be completely above the YouTube Shorts buttons and description

    # Building Filter Complex
    # Inputs: 0=Video, 1=Screenshot, 2=Like1, 3=Like2, 4=Logo
    
    filters = [
        # 1. Scale and delay assets
        f"[1:v]scale=800:-1[sc_img]",
        f"[2:v]setpts=PTS+15/TB,scale=800:-1,chromakey=0x00FF00:0.1:0.2[lk1]",
        f"[3:v]setpts=PTS+100/TB,scale=800:-1,chromakey=0x00FF00:0.1:0.2[lk2]",
        f"[4:v]scale=850:-1[lg_img]",
        
        # 2. Main video chain
        # A. Title (0-50s)
        f"[0:v]drawtext=fontfile='{escaped_font}':text='{line1}':"
        f"fontcolor=white:fontsize=55:x=(w-tw)/2:y={title_y1}:"
        f"bordercolor=black:borderw=4:enable='lt(t,50)'[v_t1]",
        
        f"[v_t1]drawtext=fontfile='{escaped_font}':text='{line2}':"
        f"fontcolor=white:fontsize=50:x=(w-tw)/2:y={title_y2}:"
        f"bordercolor=black:borderw=4:enable='lt(t,50)'[v_t2]",
        
        # B. Logo (50s-End)
        f"[v_t2][lg_img]overlay=x=(W-w)/2:y={logo_y}:enable='between(t,50,{end_start})'[v_lg]",
        
        # C. Like Button (Time 1 & 2)
        f"[v_lg][lk1]overlay=x=(W-w)/2:y={like_y}:enable='between(t,15,24)'[v_b1]",
        f"[v_b1][lk2]overlay=x=(W-w)/2:y={like_y}:enable='between(t,100,109)'[v_b2]",
        
        # D. End Card
        f"[v_b2]drawbox=x=0:y=0:w=1080:h=1920:color=black:t=fill:enable='gte(t,{end_start})'[v_eb]",
        f"[v_eb]drawtext=fontfile='{escaped_font}':text='video completo':"
        f"fontcolor=white:fontsize=80:x=(w-tw)/2:y=700:enable='gte(t,{end_start})'[v_ect]",
        f"[v_ect][sc_img]overlay=x=(W-w)/2:y=850:enable='gte(t,{end_start})'[outv]",
        
        # E. Audio Filtering
        f"[2:a]adelay=15000|15000[a1t]",
        f"[3:a]adelay=100000|100000[a2t]",
        f"[0:a][a1t][a2t]amix=inputs=3:duration=first:normalize=0[outa]"
    ]

    filter_complex = "; ".join(filters)

    cmd = [
        "ffmpeg", "-y",
        "-t", str(target_duration),
        "-i", str(video_path),
        "-i", str(screenshot_path),
        "-i", str(like_btn_path),
        "-i", str(like_btn_path),
        "-i", str(logo_path),
        "-filter_complex", filter_complex,
        "-map", "[outv]",
        "-map", "[outa]",
        "-c:v", "libx264", "-crf", "18", "-preset", "veryfast",
        "-c:a", "aac", "-b:a", "192k",
        str(output_path)
    ]

    print(f"Executing ULTIMATE DELUXE FINAL RENDERING (Fixed Layout)...")
    subprocess.run(cmd)

if __name__ == "__main__":
    v = Path(r"c:\Users\veram\OneDrive\Documentos\long to short\output\clips\short_5_bible_vs_tradition\short_5_raw_sub_fluid.mp4")
    s = Path(r"C:\Users\veram\.gemini\antigravity\brain\90f55589-7aa5-47e0-b20a-73c03a27c9c8\media__1775338779606.png")
    l = Path(r"c:\Users\veram\OneDrive\Documentos\long to short\temp_analysis_output\like_btn.webm")
    lg = Path(r"C:\Users\veram\OneDrive\Documentos\long to short\Logo\logo que va arriba de Leonardo.png")
    o = Path(r"c:\Users\veram\OneDrive\Documentos\long to short\output\clips\short_5_bible_vs_tradition\short_5_FINAL_DELUXE_HEADER.mp4")
    finalize_short_5_fix_layout(v, s, l, lg, o)
