"""Reusable, consistently styled widgets."""
from __future__ import annotations

import tkinter as tk

import customtkinter as ctk

from .icons import icon
from .theme import C, PAD, font

_KINDS = {
    "primary": dict(fg_color=C.ACCENT, hover_color=C.ACCENT_HOVER, text_color=C.ON_ACCENT, border_width=0),
    "secondary": dict(fg_color=C.RAISED, hover_color=C.HOVER, text_color=C.TEXT, border_width=1, border_color=C.BORDER),
    "ghost": dict(fg_color="transparent", hover_color=C.HOVER, text_color=C.MUTED, border_width=0),
    "danger": dict(fg_color="transparent", hover_color=C.BAD_DIM, text_color=C.BAD, border_width=0),
}
_ICON_COLOR = {"primary": C.ON_ACCENT, "secondary": C.TEXT, "ghost": C.MUTED, "danger": C.BAD}


def button(parent, text="", command=None, kind="secondary", icon_name=None, width=None, height=34, **kw):
    img = icon(icon_name, 16, _ICON_COLOR[kind]) if icon_name else None
    opts = dict(_KINDS[kind])
    opts.update(kw)
    if width:
        opts["width"] = width
    return ctk.CTkButton(parent, text=text, command=command, image=img, compound="left", height=height,
                         corner_radius=4, font=font(13, "bold" if kind == "primary" else "normal"), **opts)


def icon_button(parent, icon_name, command=None, kind="ghost", color=None, size=30):
    img = icon(icon_name, 16, color or _ICON_COLOR[kind])
    return ctk.CTkButton(parent, text="", image=img, command=command, width=size, height=size, corner_radius=4,
                         **{**_KINDS[kind]})


def entry(parent, placeholder="", width=200, **kw):
    return ctk.CTkEntry(parent, placeholder_text=placeholder, width=width, height=34, corner_radius=4,
                        fg_color=C.SURFACE, border_color=C.BORDER, border_width=1, text_color=C.TEXT,
                        placeholder_text_color=C.FAINT, font=font(13), **kw)


def textbox(parent, size=14, **kw):
    return ctk.CTkTextbox(parent, fg_color=C.SURFACE, border_color=C.BORDER, border_width=1, corner_radius=4,
                          text_color=C.TEXT, font=font(size), wrap="word", undo=True, padx=14, pady=12,
                          scrollbar_button_color=C.RAISED, scrollbar_button_hover_color=C.HOVER, **kw)


def option_menu(parent, values, command=None, width=150, variable=None):
    return ctk.CTkOptionMenu(parent, values=values or [""], command=command, width=width, height=34, corner_radius=4,
                             fg_color=C.RAISED, button_color=C.RAISED, button_hover_color=C.HOVER,
                             dropdown_fg_color=C.RAISED, dropdown_hover_color=C.HOVER, dropdown_text_color=C.TEXT,
                             text_color=C.TEXT, font=font(13), dropdown_font=font(13), variable=variable)


def label(parent, text="", size=13, weight="normal", color=C.TEXT, **kw):
    return ctk.CTkLabel(parent, text=text, font=font(size, weight), text_color=color, **kw)


def divider(parent, vertical=False):
    if vertical:
        return ctk.CTkFrame(parent, width=1, fg_color=C.BORDER, corner_radius=0)
    return ctk.CTkFrame(parent, height=1, fg_color=C.BORDER, corner_radius=0)


def scroll_frame(parent, **kw):
    return ctk.CTkScrollableFrame(parent, fg_color="transparent", corner_radius=0,
                                  scrollbar_button_color=C.RAISED, scrollbar_button_hover_color=C.HOVER, **kw)


def bind_click(widget, callback):
    """Make a row clickable, including every child widget."""
    widget.bind("<Button-1>", lambda _e: callback(), add="+")
    for child in widget.winfo_children():
        bind_click(child, callback)


class Page(ctk.CTkFrame):
    """Base class for every screen."""

    def __init__(self, app):
        super().__init__(app.content, fg_color=C.BG, corner_radius=0)
        self.app, self.db = app, app.db

    def on_show(self, **kwargs) -> None:  # called each time the page becomes visible
        pass

    def on_hide(self) -> bool:  # return False to veto navigation (e.g. unsaved changes)
        return True

    def header(self, title: str, subtitle: str = "") -> ctk.CTkFrame:
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", padx=PAD, pady=(30, 0))
        bar.grid_columnconfigure(0, weight=1)
        text = ctk.CTkFrame(bar, fg_color="transparent")
        text.grid(row=0, column=0, sticky="w")
        label(text, title, 26, "bold").pack(anchor="w")
        self.subtitle = label(text, subtitle, 13, color=C.MUTED)
        self.subtitle.pack(anchor="w", pady=(2, 0))
        actions = ctk.CTkFrame(bar, fg_color="transparent")
        actions.grid(row=0, column=1, sticky="e")
        return actions


class Toast:
    """Small confirmation that slides in from the bottom-right and leaves on its own."""

    def __init__(self, root):
        self.root, self.current = root, None

    def show(self, message: str, kind: str = "ok") -> None:
        if self.current is not None:
            try:
                self.current.destroy()
            except tk.TclError:
                pass
        color = {"ok": C.ACCENT, "error": C.BAD, "info": C.MUTED}[kind]
        box = ctk.CTkFrame(self.root, fg_color=C.RAISED, corner_radius=4, border_width=1, border_color=C.BORDER)
        ctk.CTkFrame(box, width=3, fg_color=color, corner_radius=0).pack(side="left", fill="y")
        ctk.CTkLabel(box, text=message, font=font(13), text_color=C.TEXT, wraplength=360, justify="left").pack(
            side="left", padx=(12, 16), pady=11)
        self.current = box

        def slide(step=0):
            if not box.winfo_exists():
                return
            box.place(relx=1.0, rely=1.0, anchor="se", x=-24 + (6 - step) * 9, y=-24)
            if step < 6:
                box.after(14, lambda: slide(step + 1))

        slide()
        box.after(3200 if kind == "error" else 2200, lambda: box.winfo_exists() and box.destroy())
