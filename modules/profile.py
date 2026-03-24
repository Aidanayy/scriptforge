"""
profile.py
----------
Creator Profile module — Streamlit form + save/load logic.
"""
from __future__ import annotations

import streamlit as st
from modules.storage import save_profile, load_profile, list_profiles

NICHES = ["Finance", "Fitness", "Beauty", "Food", "Tech", "Business",
          "Lifestyle", "Entertainment", "Education", "Other"]

AGE_RANGES   = ["13–17", "18–24", "25–34", "35–44", "45–54", "55+"]
GENDERS      = ["Male", "Female", "Non-binary", "All"]
CONTENT_GOALS = ["Grow followers", "Drive sales/leads", "Educate", "Entertain", "Build brand awareness"]
TONES        = ["Casual & fun", "Professional", "Motivational", "Controversial/edgy",
                "Educational", "Storytelling", "Humorous"]
CTAS         = ["Follow for more", "Visit link in bio", "Comment below",
                "Share this video", "DM me", "Buy now"]
FREQUENCIES  = ["Daily", "3–5x per week", "1–2x per week"]


def render():
    st.markdown(
        "<h1 style='font-size:1.8rem;font-weight:900;margin-bottom:4px;'>📋 Creator Profile</h1>"
        "<div style='color:#888;font-size:0.85rem;margin-bottom:24px;'>"
        "Build your creator profile so ScriptForge can write in your exact voice and style.</div>",
        unsafe_allow_html=True,
    )

    # ── Load existing profile ─────────────────────────────────────────────────
    profiles = list_profiles()
    loaded   = {}
    if profiles:
        col_load, col_spacer = st.columns([2, 3])
        with col_load:
            choice = st.selectbox("Load saved profile", ["— New profile —"] + profiles)
        if choice != "— New profile —":
            try:
                loaded = load_profile(choice)
                st.success(f"Loaded profile: **{choice}**")
            except Exception as e:
                st.error(f"Could not load profile: {e}")

    st.divider()

    # ── Form ──────────────────────────────────────────────────────────────────
    with st.form("profile_form"):
        profile_name = st.text_input(
            "Profile name *",
            value=loaded.get("profile_name", ""),
            placeholder="e.g. Charlotte FBA, My Finance Account",
        )

        col1, col2 = st.columns(2)
        with col1:
            niche_choice = st.selectbox(
                "Niche / Industry *",
                NICHES,
                index=NICHES.index(loaded.get("niche", "Finance")) if loaded.get("niche") in NICHES else 0,
            )
            custom_niche = st.text_input(
                "Custom niche (if Other)",
                value=loaded.get("custom_niche", ""),
                placeholder="Describe your niche",
            )
        with col2:
            content_goal = st.radio(
                "Content goal *",
                CONTENT_GOALS,
                index=CONTENT_GOALS.index(loaded.get("content_goal", CONTENT_GOALS[0]))
                if loaded.get("content_goal") in CONTENT_GOALS else 0,
            )

        col3, col4 = st.columns(2)
        with col3:
            age_ranges = st.multiselect(
                "Target audience age range",
                AGE_RANGES,
                default=loaded.get("age_ranges", ["18–24", "25–34"]),
            )
        with col4:
            genders = st.multiselect(
                "Target audience gender",
                GENDERS,
                default=loaded.get("genders", ["All"]),
            )

        location = st.text_input(
            "Target audience location",
            value=loaded.get("location", ""),
            placeholder="e.g. UK-based, mainly London",
        )

        tones = st.multiselect(
            "Brand voice / tone *",
            TONES,
            default=loaded.get("tones", ["Casual & fun"]),
        )

        topics = st.text_area(
            "Key topics / content pillars *",
            value=loaded.get("topics", ""),
            placeholder="List 3–5 topics you create content about, one per line",
            height=100,
        )

        product = st.text_area(
            "Product or service being promoted (optional)",
            value=loaded.get("product", ""),
            placeholder="Describe what you sell or offer",
            height=80,
        )

        ctas = st.multiselect(
            "Call-to-action preferences",
            CTAS,
            default=loaded.get("ctas", ["Follow for more"]),
        )

        posting_freq = st.selectbox(
            "Posting frequency",
            FREQUENCIES,
            index=FREQUENCIES.index(loaded.get("posting_freq", FREQUENCIES[1]))
            if loaded.get("posting_freq") in FREQUENCIES else 1,
        )

        video_length = st.slider(
            "Typical video length (seconds)",
            min_value=15,
            max_value=90,
            value=loaded.get("video_length", 30),
            step=5,
        )

        competitors = st.text_area(
            "Competitor / inspiration accounts (optional)",
            value=loaded.get("competitors", ""),
            placeholder="List usernames, one per line",
            height=80,
        )

        unique_angle = st.text_area(
            "What makes your content unique? *",
            value=loaded.get("unique_angle", ""),
            placeholder="Describe your unique angle, style, or perspective",
            height=80,
        )

        submitted = st.form_submit_button("💾 Save Profile", use_container_width=True, type="primary")

    if submitted:
        if not profile_name.strip():
            st.error("Profile name is required.")
            return
        if not tones:
            st.error("Please select at least one brand voice / tone.")
            return
        if not topics.strip():
            st.error("Please fill in your content pillars.")
            return

        niche = custom_niche.strip() if niche_choice == "Other" and custom_niche.strip() else niche_choice

        profile = {
            "profile_name":  profile_name.strip(),
            "niche":         niche,
            "custom_niche":  custom_niche.strip(),
            "content_goal":  content_goal,
            "age_ranges":    age_ranges,
            "genders":       genders,
            "location":      location.strip(),
            "tones":         tones,
            "topics":        topics.strip(),
            "product":       product.strip(),
            "ctas":          ctas,
            "posting_freq":  posting_freq,
            "video_length":  video_length,
            "competitors":   competitors.strip(),
            "unique_angle":  unique_angle.strip(),
        }

        try:
            path = save_profile(profile_name, profile)
            st.session_state["current_profile"] = profile
            st.success(f"✅ Profile saved to `{path.name}`")
            st.balloons()
        except Exception as e:
            st.error(f"Failed to save profile: {e}")
