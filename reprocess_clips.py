"""Re-process both clips from the RAW 16:9 source video with right-panel-only crop."""
import subprocess
import os
from pathlib import Path

SOURCE = Path(r"output\source_video.mp4")
BASE = Path(r"output\clips\Fenómenos paranormales_ Si haces esto_ puedes terminar poseído por el demonio")

clips = [
    {
        "name": "clip_02",
        "dir": BASE / "02_Poderes_Avengers_Demonios",
        "start": "18:51",
        "end": "21:50",
        "screenshot": BASE / r"02_Poderes_Avengers_Demonios\solo debe verse esto.png",
        "header_img": BASE / r"02_Poderes_Avengers_Demonios\titulo.png",
        "header_text": "Avengers tienen poderes de endemoniados",
        "switch_time": None,
        "robust_trim": False,
        "fluidity_opt": True  # NEW: Remove dead times
    }
]

for clip_info in clips:
    d = clip_info["dir"]
    d.mkdir(parents=True, exist_ok=True)
    
    print(f"\n{'='*60}")
    print(f"Processing: {clip_info['name']} ({clip_info['start']} -> {clip_info['end']})")
    print(f"{'='*60}")
    
    # STEP 0: Prepare Source (Handle Trimming)
    temp_source = d / "trimmed_source.mp4"
    if clip_info.get("robust_trim"):
        print("   [0/3] Performing robust re-encode cut (13s-18s removal)...")
        s1 = d / "seg1.mp4"
        subprocess.run(["ffmpeg", "-y", "-ss", clip_info["start"], "-t", "13", "-i", str(SOURCE), "-c:v", "libx264", "-crf", "18", "-c:a", "aac", "-b:a", "192k", str(s1)], check=True)
        # Skip 5 seconds (from 13 to 18)
        subprocess.run(["ffmpeg", "-y", "-ss", "00:00:18", "-i", str(SOURCE.parent / SOURCE.name), "-ss", clip_info["start"], "-t", "500", "-i", str(SOURCE), "-filter_complex", f"[1:v]trim=start=18,setpts=PTS-STARTPTS[v];[1:a]atrim=start=18,asetpts=PTS-STARTPTS[a]", "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-crf", "18", str(d/"seg2_pre.mp4")], check=False) # Simplified logic below
        
        # Actually let's use the absolute timestamps for safety
        # Start: 31:49. End: 34:45.
        # Cut 13s-18s relative to 31:49:
        # 31:49 + 13s = 32:02
        # 31:49 + 18s = 32:07
        s1_end = "32:02"
        s2_start = "32:07"
        subprocess.run(["ffmpeg", "-y", "-ss", clip_info["start"], "-to", s1_end, "-i", str(SOURCE), "-c:v", "libx264", "-crf", "18", "-c:a", "aac", "-b:a", "192k", str(s1)], check=True)
        s2 = d / "seg2.mp4"
        subprocess.run(["ffmpeg", "-y", "-ss", s2_start, "-to", clip_info["end"], "-i", str(SOURCE), "-c:v", "libx264", "-crf", "18", "-c:a", "aac", "-b:a", "192k", str(s2)], check=True)
        
        concat_list = d / "list.txt"
        with open(concat_list, "w") as f:
            f.write(f"file '{s1.name}'\n")
            f.write(f"file '{s2.name}'\n")
        subprocess.run(["ffmpeg", "-y", "-f", "concat", "-i", str(concat_list), "-c", "copy", str(temp_source)], check=True)
        s1.unlink(); s2.unlink(); concat_list.unlink()
        print(f"   [OK] Source trimmed and normalized: {temp_source.name}")
    else:
        # Just extract segment
        subprocess.run(["ffmpeg", "-y", "-ss", clip_info["start"], "-to", clip_info["end"], "-i", str(SOURCE), "-c:v", "libx264", "-crf", "18", "-c:a", "aac", "-b:a", "192k", str(temp_source)], check=True)

    # STEP 1: Crop/Framing
    if clip_info.get("switch_time"):
        fc_crop = (
            "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920,drawbox=x=0:y=0:w=1080:h=1920:color=black:t=fill[bg];"
            "[0:v]crop=768:486:1152:594,scale=1080:-2:force_original_aspect_ratio=decrease[fg_spk];"
            f"[0:v]crop=1070:690:60:100,scale=1080:-2:force_original_aspect_ratio=decrease[fg_doc];"
            f"[bg][fg_spk]overlay=(W-w)/2:(H-h)/2:enable='lt(t,{clip_info['switch_time']})'[v1];"
            f"[v1][fg_doc]overlay=(W-w)/2:(H-h)/2:enable='gte(t,{clip_info['switch_time']})'[v]"
        )
    else:
        fc_crop = (
            "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920,drawbox=x=0:y=0:w=1080:h=1920:color=black:t=fill[bg];"
            "[0:v]crop=768:486:1152:594,scale=1080:-2:force_original_aspect_ratio=decrease[fg];"
            "[bg][fg]overlay=(W-w)/2:(H-h)/2[v]"
        )

    cropped = d / "cropped_final.mp4"
    print(f"   [1/3] Applying crop/zoom to {clip_info['name']}...")
    subprocess.run([
        "ffmpeg", "-y", "-i", str(temp_source),
        "-filter_complex", fc_crop,
        "-map", "[v]", "-map", "0:a",
        "-c:v", "libx264", "-preset", "fast", "-crf", "21",
        "-c:a", "aac", "-b:a", "128k",
        str(cropped)
    ], check=True)
    
    # STEP 2: Subtitles
    subbed = d / "cropped_final_sub.mp4"
    print("   [2/3] Burning subtitles (max 6 words)...")
    subprocess.run(["python", "add_subtitles.py", str(cropped), "--output", str(subbed)], check=True)
    
    # STEP 3: Visual Enhancement (Overlay + End Card)
    final = d / "final_v2.mp4"
    print("   [3/3] Applying visual overlay (Header + End-Card)...")
    enhance_cmd = ["python", "enhance_short.py", str(subbed), str(clip_info["screenshot"]), "--output", str(final)]
    if clip_info.get("header_img"):
        enhance_cmd.extend(["--header-img", str(clip_info["header_img"])])
    if clip_info.get("header_text"):
        enhance_cmd.extend(["--header-text", clip_info["header_text"]])
    
    subprocess.run(enhance_cmd, check=True)
    
    # Cleanup
    if temp_source.exists(): temp_source.unlink()
    if cropped.exists(): cropped.unlink()
    if subbed.exists(): subbed.unlink()

    print(f"   [DONE] {final}")

print("\n" + "="*60)
print("ALL CLIPS RE-PROCESSED WITH RIGHT-PANEL CROP!")
print("="*60)
