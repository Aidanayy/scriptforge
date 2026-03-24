"""
script_generator.py
-------------------
Generates batches of 10–15 short-form video scripts using Claude.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime

import streamlit as st
from dotenv import load_dotenv

from modules.storage import (
    list_profiles, load_profile,
    list_analyses, load_analysis,
    save_scripts, timestamp_name,
)

load_dotenv()

HOOK_STYLES = [
    "Question",
    "Bold claim",
    "Controversial statement",
    "Relatable scenario",
    "Shocking statistic",
    "Story opener",
    "Pattern interrupt",
]

GENERATE_SYSTEM_PROMPT = """You are an expert short-form video scriptwriter specialising in TikTok and Instagram Reels.
You have deep knowledge of what drives engagement, virality, and conversions in short-form content.

RULES FOR EVERY SCRIPT:
- The hook MUST appear in the first 3 seconds — it must be impossible to scroll past
- Scripts must be written as natural SPOKEN words, not bullet points or formal writing
- Match the exact tone and voice described in the creator profile
- Each script must be completable within the creator's stated video length preference
- Every script ends with a clear, specific CTA that matches the creator's preference
- No two scripts should use the same hook type or opening structure
- Scripts must feel native to TikTok/Reels — punchy, direct, scroll-stopping

HOOK PRINCIPLES (apply at least one per script):
- Curiosity gap: "The reason most people fail at X is NOT what you think..."
- Bold claim: "I made £10,000 in 30 days doing this one thing..."
- Relatability: "POV: you've been doing [thing] wrong your whole life"
- Controversy: "Unpopular opinion: [contrarian take on the niche]"
- Question: "What would you do if [scenario relevant to audience]?"
- Statistic: "97% of [audience] don't know this..."
- Story opener: "I almost quit [thing] until this happened..."

ENGAGEMENT STRUCTURES (rotate through these):
- Problem → Agitate → Solution
- Story arc (setup → conflict → resolution)
- List format ("5 things nobody tells you about...")
- Before/After
- Myth-busting
- Tutorial/How-to

OUTPUT FORMAT — use EXACTLY this format for each script:

SCRIPT #[N] — [Topic / Angle Title]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HOOK (0–3 seconds):
[Hook line — designed to stop the scroll]

BODY:
[Main content — formatted as natural spoken dialogue, not bullet points]

CTA:
[Call to action line]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Estimated length: ~[X] seconds
🎯 Engagement tactic: [e.g. Curiosity gap, relatability, controversy]
🔥 Hook type: [e.g. Question, Bold claim, Story opener, Statistic]

Number them clearly. Generate ALL requested scripts without stopping."""


def _build_user_prompt(
    profile: dict,
    analyses: list[dict],
    n_scripts: int,
    variety: str,
    hook_styles: list[str],
    custom_topics: str,
) -> str:
    profile_text = f"""CREATOR PROFILE:
- Name/Account: {profile.get('profile_name', 'Unknown')}
- Platform: {profile.get('platform', 'TikTok / Instagram Reels')}
- Niche: {profile.get('niche', 'General')}
- Content goal: {profile.get('content_goal', 'Grow followers')}
- Target audience age: {', '.join(profile.get('age_ranges', []))}
- Target audience gender: {', '.join(profile.get('genders', []))}
- Location: {profile.get('location', 'Not specified')}
- Brand voice/tone: {', '.join(profile.get('tones', []))}
- Typical video length: {profile.get('video_length', 30)} seconds

AUDIENCE PAIN POINTS (use these to write hooks that hit hard):
{profile.get('pain_points', 'Not specified')}

TRANSFORMATION DELIVERED (the outcome/result the audience gets):
{profile.get('transformation', 'Not specified')}

CREATOR CREDIBILITY / STORY (use for story-opener hooks and authority claims):
{profile.get('credibility', 'Not specified')}

CONTENT PILLARS:
{profile.get('topics', 'Not specified')}

PRODUCT/SERVICE:
{profile.get('product', 'Not specified')}

CTA PREFERENCES: {', '.join(profile.get('ctas', []))}
UNIQUE ANGLE: {profile.get('unique_angle', 'Not specified')}

LANGUAGE RULES:
- Always use: {profile.get('phrases_use', 'No specific phrases required')}
- Never use: {profile.get('phrases_avoid', 'No restrictions')}

VOICE EXAMPLE (match this style exactly):
{profile.get('best_content', 'No example provided — use the tone and style described above')}"""

    if analyses:
        analysis_text = "\n\nREFERENCE VIDEO PATTERNS:\n"
        for i, a in enumerate(analyses, 1):
            analysis_text += f"""
