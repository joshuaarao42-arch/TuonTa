"""Flashcards: decks on the left, the cards of the chosen deck on the right."""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

from ...config import MAX_BOX
from ..components import Page, bind_click, button, divider, entry, icon_button, label, scroll_frame
from ..dialogs import CardEditor, TextPrompt, ensure_decks
from ..theme import C, PAD


def _clip(text: str, n: int) -> str:
    text = " ".join(text.split())
    return text if len(text) <= n else text[: n - 1] + "\u2026"


class BoxMeter(tk.Canvas):
    """Five small squares showing how far a card has climbed the Leitner boxes."""

    def __init__(self, parent, box: int):
        super().__init__(parent, width=56, height=10, bg=C.BG, highlightthickness=0, bd=0)
        for i in range(MAX_BOX):
            self.create_rectangle(i * 11, 1, i * 11 + 8, 9, outline="", fill=C.ACCENT if i < box else C.RAISED)


class FlashcardsPage(Page):
    def __init__(self, app):
        super().__init__(app)
        self.selected: int | None = None  # None = all cards
        self._job = None

        actions = self.header("Flashcards", "Organise cards into decks, then study them.")
        button(actions, "New deck", self.new_deck, "secondary", "folder").pack(side="left", padx=(0, 8))
        button(actions, "New card", self.new_card, "primary", "plus").pack(side="left")

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=PAD, pady=(22, 28))
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        left = ctk.CTkFrame(body, fg_color="transparent", width=250)
        left.grid(row=0, column=0, sticky="ns", padx=(0, 28))
        left.pack_propagate(False)
        label(left, "Decks", 13, color=C.MUTED).pack(anchor="w", pady=(0, 6))
        self.decks = scroll_frame(left)
        self.decks.pack(fill="both", expand=True)

        right = ctk.CTkFrame(body, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew")
        top = ctk.CTkFrame(right, fg_color="transparent")
        top.pack(fill="x")
        top.grid_columnconfigure(0, weight=1)
        titles = ctk.CTkFrame(top, fg_color="transparent")
        titles.grid(row=0, column=0, sticky="w")
        self.deck_title = label(titles, "All cards", 20, "bold")
        self.deck_title.pack(anchor="w")
        self.deck_meta = label(titles, "", 12, color=C.MUTED)
        self.deck_meta.pack(anchor="w")
        tools = ctk.CTkFrame(top, fg_color="transparent")
        tools.grid(row=0, column=1, sticky="e")
        self.btn_delete = button(tools, "", self.delete_deck, "danger", "trash", width=36)
        self.btn_rename = button(tools, "", self.rename_deck, "ghost", "edit", width=36)
        self.btn_quiz = button(tools, "Quiz", lambda: self._go("quiz"), "secondary", "quiz")
        self.btn_review = button(tools, "Review", lambda: self._go("review"), "primary", "review")
        for b in (self.btn_delete, self.btn_rename):
            b.pack(side="left", padx=(0, 2))
        self.btn_quiz.pack(side="left", padx=(8, 8))
        self.btn_review.pack(side="left")
        self.search = entry(right, "Search cards", width=300)
        self.search.pack(anchor="w", pady=(16, 8))
        self.search.bind("<KeyRelease>", lambda _e: self._debounced())
        divider(right).pack(fill="x")
        self.cards = scroll_frame(right)
        self.cards.pack(fill="both", expand=True)

    def on_show(self, **_):
        if self.selected is not None and self.db.get_deck(self.selected) is None:
            self.selected = None
        self.refresh()

    def _debounced(self):
        if self._job:
            self.after_cancel(self._job)
        self._job = self.after(180, self.refresh_cards)

    def refresh(self):
        self.refresh_decks()
        self.refresh_cards()

    # ----------------------------------------------------------- decks
    def refresh_decks(self):
        for child in self.decks.winfo_children():
            child.destroy()
        decks = self.db.list_decks()
        total = sum(d["card_count"] for d in decks)
        self._deck_row(None, "All cards", total)
        for d in decks:
            self._deck_row(d["id"], d["name"], d["card_count"])

    def _deck_row(self, deck_id, name, count):
        on = deck_id == self.selected
        row = ctk.CTkFrame(self.decks, fg_color=C.RAISED if on else "transparent", corner_radius=4, height=38)
        row.pack(fill="x", pady=1)
        row.pack_propagate(False)
        ctk.CTkFrame(row, width=3, fg_color=C.ACCENT if on else "transparent", corner_radius=0).pack(side="left", fill="y")
        label(row, _clip(name, 22), 13, "bold" if on else "normal", color=C.TEXT if on else C.MUTED).pack(side="left", padx=12)
        label(row, str(count), 12, color=C.FAINT).pack(side="right", padx=12)
        bind_click(row, lambda d=deck_id: self.select(d))

    def select(self, deck_id):
        self.selected = deck_id
        self.refresh()

    def new_deck(self):
        name = TextPrompt(self, "New deck", "Deck name", ok_text="Create").run()
        if not name:
            return
        try:
            self.selected = self.db.add_deck(name)
        except ValueError as exc:
            self.app.notify(str(exc), "error")
            return
        self.app.notify(f"Deck \"{name}\" created")
        self.refresh()

    def rename_deck(self):
        deck = self.db.get_deck(self.selected) if self.selected else None
        if not deck:
            return
        name = TextPrompt(self, "Rename deck", "Deck name", initial=deck["name"], ok_text="Rename").run()
        if not name:
            return
        try:
            self.db.rename_deck(deck["id"], name)
        except ValueError as exc:
            self.app.notify(str(exc), "error")
            return
        self.refresh()

    def delete_deck(self):
        deck = self.db.get_deck(self.selected) if self.selected else None
        if not deck:
            return
        n = len(self.db.list_cards(deck["id"]))
        if not messagebox.askyesno("Delete deck", f'Delete "{deck["name"]}" and its {n} cards? This cannot be undone.', parent=self):
            return
        self.db.delete_deck(deck["id"])
        self.selected = None
        self.app.notify("Deck deleted")
        self.refresh()

    # ----------------------------------------------------------- cards
    def refresh_cards(self):
        for child in self.cards.winfo_children():
            child.destroy()
        deck = self.db.get_deck(self.selected) if self.selected else None
        cards = self.db.list_cards(self.selected, self.search.get())
        self.deck_title.configure(text=deck["name"] if deck else "All cards")
        self.deck_meta.configure(text=f"{len(cards)} card{'s' if len(cards) != 1 else ''}")
        for b in (self.btn_delete, self.btn_rename):
            b.configure(state="normal" if deck else "disabled")
        self.btn_review.configure(state="normal" if cards else "disabled")
        self.btn_quiz.configure(state="normal" if cards else "disabled")
        if not cards:
            msg = "No cards match your search." if self.search.get().strip() else "No cards here yet.\nPress New card, or make cards from a note."
            label(self.cards, msg, 13, color=C.FAINT, justify="left").pack(anchor="w", pady=18)
            return
        for card in cards[:300]:
            self._card_row(card)
        if len(cards) > 300:
            label(self.cards, f"Showing the newest 300 of {len(cards)}. Use search to find the rest.", 12, color=C.FAINT).pack(pady=12)

    def _card_row(self, card):
        holder = ctk.CTkFrame(self.cards, fg_color="transparent")
        holder.pack(fill="x")
        row = ctk.CTkFrame(holder, fg_color="transparent")
        row.pack(fill="x", pady=10)
        row.grid_columnconfigure((0, 1), weight=1, uniform="col")
        front = ctk.CTkFrame(row, fg_color="transparent")
        front.grid(row=0, column=0, sticky="w", padx=(2, 16))
        label(front, _clip(card["front"], 70), 13, "bold", anchor="w", justify="left").pack(anchor="w")
        if self.selected is None:
            label(front, card["deck_name"], 11, color=C.FAINT).pack(anchor="w")
        label(row, _clip(card["back"], 80), 13, color=C.MUTED, anchor="w", justify="left").grid(row=0, column=1, sticky="w", padx=(0, 16))
        BoxMeter(row, card["box"]).grid(row=0, column=2, padx=(0, 12))
        icon_button(row, "edit", lambda c=card: self.edit_card(c)).grid(row=0, column=3)
        icon_button(row, "trash", lambda c=card: self.delete_card(c), "danger").grid(row=0, column=4, padx=(2, 0))
        divider(holder).pack(fill="x")

    def new_card(self):
        decks = ensure_decks(self, self.db)
        if not decks:
            return
        result = CardEditor(self, decks, deck_id=self.selected).run()
        if result:
            deck_id, front, back = result
            try:
                self.db.add_card(deck_id, front, back)
            except ValueError as exc:
                self.app.notify(str(exc), "error")
                return
            self.app.notify("Card added")
            self.refresh()

    def edit_card(self, card):
        result = CardEditor(self, self.db.list_decks(), card["deck_id"], card["front"], card["back"], "Edit card").run()
        if result:
            try:
                self.db.update_card(card["id"], *result)
            except ValueError as exc:
                self.app.notify(str(exc), "error")
                return
            self.app.notify("Card updated")
            self.refresh()

    def delete_card(self, card):
        if messagebox.askyesno("Delete card", "Delete this card?", parent=self):
            self.db.delete_card(card["id"])
            self.refresh()

    def _go(self, page: str):
        self.app.show(page, deck_id=self.selected)
