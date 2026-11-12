"""Canvas flashcard with a real flip animation (the card narrows to an edge, then opens on the other face).

The corner fold repeats the notch from the TuonTa logo.
"""
from __future__ import annotations

import math
import tkinter as tk

from .theme import C, tk_font

FRAMES = 10
FOLD = 30


class FlipCard(tk.Canvas):
    def __init__(self, parent, height: int = 340, on_flip=None):
        super().__init__(parent, height=height, bg=C.BG, highlightthickness=0, bd=0, cursor="hand2")
        self.front = self.back = ""
        self.face = 0
        self.busy = False
        self.on_flip = on_flip
        self._job = None
        self.bind("<Configure>", lambda _e: self.render())
        self.bind("<Button-1>", lambda _e: self.flip())

    # -- public
    def set_card(self, front: str, back: str) -> None:
        self._cancel()
        self.front, self.back, self.face, self.busy = front, back, 0, False
        self._enter(0)

    def clear(self) -> None:
        self._cancel()
        self.front = self.back = ""
        self.delete("all")

    def flip(self) -> None:
        if self.busy or not self.front:
            return
        self.busy = True
        self._flip_step(0)

    # -- animation
    def _cancel(self) -> None:
        if self._job is not None:
            try:
                self.after_cancel(self._job)
            except tk.TclError:
                pass
            self._job = None

    def _enter(self, step: int) -> None:
        self.render(1.0, dy=(7 - step) * 3)
        if step < 7:
            self._job = self.after(14, lambda: self._enter(step + 1))

    def _flip_step(self, i: int) -> None:
        scale = abs(math.cos(math.pi * i / FRAMES))
        if i == FRAMES // 2:
            self.face = 1 - self.face
        self.render(scale)
        if i < FRAMES:
            self._job = self.after(16, lambda: self._flip_step(i + 1))
        else:
            self.busy = False
            if self.on_flip:
                self.on_flip(self.face)

    # -- drawing
    def render(self, scale: float = 1.0, dy: float = 0) -> None:
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w < 60 or h < 60 or not self.front or scale < 0.02:
            return
        cw = min(w - 24, 760) * scale
        x0, x1 = w / 2 - cw / 2, w / 2 + cw / 2
        y0, y1 = 10 + dy, h - 10 + dy
        back = self.face == 1
        f = min(FOLD, cw / 3)
        self.create_polygon(x0, y0, x1 - f, y0, x1, y0 + f, x1, y1, x0, y1,
                            fill=C.SURFACE, outline=C.ACCENT_DIM if back else C.BORDER, width=1)
        self.create_polygon(x1 - f, y0, x1 - f, y0 + f, x1, y0 + f, fill=C.ACCENT_DIM if back else C.RAISED, outline="")
        if back:
            self.create_line(x0, y1 - 1, x1, y1 - 1, fill=C.ACCENT, width=2)
        if scale < 0.6:
            return
        pad = 30
        self.create_text(x0 + pad, y0 + 28, text="Answer" if back else "Question", anchor="w",
                         fill=C.ACCENT if back else C.MUTED, font=tk_font(12, "bold"))
        text = self.back if back else self.front
        size = 26 if len(text) < 70 else 21 if len(text) < 180 else 16
        self.create_text(w / 2, (y0 + y1) / 2 + 6, text=text, width=max(cw - 2 * pad - 20, 40), justify="center",
                         fill=C.TEXT, font=tk_font(size))
        if not back:
            self.create_text(w / 2, y1 - 24, text="Click the card or press Space to flip", fill=C.FAINT, font=tk_font(11))
