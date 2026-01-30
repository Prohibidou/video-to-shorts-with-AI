# 🎬 YouTube Shorts Extractor

Herramienta para extraer automáticamente múltiples clips de videos de YouTube con **subtítulos automáticos** basándose en timestamps específicos.

## ✨ Características

- 📥 Descarga automática de videos de YouTube
- ✂️ Extracción de múltiples clips por timestamps
- 📝 **Subtítulos automáticos** con IA (Whisper)
- 🎨 3 estilos de subtítulos: modern, bold, minimal
- 📐 Conversión a formato vertical 9:16
- 💾 Exporta también archivos SRT editables

## 📋 Requisitos

1. **Python 3.10+**
2. **FFmpeg** - Debe estar instalado y en el PATH del sistema
3. Dependencias Python (yt-dlp, faster-whisper)

### Instalar FFmpeg en Windows

```powershell
# Opción 1: Con winget
winget install ffmpeg

# Opción 2: Con chocolatey
choco install ffmpeg
```

### Instalar dependencias Python

```bash
pip install -r requirements.txt
```

> **Nota**: La primera vez que ejecutes el script, se descargará el modelo de Whisper (~500MB). Las siguientes ejecuciones serán más rápidas.

## 🚀 Uso Rápido

### Opción 1: Editar el script directamente

1. Abre `shorts_extractor.py`
2. Modifica la sección de configuración:

```python
VIDEO_URL = "https://www.youtube.com/watch?v=TU_VIDEO"

SEGMENTS = [
    Segment("11:29", "11:43", "Nombre del clip 1"),
    Segment("12:59", "13:33", "Nombre del clip 2"),
]

# Configuración de subtítulos
ADD_SUBTITLES = True           # Activar subtítulos automáticos
SUBTITLE_STYLE = "modern"      # Estilos: modern, bold, minimal
LANGUAGE = "es"                # Idioma del video
```

3. Ejecuta:
```bash
python shorts_extractor.py
```

### Opción 2: Usar archivo JSON

1. Crea un archivo JSON:

```json
{
    "video_url": "https://www.youtube.com/watch?v=TU_VIDEO",
    "segments": [
        {"start": "11:29", "end": "11:43", "name": "Clip 1"},
        {"start": "12:59", "end": "13:33", "name": "Clip 2"}
    ]
}
```

2. Ejecuta:
```bash
python batch_extractor.py mi_video.json
```

## ⚙️ Opciones del Batch Extractor

| Opción | Descripción |
|--------|-------------|
| `--vertical` | Convierte a formato 9:16 para Shorts/TikTok/Reels |
| `--no-subtitles` | Desactiva subtítulos automáticos |
| `--style ESTILO` | Estilo de subtítulos: `modern`, `bold`, `minimal` |
| `--lang IDIOMA` | Idioma para transcripción (default: `es`) |
| `--fast` | Modo rápido (sin subtítulos, corte instantáneo) |
| `--output RUTA` | Directorio de salida |
| `--no-keep-source` | Elimina el video fuente después de extraer |

### Ejemplos

```bash
# Con subtítulos (default)
python batch_extractor.py segments.json

# Subtítulos estilo bold + formato vertical
python batch_extractor.py segments.json --vertical --style bold

# Sin subtítulos, modo rápido
python batch_extractor.py segments.json --fast

# Video en inglés
python batch_extractor.py segments.json --lang en
```

## 📁 Estructura de Salida

```
output/
├── source_video.mp4           # Video original
└── clips/
    ├── clip_01_nombre.mp4     # Video con subtítulos quemados
    ├── clip_01_nombre.srt     # Subtítulos editables
    ├── clip_02_nombre.mp4
    ├── clip_02_nombre.srt
    └── ...
```

## 🎨 Estilos de Subtítulos

| Estilo | Descripción |
|--------|-------------|
| `modern` | Arial blanco con borde negro, semi-transparente. Ideal para la mayoría de videos. |
| `bold` | Impact grande con borde grueso. Estilo "influencer". |
| `minimal` | Helvetica delgada con sombra sutil. Elegante y discreto. |

## 💡 Tips

1. **Primeras pruebas**: Usa `--fast` para verificar que los timestamps son correctos antes de generar subtítulos.

2. **Editar subtítulos**: Los archivos `.srt` generados son editables. Puedes corregir errores y luego quemar manualmente con FFmpeg.

3. **Mejor precisión**: Para mejor calidad de transcripción, edita `shorts_extractor.py` y cambia el modelo de `"small"` a `"medium"` o `"large-v2"` (requiere más RAM/tiempo).

4. **Múltiples videos**: Crea un archivo JSON por cada video/serie para poder reprocesar fácilmente.
