import subprocess
import os
from pathlib import Path
import sys
import time

# =====================================================================
# FIX: Force UTF-8 output on Windows to prevent UnicodeEncodeError
# (characters like arrows, tildes, etc. crash on cp1252 consoles)
# =====================================================================
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')


def safe_delete(path: Path, retries=3, wait=2):
    """Delete a file safely, retrying if it's locked by another process."""
    for attempt in range(retries):
        try:
            if path.exists():
                path.unlink()
            return True
        except PermissionError:
            if attempt < retries - 1:
                print(f"   [WARN] '{path.name}' is locked (open in another program?). "
                      f"Retrying in {wait}s... ({attempt+1}/{retries})")
                time.sleep(wait)
            else:
                print(f"   [ERROR] Cannot overwrite '{path.name}'. Close it and retry.")
                return False
    return True


def run_cmd(cmd):
    """Run a command, printing it first. Raises on failure with clear message."""
    print(f"> {' '.join(cmd)}")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed (exit {result.returncode}): {' '.join(cmd[:3])}...")

def main():
    source_video = Path(r"C:\Users\veram\.gemini\antigravity\scratch\long-videos-to-shorts-with-AI\output\source_video.mp4")
    if not source_video.exists():
        print(f"Error: {source_video} not found")
        return

    temp_dir = Path("output/temp_ultimate_v3")
    temp_dir.mkdir(parents=True, exist_ok=True)

    # =====================================================================
    # NARRATIVE ARC V3 - Hook Names Lutero + Accusation, Then Body
    #
    # HOOK (2 spliced parts):
    #   P1: "En 1520, Martín Lutero, acorralado teológicamente tras la
    #        controversia de Leipzig, al no poder justificar sus doctrinas
    #        con la tradición, la cual desconocía y no tenía acceso a ella."
    #   P2: "Entonces recurrió a esta retórica de acusar a la Iglesia
    #        Católica de ser el reino del Anticristo. Y al Papa, el Anticristo."
    #
    # BODY (chronological, contextual, entertaining):
    #   - Backstory: heterodoxia, odio, Wycliffe/Hus
    #   - Evidence: San Ignacio, San Clemente, cartas perdidas
    #   - Reasoning: libertad de interpretación
    #   - Consequence: escatología historicista
    #   - Methods: historicista, futurista, preterista
    #   - Punchline: Jesús viene 3 veces
    # =====================================================================

    cuts = [
        # --- HOOK ---
        # P1 (13s): "En 1520, MARTÍN LUTERO, acorralado teológicamente tras
        # la controversia de Leipzig, al no poder justificar sus doctrinas
        # con la tradición, la cual desconocía y no tenía acceso a ella."
        ("00:31:39.940", "13.20"),

        # P2 (13s): "Entonces recurrió a esta retórica de acusar a la Iglesia
        # Católica de ser el reino del Anticristo. Y al Papa, obviamente,
        # el Anticristo."
        ("00:32:36.460", "13.22"),

        # --- BODY: BACKSTORY ---
        # (40s): Heterodoxia → odio → Wycliffe/Hus sistematizaron el ataque
        # "Es su visión extrema y heterodoxa... los consideró herejes.
        #  Al quedarse fuera de la iglesia, el odio les llevó a llamarle
        #  anticristo. Luego tenemos a Wycliffe, Hus y Lutero...
        #  sistematizaron este lenguaje como ataque al poder temporal de Roma."
        ("00:31:00.000", "39.94"),

        # --- BODY: EVIDENCE ---
        # (21s): San Ignacio, San Clemente, tradition he didn't know
        # "Después vas a la carta de San Ignacio de Antioquía o San Clemente...
        #  Él la tradición simplemente la había oído, pero no la conocía.
        #  No conocía los fundamentos porque eran cartas perdidas."
        ("00:32:02.180", "20.84"),

        # --- BODY: REASONING ---
        # (10s): Why he made up his own rules
        # "Como no podía justificar sus doctrinas como doctrinas que hubieran
        #  creído los primeros cristianos, las justificaba con la libertad
        #  que él tenía para interpretar las escrituras."
        ("00:32:26.020", "10.44"),

        # --- BODY: CONSEQUENCE ---
        # (13s): He created historicist eschatology
        # "Lutero popularizó la escatología historicista. Esto es extremadamente
        #  importante porque ustedes cuando buscan en internet acerca de cómo
        #  se tiene que interpretar el apocalipsis..."
        ("00:32:50.700", "13.08"),

        # [ELIMINADOS 52s DE BÚSQUEDAS EN GOOGLE]

        # --- BODY: METHOD ---
        # (9s): What the historicist method is
        # "Uno de estos métodos, el historicista, es el luterano, calvinista,
        #  alvigense, el de Wycliffe."
        ("00:33:56.340", "8.96"),

        # --- BODY: WHAT IT CLAIMS ---
        # (16s): Church = Antichrist period
        # "Procura mostrar que el período de la Iglesia es el período del
        #  Anticristo... las condenas que va recibiendo la Iglesia Católica.
        #  Ese es el método historicista."
        ("00:34:07.700", "16.42"),

        # --- BODY: DISPENSATIONALISM ---
        # (21s): Futurism, rapture, 3 comings
        # "Luego está el método futurista... dispensacionalistas...
        #  rapto secreto... Jesucristo viene tres veces."
        ("00:34:25.160", "21.30"),

        # --- BODY: PRETERISM ---
        # (12s): Everything already happened
        # "El preterista dice que todo ocurrió en el pasado, con la caída
        #  de Jerusalén. Luego el idealista y el histórico gramatical."
        ("00:34:47.660", "12.32"),
    ]

    labels = ["HOOK_P1", "HOOK_P2", "BACKSTORY", "EVIDENCE", "REASONING",
              "CONSEQUENCE", "METHOD", "CLAIMS", "DISPENSATIONALISM", "PRETERISM"]

    # 1. EXTRACT ALL CUTS
    print("\n" + "=" * 60)
    print("PASO 1: Extrayendo 10 Cortes Narrativos (Hook con Lutero)")
    print("=" * 60)

    cut_files = []
    for i, ((ss, duration), label) in enumerate(zip(cuts, labels)):
        cut_file = temp_dir / f"cut_{i:02d}_{label.lower()}.mp4"
        cut_files.append(cut_file)
        print(f"\n   [{label}] ss={ss}, dur={duration}s")
        run_cmd([
            "ffmpeg", "-y", "-ss", ss, "-i", str(source_video),
            "-t", duration, "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k", "-r", "30", str(cut_file)
        ])

    # 2. CONCATENATE
    print("\n" + "=" * 60)
    print("PASO 2: Soldando Arco Narrativo (Hook -> Body)")
    print("=" * 60)

    concat_list = temp_dir / "concat.txt"
    with open(concat_list, "w") as f:
        for cf in cut_files:
            f.write(f"file '{cf.name}'\n")

    spliced_out = temp_dir / "spliced_narrative.mp4"
    run_cmd([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list),
        "-c", "copy", str(spliced_out)
    ])

    # 3. WEBCAM ISOLATION (BLACK BACKGROUND)
    print("\n" + "=" * 60)
    print("PASO 3: Aislamiento Webcam en Fondo Negro")
    print("=" * 60)

    output_dir = Path("output/clips/01_la_verdadera_razon_lutero")
    output_dir.mkdir(parents=True, exist_ok=True)
    base_file = output_dir / "short1_narrative_base.mp4"

    dur_cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration",
               "-of", "default=noprint_wrappers=1:nokey=1", str(spliced_out)]
    res = subprocess.run(dur_cmd, capture_output=True, text=True)
    duration = float(res.stdout.strip())
    print(f"   Duración total: {duration:.1f}s ({int(duration//60)}:{int(duration%60):02d})")

    # Title text burned above the speaker
    title_line1 = "Lutero estaba acorralado,"
    title_line2 = "y acuso al papa de ser anticristo"
    font_path = "C:/Windows/Fonts/arialbd.ttf"
    escaped_font = font_path.replace(":", "\\:")

    filter_complex = (
        f"color=c=black:s=1080x1920:d={duration+1}[bg_black];"
        f"[0:v]crop=753:473:1148:587,scale=1080:-2:force_original_aspect_ratio=decrease,setsar=1[webcam];"
        f"[bg_black][webcam]overlay=(W-w)/2:(H-h)/2:shortest=1[v_base];"
        f"[v_base]drawtext=fontfile='{escaped_font}':"
        f"text='{title_line1}':"
        f"fontcolor=white:fontsize=52:borderw=3:bordercolor=black:"
        f"x=(w-tw)/2:y=470[v_t1];"
        f"[v_t1]drawtext=fontfile='{escaped_font}':"
        f"text='{title_line2}':"
        f"fontcolor=white:fontsize=52:borderw=3:bordercolor=black:"
        f"x=(w-tw)/2:y=540[outv]"
    )

    cmd = [
        "ffmpeg", "-y", "-i", str(spliced_out),
        "-filter_complex", filter_complex,
        "-map", "[outv]", "-map", "0:a",
        "-c:v", "libx264", "-crf", "18", "-preset", "fast",
        "-c:a", "aac", "-b:a", "128k",
        str(base_file)
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # 4. SUBTITLES (WHISPER MEDIUM)
    print("\n" + "=" * 60)
    print("PASO 4: Subtítulos (MEDIUM)")
    print("=" * 60)
    run_cmd([sys.executable, "add_subtitles.py", str(base_file), "--model", "medium"])

    sub_file = output_dir / "short1_narrative_base_sub.mp4"

    # 5. ENHANCE (OVERLAYS)
    print("\n" + "=" * 60)
    print("PASO 5: Overlays Finales")
    print("=" * 60)
    thumbnail = output_dir / "thumbnail_new.png"
    final_file = output_dir / "SHORT_01_LUTERO_FINAL.mp4"
    if not safe_delete(final_file):
        final_file = output_dir / "SHORT_01_LUTERO_FINAL_new.mp4"
        print(f"   [FALLBACK] Writing to: {final_file.name}")
    run_cmd([sys.executable, "enhance_short.py", str(sub_file), str(thumbnail),
             "--output", str(final_file)])

    size_mb = final_file.stat().st_size / (1024 * 1024)
    print(f"\n{'=' * 60}")
    print(f"¡SHORT NARRATIVO COMPLETADO!")
    print(f"Duración: {int(duration//60)}:{int(duration%60):02d}")
    print(f"Tamaño: {size_mb:.1f} MB")
    print(f"Archivo: {final_file}")
    print(f"{'=' * 60}")

if __name__ == "__main__":
    main()
