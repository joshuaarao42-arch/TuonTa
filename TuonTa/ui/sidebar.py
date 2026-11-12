"""Fixed navigation sidebar."""
from __future__ import annotations

import customtkinter as ctk

from .components import label
from .icons import icon, logo
from .theme import C, font

NAV = (
    ("dashboard", "Dashboard", "dashboard"),
    ("scan", "Scan", "scan"),
    ("notes", "Notes", "notes"),
    ("flashcards", "Flashcards", "cards"),
    ("review", "Review", "review"),
    ("quiz", "Quiz", "quiz"),
)


class Sidebar(ctk.CTkFrame):
    WIDTH = 228

    def __init__(self, master, navigate):
        super().__init__(master, width=self.WIDTH, fg_color=C.SIDEBAR, corner_radius=0)
        self.pack_propagate(False)
        self.navigate = navigate
        self.items: dict[str, tuple] = {}

        brand = ctk.CTkFrame(self, fg_color="transparent")
        brand.pack(fill="x", padx=22, pady=(28, 26))
        ctk.CTkLabel(brand, text="", image=logo(34)).pack(side="left")
        word = ctk.CTkFrame(brand, fg_color="transparent")
        word.pack(side="left", padx=(11, 0))
        label(word, "Tuon", 21, "bold").pack(side="left")
        label(word, "Ta", 21, "bold", color=C.ACCENT).pack(side="left")

        for key, text, icon_name in NAV:
            self._item(key, text, icon_name, side="top")

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(side="bottom", fill="x", pady=(0, 18))
        label(footer, "Works fully offline", 12, color=C.FAINT).pack(anchor="w", padx=24, pady=(10, 0))
        self._item("settings", "Settings", "settings", side="bottom", parent=footer, first=True)

    def _item(self, key, text, icon_name, side="top", parent=None, first=False):
        row = ctk.CTkFrame(parent or self, fg_color="transparent", height=40)
        row.pack(fill="x", padx=(0, 14), pady=1, side="top")
        row.pack_propagate(False)
        bar = ctk.CTkFrame(row, width=3, fg_color="transparent", corner_radius=0)
        bar.pack(side="left", fill="y", pady=7)
        btn = ctk.CTkButton(
            row, text=f"  {text}", image=icon(icon_name, 18, C.MUTED), compound="left", anchor="w", height=38,
            corner_radius=4, fg_color="transparent", hover_color=C.HOVER, text_color=C.MUTED, font=font(14),
            command=lambda k=key: self.navigate(k),
        )
        btn.pack(side="left", fill="x", expand=True, padx=(15, 0))
        self.items[key] = (bar, btn, icon_name)

    def set_active(self, key: str) -> None:
        for k, (bar, btn, icon_name) in self.items.items():
            on = k == key
            bar.configure(fg_color=C.ACCENT if on else "transparent")
            btn.configure(fg_color=C.RAISED if on else "transparent", text_color=C.TEXT if on else C.MUTED,
                          image=icon(icon_name, 18, C.TEXT if on else C.MUTED))
