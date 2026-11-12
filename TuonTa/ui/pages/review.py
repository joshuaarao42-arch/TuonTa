"""Flashcard review with flip animation. Weakest cards come first (Leitner boxes)."""
from __future__ import annotations

import customtkinter as ctk

from ..components import Page, button, label, option_menu
from ..flipcard import FlipCard
from ..theme import C, PAD

ALL = "All decks"


class ReviewPage(Page):
    def __init__(self, app):
        super().__init__(app)
        self.queue: list = []
        self.index = self.known = 0
        self.revealed = False
        self.deck_id: int | None = None

        actions = self.header("Review", "Flip the card, then say whether you knew it.")
        self.deck_menu = option_menu(actions, [ALL], command=self._deck_changed, width=190)
        self.deck_menu.pack()

        self.stage = ctk.CTkFrame(self, fg_color="transparent")
        top = ctk.CTkFrame(self.stage, fg_color="transparent")
        top.pack(fill="x", pady=(0, 14))
        self.counter = label(top, "", 13, color=C.MUTED)
        self.counter.pack(side="left")
        self.bar = ctk.CTkProgressBar(self.stage, height=3, corner_radius=0, fg_color=C.RAISED, progress_color=C.ACCENT)
        self.bar.set(0)
        self.bar.pack(fill="x", pady=(0, 18))
        self.card = FlipCard(self.stage, on_flip=self._flipped)
        self.card.pack(fill="both", expand=True)
        controls = ctk.CTkFrame(self.stage, fg_color="transparent")
        controls.pack(pady=(22, 0))
        self.btn_again = button(controls, "Still learning", lambda: self.rate(False), "secondary", "cross", width=150, height=40)
        self.btn_flip = button(controls, "Flip", self.card.flip, "ghost", "flip", width=100, height=40)
        self.btn_known = button(controls, "Got it", lambda: self.rate(True), "primary", "check", width=150, height=40)
        self.btn_again.pack(side="left", padx=6)
        self.btn_flip.pack(side="left", padx=6)
        self.btn_known.pack(side="left", padx=6)
        label(self.stage, "Space flips. Left arrow means still learning, right arrow means got it.", 12, color=C.FAINT).pack(pady=(14, 0))

        self.done = ctk.CTkFrame(self, fg_color="transparent")
        self.done_title = label(self.done, "", 28, "bold")
        self.done_title.pack(pady=(0, 6))
        self.done_text = label(self.done, "", 14, color=C.MUTED, justify="center")
        self.done_text.pack()
        row = ctk.CTkFrame(self.done, fg_color="transparent")
        row.pack(pady=26)
        button(row, "Review again", self.start, "primary", "review", height=40).pack(side="left", padx=6)
        button(row, "Back to decks", lambda: app.show("flashcards"), "secondary", "cards", height=40).pack(side="left", padx=6)

        app.bind("<space>", lambda e: self._key(self.card.flip), add="+")
        app.bind("<Left>", lambda e: self._key(lambda: self.rate(False)), add="+")
        app.bind("<Right>", lambda e: self._key(lambda: self.rate(True)), add="+")

    def _key(self, action):
        if self.app.current == "review" and self.stage.winfo_ismapped():
            action()
            return "break"
        return None

    def on_show(self, deck_id=None, **_):
        decks = self.db.list_decks()
        self.names = {d["name"]: d["id"] for d in decks}
        self.deck_menu.configure(values=[ALL] + list(self.names))
        name = next((n for n, i in self.names.items() if i == deck_id), ALL)
        self.deck_menu.set(name)
        self.deck_id = self.names.get(name)
        self.start()

    def _deck_changed(self, name):
        self.deck_id = self.names.get(name)
        self.start()

    def start(self):
        self.queue = list(self.db.review_queue(self.deck_id, 30))
        self.index = self.known = 0
        self.done.pack_forget()
        if not self.queue:
            self.stage.pack_forget()
            self.done_title.configure(text="Nothing to review yet")
            self.done_text.configure(text="Add flashcards to a deck, or scan a note and make cards from it.")
            self.done.pack(expand=True)
            return
        self.stage.pack(fill="both", expand=True, padx=PAD + 60, pady=(26, 28))
        self._show_card()

    def _show_card(self):
        card = self.queue[self.index]
        self.revealed = False
        self.counter.configure(text=f"Card {self.index + 1} of {len(self.queue)}")
        self.bar.set(self.index / len(self.queue))
        self.card.set_card(card["front"], card["back"])
        self._set_rating(False)

    def _set_rating(self, on: bool):
        state = "normal" if on else "disabled"
        self.btn_again.configure(state=state)
        self.btn_known.configure(state=state)

    def _flipped(self, face: int):
        if face == 1:
            self.revealed = True
            self._set_rating(True)

    def rate(self, known: bool):
        if not self.revealed or self.card.busy:
            return
        self.db.record_review(self.queue[self.index]["id"], known)
        self.known += known
        self.index += 1
        if self.index >= len(self.queue):
            self._finish()
        else:
            self._show_card()

    def _finish(self):
        total = len(self.queue)
        self.stage.pack_forget()
        self.card.clear()
        self.bar.set(1)
        pct = round(100 * self.known / total)
        self.done_title.configure(text="Session complete")
        self.done_text.configure(text=f"You knew {self.known} of {total} cards ({pct}%).\nCards you missed go back to the first box and come up sooner.")
        self.done.pack(expand=True)
