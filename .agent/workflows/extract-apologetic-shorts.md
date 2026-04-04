---
description: Extract apologetic shorts from YouTube URL following PROMPT_AND_EXPLANATION.txt
---
// turbo-all

This workflow extracts apologetic shorts directly from a YouTube URL.

> [!IMPORTANT]
> **ALWAYS analyze the provided URL.** DO NOT use the database to search for existing shorts.
> Generate ONLY: shorts (~3 min). 
---

## Step by Step Process

### 1. Download video subtitles

```bash
python get_subs.py "{{VIDEO_URL}}"
```

This downloads `temp_analysis_output/transcript.es.vtt`

### 1.5. Check DB for previously processed shorts (MANDATORY)

Before analyzing the transcript, check if this URL has been processed before:

```python
from database import get_processed_segments
segments = get_processed_segments("{{VIDEO_URL}}")
```

If segments exist, display them to the user:
```
Previously processed shorts for this URL:
  ✅ ID=42 | 13:05-14:07 | approved | Iglesia_Apostolica_es_Catolica
  ❌ ID=41 | 20:30-20:40 | rejected | Verification_Test
```

**DEDUPLICATION RULE — COMPARE BY SCRIPT CONTENT, NOT TIMESTAMPS:**
A proposed short is considered a duplicate ONLY if:
- The **hook text** AND the **first seconds of the script** match an existing short in the DB.

A proposed short is NOT a duplicate if:
- The hook or script content is **different**, even if the time range overlaps with an existing short.
- The same time range was used but with a different hook / script angle.

**Do NOT skip a time range just because it overlaps with a previous short.** Only skip if the actual spoken content in the first seconds is the same.

### 2. Analyze the transcript (Claude does this directly)

Read the VTT file and look for impactful segments with these criteria:
- **Target**: Evangelicals/Protestants 
- **Key topics**: heresy, protestant, early church, eucharist, catholic, bishops, apostolic tradition
- **Hook**: The first seconds must capture immediate attention

For each identified segment, define:
- `start`: start timestamp (format MM:SS)
- `end`: end timestamp (~55-65 seconds after start)
- `name`: descriptive title for the short

### 3. MANDATORY STOP — Present proposals to user

> [!CAUTION]
> **DO NOT RENDER YET.** You MUST stop here and present ALL proposed shorts to the user.
> The user will explicitly tell you WHICH shorts to render. Only proceed to Step 4 after explicit approval.

For EACH proposed short, present:
1. 🎣 **Hook** — The exact first words spoken (verbatim)
2. 📜 **Full script** — The complete transcript text for the segment
3. 📝 **Summary** — What the short argues/proves
4. 🧠 **Why this hook** — Explain why this hook captures attention and provokes cognitive dissonance
5. ⏱ **Timestamps** — start → end
6. 📛 **Title** — Descriptive name

Wait for the user to say which shorts they want rendered (e.g., "render 1 and 3" or "render all").

### 4. Modify `shorts_extractor.py` with the APPROVED segments

Only after user approval, edit the `SEGMENTS` and `VIDEO_URL` section:

```python
VIDEO_URL = "{{VIDEO_URL}}"

SEGMENTS = [
    Segment("MM:SS", "MM:SS", "Short Title 1"),
    Segment("MM:SS", "MM:SS", "Short Title 2"),
    # ... more segments
]
```

### 4. Execute shorts extraction (Process time: ~1 min)

```bash
python shorts_extractor.py
```

### 5. Generate extended shorts (Duration: ~3 min) 
> [!CAUTION]
> `generate_extended.py` uses the DB to get shorts. Make sure the newly created shorts are in the DB.

```bash
python generate_extended.py
```

### 6. Enhance shorts with visual overlays (OPTIONAL — requires screenshot)

> [!IMPORTANT]
> This step requires the user to provide a **screenshot/thumbnail image** for the "video completo" overlay.
> The user can send a different screenshot for each video. Ask the user for the image path.

```bash
python enhance_short.py "<clip_path>" "<screenshot_path>"
```

