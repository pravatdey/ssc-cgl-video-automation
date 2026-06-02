# SSC CGL Complete Preparation — Daily Video Automation

Automatically generates and uploads **two SSC CGL lesson videos to YouTube every day**:

| Time (IST) | Slot | Subjects |
|---|---|---|
| **5:00 AM** | morning | General Intelligence & Reasoning → Quantitative Aptitude |
| **5:00 PM** | evening | English Comprehension → General Awareness (GK/GS) |

Each video (minimum **15 minutes**, Hindi narration) is built fully automatically:

```
Topic → LLM script (Hindi) → Gemini voice → Video (intro.mp4 + welcome) →
Branded thumbnail → PUBLIC upload → SEO description → Playlist →
Pinned comment (study notes + practice questions + answer key)
```

The full **320-topic syllabus** (`config/syllabus.yaml`) covers all 4 SSC CGL subjects so a student who watches the whole series is prepared for every exam question.

---

## How it works

- **Two independent sequences.** `progress.json` tracks `morning_next` and `evening_next`. The morning job walks Reasoning (parts 1–45) then Quant (91–124); the evening job walks English (181–207) then GA (251–278). Gaps in numbering leave room to add more topics later without renumbering.
- **Intro + welcome.** Your `assets/intro.mp4` is prepended to every video, followed by a spoken Hindi welcome ("Namaste doston! SSC CGL Complete Preparation mein aapka swagat hai…").
- **Branded thumbnails.** `assets/thumbnail_base.png` (your design) is the base of every thumbnail; the subject, topic title and part number are overlaid in the lower-left.
- **Practice questions in comments.** Every upload gets a pinned comment with study notes + practice questions, and the answer key as a reply.
- **Public.** Videos upload as `public` (set in `config/settings.yaml`).

---

## One-time setup

### 1. Install dependencies (for local runs)
```powershell
pip install -r requirements.txt
# ffmpeg must be installed and on PATH (https://ffmpeg.org/download.html)
```

### 2. API keys (free)
Create a `.env` file (or set environment variables):
```
GROQ_API_KEY=your_groq_key      # https://console.groq.com  (free)
GEMINI_API_KEY=your_gemini_key  # https://aistudio.google.com/app/apikey  (free)
```

### 3. YouTube credentials
Already copied from your reference project:
- `config/client_secrets.json`
- `config/youtube_token.json`

If the token ever expires, re-run any local upload once to refresh it.

> ⚠️ These two files are **git-ignored** — they are secrets and must never be committed.

### 4. Test locally (no upload)
```powershell
python main.py --slot morning --no-upload --part 1
```
Check `output/videos/part_001.mp4` and `output/thumbnails/part_001_thumb.png`.

### 5. Test a real (private) upload
```powershell
python main.py --slot morning --test
```

---

## Running on a schedule

### Option A — GitHub Actions (recommended, runs in the cloud, free)
1. Push this repo to GitHub.
2. Add these **repository secrets** (Settings → Secrets and variables → Actions):
   - `GROQ_API_KEY`
   - `GEMINI_API_KEY`
   - `YOUTUBE_CLIENT_SECRETS` — paste the full contents of `config/client_secrets.json`
   - `YOUTUBE_TOKEN` — paste the full contents of `config/youtube_token.json`
3. The two workflows run automatically:
   - `.github/workflows/morning-video.yml` → 23:30 UTC (5:00 AM IST)
   - `.github/workflows/evening-video.yml` → 11:30 UTC (5:00 PM IST)
4. To run on demand: Actions tab → pick a workflow → **Run workflow** (optionally set a part number or test mode).

> The two jobs share a `concurrency: cgl-progress` group so they never write `progress.json` at the same time.

### Option B — Local scheduler (your PC must stay on)
```powershell
python scheduler.py                 # runs forever at 5 AM & 5 PM IST
python scheduler.py --now morning   # run one morning video right now
```

---

## Useful commands
```powershell
python main.py --progress                  # show how many parts are done + next parts
python main.py --slot evening              # generate & upload next evening topic
python main.py --part 96 --no-upload       # render a specific part without uploading
python main.py --slot morning --test       # upload next morning topic as PRIVATE
```

---

## Project layout
```
config/syllabus.yaml      4-subject, 320-topic syllabus (slot-tagged)
config/settings.yaml      branding, voice, schedule, 15-min target
config/youtube_config.yaml SEO title/description/tags + comment templates
main.py                   slot-aware orchestrator
scheduler.py              local 5 AM / 5 PM scheduler
progress.json             morning_next / evening_next sequences
assets/intro.mp4          channel intro (prepended to every video)
assets/thumbnail_base.png branded thumbnail base
src/…                     script, tts, video, youtube, syllabus modules
```

## Adding more topics later
Append new topics to a subject's section in `config/syllabus.yaml`, keeping the
part number inside that subject's reserved range (Reasoning 1–90, Quant 91–180,
English 181–250, GA 251–320) and the correct `slot`. No code changes needed.
