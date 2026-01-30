from pathlib import Path
import json
from shorts_extractor import download_video, transcribe_audio

def main():
    video_url = "https://www.youtube.com/watch?v=JxAdV9YVbsY"
    output_dir = Path("temp_analysis_output")
    output_dir.mkdir(exist_ok=True)
    
    print("Downloading/Checking video...")
    try:
        video_path = download_video(video_url, output_dir)
    except Exception as e:
        print(f"Error downloading: {e}")
        return

    print("Transcribing...")
    # Use max_words_per_line=100 to get larger chunks for context analysis
    transcript = transcribe_audio(video_path, language="es", max_words_per_line=20)
    
    output_file = Path("full_transcript.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(transcript, f, indent=2, ensure_ascii=False)
        
    print(f"Transcript saved to {output_file}")

if __name__ == "__main__":
    main()
