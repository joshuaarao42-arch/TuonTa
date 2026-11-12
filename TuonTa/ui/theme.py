"""Design tokens: colours, type and spacing."""
from __future__ import annotations

import tkinter.font as tkfont

import customtkinter as ctk


class C:
    BG = "#141619"        # charcoal
    SIDEBAR = "#0f1113"
    SURFACE = "#1a1d21"
    RAISED = "#212529"
    HOVER = "#2a2f35"
    BORDER = "#2a2f36"
    TEXT = "#e9e6df"      # off-white
    MUTED = "#8a919a"
    FAINT = "#5d646d"
    ACCENT = "#5b8def"    # the single blue
    ACCENT_HOVER = "#7aa3f5"
    ACCENT_DIM = "#2b3f6b"
    ON_ACCENT = "#0c1220"
    OK = "#6fae8a"
    BAD = "#c9615f"
    BAD_DIM = "#3a2424"
    OK_DIM = "#1f3329"


PAD = 40
_PREFERRED = ("Segoe UI Variable Text", "Segoe UI", "SF Pro Text", "Helvetica Neue", "Inter", "Ubuntu", "Cantarell", "DejaVu Sans")
_family: str | None = None
_cache: dict = {}


def family() -> str:
    global _family
    if _family is None:
        try:
            available = set(tkfont.families())
        except Exception:
            available = set()
        _family = next((f for f in _PREFERRED if f in available), "Helvetica")
    return _family


def font(size: int = 13, weight: str = "normal") -> ctk.CTkFont:
    key = (size, weight)
    if key not in _cache:
        _cache[key] = ctk.CTkFont(family=family(), size=size, weight=weight)
    return _cache[key]


def tk_font(size: int, weight: str = "normal") -> tuple:
    return (family(), size, weight)
