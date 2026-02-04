# 🎬 YouTube Shorts Extractor

Tool to automatically extract multiple clips from YouTube videos with **automatic subtitles** based on specific timestamps.

## ✨ Features

- 📥 Automatic YouTube video download
- ✂️ Multiple clip extraction by timestamps
- 📝 **Automatic subtitles** with AI (Whisper)
- 🎨 3 subtitle styles: modern, bold, minimal
- 📐 Vertical 9:16 format conversion
- 💾 Also exports editable SRT files

## 📋 Requirements

1. **Python 3.10+**
2. **FFmpeg** - Must be installed and in system PATH
3. Python dependencies (yt-dlp, faster-whisper)

### Install FFmpeg on Windows

```powershell
# Option 1: With winget
winget install ffmpeg

# Option 2: With chocolatey
choco install ffmpeg
```

### Install Python dependencies

```bash
pip install -r requirements.txt
```

> **Note**: The first time you run the script, the Whisper model (~500MB) will be downloaded. Subsequent runs will be faster.

## 🚀 Quick Start

### Option 1: Edit the script directly

1. Open `shorts_extractor.py`
2. Modify the configuration section:

```python
VIDEO_URL = "https://www.youtube.com/watch?v=YOUR_VIDEO"

SEGMENTS = [
    Segment("11:29", "11:43", "Clip 1 name"),
    Segment("12:59", "13:33", "Clip 2 name"),
]

# Subtitle configuration
ADD_SUBTITLES = True           # Enable automatic subtitles
SUBTITLE_STYLE = "modern"      # Styles: modern, bold, minimal
LANGUAGE = "es"                # Video language
```

3. Run:
```bash
python shorts_extractor.py
```

### Option 2: Use JSON file

1. Create a JSON file:

```json
{
    "video_url": "https://www.youtube.com/watch?v=YOUR_VIDEO",
    "segments": [
        {"start": "11:29", "end": "11:43", "name": "Clip 1"},
        {"start": "12:59", "end": "13:33", "name": "Clip 2"}
    ]
}
```

2. Run:
```bash
python batch_extractor.py my_video.json
```

## ⚙️ Batch Extractor Options

| Option | Description |
|--------|-------------|
| `--vertical` | Convert to 9:16 format for Shorts/TikTok/Reels |
| `--no-subtitles` | Disable automatic subtitles |
| `--style STYLE` | Subtitle style: `modern`, `bold`, `minimal` |
| `--lang LANGUAGE` | Language for transcription (default: `es`) |
| `--fast` | Fast mode (no subtitles, instant cut) |
| `--output PATH` | Output directory |
| `--no-keep-source` | Delete source video after extraction |

### Examples

```bash
# With subtitles (default)
python batch_extractor.py segments.json

# Bold style subtitles + vertical format
python batch_extractor.py segments.json --vertical --style bold

# No subtitles, fast mode
python batch_extractor.py segments.json --fast

# English video
python batch_extractor.py segments.json --lang en
```

## 📁 Output Structure

```
output/
├── source_video.mp4           # Original video
└── clips/
    ├── clip_01_name.mp4       # Video with burned-in subtitles
    ├── clip_01_name.srt       # Editable subtitles
    ├── clip_02_name.mp4
    ├── clip_02_name.srt
    └── ...
```

## 🎨 Subtitle Styles

| Style | Description |
|-------|-------------|
| `modern` | White Arial with black border, semi-transparent. Ideal for most videos. |
| `bold` | Large Impact with thick border. "Influencer" style. |
| `minimal` | Thin Helvetica with subtle shadow. Elegant and discreet. |

## 🧠 AI Analysis to Find Timestamps

If you don't know which parts of the video to cut, you can use AI to analyze the script and find the most impactful moments.

### Step 1: Download video subtitles

```bash
python get_subs.py
```

This downloads YouTube's automatic subtitles in VTT format to the `temp_analysis_output/` folder.

### Step 2: Analyze the script with keywords

Edit `analyze_vtt.py` and modify the `keywords` list according to what you're looking for. For example, for Catholic apologetics:

```python
keywords = [
    "eucharist", "altar", "bishop", "heresy", 
    "protestant", "Luther", "bible", "authority"
]
```

Then run:

```bash
python analyze_vtt.py
```

This generates `analysis_results.txt` with the fragments where those words appear and their timestamps.

### Step 3: Use an AI to reason

Pass the contents of `analysis_results.txt` to an AI (like Gemini or Claude) along with a prompt like this:

> "Analyze these fragments and tell me which would be the most impactful for creating YouTube Shorts that capture attention in the first 2 seconds. Give me the start and end timestamps."

The AI will filter the informative content and give you the moments of greatest "friction" or emotional impact.

### Step 4: Create the JSON and extract

With the timestamps the AI gave you, create your JSON file and run:

```bash
python batch_extractor.py my_analysis.json --vertical --style bold
```

> 📄 See `PROMPT_EXPLANATION.txt` for a detailed example of how the AI reasons when selecting clips.

## 💡 Tips

1. **First tests**: Use `--fast` to verify that the timestamps are correct before generating subtitles.

2. **Edit subtitles**: The generated `.srt` files are editable. You can correct errors and then manually burn them with FFmpeg.

3. **Better precision**: For better transcription quality, edit `shorts_extractor.py` and change the model from `"small"` to `"medium"` or `"large-v2"` (requires more RAM/time).

4. **Multiple videos**: Create a JSON file for each video/series to easily reprocess.
