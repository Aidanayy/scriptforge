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
Your only job is to write scripts that keep people watching. Retention is everything.
Every word earns its place. If a line doesn't pull the viewer forward, cut it.

CORE RULES:
- Hook lands in the first 3 seconds — the viewer must feel they cannot leave
- Natural SPOKEN words only. One short sentence per line. Never paragraphs or lists.
- Ultra short sentences. Direct. Punchy. Conversational. UK English always (mum not mom, £ not $).
- No two scripts use the same hook format or structure
- Scripts range 25–40 seconds. Vary the length — not all the same.
- Do NOT mention specific tools or apps unless they are central to the story
- Do NOT write filming directions — the creator handles all production
- Focus entirely on the words. Make every line pull the viewer into the next.

RETENTION TECHNIQUES — weave these throughout:
- Open loops: raise a question or tension early that only gets answered at the end
- Pattern interrupts: unexpected turns that make the viewer reset and keep watching
- Micro-rewards: small payoffs every few lines (a surprising stat, a relatable moment, a reveal)
- Stakes: make the viewer feel something is at risk — money, time, a mistake they might be making
- Pace variation: short punchy lines followed by a slightly longer one to create rhythm
- Direct address: talk to ONE person, not an audience. "You" not "people".

HOOK FORMATS (ranked by real performance for this creator):
1. Time challenge: "X minutes in [store] and I found..."
2. Calling out: "Stop doing X" / "Avoid these X"
3. Controversial admission: "I've stopped doing X. Here's why."
4. Superlative: "Biggest / Best / Worst / Craziest..."
5. Money moment: "I just found £X" / "I lost £X" / "£X profit..."
6. Secret reveal: "There's a code in [store] nobody talks about."
7. Relatable situation: "POV: you're in [store] with no idea what you're doing."

LOOPING ENDINGS (use on most scripts — this is critical):
The last line must connect back into the hook so the video loops seamlessly on repeat.
The viewer reaches the end and flows straight back into the beginning without noticing.
This is one of the biggest drivers of watch time for this creator.
Example:
  HOOK: "10 minutes in Home Bargains and I found £140 profit."
  LAST LINE: "And all of that in just 10 minutes in Home Bargains."
Only use "Follow for more" occasionally as an alternative. Never use link CTAs.

PRODUCT PLACEHOLDERS:
Shopping and store visit scripts use XXXXX for product names and £XXXXX for prices.
These are filled in on shoot day when the actual products are found.
Only use real numbers in educational or story-based scripts with no live product find.

ENGAGEMENT STRUCTURES (rotate across the batch):
- Problem → Agitate → Solution
- Story arc: setup → conflict → resolution
- Myth-bust: "Everyone thinks X. But actually..."
- Countdown / list with a twist at the end
- Before / After
- Fast tutorial with a hook reveal at the end

OUTPUT FORMAT — use EXACTLY this for each script:

SCRIPT #[N] — [Topic / Angle Title]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HOOK (0-3 seconds):
[Hook line]

BODY:
[One short spoken sentence per line, blank line between each]

CTA:
[Final line — loops back to hook, or Follow for more]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Estimated length: ~[X] seconds
🎯 Retention technique: [what keeps people watching]
🔥 Hook type: [type]

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
- Niche: {profile.get('custom_niche') or profile.get('niche', 'General')}
- Brand voice/tone: {', '.join(profile.get('tones', []))}
- Typical video length: {profile.get('video_length', 30)} seconds

CREATOR BIO (understand who this person is):
{profile.get('creator_bio', 'Not specified')}

AUDIENCE (who is watching and why):
- Age: {', '.join(profile.get('age_ranges', []))}
- Gender: {', '.join(profile.get('genders', []))}
- Location: {profile.get('location', 'UK')}
{profile.get('audience_note', '')}

AUDIENCE PAIN POINTS (write hooks that hit these directly):
{profile.get('pain_points', 'Not specified')}

TRANSFORMATION DELIVERED:
{profile.get('transformation', 'Not specified')}

CREATOR CREDIBILITY (use in story hooks and authority claims):
{profile.get('credibility', 'Not specified')}

CONTENT PILLARS:
{profile.get('topics', 'Not specified')}

PRODUCT/SERVICE BEING PROMOTED:
{profile.get('product', 'Not specified')}

