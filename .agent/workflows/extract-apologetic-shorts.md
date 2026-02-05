---
description: Extract apologetic shorts from YouTube URL following PROMPT_AND_EXPLANATION.txt
---
// turbo-all

This workflow extracts apologetic shorts directly from a YouTube URL.

> [!IMPORTANT]
> **ALWAYS analyze the provided URL.** DO NOT use the database to search for existing shorts.
> Generate ONLY: Shorts (~1 min) + Extended (~3 min). **NEVER generate Long (~10 min)** unless explicitly requested.
> Every Shorts (~1 min) have one related Extended (~3 min) video. dont forget to make both
---

## Step by Step Process

### 1. Download video subtitles

```bash
python get_subs.py "{{VIDEO_URL}}"
```

This downloads `temp_analysis_output/transcript.es.vtt`

### 2. Analyze the transcript (Claude does this directly)

Read the VTT file and look for impactful segments with these criteria:
- **Target**: Evangelicals/Protestants 
- **Key topics**: heresy, protestant, early church, eucharist, catholic, bishops, apostolic tradition
- **Hook**: The first seconds must capture immediate attention

For each identified segment, define:
- `start`: start timestamp (format MM:SS)
- `end`: end timestamp (~55-65 seconds after start)
- `name`: descriptive title for the short

### 3. Modify `shorts_extractor.py` with the segments

Edit the `SEGMENTS` and `VIDEO_URL` section:

```python
VIDEO_URL = "{{VIDEO_URL}}"

SEGMENTS = [
    Segment("MM:SS", "MM:SS", "Short Title 1"),
    Segment("MM:SS", "MM:SS", "Short Title 2"),
    # ... more segments
]
```

### 4. Execute shorts extraction (~1 min)

```bash
python shorts_extractor.py
```

### 5. Generate Extended (~3 min) for the newly created shorts

> [!CAUTION]
> `generate_extended.py` uses the DB to get shorts. Make sure the newly created shorts are in the DB.
> **DO NOT generate Long videos (generate_long.py) unless the user explicitly requests it.**

```bash
python generate_extended.py
```

---

## Duration Rules

| Type | Duration | When to generate |
|------|----------|------------------|
| **Short** | ~1 min (55-65s) | ALWAYS |
| **Extended** | ~3 min | ALWAYS (same start as short) |
| **Long** | ~10 min | ONLY if user requests it |

---

## Output Structure

```
output/
├── source_video.mp4
└── clips/
    └── [Video_Title]/
        ├── 01_Short_Title/
        │   ├── clip_01_Title.mp4      # Short ~1 min
        │   └── extended/
        │       └── clip_01_EXTENDED.mp4 # Extended ~3 min
        └── ...
```

---

## Technical Notes

- Whisper model: **small** (never use tiny. process each video alone in a stack, always, to dont have any trouble with RAM memory, okey ? always avoid having RAM memory, doesnt matter if the process is slow)
- Format: vertical 9:16
- Subtitles: hardcoded, bold style
- Visual hook: first ~4 seconds with fixed text