**What it does:**
- Adds "video completo :" text + screenshot thumbnail (top-right corner, blurred zone)
- Adds animated "Like & Subscribe" button (bottom center, 3 appearances with sound)  
- Green screen is auto-removed via chromakey
- The Like button animation is auto-downloaded and cached

**Options:**
- `--like-btn <path>` — Use a custom Like button animation instead of the default
- `--output <path>` — Custom output path (default: `<clip>_final.mp4`)

### 7. Add movie-style subtitles (OPTIONAL)

> [!IMPORTANT]
> Uses `faster-whisper` with the `large-v3` model for maximum Spanish accuracy.
> First run downloads the model (~3GB). Subsequent runs use the cached version.

```bash
python add_subtitles.py "<video_path>"
```

**What it does:**
- Transcribes audio using Whisper large-v3 (high accuracy, minimal typos)
- Generates SRT + ASS subtitle files
- Burns movie-style subtitles (black background, yellowish text) into the video

**Options:**
- `--model NAME` — Whisper model: tiny, base, small, medium, large-v3 (default)
- `--output PATH` — Custom output path (default: `<clip>_sub.mp4`)
- `--srt-only` — Only generate SRT file, skip video burn-in

### 8. Remove dead times / silences (POST-PRODUCTION — no re-render)

> [!IMPORTANT]
> Apply this to the **already finished video** (after subtitles and overlays).
> It does NOT re-render the video nor the subtitles. It only cuts silent segments out.

```bash
python remove_silence.py "<final_video>"
```

**What it does:**
- Detects silences using FFmpeg `silencedetect` (default: pauses > 0.4s at -30dB)
- Cuts them out and concatenates the remaining segments
- Output: `<video>_fluid.mp4`

**Options:**
- `--threshold N` — Silence threshold in dB (default: -30)
- `--min-silence N` — Minimum silence duration in seconds to cut (default: 0.4)
- `--output PATH` — Custom output path

### 9. Trim video (POST-PRODUCTION — no re-render)

> [!IMPORTANT]
> Apply this to the **already finished video** (after subtitles and overlays).
> It does NOT re-render the video nor the subtitles. It only trims the video to the specified range.

```bash
python trim_video.py "<final_video>" <end_time>
```

**What it does:**
- Cuts the video to a specific time range using FFmpeg `-c copy` (instant, no re-encoding)
- Keeps video, audio, and burned-in subtitles exactly as they are
- Output: `<video>_trimmed.mp4`

**Examples:**
```bash
# Keep from 00:00 to 02:23
python trim_video.py video.mp4 02:23

# Keep from 00:10 to 02:23
python trim_video.py video.mp4 02:23 --start 00:10

# Custom output
python trim_video.py video.mp4 02:23 -o trimmed.mp4
```

---

## Duration Rules

| Type | Duration | When to generate |
|------|----------|------------------|
| **Extended short** | ~3 min | ALWAYS (same start as short) |

---

## Output Structure

