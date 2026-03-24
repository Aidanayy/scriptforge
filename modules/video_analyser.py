"""
video_analyser.py
-----------------
Transcribes YouTube and TikTok videos, then analyses them with Claude.
"""
from __future__ import annotations

import os
import re
import json
import tempfile
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

load_dotenv()


# ── Platform detection ────────────────────────────────────────────────────────

def _is_youtube(url: str) -> bool:
    return "youtube.com" in url or "youtu.be" in url


def _is_tiktok(url: str) -> bool:
    return "tiktok.com" in url or "vm.tiktok.com" in url


# ── Transcription ─────────────────────────────────────────────────────────────

def transcribe_video(url: str, whisper_model: str = "base") -> dict:
    """
    Returns: {"url": url, "platform": str, "transcript": str, "title": str}
    """
    url = url.strip()
    if _is_youtube(url):
        return _transcribe_youtube(url, whisper_model)
    elif _is_tiktok(url):
        return _transcribe_tiktok(url, whisper_model)
    else:
        raise ValueError(f"Unsupported URL: {url}")


def _transcribe_youtube(url: str, whisper_model: str) -> dict:
    """Try youtube-transcript-api first, fall back to yt-dlp + whisper."""
    # Extract video ID
    video_id = _extract_youtube_id(url)
    title = url  # default if we can't get title

    # Attempt 1: youtube-transcript-api
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        transcript = " ".join(t["text"] for t in transcript_list)
        return {"url": url, "platform": "youtube", "transcript": transcript, "title": title, "method": "captions"}
    except Exception:
        pass

    # Attempt 2: yt-dlp + whisper
    return _whisper_transcribe(url, "youtube", whisper_model)


def _transcribe_tiktok(url: str, whisper_model: str) -> dict:
    return _whisper_transcribe(url, "tiktok", whisper_model)


def _whisper_transcribe(url: str, platform: str, whisper_model: str) -> dict:
    """Download audio with yt-dlp and transcribe with Whisper."""
    import yt_dlp
    import whisper

    with tempfile.TemporaryDirectory() as tmp:
        audio_path = os.path.join(tmp, "audio.%(ext)s")
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": audio_path,
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "128",
            }],
            "quiet": True,
            "no_warnings": True,
        }

        title = url
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                title = info.get("title", url)
                actual_path = os.path.join(tmp, "audio.mp3")

            model = whisper.load_model(whisper_model)
            result = whisper.transcribe(model, actual_path)
            transcript = result["text"].strip()
        except Exception as e:
            raise RuntimeError(f"yt-dlp/Whisper transcription failed: {e}")

    return {"url": url, "platform": platform, "transcript": transcript, "title": title, "method": "whisper"}


def _extract_youtube_id(url: str) -> str:
    patterns = [
        r"(?:v=|youtu\.be/)([A-Za-z0-9_\-]{11})",
        r"(?:embed/)([A-Za-z0-9_\-]{11})",
        r"(?:shorts/)([A-Za-z0-9_\-]{11})",
    ]
    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)
    return url


# ── Claude analysis ───────────────────────────────────────────────────────────

ANALYSIS_PROMPT = """You are an expert short-form video strategist. Analyse the following video transcript and extract the key performance patterns.

Return your analysis as a valid JSON object with EXACTLY these keys:
{
  "hook": {
    "text": "exact first 1-3 sentences",
    "why_it_works": "explanation of why this hook is effective"
  },
  "content_structure": "description of how the video is organised (problem/solution, story arc, list format, etc.)",
  "engagement_triggers": ["trigger1", "trigger2", "trigger3"],
  "pacing": "description of how fast information is delivered, use of pauses or pattern interrupts",
  "call_to_action": {
    "text": "exact CTA used",
    "framing": "how it is framed"
  },
  "emotional_tone": "what emotion does the creator evoke and how",
  "viral_patterns": ["pattern1", "pattern2", "pattern3"],
  "script_format": {
    "approximate_word_count": 0,
    "sentence_length": "short/medium/long/mixed",
    "key_phrases": ["phrase1", "phrase2"]
  },
  "hook_type": "Question/Bold claim/Story opener/Statistic/Relatable scenario/Controversial statement/Pattern interrupt",
  "overall_score": "1-10 rating of how strong this script is and why"
}

Return ONLY valid JSON. No markdown, no explanation outside the JSON."""