Video {i} ({a.get('_platform','').upper()}):
- Hook: {a.get('hook', {}).get('text', 'N/A')} | Why: {a.get('hook', {}).get('why_it_works', 'N/A')}
- Structure: {a.get('content_structure', 'N/A')}
- Hook type: {a.get('hook_type', 'N/A')}
- Engagement triggers: {', '.join(a.get('engagement_triggers', []))}
- Viral patterns: {', '.join(a.get('viral_patterns', []))}
- CTA: {a.get('call_to_action', {}).get('text', 'N/A')}
- Tone: {a.get('emotional_tone', 'N/A')}
"""
    else:
        analysis_text = "\n\nNo reference videos provided — use your expert knowledge of what performs well in this niche."

    topics_text = ""
    if custom_topics.strip():
        topics_text = f"\n\nCUSTOM TOPIC FOCUS:\n{custom_topics.strip()}"

    variety_text = f"\n\nVARIETY INSTRUCTION: {variety}"
    hook_text = f"\n\nHOOK STYLES TO USE (rotate through these): {', '.join(hook_styles)}" if hook_styles else ""

    return (
        f"Generate {n_scripts} complete video scripts.\n\n"
        f"{profile_text}{analysis_text}{topics_text}{variety_text}{hook_text}\n\n"
        f"Write all {n_scripts} scripts now, numbered clearly."
    )


def _parse_scripts(raw: str) -> list[dict]:
    """Parse the raw Claude output into a list of script dicts."""
    scripts = []
    # Split on SCRIPT #N pattern
    parts = re.split(r"(?=SCRIPT #\d+)", raw.strip())
    for part in parts:
        part = part.strip()
        if not part.startswith("SCRIPT #"):
            continue

        # Title line
        title_match = re.match(r"SCRIPT #(\d+)\s*[—–-]\s*(.+)", part)
        number = int(title_match.group(1)) if title_match else len(scripts) + 1
        title  = title_match.group(2).strip() if title_match else f"Script {number}"

        # Extract sections
        hook_match   = re.search(r"HOOK \(0[–—-]3 seconds?\):\s*\n(.+?)(?=\n\nBODY:|\Z)", part, re.DOTALL)
        body_match   = re.search(r"BODY:\s*\n(.+?)(?=\n\nCTA:|\Z)", part, re.DOTALL)
        cta_match    = re.search(r"CTA:\s*\n(.+?)(?=\n━+|\Z)", part, re.DOTALL)
        length_match = re.search(r"📊 Estimated length: (.+?)(?:\n|$)", part)
        tactic_match = re.search(r"🎯 Engagement tactic: (.+?)(?:\n|$)", part)
        hook_t_match = re.search(r"🔥 Hook type: (.+?)(?:\n|$)", part)

        scripts.append({
            "number":           number,
            "title":            title,
            "hook":             hook_match.group(1).strip()   if hook_match   else "",
            "body":             body_match.group(1).strip()   if body_match   else "",
            "cta":              cta_match.group(1).strip()    if cta_match    else "",
            "estimated_length": length_match.group(1).strip() if length_match else "",
            "engagement_tactic":tactic_match.group(1).strip() if tactic_match else "",
            "hook_type":        hook_t_match.group(1).strip() if hook_t_match else "",
            "raw":              part,
        })

    return scripts


def render():
    st.markdown(
        "<h1 style='font-size:1.8rem;font-weight:900;margin-bottom:4px;'>✍️ Script Generator</h1>"
        "<div style='color:#888;font-size:0.85rem;margin-bottom:24px;'>"
        "Generate 10–15 high-converting scripts based on your creator profile and video patterns.</div>",
        unsafe_allow_html=True,
    )

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key or api_key == "your_key_here":
        st.warning("⚠️ Anthropic API key not set. Go to ⚙️ Settings to add it.")
        return

    model = st.session_state.get("model", "claude-sonnet-4-6")

    # ── Profile selection ─────────────────────────────────────────────────────
    st.markdown("#### 1. Select Creator Profile")
    profiles = list_profiles()
    if not profiles:
        st.info("No profiles saved yet. Create one in 📋 Creator Profile first.")
        quick_mode = True
        profile = {}
    else:
        profile_choice = st.selectbox("Profile", profiles, key="gen_profile")
        try:
            profile = load_profile(profile_choice)
            st.session_state["current_profile"] = profile
            with st.expander("Preview profile"):
                st.json(profile)
        except Exception as e:
            st.error(f"Could not load profile: {e}")
            profile = {}
        quick_mode = False

    # ── Analysis selection ────────────────────────────────────────────────────
    st.markdown("#### 2. Reference Video Analyses (optional)")

    # Use analyses from current session or from saved files
    session_analyses = st.session_state.get("selected_analyses", [])
    saved_names      = list_analyses()

    analyses_to_use: list[dict] = []

    if session_analyses:
        use_session = st.checkbox(f"Use {len(session_analyses)} analyses from current session", value=True)
        if use_session:
            analyses_to_use = session_analyses

    if saved_names:
        chosen_saved = st.multiselect(
            "Or load saved analyses",
            saved_names,
            key="gen_analyses",
        )
        for name in chosen_saved:
            try:
                analyses_to_use.extend(load_analysis(name))
            except Exception:
                pass

    if not analyses_to_use:
        st.info("💡 No analyses selected — Quick Generate mode will be used (Claude uses its own niche knowledge).")

    # ── Generation settings ───────────────────────────────────────────────────
    st.markdown("#### 3. Generation Settings")
    col1, col2 = st.columns(2)
    with col1:
        n_scripts = st.slider("Number of scripts", min_value=10, max_value=15, value=10, key="n_scripts")
        variety   = st.radio(
            "Script variety",
            ["Maximum variety (different hooks, structures, topics)",
             "Consistent format (same structure, different topics)"],
            key="variety",
        )
    with col2:
        hook_styles = st.multiselect(
            "Hook style preferences",
            HOOK_STYLES,
            default=HOOK_STYLES[:4],
            key="hook_styles",
        )

    custom_topics = st.text_area(
        "Custom topic focus (optional — overrides profile topics)",
        placeholder="e.g. Focus on Amazon FBA for beginners, starting with no money",
        height=80,
        key="custom_topics",
    )

    # ── Generate ──────────────────────────────────────────────────────────────
    st.divider()
    gen_btn = st.button("🚀 Generate Scripts", type="primary", use_container_width=True)

    if gen_btn:
        if not profile and not quick_mode:
            st.error("Please select a profile.")
            return

        import anthropic as _anthropic

        user_msg = _build_user_prompt(
            profile, analyses_to_use, n_scripts, variety,
            hook_styles, custom_topics,
        )

        with st.spinner(f"Generating {n_scripts} scripts with Claude… this may take 30–60 seconds"):
            try:
                client = _anthropic.Anthropic(api_key=api_key)
                message = client.messages.create(
                    model=model,
                    max_tokens=8096,
                    system=GENERATE_SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": user_msg}],
                )
                raw_output = message.content[0].text
                usage = message.usage
                scripts = _parse_scripts(raw_output)

                st.session_state["current_scripts"] = scripts
                st.session_state["current_scripts_raw"] = raw_output
                st.info(
                    f"✅ {len(scripts)} scripts generated | "
                    f"🔢 Tokens — In: {usage.input_tokens:,} Out: {usage.output_tokens:,} | "
                    f"Est. cost: ~${(usage.input_tokens*0.000003 + usage.output_tokens*0.000015):.4f}"
                )
            except Exception as e:
                st.error(f"Generation failed: {e}")
                return

    # ── Display scripts ───────────────────────────────────────────────────────
    scripts = st.session_state.get("current_scripts", [])
    if scripts:
        st.divider()
        col_save, col_dl = st.columns(2)

        with col_save:
            if st.button("💾 Save Script Batch", use_container_width=True):
                name = timestamp_name("scripts")
                batch = {
                    "name":      name,
                    "generated": datetime.now().isoformat(),
                    "profile":   profile.get("profile_name", "unknown"),
                    "scripts":   scripts,
                }
                save_scripts(name, batch)
                st.success(f"✅ Saved as `{name}`")

        with col_dl:
            raw = st.session_state.get("current_scripts_raw", "")
            st.download_button(
                "⬇️ Download as .txt",
                data=raw.encode("utf-8"),
                file_name=f"scripts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain",
                use_container_width=True,
            )

        st.markdown(f"### {len(scripts)} Generated Scripts")
        for s in scripts:
            with st.expander(f"**Script #{s['number']}** — {s['title']}", expanded=s['number'] == 1):
                # Metadata row
                c1, c2, c3 = st.columns(3)
                c1.markdown(f"📊 **{s['estimated_length']}**")
                c2.markdown(f"🔥 **{s['hook_type']}**")
                c3.markdown(f"🎯 **{s['engagement_tactic']}**")
                st.divider()
                st.markdown(f"**🎣 HOOK (0–3s)**")
                st.markdown(f"> {s['hook']}")
                st.markdown(f"**📝 BODY**")
                st.markdown(s['body'])
                st.markdown(f"**📣 CTA**")
                st.markdown(f"> {s['cta']}")
                st.divider()
                # Copy button
                full_script = f"HOOK:\n{s['hook']}\n\nBODY:\n{s['body']}\n\nCTA:\n{s['cta']}"
                st.code(full_script, language=None)
