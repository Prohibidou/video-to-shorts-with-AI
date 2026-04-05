import argparse
import subprocess
import sys
import os
from pathlib import Path

def time_to_seconds(time_str):
    """Converts MM:SS or HH:MM:SS to seconds float"""
    parts = list(map(float, time_str.split(':')))
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    elif len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    return float(time_str)

def main():
    parser = argparse.ArgumentParser(description="Construye un hook centrado para videos horizontales apologéticos.")
    parser.add_argument("--raw-video", required=True, help="Video original sin recortes.")
    parser.add_argument("--ass-file", required=True, help="Archivo .ass original para quemar los subtítulos exactos.")
    parser.add_argument("--sub-fluid-video", required=True, help="Video fluido principal del que se extraerá la continuación (desde el 0.0s).")
    parser.add_argument("--screenshot", required=True, help="Miniatura para el branding final de enhance_short.")
    parser.add_argument("--hook-start", required=True, help="Marca de tiempo de inicio del hook en el RAW (ej: 02:34 o 154).")
    parser.add_argument("--hook-end", required=True, help="Marca de tiempo de fin del hook.")
    parser.add_argument("--crop-coords", required=True, help="Coordenadas del orador para enfocar y centrar: W:H:X:Y (ej. 760:490:1100:590).")
    parser.add_argument("--title", default="¿Entraron al cielo Platón, Sócrates y Aristóteles?", help="Título gigante superior amarillo.")
    parser.add_argument("--teaser", default="Más adelante en este video...", help="Teaser inferior izquierdo (blanco con fondo).")
    parser.add_argument("--output", required=True, help="Archivo de salida final de 1920x1080.")

    args = parser.parse_args()

    start_sec = time_to_seconds(args.hook_start)
    end_sec = time_to_seconds(args.hook_end)
    
    out_path = Path(args.output)
    base_dir = out_path.parent
    
    hook_clip = base_dir / "temp_custom_hook_generated.mp4"
    rem_clip = base_dir / "temp_remaining_reencoded.mp4"
    hooked_video = base_dir / "temp_hooked_spliced.mp4"
    list_file = base_dir / "temp_concat_demux.txt"

    # 1. Custom Hook Generation
    print(f"\n[1/3] Generando Hook Customizado ({start_sec}s -> {end_sec}s)...")
    font_path = "C:/Windows/Fonts/arial.ttf"
    escaped_font = font_path.replace(":", "\\:")

    vf_chain = (
        f"crop={args.crop_coords},scale=1240:800,"
        f"pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black,"
        f"drawtext=fontfile='{escaped_font}':text='{args.title}':"
        f"fontcolor=yellow:fontsize=58:x=(w-tw)/2:y=60,"
        f"drawtext=fontfile='{escaped_font}':text='{args.teaser}':"
        f"fontcolor=white:fontsize=42:x=80:y=850:box=1:boxcolor=black@0.6:boxborderw=15,"
        f"setsar=1,fps=30"
    )

    cmd_hook = [
        "ffmpeg", "-y",
        "-ss", str(start_sec), "-to", str(end_sec),
        "-i", str(args.raw_video),
        "-vf", vf_chain,
        "-c:v", "libx264", "-crf", "18", "-preset", "fast",
        "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2",
        str(hook_clip)
    ]
    r = subprocess.run(cmd_hook, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"Error generando gancho visual:\n{r.stderr[-1000:]}")
        sys.exit(1)

    # 3. Concat demux (with strict CFR & PTS generation)
    print("\n[3/4] Uniendo el Nuevo Hook con el Resto (CFR estricto)...")
    filter_complex = (
        "[0:v:0]fps=30,scale=1920:1080,setsar=1,format=yuv420p[v0]; "
        "[1:v:0]fps=30,scale=1920:1080,setsar=1,format=yuv420p[v1]; "
        "[0:a:0]asetpts=PTS-STARTPTS,aformat=sample_rates=44100:channel_layouts=stereo[a0]; "
        "[1:a:0]asetpts=PTS-STARTPTS,aformat=sample_rates=44100:channel_layouts=stereo[a1]; "
        "[v0][a0][v1][a1]concat=n=2:v=1:a=1[outv][outa]"
    )

    cmd_concat = [
        "ffmpeg", "-y",
        "-i", str(hook_clip),
        "-i", str(args.sub_fluid_video),
        "-filter_complex", filter_complex,
        "-map", "[outv]", "-map", "[outa]",
        "-c:v", "libx264", "-crf", "18", "-preset", "fast",
        "-c:a", "aac", "-b:a", "192k",
        str(hooked_video)
    ]
    r = subprocess.run(cmd_concat, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"Error uniendo videos:\n{r.stderr[-1000:]}")
        sys.exit(1)

    # 4. Brand
    print("\n[4/4] Añadiendo Cierre Promocional de la Marca...")
    cmd_brand = [
        "python", "enhance_short.py",
        str(hooked_video), args.screenshot,
        "--output", str(out_path)
    ]
    r = subprocess.run(cmd_brand, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"Error aplicando branding final:\n{r.stderr}")
        sys.exit(1)

    # Cleanup
    for f in [hook_clip, rem_clip, hooked_video, list_file]:
        f.unlink(missing_ok=True)

    print(f"\n[EXITO] Workflow Horizontal completado -> {out_path.name}")

if __name__ == "__main__":
    main()
