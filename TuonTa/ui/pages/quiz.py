"""Multiple-choice quiz built from saved flashcards. Scores are saved for the dashboard."""
from __future__ import annotations

import time

import customtkinter as ctk

from ...core.quiz import build_quiz
from ..components import Page, button, divider, label, option_menu, scroll_frame
from ..theme import C, PAD, font

ALL = "All decks"
LETTERS = "ABCD"


class QuizPage(Page):
    def __init__(self, app):
        super().__init__(app)
        self.questions: list = []
        self.index = self.score = 0
        self.answered = False
        self.missed: list = []
        self.started = 0.0
        self.deck_id: int | None = None
        self.deck_name = ALL
        self.count = 10
        self.header("Quiz", "Multiple-choice questions built from your flashcards.")

        # ---- setup
        self.setup = ctk.CTkFrame(self, fg_color="transparent")
        label(self.setup, "Deck", 13, color=C.MUTED).pack(anchor="w")
        self.deck_menu = option_menu(self.setup, [ALL], width=320)
        self.deck_menu.pack(anchor="w", pady=(6, 20))
        label(self.setup, "Questions", 13, color=C.MUTED).pack(anchor="w")
        self.length = ctk.CTkSegmentedButton(
            self.setup, values=["5", "10", "20"], width=320, height=34, corner_radius=4, font=font(13),
            fg_color=C.RAISED, selected_color=C.ACCENT, selected_hover_color=C.ACCENT_HOVER,
            unselected_color=C.RAISED, unselected_hover_color=C.HOVER, text_color=C.TEXT)
        self.length.set("10")
        self.length.pack(anchor="w", pady=(6, 20))
        self.info = label(self.setup, "", 13, color=C.MUTED)
        self.info.pack(anchor="w")
        self.error = label(self.setup, "", 13, color=C.BAD, wraplength=420, justify="left")
        self.error.pack(anchor="w", pady=(4, 0))
        button(self.setup, "Start quiz", self.start, "primary", "quiz", height=40, width=160).pack(anchor="w", pady=(18, 0))

        # ---- play
        self.play = ctk.CTkFrame(self, fg_color="transparent")
        meta = ctk.CTkFrame(self.play, fg_color="transparent")
        meta.pack(fill="x")
        self.counter = label(meta, "", 13, color=C.MUTED)
        self.counter.pack(side="left")
        self.running = label(meta, "", 13, color=C.MUTED)
        self.running.pack(side="right")
        self.bar = ctk.CTkProgressBar(self.play, height=3, corner_radius=0, fg_color=C.RAISED, progress_color=C.ACCENT)
        self.bar.pack(fill="x", pady=(10, 28))
        self.prompt = label(self.play, "", 22, "bold", anchor="w", justify="left", wraplength=760)
        self.prompt.pack(anchor="w", pady=(0, 24))
        self.options = ctk.CTkFrame(self.play, fg_color="transparent")
        self.options.pack(fill="x")
        foot = ctk.CTkFrame(self.play, fg_color="transparent")
        foot.pack(fill="x", pady=(20, 0))
        self.feedback = label(foot, "", 14, "bold")
        self.feedback.pack(side="left")
        self.next_btn = button(foot, "Next question", self.next, "primary", height=38, width=150)

        # ---- result
        self.result = ctk.CTkFrame(self, fg_color="transparent")
        self.big = label(self.result, "", 56, "bold")
        self.big.pack(anchor="w")
        self.summary = label(self.result, "", 14, color=C.MUTED, justify="left")
        self.summary.pack(anchor="w", pady=(2, 18))
        self.missed_title = label(self.result, "Worth another look", 16, "bold")
        self.missed_box = scroll_frame(self.result, height=240)
        row = ctk.CTkFrame(self.result, fg_color="transparent")
        row.pack(side="bottom", anchor="w", pady=(18, 0))
        button(row, "Retake quiz", self.start, "primary", "quiz", height=38).pack(side="left", padx=(0, 8))
        button(row, "Change settings", self.show_setup, "secondary", "settings", height=38).pack(side="left")

        for n in range(4):
            app.bind(f"<Key-{n + 1}>", lambda e, i=n: self._key(lambda: self.choose(i)), add="+")
        app.bind("<Return>", lambda e: self._key(self.next), add="+")

    def _key(self, action):
        if self.app.current == "quiz" and self.play.winfo_ismapped():
            action()
            return "break"
        return None

    def _only(self, frame):
        for f in (self.setup, self.play, self.result):
            f.pack_forget()
        frame.pack(fill="both", expand=True, padx=PAD, pady=(28, 28), anchor="w")

    # ------------------------------------------------------------ setup
    def on_show(self, deck_id=None, **_):
        decks = self.db.list_decks()
        self.names = {f'{d["name"]} ({d["card_count"]})': d["id"] for d in decks}
        self.deck_menu.configure(values=[ALL] + list(self.names))
        self.deck_menu.set(next((n for n, i in self.names.items() if i == deck_id), ALL))
        total = self.db.conn.execute("SELECT COUNT(*) FROM cards").fetchone()[0]
        self.info.configure(text=f"{total} flashcards available. Wrong options come from your other cards' answers.")
        self.show_setup()

    def show_setup(self):
        self.error.configure(text="")
        self._only(self.setup)

    def start(self):
        choice = self.deck_menu.get()
        self.deck_id = self.names.get(choice)
        self.deck_name = choice.rsplit(" (", 1)[0] if self.deck_id else ALL
        self.count = int(self.length.get())
        try:
            self.questions = build_quiz(self.db.list_cards(self.deck_id), self.count)
        except ValueError as exc:
            self.show_setup()
            self.error.configure(text=f"{exc} Add more cards, or pick a bigger deck.")
            return
        self.index = self.score = 0
        self.missed = []
        self.started = time.monotonic()
        self._only(self.play)
        self._show_question()

    # ------------------------------------------------------------ play
    def _show_question(self):
        q = self.questions[self.index]
        self.answered = False
        self.counter.configure(text=f"Question {self.index + 1} of {len(self.questions)}")
        self.running.configure(text=f"{self.score} correct")
        self.bar.set(self.index / len(self.questions))
        self.prompt.configure(text=q.prompt)
        self.feedback.configure(text="")
        self.next_btn.pack_forget()
        for child in self.options.winfo_children():
            child.destroy()
        self.buttons = []
        for i, option in enumerate(q.options):
            b = ctk.CTkButton(
                self.options, text=f"{LETTERS[i]}     {option}", anchor="w", height=54, corner_radius=4,
                fg_color=C.RAISED, hover_color=C.HOVER, text_color=C.TEXT, border_width=1, border_color=C.BORDER,
                font=font(14), wraplength=700, command=lambda n=i: self.choose(n))
            b.pack(fill="x", pady=4)
            self.buttons.append(b)

    def choose(self, i: int):
        if self.answered or i >= len(self.buttons):
            return
        self.answered = True
        q = self.questions[self.index]
        right = i == q.answer_index
        self.score += right
        if not right:
            self.missed.append(q)
        for n, b in enumerate(self.buttons):
            b.configure(state="disabled", text_color_disabled=C.TEXT if n in (i, q.answer_index) else C.FAINT)
            if n == q.answer_index:
                b.configure(fg_color=C.OK_DIM, border_color=C.OK)
            elif n == i:
                b.configure(fg_color=C.BAD_DIM, border_color=C.BAD)
        self.feedback.configure(text="Correct" if right else "Not quite. The right answer is highlighted.",
                                text_color=C.OK if right else C.BAD)
        self.running.configure(text=f"{self.score} correct")
        last = self.index == len(self.questions) - 1
        self.next_btn.configure(text="See results" if last else "Next question")
        self.next_btn.pack(side="right")

    def next(self):
        if not self.answered:
            return
        self.index += 1
        if self.index >= len(self.questions):
            self._finish()
        else:
            self._show_question()

    # ------------------------------------------------------------ result
    def _finish(self):
        total = len(self.questions)
        seconds = int(time.monotonic() - self.started)
        self.db.save_quiz(self.deck_id, self.deck_name, total, self.score, seconds)
        pct = round(100 * self.score / total)
        self.big.configure(text=f"{pct}%", text_color=C.OK if pct >= 70 else C.TEXT)
        self.summary.configure(text=f"{self.score} of {total} correct in {seconds // 60}:{seconds % 60:02d}\nDeck: {self.deck_name}")
        for child in self.missed_box.winfo_children():
            child.destroy()
        self.missed_title.pack_forget()
        self.missed_box.pack_forget()
        if self.missed:
            self.missed_title.pack(anchor="w", pady=(0, 6))
            self.missed_box.pack(fill="x")
            for q in self.missed:
                line = ctk.CTkFrame(self.missed_box, fg_color="transparent")
                line.pack(fill="x")
                inner = ctk.CTkFrame(line, fg_color="transparent")
                inner.pack(fill="x", pady=9)
                label(inner, q.prompt, 13, "bold", anchor="w", justify="left", wraplength=700).pack(anchor="w")
                label(inner, q.options[q.answer_index], 13, color=C.OK, anchor="w", justify="left", wraplength=700).pack(anchor="w")
                divider(line).pack(fill="x")
        self._only(self.result)
