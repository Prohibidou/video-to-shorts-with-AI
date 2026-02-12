---
description: Interactive workflow to extract 3-minute shorts with script review
---


This workflow allows you to extract specific shorts (up to 3 minutes, aprox 3 minutes) from a YouTube video, reviewing the full script before rendering.

## Step 1: Download Subtitles

Provide the YouTube URL.

```bash
python get_subs.py [URL]
```

## Step 2: Analysis & Script Selection

The agent will analyze the `temp_analysis_output/*.vtt` file and propose 2 scripts based on your criteria (max 3 minutes).

**CRITICAL:** The agent MUST extract and display the FULL script of the proposed shorts in a `proposed_shorts.md` artifact.

**STOP:** The agent MUST STOP execution here and ask the user for approval to proceed. Do NOT render video until the user explicitly selects which shorts to generate.

## Step 3: Approval

The user need to say me which short(s) to render.

## Step 4: Render

Once the user approves, the agent will configure `shorts_extractor.py` and render the selected shorts.