def analyse_video(transcription: dict, model: str = "claude-sonnet-4-6") -> dict:
    """Send transcript to Claude and return structured analysis dict."""
    import anthropic

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    user_msg = f"""Platform: {transcription['platform'].upper()}
Title: {transcription['title']}
URL: {transcription['url']}

TRANSCRIPT:
{transcription['transcript']}

Analyse this transcript and return the structured JSON analysis."""

    try:
        message = client.messages.create(
            model=model,
            max_tokens=2048,
            system=ANALYSIS_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
        )
        raw = message.content[0].text.strip()
        # Strip markdown code fences if present
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        analysis = json.loads(raw)
        analysis["_url"]      = transcription["url"]
        analysis["_platform"] = transcription["platform"]
        analysis["_title"]    = transcription["title"]
        analysis["_usage"]    = {
            "input_tokens":  message.usage.input_tokens,
            "output_tokens": message.usage.output_tokens,
        }
        return analysis
    except json.JSONDecodeError as e:
        raise ValueError(f"Claude returned invalid JSON: {e}\n\nRaw:\n{raw[:500]}")


def patterns_summary(analyses: list[dict], model: str = "claude-sonnet-4-6") -> str:
    """Synthesise multiple analyses into 5 bullet points of key patterns."""
    import anthropic

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    analyses_text = json.dumps([{k: v for k, v in a.items() if not k.startswith("_")} for a in analyses], indent=2)

    message = client.messages.create(
        model=model,
        max_tokens=512,
        system="You are an expert short-form video strategist.",
        messages=[{"role": "user", "content":
            f"Here are {len(analyses)} video analyses:\n\n{analyses_text}\n\n"
            "Synthesise the 5 most common high-performing techniques across ALL of these videos. "
            "Return exactly 5 bullet points, each starting with '•'. Be specific and actionable."}],
    )
    return message.content[0].text.strip()


# ── MP4 transcription ─────────────────────────────────────────────────────────

