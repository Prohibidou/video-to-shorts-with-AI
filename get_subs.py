from pathlib import Path
import subprocess
import json
import glob

import sys

def main():
    video_url = sys.argv[1] if len(sys.argv) > 1 else "https://www.youtube.com/watch?v=JxAdV9YVbsY"
    output_dir = Path("temp_analysis_output")
    output_dir.mkdir(exist_ok=True)
    
    print("Downloading subtitles...")
    cmd = [
        "yt-dlp",
        "--write-auto-sub",
        "--sub-lang", "es",
        "--skip-download",
        "--output", str(output_dir / "transcript"),
        video_url
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        return

    # Find the VTT file
    vtt_files = list(output_dir.glob("*.vtt"))
    if not vtt_files:
        print("No VTT files found.")
        print(result.stdout)
        return
        
    vtt_path = vtt_files[0]
    print(f"Subtitles downloaded to {vtt_path}")

if __name__ == "__main__":
    main()
