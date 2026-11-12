"""CustomTkinter wrappers around the Pillow artwork."""
from __future__ import annotations

import customtkinter as ctk

from .drawing import draw_icon, draw_logo
from .theme import C

_cache: dict = {}


def icon(name: str, size: int = 18, color: str = C.TEXT) -> ctk.CTkImage:
    key = (name, size, color)
    if key not in _cache:
        img = draw_icon(name, size, color)
        _cache[key] = ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))
    return _cache[key]


def logo(size: int = 36, tile: bool = False) -> ctk.CTkImage:
    key = ("logo", size, tile)
    if key not in _cache:
        img = draw_logo(size * 4, tile=tile)
        _cache[key] = ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))
    return _cache[key]