def transcribe_mp4(uploaded_file, whisper_model: str = "base") -> dict:
    """Transcribe an uploaded MP4 file directly using Whisper."""
    import whisper

    with tempfile.TemporaryDirectory() as tmp:
        video_path = os.path.join(tmp, uploaded_file.name)
        with open(video_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        model = whisper.load_model(whisper_model)
        result = whisper.transcribe(model, video_path)
        transcript = result["text"].strip()

    return {
        "url": uploaded_file.name,
        "platform": "mp4",
        "transcript": transcript,
        "title": Path(uploaded_file.name).stem,
        "method": "whisper",
    }


# ── Streamlit UI ──────────────────────────────────────────────────────────────

def render():
    st.markdown(
        "<h1 style='font-size:1.8rem;font-weight:900;margin-bottom:4px;'>🎥 Video Analyser</h1>"
        "<div style='color:#555;font-size:0.85rem;margin-bottom:24px;'>"
        "Upload MP4 files or paste YouTube / TikTok URLs to transcribe and analyse what makes them high-performing.</div>",
        unsafe_allow_html=True,
    )

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key or api_key == "your_key_here":
        st.warning("⚠️ Anthropic API key not set. Go to ⚙️ Settings to add it.")
        return

    model       = st.session_state.get("model", "claude-sonnet-4-6")
    whisper_mdl = st.session_state.get("whisper_model", "base")

    # ── Profile selector ──────────────────────────────────────────────────────
    from modules.storage import list_profiles
    profiles = list_profiles()
    if profiles:
        selected_profile = st.selectbox(
            "Profile these videos belong to",
            ["— No profile —"] + profiles,
            key="analyser_profile",
            help="Tag this analysis to a profile so it only shows up for that profile in the script generator.",
        )
        st.session_state["analyser_selected_profile"] = selected_profile if selected_profile != "— No profile —" else None
    else:
        st.session_state["analyser_selected_profile"] = None

    st.divider()

    # ── Input tabs ────────────────────────────────────────────────────────────
    tab_mp4, tab_url = st.tabs(["📁 Upload MP4", "🔗 Paste URL"])

    with tab_mp4:
        uploaded_files = st.file_uploader(
            "Drop your MP4 files here (up to 8)",
            type=["mp4"],
            accept_multiple_files=True,
            label_visibility="collapsed",
        )
        if uploaded_files and len(uploaded_files) > 8:
            st.warning("Maximum 8 files at once — only the first 8 will be processed.")
            uploaded_files = uploaded_files[:8]

        col_btn_mp4, col_save_mp4 = st.columns([2, 1])
        run_mp4  = col_btn_mp4.button("🔍 Analyse Videos", type="primary", use_container_width=True, key="run_mp4")
        save_mp4 = col_save_mp4.button("💾 Save Analysis", use_container_width=True, key="save_mp4")

        if run_mp4:
            if not uploaded_files:
                st.error("Upload at least one MP4 file.")
            else:
                results  = []
                progress = st.progress(0, text="Starting…")
                total_in = total_out = 0

                for i, f in enumerate(uploaded_files):
                    progress.progress(i / len(uploaded_files), text=f"Processing {i+1}/{len(uploaded_files)}: {f.name}…")
                    try:
                        with st.spinner(f"Transcribing {f.name}…"):
                            transcription = transcribe_mp4(f, whisper_mdl)
                        with st.spinner("Analysing with Claude…"):
                            analysis = analyse_video(transcription, model)
                            total_in  += analysis.get("_usage", {}).get("input_tokens", 0)
                            total_out += analysis.get("_usage", {}).get("output_tokens", 0)
                        results.append(analysis)
                    except Exception as e:
                        st.error(f"❌ Failed on `{f.name}`: {e}")

                progress.progress(1.0, text="Done!")
                st.session_state["current_analyses"] = results
                st.info(f"🔢 Token usage — Input: {total_in:,} | Output: {total_out:,} | Est. cost: ~${(total_in*0.000003 + total_out*0.000015):.4f}")

        if save_mp4:
            _save_current_analyses()

    with tab_url:
        st.markdown("#### Paste video URLs (one per line, up to 8)")
        urls_text = st.text_area(
            "URLs",
            label_visibility="collapsed",
            height=160,
            placeholder="https://www.youtube.com/watch?v=...\nhttps://www.tiktok.com/@user/video/...",
            key="analyser_urls",
        )

        col_btn, col_save = st.columns([2, 1])
        run_btn  = col_btn.button("🔍 Analyse Videos", type="primary", use_container_width=True, key="run_url")
        save_btn = col_save.button("💾 Save Analysis", use_container_width=True, key="save_url")

        if run_btn:
            urls = [u.strip() for u in urls_text.strip().splitlines() if u.strip()][:8]
            if not urls:
                st.error("Paste at least one URL.")
            else:
                results  = []
                progress = st.progress(0, text="Starting…")
                total_in = total_out = 0

                for i, url in enumerate(urls):
                    progress.progress(i / len(urls), text=f"Processing {i+1}/{len(urls)}: {url[:60]}…")
                    try:
                        with st.spinner(f"Transcribing {url[:60]}…"):
                            transcription = transcribe_video(url, whisper_mdl)
                        with st.spinner("Analysing with Claude…"):
                            analysis = analyse_video(transcription, model)
                            total_in  += analysis.get("_usage", {}).get("input_tokens", 0)
                            total_out += analysis.get("_usage", {}).get("output_tokens", 0)
                        results.append(analysis)
                    except Exception as e:
                        st.error(f"❌ Failed on `{url}`: {e}")

                progress.progress(1.0, text="Done!")
                st.session_state["current_analyses"] = results
                st.info(f"🔢 Token usage — Input: {total_in:,} | Output: {total_out:,} | Est. cost: ~${(total_in*0.000003 + total_out*0.000015):.4f}")

        if save_btn:
            _save_current_analyses()

    # ── Display results ───────────────────────────────────────────────────────
    analyses = st.session_state.get("current_analyses", [])
    if analyses:
        st.divider()
        st.markdown(f"### {len(analyses)} Video(s) Analysed")

        titles = [a.get("_title", a.get("_url", f"Video {i+1}")) for i, a in enumerate(analyses)]
        selected = st.multiselect(
            "Select analyses to use for script generation",
            options=list(range(len(analyses))),
            default=list(range(len(analyses))),
            format_func=lambda i: titles[i],
            key="selected_analyses_idx",
        )
        st.session_state["selected_analyses"] = [analyses[i] for i in selected]

        if len(analyses) >= 2 and st.button("✨ Generate Key Patterns Summary", use_container_width=True):
            with st.spinner("Synthesising patterns…"):
                try:
                    summary = patterns_summary(analyses, model)
                    st.session_state["patterns_summary"] = summary
                except Exception as e:
                    st.error(f"Failed to generate summary: {e}")

        if "patterns_summary" in st.session_state:
            st.markdown(
                "<div class='insight-box'>"
                "<div class='insight-label'>🔑 Key Patterns Across All Videos</div>"
                + st.session_state["patterns_summary"].replace("\n", "<br>") +
                "</div>",
                unsafe_allow_html=True,
            )

        for i, analysis in enumerate(analyses):
            with st.expander(f"📹 Video {i+1}: {analysis.get('_title', analysis.get('_url', ''))[:80]}", expanded=i==0):
                hook = analysis.get("hook", {})
                st.markdown(f"**🎣 Hook:** {hook.get('text', 'N/A')}")
                st.markdown(f"*Why it works:* {hook.get('why_it_works', 'N/A')}")
                st.divider()
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown(f"**📐 Structure:** {analysis.get('content_structure', 'N/A')}")
                    st.markdown(f"**🎭 Emotional tone:** {analysis.get('emotional_tone', 'N/A')}")
                    st.markdown(f"**⏱ Pacing:** {analysis.get('pacing', 'N/A')}")
                with c2:
                    st.markdown(f"**📣 CTA:** {analysis.get('call_to_action', {}).get('text', 'N/A')}")
                    st.markdown(f"**🔥 Hook type:** {analysis.get('hook_type', 'N/A')}")
                    st.markdown(f"**⭐ Score:** {analysis.get('overall_score', 'N/A')}")
                st.markdown("**🚀 Viral patterns:**")
                for p in analysis.get("viral_patterns", []):
                    st.markdown(f"- {p}")
                st.markdown("**⚡ Engagement triggers:**")
                for t in analysis.get("engagement_triggers", []):
                    st.markdown(f"- {t}")


def _save_current_analyses():
    analyses = st.session_state.get("current_analyses", [])
    if not analyses:
        st.error("No analyses to save. Run the analyser first.")
    else:
        from modules.storage import save_analysis, timestamp_name
        profile_tag = st.session_state.get("analyser_selected_profile")
        if profile_tag:
            for a in analyses:
                a["_profile"] = profile_tag
        name = timestamp_name("analysis")
        save_analysis(name, analyses)
        label = f" [{profile_tag}]" if profile_tag else ""
        st.success(f"✅ Saved as `{name}`{label}")
