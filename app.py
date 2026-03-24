"""
ReelHaus — AI-powered short-form video script writing tool
for TikTok and Instagram Reels creators.
"""
from __future__ import annotations

import os
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

load_dotenv()

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ReelHaus",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Imports ───────────────────────────────────────────────────────────────────
from modules import profile as profile_module
from modules import video_analyser as analyser_module
from modules import script_generator as generator_module
from modules.storage import list_scripts, load_scripts, delete_scripts


# ── Session state defaults ────────────────────────────────────────────────────
def _init_state():
    defaults = {
        "page":             "✍️ Script Generator",
        "model":            "claude-sonnet-4-6",
        "whisper_model":    "base",
        "current_profile":  {},
        "current_analyses": [],
        "selected_analyses":[],
        "current_scripts":  [],
        "current_scripts_raw": "",
        "authenticated":    False,
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)

_init_state()


# ── CSS ───────────────────────────────────────────────────────────────────────
def _inject_css(hide_sidebar: bool = False):
    sidebar_hide = """
    [data-testid="stSidebar"],
    [data-testid="stSidebarCollapsedControl"],
    [data-testid="collapsedControl"] { display: none !important; }
    """ if hide_sidebar else """
    button[data-testid="stSidebarCollapseButton"],
    [data-testid="stSidebarCollapsedControl"] { display: none !important; }
    """

    st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700;900&display=swap');

/* ── Keyframes ── */
@keyframes slideUp {{
    from {{ opacity: 0; transform: translateY(22px); }}
    to   {{ opacity: 1; transform: translateY(0);    }}
}}
@keyframes slideRight {{
    from {{ opacity: 0; transform: translateX(-18px); }}
    to   {{ opacity: 1; transform: translateX(0);     }}
}}
@keyframes scaleIn {{
    from {{ opacity: 0; transform: scale(0.96); }}
    to   {{ opacity: 1; transform: scale(1);    }}
}}
@keyframes fadeIn {{
    from {{ opacity: 0; }}
    to   {{ opacity: 1; }}
}}
@keyframes orbDrift {{
    0%, 100% {{ transform: translate(0px, 0px);    }}
    33%       {{ transform: translate(-15px, 20px); }}
    66%       {{ transform: translate(15px, -10px); }}
}}
@keyframes logoGlow {{
    0%, 100% {{ text-shadow: none; }}
    50%       {{ text-shadow: 0 0 40px rgba(255,255,255,0.3), 0 0 80px rgba(124,58,237,0.2); }}
}}
@keyframes btnGradient {{
    0%   {{ background-position: 0% center;   }}
    100% {{ background-position: 200% center; }}
}}
@keyframes insightBorder {{
    0%   {{ background-position: 0 0, 0% 50%;   }}
    100% {{ background-position: 0 0, 300% 50%; }}
}}

*, body, .stApp {{ font-family: 'Roboto', sans-serif !important; }}
.stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {{
    background-color: #050505 !important;
}}

/* Ambient orb */
.stApp::before {{
    content: '';
    position: fixed;
    top: -30%; left: -20%;
    width: 140%; height: 140%;
    background:
        radial-gradient(ellipse at 20% 20%, rgba(124,58,237,0.04) 0%, transparent 55%),
        radial-gradient(ellipse at 80% 80%, rgba(79,70,229,0.04) 0%, transparent 55%),
        radial-gradient(ellipse at 60% 10%, rgba(167,139,250,0.025) 0%, transparent 45%);
    animation: orbDrift 14s ease-in-out infinite;
    pointer-events: none;
    z-index: 0;
}}

.main .block-container {{
    padding-top: 2rem !important;
    max-width: 100% !important;
    transition: opacity 0.35s ease, transform 0.35s ease;
}}

