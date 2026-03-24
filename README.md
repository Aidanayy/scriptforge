# 🎬 ScriptForge

AI-powered social media script writing tool for TikTok and Instagram Reels creators.

## Setup

1. **Clone or download** this project
2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Add your Anthropic API key** — edit `.env`:
   ```
   ANTHROPIC_API_KEY=your_key_here
   ```
   Or enter it in the app via ⚙️ Settings after launching.
4. **Run the app:**
   ```bash
   streamlit run app.py
   ```
   Opens at http://localhost:8501

## Workflow

### Step 1 — Creator Profile (📋)
Fill in your niche, audience, tone, content pillars, and CTA preferences. Save your profile. This is what ScriptForge uses to write in your exact voice.

### Step 2 — Video Analyser (🎥)
Paste up to 8 YouTube or TikTok URLs. ScriptForge will:
- Transcribe each video (YouTube captions or Whisper AI)
- Use Claude to extract hooks, structure, engagement triggers, and viral patterns
- Synthesise the top patterns across all videos

### Step 3 — Script Generator (✍️)
Select your profile and video analyses, choose settings, and generate 10–15 complete scripts. Each script includes hook, body, CTA, estimated length, and engagement strategy.

## Features

- **Saved Scripts** — browse, download, and delete all your script batches
- **Quick Generate** — generate scripts with no video analysis (Claude uses niche knowledge)
- **Token usage tracking** — see estimated API cost after every call
- **Export** — download any script batch as a .txt file
- **Settings** — change Claude model, Whisper model size, manage data

## Notes

- TikTok transcription requires `ffmpeg` to be installed on your system
- Whisper models download on first use (base model = ~140MB)
- All data is stored locally in the `data/` folder as human-readable JSON
- The app works fully offline except for Claude API calls and video transcription
