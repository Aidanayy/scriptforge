"""
ScriptForge — AI-powered social media script writing tool
for TikTok and Instagram Reels creators.
"""
from __future__ import annotations

import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ScriptForge",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Inject CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
[data-testid="stSidebar"] { background: #0d0d0d; }
[data-testid="stSidebar"] * { color: #e0e0e0 !important; }
.stButton > button { border-radius: 8px; font-weight: 600; }
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #7C3AED, #4F46E5);
    border: none; color: white !important;
}
.stButton > button[kind="primary"]:hover { opacity: 0.9; }
div[data-testid="metric-container"] {
    background: #111; border: 1px solid #222; border-radius: 10px; padding: 12px;
}
</style>
""", unsafe_allow_html=True)


# ── Imports ───────────────────────────────────────────────────────────────────
from modules import profile as profile_module
from modules import video_analyser as analyser_module
from modules import script_generator as generator_module
from modules.storage import list_scripts, load_scripts, delete_scripts


# ── Session state defaults ────────────────────────────────────────────────────
def _init_state():
    defaults = {
        "page":            "📋 Creator Profile",
        "model":           "claude-sonnet-4-6",
        "whisper_model":   "base",
        "current_profile": {},
        "current_analyses": [],
        "selected_analyses": [],
        "current_scripts": [],
        "current_scripts_raw": "",
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)

_init_state()


# ── Sidebar ───────────────────────────────────────────────────────────────────
def _sidebar() -> str:
    with st.sidebar:
        st.markdown(
            "<div style='font-size:1.8rem;font-weight:900;letter-spacing:-0.02em;"
            "color:#7C3AED;margin-bottom:2px;'>🎬 ScriptForge</div>"
            "<div style='font-size:0.72rem;color:#555;letter-spacing:0.12em;"
            "text-transform:uppercase;margin-bottom:20px;'>AI Script Writing Tool</div>",
            unsafe_allow_html=True,
        )
        st.divider()

        page = st.radio(
            "Navigation",
            options=[
                "📋 Creator Profile",
                "🎥 Video Analyser",
                "✍️ Script Generator",
                "📁 Saved Scripts",
                "⚙️ Settings",
            ],
            label_visibility="collapsed",
            key="nav_radio",
        )

        st.divider()

        # Status indicators
        api_ok      = bool(os.getenv("ANTHROPIC_API_KEY", "").strip()) and os.getenv("ANTHROPIC_API_KEY") != "your_key_here"
        profile_ok  = bool(st.session_state.get("current_profile"))
        analyses_ok = bool(st.session_state.get("selected_analyses"))
        scripts_ok  = bool(st.session_state.get("current_scripts"))

        st.markdown(
            f"<div style='font-size:0.75rem;color:#555;line-height:2;'>"
            f"{'✅' if api_ok else '❌'} API Key<br>"
            f"{'✅' if profile_ok else '⬜'} Profile loaded<br>"
            f"{'✅' if analyses_ok else '⬜'} Analyses ready<br>"
            f"{'✅' if scripts_ok else '⬜'} Scripts generated"
            f"</div>",
            unsafe_allow_html=True,
        )

        st.divider()
        st.markdown(
            "<div style='font-size:0.65rem;color:#333;text-align:center;'>ScriptForge v1.0</div>",
            unsafe_allow_html=True,
        )

    return page


# ── Settings page ─────────────────────────────────────────────────────────────
def _page_settings():
    st.markdown(
        "<h1 style='font-size:1.8rem;font-weight:900;margin-bottom:4px;'>⚙️ Settings</h1>",
        unsafe_allow_html=True,
    )

    env_path = Path(__file__).parent / ".env"

    st.markdown("#### Anthropic API Key")
    current_key = os.getenv("ANTHROPIC_API_KEY", "")
    new_key = st.text_input(
        "API Key",
        value=current_key if current_key != "your_key_here" else "",
        type="password",
        placeholder="sk-ant-...",
        label_visibility="collapsed",
    )
    if st.button("Save API Key", use_container_width=True):
        if new_key.strip():
            # Update .env file
            env_content = f"ANTHROPIC_API_KEY={new_key.strip()}\n"
            env_path.write_text(env_content, encoding="utf-8")
            os.environ["ANTHROPIC_API_KEY"] = new_key.strip()
            st.success("✅ API key saved. Restart the app for changes to take full effect.")
        else:
            st.error("Please enter a valid API key.")

    st.divider()
    st.markdown("#### Claude Model")
    model = st.selectbox(
        "Default model",
        ["claude-sonnet-4-6", "claude-opus-4-6"],
        index=0 if st.session_state.get("model") == "claude-sonnet-4-6" else 1,
    )
    st.session_state["model"] = model
    st.caption("Sonnet is faster and cheaper. Opus is more capable for complex scripts.")

    st.divider()
    st.markdown("#### Whisper Model (TikTok transcription)")
    whisper = st.selectbox(
        "Whisper model size",
        ["tiny", "base", "small", "medium"],
        index=["tiny", "base", "small", "medium"].index(st.session_state.get("whisper_model", "base")),
    )
    st.session_state["whisper_model"] = whisper
    st.caption("Larger models are more accurate but slower. 'base' is a good balance.")

    st.divider()
    st.markdown("#### Data Management")
    if st.button("🗑️ Clear all saved data", type="secondary", use_container_width=True):
        from modules.storage import PROFILES_DIR, ANALYSES_DIR, SCRIPTS_DIR
        for d in (PROFILES_DIR, ANALYSES_DIR, SCRIPTS_DIR):
            for f in d.glob("*.json"):
                f.unlink()
        st.success("All saved data cleared.")
        st.rerun()


# ── Saved Scripts page ────────────────────────────────────────────────────────
def _page_saved_scripts():
    st.markdown(
        "<h1 style='font-size:1.8rem;font-weight:900;margin-bottom:4px;'>📁 Saved Scripts</h1>"
        "<div style='color:#888;font-size:0.85rem;margin-bottom:24px;'>"
        "Browse and export your saved script batches.</div>",
        unsafe_allow_html=True,
    )

    names = list_scripts()
    if not names:
        st.info("No saved scripts yet. Generate some in ✍️ Script Generator.")
        return

    for name in reversed(names):
        with st.expander(f"📄 {name}", expanded=False):
            try:
                batch = load_scripts(name)
                scripts = batch.get("scripts", [])
                st.caption(
                    f"Generated: {batch.get('generated', 'Unknown')} | "
                    f"Profile: {batch.get('profile', 'Unknown')} | "
                    f"{len(scripts)} scripts"
                )

                # Download full batch
                raw_text = "\n\n".join(
                    f"SCRIPT #{s['number']} — {s['title']}\n"
                    f"{'━'*35}\n"
                    f"HOOK:\n{s['hook']}\n\n"
                    f"BODY:\n{s['body']}\n\n"
                    f"CTA:\n{s['cta']}\n"
                    f"{'━'*35}\n"
                    f"📊 {s['estimated_length']}\n"
                    f"🎯 {s['engagement_tactic']}\n"
                    f"🔥 {s['hook_type']}"
                    for s in scripts
                )

                col_dl, col_del = st.columns([3, 1])
                with col_dl:
                    st.download_button(
                        "⬇️ Download batch as .txt",
                        data=raw_text.encode("utf-8"),
                        file_name=f"{name}.txt",
                        mime="text/plain",
                        use_container_width=True,
                        key=f"dl_{name}",
                    )
                with col_del:
                    if st.button("🗑️ Delete", key=f"del_{name}", use_container_width=True):
                        delete_scripts(name)
                        st.rerun()

                # Individual scripts
                for s in scripts:
                    st.divider()
                    st.markdown(f"**Script #{s['number']} — {s['title']}**")
                    c1, c2, c3 = st.columns(3)
                    c1.caption(f"📊 {s['estimated_length']}")
                    c2.caption(f"🔥 {s['hook_type']}")
                    c3.caption(f"🎯 {s['engagement_tactic']}")
                    st.markdown(f"🎣 **Hook:** {s['hook']}")
                    st.markdown(f"📝 **Body:** {s['body'][:200]}{'…' if len(s['body'])>200 else ''}")
                    st.markdown(f"📣 **CTA:** {s['cta']}")
                    full = f"HOOK:\n{s['hook']}\n\nBODY:\n{s['body']}\n\nCTA:\n{s['cta']}"
                    st.code(full, language=None)

            except Exception as e:
                st.error(f"Could not load batch: {e}")


# ── Router ────────────────────────────────────────────────────────────────────
def main():
    page = _sidebar()

    if   "Creator Profile"  in page: profile_module.render()
    elif "Video Analyser"   in page: analyser_module.render()
    elif "Script Generator" in page: generator_module.render()
    elif "Saved Scripts"    in page: _page_saved_scripts()
    elif "Settings"         in page: _page_settings()


if __name__ == "__main__":
    main()
