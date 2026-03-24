"""
storage.py
----------
JSON load/save helpers for profiles, analyses, and scripts.
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

DATA_DIR      = Path(__file__).parent.parent / "data"
PROFILES_DIR  = DATA_DIR / "profiles"
ANALYSES_DIR  = DATA_DIR / "analyses"
SCRIPTS_DIR   = DATA_DIR / "scripts"

for _d in (PROFILES_DIR, ANALYSES_DIR, SCRIPTS_DIR):
    _d.mkdir(parents=True, exist_ok=True)


def _read(path: Path) -> dict | list:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _write(path: Path, data: dict | list) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ── Profiles ──────────────────────────────────────────────────────────────────

def save_profile(name: str, data: dict) -> Path:
    path = PROFILES_DIR / f"{_safe(name)}.json"
    _write(path, data)
    return path


def load_profile(name: str) -> dict:
    path = PROFILES_DIR / f"{_safe(name)}.json"
    return _read(path)


def list_profiles() -> list[str]:
    return [p.stem for p in sorted(PROFILES_DIR.glob("*.json"))]


# ── Analyses ──────────────────────────────────────────────────────────────────

def save_analysis(name: str, data: list) -> Path:
    path = ANALYSES_DIR / f"{_safe(name)}.json"
    _write(path, data)
    return path


def load_analysis(name: str) -> list:
    path = ANALYSES_DIR / f"{_safe(name)}.json"
    return _read(path)


def list_analyses() -> list[str]:
    return [p.stem for p in sorted(ANALYSES_DIR.glob("*.json"))]


# ── Scripts ───────────────────────────────────────────────────────────────────

def save_scripts(name: str, data: dict) -> Path:
    path = SCRIPTS_DIR / f"{_safe(name)}.json"
    _write(path, data)
    return path


def load_scripts(name: str) -> dict:
    path = SCRIPTS_DIR / f"{_safe(name)}.json"
    return _read(path)


def list_scripts() -> list[str]:
    return [p.stem for p in sorted(SCRIPTS_DIR.glob("*.json"))]


def delete_scripts(name: str) -> None:
    path = SCRIPTS_DIR / f"{_safe(name)}.json"
    if path.exists():
        path.unlink()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _safe(name: str) -> str:
    """Make a filename-safe slug."""
    import re
    return re.sub(r"[^\w\-]", "_", name.strip().lower())


def timestamp_name(prefix: str = "batch") -> str:
    return f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
