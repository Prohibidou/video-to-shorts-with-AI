import sys
import os
import time
from faster_whisper import WhisperModel

def main():
    audio_path = "temp_analysis_output/audio.mp3"
    out_path = "temp_analysis_output/transcript.txt"
    model_size = "base"
    
    print(f"Loading {model_size} model...")
    # Run on default settings (cpu/int8 usually if no gpu)
    model = WhisperModel(model_size, compute_type="int8")
    
    print(f"Transcribing {audio_path}...")
    start_time = time.time()
    
    segments, info = model.transcribe(audio_path, language="es", beam_size=5)
    
    with open(out_path, "w", encoding="utf-8") as f:
        for idx, segment in enumerate(segments):
            line = f"[{segment.start:.2f} -> {segment.end:.2f}] {segment.text}"
            f.write(line + "\n")
            if idx % 50 == 0:
                print(line)
                
    elapsed = time.time() - start_time
    print(f"Done in {elapsed:.2f} seconds.")

if __name__ == "__main__":
    main()