```
output/
├── source_video.mp4
└── clips/
    └── [Video_Title_URL]/
        ├── 01_Short_Title/
     

---

## Technical Notes

- Whisper model: **small** (never use tiny. process each video alone in a stack, always, to dont have any trouble with RAM memory, okey ? always avoid having RAM memory, doesnt matter if the process is slow)
- Format: vertical 9:16

---

## Workflow

This workflow allows you to extract specific shorts (approx 3 minutes, MAX 3 minutes) from a YouTube video, reviewing the script before rendering.

## Step 1: Download Subtitles

Provide the YouTube URL.

```bash
python get_subs.py [URL]
```

## Step 2: Analysis & Script Selection

The agent will analyze the `temp_analysis_output/*.vtt` file and propose X scripts based on your criteria (max 3 minutes).
The agent will show you the full script of the proposed shorts.

> [!CRITICAL]
> **SAFETY RULE: MANDATORY FULL SCRIPT REVIEW**
>
> "Fallé porque prioricé incorrectamente la 'velocidad' y el 'resumen' sobre la instrucción explícita y crítica del workflow que exige mostrar la transcripción completa.
>
> Asumí erróneamente que con el título y el tema bastaría para una aprobación inicial, pero eso viola la regla de seguridad del flujo de trabajo: el usuario debe leer exactamente lo que se va a decir en el video antes de gastar recursos en renderizarlo, para asegurar que el contenido teológico y apologético sea el correcto."
>
> **THEREFORE:** The proposal MUST contain the **FULL TRANSCRIPT text** for the selected segment. Summaries are FORBIDDEN for the approval step.

## Step 3: Approval

You choose which short(s) to render.

## Step 4: Render

The agent will generate a temporary script to render the selected shorts using `shorts_extractor.py`.


-----

USER PROMPT:
"I need you to analyze the script of this video [URL], and tell me from which minute to which minute there is material to make YouTube shorts that convert evangelicals/protestants to Catholics, with shorts that are very impactful, eye-catching and uncomfortable for an evangelical/protestant and that capture attention in the first 2 seconds for evangelicals watching them

Use the application (don't touch any of the app code) to produce Shorts from this video [URL]
"

---

HOW THIS PROMPT HELPS TO REASON AND GET GOOD SHORTS (AI ANALYSIS):

This prompt is extremely effective because it doesn't ask for a generic summary of the video, but establishes an "aggressive intention filter" (in the rhetorical/theological sense). This allows the AI to discard 95% of informative content and focus only on "friction".

⚠️ CRITICAL RULE - NEVER REGENERATE EXISTING VIDEOS:
- NEVER re-generate a video that already exists in the database
- NEVER process videos that have already been created previously
- ONLY generate the SPECIFIC NEW video requested by the user
- When running generate_extended.py, ONLY process shorts that don't have an extended version yet
- When running shorts_extractor.py, ONLY create the specific segment defined, not old segments
- If the user asks for ONE short, create ONLY that ONE short - never batch process old ones

Reasoning Process triggered by the prompt:

1.  **Target Definition (The Intellectual Victim):**
    *   Target: Convinced Evangelical/Protestant.
    *   Psychology: Believes that the Catholic Church is apostate, idolatrous and corrupt.
    *   Derived strategy: Don't use defensive arguments ("we don't worship images"), but counterattacks that question THEIR own base ("your pastor has no authority").

2.  **The "Discomfort" Criterion (Cognitive Dissonance):**
    *   The prompt asks for it to be "uncomfortable". This discards soft teachings about love or peace.
    *   The AI looks for conflict keywords: *Heresy, Condemnation, Hell, Luther, Division, Altar*.
    *   If a segment says "Ignatius loved God", it is discarded. If it says "If you are not with Ignatius, your bread is not from God", it is selected.

3.  **The 3-4 Second Hook (POTENT HOOK DETECTION SYSTEM):**

    > ⚠️ **GATE: If a segment does NOT have a potent hook in its first 3-4 seconds, DISCARD IT IMMEDIATELY. Do not proceed with analysis.**

    #### 3.1 Hook Duration
    *   **STRICT: 3 to 4 seconds maximum.**
    *   The hook is the FIRST phrase the speaker says when the short begins.
    *   It MUST be verbatim — the video starts with the speaker saying these exact words.
    *   The segment `start` timestamp = the exact moment the speaker begins saying the hook phrase.

    #### 3.2 Potent Hook Scoring System (MANDATORY)
    
    Every candidate hook MUST be scored on **5 dimensions** (1-10 each). The total average determines if it passes:

    | Dimension | What it measures | Score 1 (weak) | Score 10 (explosive) |
    |-----------|-----------------|----------------|---------------------|
    | **Shock Value** | Does it make you stop scrolling in 1 second? | Generic theological statement | Radical claim that feels like a slap ("los herejes NO heredarán el reino de Dios") |
    | **Cognitive Dissonance** | Does it directly contradict what a Protestant believes? | Tangential topic | Directly attacks Sola Fide, Sola Scriptura, invisible church, or pastoral authority |
    | **Emotional Trigger** | Does it provoke ANGER, FEAR, or CURIOSITY instantly? | Informational/neutral tone | Provokes "Wait, WHAT?" or "That's not true!" or "How dare they!" |
    | **Specificity** | Is it a concrete, quotable claim (not vague)? | "The church teaches..." (generic) | "Pablo dice que los herejes no heredarán el reino de Dios" (specific, citable) |
    | **Completeness** | Can the hook be understood in 3-4 seconds as a complete thought? | Fragment that needs context | Self-contained bomb — fully understood on its own |

    **DISCARD THRESHOLD: Average score < 8.0 → DISCARD the segment. Do NOT include it in the proposal.**
    
    Only hooks scoring **≥ 8.0 average** are considered "extremely potent."

    #### 3.3 Hook Potency Patterns (What Makes a Hook EXPLOSIVE)
    
    **✅ POTENT patterns (use these):**
    - **Direct condemnation:** "Los herejes no heredarán el reino de Dios" → SHOCK + FEAR
    - **Authority challenge:** "Tu pastor no tiene autoridad apostólica" → ANGER + DISSONANCE  
    - **Historical proof:** "San Ignacio en el año 107 ya llamaba a la iglesia CATÓLICA" → CURIOSITY + DISSONANCE
    - **Biblical contradiction:** "Cristo dijo 'esto ES mi cuerpo', no 'esto REPRESENTA mi cuerpo'" → DISSONANCE + SPECIFICITY
    - **Personal accusation:** "Te están mintiendo sobre la historia de la iglesia" → EMOTIONAL + SHOCK
    
    **❌ WEAK patterns (auto-discard):**
    - Generic teaching: "La iglesia enseña que..." → Too soft, no shock
    - Narrative/story: "San Ignacio fue llevado a Roma..." → No immediate emotional punch
    - Internal Catholic topic: "La bienaventuranza significa..." → Doesn't target Protestants
    - Extended context needed: "Cuando leemos Efesios 14:1..." → Needs too much setup
    - Meta/channel talk: "En este canal..." → Zero theological impact

    #### 3.4 Mandatory Structured Output Template
    
    For EACH proposed short, the Agent MUST present ALL of the following:

    ```
    ## SHORT [N]: [Title]
    
    ### 🎣 HOOK (3-4 seconds)
    **Verbatim text:** "[exact words the speaker says in the first 3-4 seconds]"
    **Start timestamp:** [MM:SS]
    
    ### 📊 Hook Potency Score
    | Dimension | Score | Justification |
    |-----------|-------|---------------|
    | Shock Value | X/10 | [why] |
    | Cognitive Dissonance | X/10 | [why] |
    | Emotional Trigger | X/10 | [why] |
    | Specificity | X/10 | [why] |
    | Completeness | X/10 | [why] |
    | **AVERAGE** | **X.X/10** | **PASS/DISCARD** |
    
    ### 🔥 Why This Hook is Extremely Potent
    [2-3 sentences explaining the psychological/theological mechanism: 
    what exact reaction it triggers in a Protestant viewer in the first 3 seconds]
    
    ### 📝 Summary
    [Brief summary of the full ~3 min segment's argument]
    
    ### 📜 Full Script (~3 min)
    | Field | Value |
    |---|---|
    | Start | MM:SS |
    | End | MM:SS |
    | Duration | ~X:XX |
    
    [Complete verbatim transcript of the segment]
    ```

    #### 3.5 Analysis Process (Step by Step)
    
    1. **SCAN** the entire transcript for phrases that match POTENT patterns (§3.3)
    2. **IDENTIFY** all candidate hooks (phrases that could open a short)
    3. **SCORE** each candidate using the 5-dimension system (§3.2)  
    4. **DISCARD** all candidates scoring < 8.0 average
    5. **EXTEND** surviving hooks into ~3 min segments (find natural conclusion)
    6. **PRESENT** using the structured template (§3.4) with FULL SCRIPT
    
    > ⚠️ If scanning the entire transcript yields ZERO hooks scoring ≥ 8.0, report to the user that no potent hooks were found, rather than lowering the standard.

    #### 3.6 RULE: VERBATIM-FIRST — Hook MUST Be the FIRST Words Spoken

    > ⚠️ **NON-NEGOTIABLE GATE — If violated, DISCARD the segment IMMEDIATELY.**

    *   The hook phrase MUST be the **literal first words** the speaker says when the short begins.
    *   There can be **ZERO preceding words** before the hook. No "Sigan por ese camino...", no "Bueno...", no "Entonces...". The short opens with the speaker saying the hook — period.
    *   The `start` timestamp = the exact moment the speaker **begins saying the hook phrase**.
    *   If the impactful phrase occurs **later** in a segment (even 5 seconds later), it **CANNOT** be used as a hook. Either find a `start` time where the speaker says the hook as their opening words, or **discard** the hook entirely.
    *   **Test:** Read the transcript from the proposed `start` timestamp. Are the first spoken words the hook text? If NO → DISCARD.

    **Example of VIOLATION (SHORT 1 that was correctly rejected):**
    - Hook text: "Los que no tienen la verdadera doctrina no van a heredar el reino de Dios"
    - But the speaker's FIRST words at 31:06 were: "Sigan por ese camino, no acepten a los falsos maestros..."
    - The hook phrase appears LATER → **DISCARDED** ✗

    #### 3.7 RULE: ARGUMENTATIVE-ONLY CONTENT — Entire Short Must Argue the Hook

    > ⚠️ **The full ~3 minutes after the hook MUST be the speaker arguing, demonstrating, and defending the hook claim.**

    *   Every sentence in the short must **advance the hook's thesis** — providing evidence, biblical citations, patristic quotes, logical arguments, or emotional appeals that reinforce the hook.
    *   If the speaker **drifts** into unrelated teaching, generic doctrine, channel promotion, or tangential topics that don't reinforce the hook, the short must be **TRIMMED** to end where the on-hook argumentation stops.
    *   The short's duration should be determined by **how long the speaker stays on-topic arguing the hook**, NOT by an arbitrary 3-minute target.
    *   **Test:** For each paragraph of the script, ask: "Does this directly argue, prove, or emotionally reinforce the hook claim?" If NO for more than 1 sentence → TRIM the short to end before that drift.

    #### 3.8 RULE: NO INFORMATIONAL SHORTS — Must Provoke Emotions, Not Just Teach

    > ⚠️ **A short that merely teaches a doctrine or informs the viewer is FORBIDDEN.**

    *   The entire short — hook AND body — must **provoke emotions** in the evangelical viewer: anger, fear, doubt, discomfort, urgency, cognitive dissonance.
    *   The viewer must feel **throughout the entire short** that as an evangelical they are WRONG and must convert to Catholic Apostolic Roman.
    *   A hook that says "The early church had bishops" is **informational** → DISCARD.
    *   A hook that says "Your pastor has NO apostolic authority — he invented his own church" is **argumentative + emotional** → PASS.
    *   **Test:** Would an evangelical watching this short feel emotionally challenged, uncomfortable, and confronted at EVERY moment? If any part of the short feels like a calm classroom lecture, it **FAILS**.

    #### 3.9 SELF-CHECK GATE (Mandatory Before Presenting Any Short)

    Before presenting ANY short to the user, the Agent MUST answer these 3 questions:

    | # | Check | Question | If NO → |
    |---|-------|----------|---------|
    | 1 | Verbatim-First (§3.6) | Are the hook words the LITERAL FIRST words spoken at the `start` timestamp? | **DISCARD** the hook |
    | 2 | Argumentative-Only (§3.7) | Does every paragraph of the script argue/prove/reinforce the hook? | **TRIM** or **DISCARD** |
    | 3 | No Informational (§3.8) | Does the short provoke emotions throughout, never becoming a calm lecture? | **DISCARD** |

    > ⚠️ ALL 3 checks must pass. If ANY fails, do NOT present the short to the user.

4.  **VIDEO PURPOSE (Context for Agent):**
    These videos are created by a Catholic attempting to evangelize Protestants/Evangelicals. The goal is to:
    - Make them DOUBT their evangelical/protestant faith
    - Make them doubt that their Evangelical/Protestant church is the true one
    - Make them begin to question what they previously believed with such certainty
    - Help them understand the Catholic perspective and the evidence/proofs/arguments that support it
    - Convert them to the Catholic faith
    - Show them that the Evangelical/Protestant church is FALSE
    
    **THEOLOGICAL FOUNDATION (Agent Context):**
    - The ONLY Church of Jesus Christ is the Catholic Apostolic Roman Church
    - All other Protestant/Evangelical churches are FALSE - they are not the Church founded by Jesus Christ
    - Protestant/Evangelical denominations are heresies that teach false doctrines
    - The true Church was founded by Jesus in Matthew 16:18
    - The Church has ALWAYS been, IS, and WILL ALWAYS BE Catholic Apostolic Roman
    - The Church is NOT invisible - it is spiritual but VISIBLE in:
        * Hierarchy and authorities
        * Doctrine and teaching
        * Leaders and structure
        * Name: Catholic Apostolic Roman
    - All Protestant/Evangelical denominations are FALSE churches that Jesus does NOT want us to believe in or congregate in
    
    **⚠️ CRITICAL - VERBATIM HOOK REQUIREMENT:**
    - The video MUST begin with the speaker SAYING THE HOOK WORD BY WORD
    - The hook text displayed on screen MUST MATCH what the speaker is saying verbatim
    - This is NON-NEGOTIABLE for maximum attention capture
    - The hook is NOT an overlay - it's the actual spoken words at the start
    - When selecting a segment, find where the speaker says the impactful phrase
    - The segment start time = the moment the speaker begins saying the hook
    - This synchronization makes the short MORE POWERFUL and attention-grabbing

    **⚠️ VIDEO DURATION CRITERIA (Agent Determines Final Length):**
    
    *   **STRICT DURATION:** Approximately 3 minutes.
    *   **MAXIMUM:** 3 minutes.
    *   **MINIMUM:** 2 minutes 30 seconds (to ensure depth).
    *   **FORBIDDEN:** Do NOT generate 1-minute shorts (TikTok style). Do NOT generate videos longer than 3 minutes.
    
    **Extended short (Target: ~3 minutes):**
    - The Agent determines the EXACT duration (MUST be <= 3 minutes).
    - The video MUST end at a natural conclusion point.
    - NO incomplete sentences or incoherent endings.
    - End the video when the apologetic argument is complete.
    - The goal is to provide more evidence/context for protestant conversion.



Result:
Thanks to this specific prompt, the AI works not as a "summarizer", but as an "apologetic video editor", selecting clips surgically designed to generate debate, comments and retention, and generate cognitive dissonance in the first aprox 4 seconds of the short, which is what viralize a Short.

---

6.  **OUTPUT ORGANIZATION AND DATABASE:**

    **Video Types Generated:**
    - EXTENDED (max 3 min, agent decides exact duration, but aprox 3 minutes)
    **Folder Structure:**
    ```
    output/
    ├── source_video.mp4                    # Original downloaded video
    └── clips/
        └── [Video Title_URL]/
                └── short_extended/
                    └── clip_XX_[Name]_EXTENDED.mp4  # Extended version (~3 min)
    ```
    
    **Database Requirements (shorts_tracker.db):**
    - Store the SOURCE VIDEO URL for each video processed
    - Register each SHORT created with:
        * Video reference (URL)
        * Start/end timestamps
        * Hook text used
        * File path
        * Creation date
    - Register EXTENDED versions linked to their parent SHORT
    - Track APPROVAL STATUS from the Web UI
    
    **Web UI Integration:**
    - The Web UI mirrors the local folder organization
    - Shorts can be approved/rejected in the UI
    - Approval status is synced to the database
    - Approved shorts are marked for publishing
