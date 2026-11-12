"""Dashboard: study numbers, a 7-day activity chart and recent quiz scores."""
from __future__ import annotations

import tkinter as tk
from datetime import datetime

import customtkinter as ctk

from ..components import Page, button, divider, label
from ..theme import C, PAD, tk_font


class BarChart(tk.Canvas):
    """Seven bars that rise into place when new data arrives."""

    def __init__(self, parent, height=210):
        super().__init__(parent, height=height, bg=C.BG, highlightthickness=0, bd=0)
        self.data: list[tuple[str, int]] = []
        self.t = 1.0
        self.bind("<Configure>", lambda _e: self.draw())

    def set_data(self, data) -> None:
        self.data, self.t = list(data), 0.0
        self._tick()

    def _tick(self) -> None:
        if not self.winfo_exists():
            return
        self.t = min(1.0, self.t + 0.09)
        self.draw()
        if self.t < 1.0:
            self.after(16, self._tick)

    def draw(self) -> None:
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if not self.data or w < 80:
            return
        base, top = h - 26, 22
        peak = max(max(v for _, v in self.data), 1)
        ease = 1 - (1 - self.t) ** 3
        slot = w / len(self.data)
        bw = min(38, slot * 0.46)
        self.create_line(0, base, w, base, fill=C.BORDER)
        for i, (day, value) in enumerate(self.data):
            x0 = slot * i + (slot - bw) / 2
            bh = (base - top) * value / peak * ease
            last = i == len(self.data) - 1
            if value:
                self.create_rectangle(x0, base - bh, x0 + bw, base, fill=C.ACCENT if last else C.ACCENT_DIM, outline="")
                self.create_text(x0 + bw / 2, base - bh - 10, text=str(value), fill=C.MUTED, font=tk_font(11))
            else:
                self.create_line(x0, base - 1, x0 + bw, base - 1, fill=C.FAINT)
            self.create_text(x0 + bw / 2, base + 13, text=day, fill=C.TEXT if last else C.MUTED, font=tk_font(11))


class DashboardPage(Page):
    STATS = (("notes", "Notes"), ("cards", "Flashcards"), ("mastered", "Mastered"),
             ("streak", "Day streak"), ("avg_score", "Quiz average"))

    def __init__(self, app):
        super().__init__(app)
        actions = self.header("Dashboard", datetime.now().strftime("%A, %d %B"))
        self.actions = actions
        button(actions, "Scan an image", lambda: app.show("scan"), "primary", "scan").pack()

        strip = ctk.CTkFrame(self, fg_color="transparent")
        strip.pack(fill="x", padx=PAD, pady=(30, 0))
        self.numbers, self.targets = {}, {}
        for i, (key, caption) in enumerate(self.STATS):
            strip.grid_columnconfigure(i * 2, weight=1, uniform="stat")
            col = ctk.CTkFrame(strip, fg_color="transparent")
            col.grid(row=0, column=i * 2, sticky="w", padx=(0 if i == 0 else 22, 0))
            num = label(col, "0", 34, "bold")
            num.pack(anchor="w")
            label(col, caption, 13, color=C.MUTED).pack(anchor="w")
            self.numbers[key] = num
            if i < len(self.STATS) - 1:
                divider(strip, vertical=True).grid(row=0, column=i * 2 + 1, sticky="ns", padx=(0, 0))
        divider(self).pack(fill="x", padx=PAD, pady=26)

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=PAD, pady=(0, 28))
        body.grid_columnconfigure(0, weight=3, uniform="b")
        body.grid_columnconfigure(1, weight=2, uniform="b")
        body.grid_rowconfigure(0, weight=1)

        left = ctk.CTkFrame(body, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 40))
        label(left, "Last 7 days", 16, "bold").pack(anchor="w")
        label(left, "Cards reviewed plus quiz questions answered", 12, color=C.MUTED).pack(anchor="w", pady=(2, 14))
        self.chart = BarChart(left)
        self.chart.pack(fill="x")
        row = ctk.CTkFrame(left, fg_color="transparent")
        row.pack(anchor="w", pady=(24, 0))
        button(row, "Review cards", lambda: app.show("review"), "secondary", "review").pack(side="left", padx=(0, 8))
        button(row, "Take a quiz", lambda: app.show("quiz"), "secondary", "quiz").pack(side="left", padx=(0, 8))
        button(row, "Write a note", lambda: app.show("notes", new=True), "secondary", "notes").pack(side="left")

        right = ctk.CTkFrame(body, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew")
        label(right, "Recent quizzes", 16, "bold").pack(anchor="w")
        self.quiz_box = ctk.CTkFrame(right, fg_color="transparent")
        self.quiz_box.pack(fill="x", pady=(14, 0))

    def on_show(self, **_):
        stats = self.db.stats()
        for key, widget in self.numbers.items():
            value = stats[key]
            if value is None:
                widget.configure(text="-")
            else:
                self._count(widget, int(value), suffix="%" if key == "avg_score" else "")
        self.chart.set_data(stats["week"])
        for child in self.quiz_box.winfo_children():
            child.destroy()
        quizzes = self.db.recent_quizzes(6)
        if not quizzes:
            label(self.quiz_box, "No quizzes yet. Build a deck of flashcards, then test yourself.", 13,
                  color=C.MUTED, wraplength=300, justify="left").pack(anchor="w")
        for q in quizzes:
            pct = round(100 * q["correct"] / q["total"]) if q["total"] else 0
            line = ctk.CTkFrame(self.quiz_box, fg_color="transparent")
            line.pack(fill="x")
            row = ctk.CTkFrame(line, fg_color="transparent")
            row.pack(fill="x", pady=9)
            row.grid_columnconfigure(0, weight=1)
            info = ctk.CTkFrame(row, fg_color="transparent")
            info.grid(row=0, column=0, sticky="w")
            label(info, q["deck_name"], 13, "bold").pack(anchor="w")
            label(info, q["taken_at"][:16].replace("T", "  "), 12, color=C.MUTED).pack(anchor="w")
            label(row, f'{q["correct"]}/{q["total"]}', 15, "bold",
                  color=C.OK if pct >= 70 else C.TEXT).grid(row=0, column=1, sticky="e")
            divider(line).pack(fill="x")

    def _count(self, widget, target: int, suffix: str = "", step: int = 0) -> None:
        if not widget.winfo_exists():
            return
        steps = 10
        widget.configure(text=f"{round(target * min(step, steps) / steps)}{suffix}")
        if step < steps:
            widget.after(22, lambda: self._count(widget, target, suffix, step + 1))