CTA RULES (follow these exactly):
{profile.get('cta_rules', 'End with Follow for more or a looping line.')}

PRODUCT PLACEHOLDER RULE:
{profile.get('product_placeholder_rule', 'Use XXXXX for unknown product names and prices.')}

LOOPING ENDING EXAMPLE:
{profile.get('looping_example', 'Last line should echo the hook.')}

UNIQUE ANGLE: {profile.get('unique_angle', 'Not specified')}

LANGUAGE RULES:
- Always use: {profile.get('phrases_use', 'No specific phrases required')}
- Never use: {profile.get('phrases_avoid', 'No restrictions')}

TOP PERFORMING HOOKS AND VOICE REFERENCE (match this style exactly):
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

    shop_text = ""
    if profile.get("shop_list", "").strip():
        shop_text = f"\n\nSHOP LIST — STORES AT THIS SHOOT LOCATION:\n{profile['shop_list'].strip()}\nUse these stores when writing shopping trip and store visit scripts. Spread the scripts across different stores where possible — don't repeat the same store too often."

    topics_text = ""
    if custom_topics.strip():
        topics_text = f"\n\nCUSTOM TOPIC FOCUS:\n{custom_topics.strip()}"

    variety_text = f"\n\nVARIETY INSTRUCTION: {variety}"
    hook_text = f"\n\nHOOK STYLES TO USE (rotate through these): {', '.join(hook_styles)}" if hook_styles else ""

    return (
        f"Generate {n_scripts} complete video scripts.\n\n"
        f"{profile_text}{analysis_text}{shop_text}{topics_text}{variety_text}{hook_text}\n\n"
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
        hook_match   = re.search(r"HOOK\s*\([^)]*\):\s*\n(.+?)(?=\n\nBODY:|\Z)", part, re.DOTALL)
        body_match   = re.search(r"BODY:\s*\n(.+?)(?=\n\nCTA:|\Z)", part, re.DOTALL)
        cta_match    = re.search(r"CTA:\s*\n(.+?)(?=\n━+|\n📊|\Z)", part, re.DOTALL)
        length_match = re.search(r"📊 Estimated length: (.+?)(?:\n|$)", part)
        tactic_match = re.search(r"🎯 (?:Retention technique|Engagement tactic): (.+?)(?:\n|$)", part)
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

    session_analyses = st.session_state.get("selected_analyses", [])
    saved_names      = list_analyses()
    current_profile_name = profile.get("profile_name", "") if profile else ""

    analyses_to_use: list[dict] = []

    if session_analyses:
        use_session = st.checkbox(f"Use {len(session_analyses)} analyses from current session", value=True)
        if use_session:
            analyses_to_use = session_analyses

    if saved_names:
        # Filter saved analyses to those tagged to the current profile, with option to show all
        def _analyses_for_profile(names: list[str], profile_name: str) -> list[str]:
            """Return saved analysis names tagged to this profile (or untagged)."""
            matched = []
            for n in names:
                try:
                    data = load_analysis(n)
                    tags = {a.get("_profile") for a in data}
                    if not profile_name or not any(tags - {None}):
                        matched.append(n)
                    elif profile_name in tags:
                        matched.append(n)
                except Exception:
                    pass
            return matched

        profile_analyses = _analyses_for_profile(saved_names, current_profile_name)
        other_count = len(saved_names) - len(profile_analyses)

        show_all = st.checkbox(
            f"Show all saved analyses ({other_count} from other profiles hidden)",
            value=False,
            key="gen_show_all_analyses",
        ) if other_count > 0 else False

        display_names = saved_names if show_all else profile_analyses

        if display_names:
            chosen_saved = st.multiselect(
                "Load saved analyses",
                display_names,
                key="gen_analyses",
            )
            for name in chosen_saved:
                try:
                    analyses_to_use.extend(load_analysis(name))
                except Exception:
                    pass
        elif not session_analyses:
            st.caption("No saved analyses for this profile yet.")

    if not analyses_to_use:
        st.info("💡 No analyses selected — Quick Generate mode will be used (Claude uses its own niche knowledge).")

    # ── Generation settings ───────────────────────────────────────────────────
    st.markdown("#### 3. Generation Settings")
    col1, col2 = st.columns(2)
    with col1:
        n_scripts = st.slider("Number of scripts", min_value=1, max_value=12, value=10, key="n_scripts")
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