/* ── Sidebar ── */
[data-testid="stSidebar"] {{
    background-color: #080808 !important;
    border-right: 1px solid #141414;
}}
[data-testid="stSidebar"] * {{ color: #ffffff !important; }}

/* Hide radio circles */
[data-testid="stSidebar"] [data-testid="stRadio"] [role="radio"],
[data-testid="stSidebar"] [data-testid="stRadio"] [aria-checked],
[data-testid="stSidebar"] [data-testid="stRadio"] input[type="radio"],
[data-testid="stSidebar"] [data-testid="stRadio"] label > div:has([role="radio"]),
[data-testid="stSidebar"] [data-testid="stRadio"] label > div:has([aria-checked]),
[data-testid="stSidebar"] [data-testid="stRadio"] label > span:first-child {{
    display: none !important;
    width: 0 !important;
    height: 0 !important;
}}

/* Nav items */
[data-testid="stSidebar"] [data-testid="stRadio"] label {{
    display: flex !important;
    align-items: center !important;
    padding: 10px 14px !important;
    border-radius: 8px !important;
    cursor: pointer !important;
    font-size: 0.95rem !important;
    font-weight: 500 !important;
    color: #777 !important;
    -webkit-text-fill-color: #777 !important;
    border-left: 3px solid transparent !important;
    transition: background 0.15s, border-color 0.15s !important;
    margin: 2px 0 !important;
    line-height: 1.35 !important;
}}
[data-testid="stSidebar"] [data-testid="stRadio"] label:hover {{
    background: rgba(255,255,255,0.05) !important;
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
    border-left-color: rgba(124,58,237,0.4) !important;
}}
[data-testid="stSidebar"] [data-testid="stRadio"] label:has([aria-checked="true"]) {{
    background: rgba(124,58,237,0.12) !important;
    border-left-color: #7C3AED !important;
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
    font-weight: 700 !important;
}}
[data-testid="stSidebar"] [data-testid="stRadio"] [aria-checked="true"] + label {{
    background: rgba(124,58,237,0.12) !important;
    border-left-color: #7C3AED !important;
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
    font-weight: 700 !important;
}}
[data-testid="stSidebar"] [data-testid="stRadio"] > div {{ gap: 0 !important; }}
[data-testid="stSidebar"] .stRadio > div {{
    animation: slideRight 0.4s cubic-bezier(0.22, 1, 0.36, 1) 0.05s both;
}}
{sidebar_hide}

/* ── Typography ── */
body, p, span, div, label, h1, h2, h3, h4 {{ color: #ffffff !important; }}
h1 {{ font-weight: 900 !important; letter-spacing: -0.02em; animation: slideUp 0.4s cubic-bezier(0.22,1,0.36,1) both; }}
h2 {{ font-weight: 700 !important; animation: slideUp 0.4s cubic-bezier(0.22,1,0.36,1) both; }}
h3 {{ font-weight: 600 !important; animation: slideUp 0.4s cubic-bezier(0.22,1,0.36,1) both; }}

/* ── Metric cards ── */
[data-testid="metric-container"] {{
    background: #0e0e0e !important;
    border: 1px solid #1c1c1c;
    border-radius: 12px;
    padding: 16px !important;
    animation: slideUp 0.5s cubic-bezier(0.22, 1, 0.36, 1) both;
    transition: border-color 0.25s, box-shadow 0.25s, transform 0.25s !important;
}}
[data-testid="column"]:nth-child(1) [data-testid="metric-container"] {{ animation-delay: 0.04s; }}
[data-testid="column"]:nth-child(2) [data-testid="metric-container"] {{ animation-delay: 0.10s; }}
[data-testid="column"]:nth-child(3) [data-testid="metric-container"] {{ animation-delay: 0.16s; }}
[data-testid="column"]:nth-child(4) [data-testid="metric-container"] {{ animation-delay: 0.22s; }}
[data-testid="metric-container"]:hover {{
    border-color: rgba(124,58,237,0.5) !important;
    box-shadow: 0 0 24px rgba(124,58,237,0.14), 0 0 48px rgba(79,70,229,0.08) !important;
    transform: translateY(-4px) !important;
}}
[data-testid="metric-container"] [data-testid="stMetricValue"] {{
    background: linear-gradient(135deg, #7C3AED, #4F46E5);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    font-weight: 800 !important;
    font-size: 1.5rem !important;
}}
[data-testid="metric-container"] [data-testid="stMetricLabel"] {{
    color: #999 !important;
    font-size: 0.72rem !important;
    text-transform: uppercase;
    letter-spacing: 0.1em;
}}

/* ── Buttons ── */
.stButton > button {{
    background: linear-gradient(135deg, #7C3AED 0%, #4F46E5 50%, #7C3AED 100%) !important;
    background-size: 200% auto !important;
    color: #fff !important;
    border: none !important;
    font-weight: 700 !important;
    border-radius: 10px !important;
    font-size: 0.95rem !important;
    letter-spacing: 0.02em;
    animation: btnGradient 3s linear infinite,
               scaleIn 0.35s cubic-bezier(0.22, 1, 0.36, 1) 0.05s both !important;
    box-shadow: 0 4px 18px rgba(124,58,237,0.3) !important;
    transition: transform 0.15s, box-shadow 0.15s !important;
}}
.stButton > button:hover {{
    opacity: 1 !important;
    transform: translateY(-3px) scale(1.02) !important;
    box-shadow: 0 10px 32px rgba(124,58,237,0.5) !important;
}}
.stButton > button:active {{
    transform: translateY(0) scale(0.97) !important;
    box-shadow: 0 2px 8px rgba(124,58,237,0.3) !important;
}}

/* ── Inputs & textareas ── */
.stTextInput input, .stTextArea textarea {{
    background: #0e0e0e !important;
    color: #ffffff !important;
    border: 1px solid #222 !important;
    border-radius: 10px !important;
    font-size: 0.95rem !important;
    transition: border-color 0.2s, box-shadow 0.2s !important;
}}
.stTextInput input:focus, .stTextArea textarea:focus {{
    border-color: #7C3AED !important;
    box-shadow: 0 0 0 2px rgba(124,58,237,0.2), 0 0 20px rgba(124,58,237,0.1) !important;
    outline: none !important;
}}
[data-testid="stSelectbox"] > div > div,
[data-testid="stMultiSelect"] > div > div {{
    background: #0e0e0e !important;
    border: 1px solid #222 !important;
    border-radius: 10px !important;
    color: #ffffff !important;
}}

/* ── Expanders ── */
[data-testid="stExpander"] {{
    background: #0a0a0a !important;
    border: 1px solid #1a1a1a !important;
    border-radius: 12px !important;
    overflow: hidden !important;
    transition: border-color 0.2s, box-shadow 0.2s;
    animation: slideUp 0.45s cubic-bezier(0.22, 1, 0.36, 1) both;
    margin-bottom: 8px !important;
}}
[data-testid="stExpander"]:hover {{
    border-color: rgba(124,58,237,0.3) !important;
    box-shadow: 0 4px 20px rgba(124,58,237,0.07) !important;
}}
[data-testid="stExpander"] summary {{
    padding: 14px 18px !important;
    font-weight: 600 !important;
}}

/* ── Code blocks (script copy area) ── */
[data-testid="stCode"] {{
    background: #0a0a0a !important;
    border: 1px solid #1a1a1a !important;
    border-radius: 10px !important;
    animation: scaleIn 0.4s cubic-bezier(0.22, 1, 0.36, 1) both;
}}

/* ── Insight / info boxes ── */
.insight-box {{
    background: linear-gradient(#0d0814, #0d0814) padding-box,
                linear-gradient(135deg, #7C3AED, #4F46E5, #9315E0, #7C3AED) border-box !important;
    border: 1px solid transparent !important;
    background-size: 100% 100%, 300% 100% !important;
    border-radius: 10px;
    padding: 14px 18px;
    margin-bottom: 20px;
    font-size: 0.88rem;
    animation: slideRight 0.45s cubic-bezier(0.22, 1, 0.36, 1) 0.05s both,
               insightBorder 4s linear 0.5s infinite !important;
}}
.insight-label {{
    font-size: 0.68rem; font-weight: 700; letter-spacing: 0.14em;
    color: #a78bfa !important; margin-bottom: 6px; text-transform: uppercase;
}}

.stat-card {{
    background: #0a0a0a; border: 1px solid #181818; border-radius: 10px;
    padding: 14px 18px; margin-bottom: 10px;
    animation: slideUp 0.4s cubic-bezier(0.22, 1, 0.36, 1) both;
    transition: border-color 0.2s, box-shadow 0.2s, transform 0.2s;
}}
.stat-card:hover {{
    border-color: rgba(124,58,237,0.3) !important;
    box-shadow: 0 4px 20px rgba(124,58,237,0.08) !important;
    transform: translateY(-2px);
}}
.stat-label {{ font-size: 0.72rem; color: #888 !important; text-transform: uppercase; letter-spacing: 0.08em; }}
.stat-value {{ font-size: 1.4rem; font-weight: 800; background: linear-gradient(135deg,#7C3AED,#4F46E5); -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text; }}

.info-note {{
    background: #0a0a0a; border: 1px solid #1c1c1c; border-radius: 10px;
    padding: 12px 16px; margin-bottom: 16px; font-size: 0.82rem; color: #888 !important;
    animation: slideRight 0.45s cubic-bezier(0.22, 1, 0.36, 1) 0.05s both;
}}

/* ── Dividers ── */
hr {{
    border: none !important;
    height: 1px !important;
    background: linear-gradient(90deg, transparent, rgba(124,58,237,0.5), rgba(79,70,229,0.5), transparent) !important;
    margin: 24px 0 !important;
    animation: fadeIn 0.6s ease 0.2s both;
    opacity: 0.6;
}}

/* ── Tabs ── */
[data-testid="stTabs"] [role="tab"] {{ color: #888 !important; font-weight: 500 !important; transition: color 0.2s !important; }}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {{
    color: #a78bfa !important;
    border-bottom: 2px solid #7C3AED !important;
    text-shadow: 0 0 12px rgba(124,58,237,0.4);
}}

/* ── Dataframes ── */
[data-testid="stDataFrame"] {{
    background: #0a0a0a !important;
    border-radius: 10px;
    animation: fadeIn 0.5s ease 0.12s both;
}}

/* ── Captions / status ── */
[data-testid="stCaptionContainer"] {{ animation: fadeIn 0.5s ease 0.1s both; color: #888 !important; }}
[data-testid="stStatusContainer"] {{
    background: #0a0a0a !important;
    border: 1px solid #1a1a1a !important;
    border-radius: 10px !important;
}}

/* ── Landing / login ── */
.landing-logo {{
    font-size: 3.2rem; font-weight: 900; letter-spacing: -0.03em; line-height: 1;
    background: linear-gradient(135deg, #a78bfa, #818cf8);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
    animation: slideUp 0.6s cubic-bezier(0.22, 1, 0.36, 1) both,
               logoGlow 5s ease-in-out 0.8s infinite !important;
}}
.landing-tagline {{
    font-size: 0.88rem; color: #555 !important; letter-spacing: 0.14em;
    text-transform: uppercase; margin-bottom: 40px;
    animation: fadeIn 0.6s ease 0.18s both;
}}

/* ── Custom scrollbar ── */
.main ::-webkit-scrollbar {{ width: 5px; height: 5px; }}
.main ::-webkit-scrollbar-track {{ background: #050505; }}
.main ::-webkit-scrollbar-thumb {{
    background: linear-gradient(180deg, #7C3AED, #4F46E5);
    border-radius: 99px;
}}
[data-testid="stSidebar"], [data-testid="stSidebar"] * {{
    scrollbar-width: none !important;
    -ms-overflow-style: none !important;
    overflow-x: hidden !important;
}}
[data-testid="stSidebar"] ::-webkit-scrollbar,
[data-testid="stSidebar"]::-webkit-scrollbar {{ display: none !important; width: 0 !important; }}

/* ── Hide default chrome ── */
#MainMenu, footer {{ visibility: hidden; }}
header[data-testid="stHeader"] {{ background: transparent !important; }}
div[data-testid="stSidebarCollapseButton"],
[data-testid="stSidebarCollapsedControl"],
[data-testid="collapsedControl"],
[data-testid="stIconMaterial"] {{
    display: none !important;
    visibility: hidden !important;
}}

/* ── Checkbox ── */
[data-testid="stCheckbox"] label {{ font-size: 0.85rem !important; color: #aaa !important; }}

/* ── Section header ── */
.section-header {{ font-size: 1.1rem; font-weight: 700; color: #ffffff !important; margin-top: 24px; margin-bottom: 12px; animation: fadeIn 0.5s ease 0.12s both; }}

/* ── Footer ── */
.rh-footer {{
    text-align: center; font-size: 0.72rem; color: #282828 !important;
    margin-top: 48px; padding: 16px 0; border-top: 1px solid #111;
}}

/* ── Slider ── */
[data-testid="stSlider"] [data-baseweb="slider"] [data-testid="stTickBarMin"],
[data-testid="stSlider"] [data-baseweb="slider"] [data-testid="stTickBarMax"] {{
    color: #555 !important;
}}

/* ── Info/warning/success boxes ── */
[data-testid="stAlert"] {{
    border-radius: 10px !important;
    border: 1px solid #222 !important;
    background: #0a0a0a !important;
    animation: slideUp 0.35s cubic-bezier(0.22,1,0.36,1) both;
}}

/* ── Script copy code block ── */
pre {{ background: #0a0a0a !important; border: 1px solid #1a1a1a !important; border-radius: 10px !important; }}
</style>
""", unsafe_allow_html=True)


# ── Page fade transition ──────────────────────────────────────────────────────
def _page_fade():
    components.html("""
<script>
(function() {
    try {
        try { parent.document.querySelector('.main').scrollTo({top:0,behavior:'instant'}); } catch(e) {}
        try { parent.document.documentElement.scrollTop = 0; } catch(e) {}

        try {
            var style = parent.document.getElementById('rh-sidebar-noscroll');
            if (!style) {
                style = parent.document.createElement('style');
                style.id = 'rh-sidebar-noscroll';
                style.textContent = '[data-testid="stSidebar"] > div:first-child { overflow-y: hidden !important; scrollbar-width: none !important; } [data-testid="stSidebar"] > div:first-child::-webkit-scrollbar { display: none !important; width: 0 !important; }';
                parent.document.head.appendChild(style);
            }
        } catch(e) {}

        var el = parent.document.querySelector('.main .block-container');
        if (!el) return;
        el.style.transition = 'none';
        el.style.opacity = '0';
        el.style.transform = 'translateY(10px)';
        el.offsetHeight;
        requestAnimationFrame(function() {
            requestAnimationFrame(function() {
                el.style.transition = 'opacity 0.38s cubic-bezier(0.22, 1, 0.36, 1), transform 0.38s cubic-bezier(0.22, 1, 0.36, 1)';
                el.style.opacity = '1';
                el.style.transform = 'translateY(0)';
            });
        });

        // Sidebar nav patch
        (function() {
            var attempts = 0;
            function patchNav() {
                attempts++;
                try {
                    var doc = parent.document;
                    var labels = doc.querySelectorAll('[data-testid="stSidebar"] [data-testid="stRadio"] label');
                    if (!labels.length) {
                        var all = doc.querySelectorAll('[data-testid="stSidebar"] label');
                        labels = Array.from(all).filter(function(l) {
                            return l.querySelector('[role="radio"],[aria-checked],input[type="radio"]');
                        });
                    }
                    if (labels.length < 3 && attempts < 25) { setTimeout(patchNav, 200); return; }
                    labels.forEach(function(label) {
                        label.querySelectorAll('[role="radio"],[aria-checked],input[type="radio"],svg').forEach(function(el) {
                            el.style.cssText = 'display:none!important;width:0!important;height:0!important;';
                            var p = el.parentElement;
                            if (p && p !== label && p.children.length === 1) {
                                p.style.cssText = 'display:none!important;width:0!important;height:0!important;';
                            }
                        });
                        var BASE = 'display:flex!important;align-items:center!important;padding:10px 14px!important;' +
                                   'border-radius:8px!important;cursor:pointer!important;font-size:0.95rem!important;' +
                                   'font-weight:500!important;color:#777!important;-webkit-text-fill-color:#777!important;' +
                                   'border-left:3px solid transparent!important;margin:2px 0!important;' +
                                   'transition:background 0.15s,border-color 0.15s!important;line-height:1.35!important;';
                        if (!label.dataset.rhPatched) {
                            label.dataset.rhPatched = '1';
                            label.style.cssText = BASE;
                            label.addEventListener('mouseenter', function() {
                                if (!label.dataset.rhActive) {
                                    label.style.background = 'rgba(255,255,255,0.05)';
                                    label.style.color = '#fff';
                                    label.style.webkitTextFillColor = '#fff';
                                    label.style.borderLeftColor = 'rgba(124,58,237,0.4)';
                                }
                            });
                            label.addEventListener('mouseleave', function() {
                                if (!label.dataset.rhActive) {
                                    label.style.background = '';
                                    label.style.color = '#777';
                                    label.style.webkitTextFillColor = '#777';
                                    label.style.borderLeftColor = 'transparent';
                                }
                            });
                        }
                    });
                    function sync() {
                        labels.forEach(function(label) {
                            var r = label.querySelector('[aria-checked],[role="radio"],input[type="radio"]');
                            var on = r && (r.getAttribute('aria-checked') === 'true' || r.checked);
                            label.dataset.rhActive = on ? '1' : '';
                            if (on) {
                                label.style.background = 'rgba(124,58,237,0.12)';
                                label.style.borderLeftColor = '#7C3AED';
                                label.style.color = '#fff';
                                label.style.webkitTextFillColor = '#fff';
                                label.style.fontWeight = '700';
                            } else {
                                label.style.background = '';
                                label.style.borderLeftColor = 'transparent';
                                label.style.color = '#777';
                                label.style.webkitTextFillColor = '#777';
                                label.style.fontWeight = '500';
                            }
                        });
                    }
                    var sb = doc.querySelector('[data-testid="stSidebar"]');
                    if (sb) new MutationObserver(sync).observe(sb, { subtree:true, attributes:true });
                    sync();
                } catch(e) {
                    if (attempts < 25) setTimeout(patchNav, 300);
                }
            }
            setTimeout(patchNav, 200);
        })();
    } catch(e) {}
})();
</script>
""", height=0, scrolling=False)


# ── Login page ────────────────────────────────────────────────────────────────
def _page_login():
    _, col, _ = st.columns([1, 1.1, 1])
    with col:
        st.markdown(
            '<div class="landing-logo" style="text-align:center;margin-bottom:6px;">ReelHaus</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="landing-tagline" style="text-align:center;">AI Script Writing Tool</div>',
            unsafe_allow_html=True,
        )

        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
        password = st.text_input("Password", type="password", placeholder="Enter password…", label_visibility="collapsed")
        if st.button("Enter", use_container_width=True):
            try:
                cloud_pw = st.secrets.get("APP_PASSWORD")
            except Exception:
                cloud_pw = None
            correct = cloud_pw or os.getenv("APP_PASSWORD") or "Reelhaus#8534"
            if password == correct:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Incorrect password.")

    st.markdown(
        "<div class='rh-footer'>ReelHaus v1.1</div>",
        unsafe_allow_html=True,
    )


# ── Sidebar ───────────────────────────────────────────────────────────────────
def _sidebar() -> str:
    with st.sidebar:
        st.markdown(
            "<div style='font-size:1.6rem;font-weight:900;letter-spacing:-0.02em;"
            "background:linear-gradient(135deg,#a78bfa,#818cf8);-webkit-background-clip:text;"
            "-webkit-text-fill-color:transparent;background-clip:text;"
            "margin-bottom:2px;'>🎬 ReelHaus</div>"
            "<div style='font-size:0.7rem;color:#444;letter-spacing:0.13em;"
            "text-transform:uppercase;margin-bottom:20px;'>AI Script Writing Tool</div>",
            unsafe_allow_html=True,
        )
        st.divider()

        page = st.radio(
            "Navigation",
            options=[
                "✍️ Script Generator",
                "📋 Creator Profile",
                "🎥 Video Analyser",
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
            f"<div style='font-size:0.75rem;color:#444;line-height:2.2;'>"
            f"{'<span style=\"color:#7C3AED\">●</span>' if api_ok else '<span style=\"color:#333\">●</span>'} API Connected<br>"
            f"{'<span style=\"color:#7C3AED\">●</span>' if profile_ok else '<span style=\"color:#333\">●</span>'} Profile loaded<br>"
            f"{'<span style=\"color:#7C3AED\">●</span>' if analyses_ok else '<span style=\"color:#333\">●</span>'} Analyses ready<br>"
            f"{'<span style=\"color:#7C3AED\">●</span>' if scripts_ok else '<span style=\"color:#333\">●</span>'} Scripts generated"
            f"</div>",
            unsafe_allow_html=True,
        )

        st.divider()

        # Sign out
        if st.button("Sign out", use_container_width=True):
            st.session_state.authenticated = False
            st.rerun()

        st.markdown(
            "<div style='font-size:0.62rem;color:#282828;text-align:center;margin-top:8px;'>ReelHaus v1.1</div>",
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
        "<div style='color:#555;font-size:0.85rem;margin-bottom:24px;'>"
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
    if not st.session_state.get("authenticated"):
        _inject_css(hide_sidebar=True)
        _page_login()
        return

    _inject_css(hide_sidebar=False)
    page = _sidebar()
    _page_fade()

    if   "Script Generator" in page: generator_module.render()
    elif "Creator Profile"  in page: profile_module.render()
    elif "Video Analyser"   in page: analyser_module.render()
    elif "Saved Scripts"    in page: _page_saved_scripts()
    elif "Settings"         in page: _page_settings()


if __name__ == "__main__":
    main()
