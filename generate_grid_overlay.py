import cv2
import os
import argparse
import subprocess
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="Extracts a test frame and overlays a coordinate grid.")
    parser.add_argument("video", help="Path to raw video to extract a frame from.")
    parser.add_argument("--time", default="00:00:10", help="Timestamp to extract frame (e.g. 00:00:10).")
    parser.add_argument("--output", default="grid_frame.jpg", help="Output path for the grid image.")
    args = parser.parse_args()

    video_path = Path(args.video)
    out_path = Path(args.output).absolute()
    
    if not video_path.exists():
        print(f"Error: Video {video_path} not found.")
        sys.exit(1)

    temp_frame = "temp_frame_raw.jpg"
    print(f"Extracting frame from {args.time}...")
    subprocess.run(["ffmpeg", "-y", "-i", str(video_path), "-ss", args.time, "-vframes", "1", temp_frame], 
                   capture_output=True)

    img = cv2.imread(temp_frame)
    if img is None:
        print("Error: Could not read extracted frame.")
        import sys
        sys.exit(1)

    h, w, _ = img.shape

    # Draw vertical lines
    for x in range(0, w, 100):
        cv2.line(img, (x, 0), (x, h), (255, 255, 255), 1)
        cv2.putText(img, str(x), (x + 5, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        cv2.putText(img, str(x), (x + 5, int(h * 0.8)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

    # Draw horizontal lines
    for y in range(0, h, 100):
        cv2.line(img, (0, y), (w, y), (255, 255, 255), 1)
        cv2.putText(img, str(y), (int(w * 0.7), y + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 255), 2)
        cv2.putText(img, str(y), (int(w * 0.9), y + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 255), 2)

    cv2.imwrite(str(out_path), img)
    if os.path.exists(temp_frame):
        os.remove(temp_frame)
        
    print(f"\n[OK] Cuadrícula generada en: {out_path}")
    print("Revisa la imagen y determina tu coordenada focal usando el formato: W:H:X:Y")
    print("Para encontrar: X e Y son la esquina superior izquierda. W y H son la anchura y altura del recuadro del orador.")

if __name__ == "__main__":
    main()
