"""Modal dialogs."""
from __future__ import annotations

import customtkinter as ctk

from .components import button, entry, label, option_menu, scroll_frame, textbox
from .theme import C, font


class Modal(ctk.CTkToplevel):
    def __init__(self, master, title: str, width: int, height: int):
        super().__init__(master)
        self.title(title)
        self.configure(fg_color=C.BG)
        self.resizable(False, False)
        self.result = None
        top = master.winfo_toplevel()
        x = top.winfo_rootx() + (top.winfo_width() - width) // 2
        y = top.winfo_rooty() + (top.winfo_height() - height) // 3
        self.geometry(f"{width}x{height}+{max(x, 0)}+{max(y, 0)}")
        self.transient(top)
        self.bind("<Escape>", lambda _e: self.destroy())
        self.after(120, self._grab)

    def _grab(self):
        try:
            self.grab_set()
            self.focus_force()
        except Exception:
            pass

    def finish(self, value) -> None:
        self.result = value
        self.destroy()

    def run(self):
        self.wait_window(self)
        return self.result

    def footer(self, ok_text: str, on_ok):
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(side="bottom", fill="x", padx=24, pady=(8, 20))
        button(row, ok_text, on_ok, "primary", width=110).pack(side="right")
        button(row, "Cancel", self.destroy, "ghost", width=80).pack(side="right", padx=(0, 8))


class TextPrompt(Modal):
    def __init__(self, master, title: str, prompt: str, initial: str = "", ok_text: str = "Save", max_len: int = 80):
        super().__init__(master, title, 420, 190)
        self.max_len = max_len
        label(self, prompt, 13, color=C.MUTED).pack(anchor="w", padx=24, pady=(24, 6))
        self.entry = entry(self, width=372)
        self.entry.pack(padx=24)
        self.entry.insert(0, initial)
        self.error = label(self, "", 12, color=C.BAD)
        self.error.pack(anchor="w", padx=24, pady=(6, 0))
        self.footer(ok_text, self._ok)
        self.entry.bind("<Return>", lambda _e: self._ok())
        self.after(150, self.entry.focus_set)

    def _ok(self):
        value = self.entry.get().strip()
        if not value:
            self.error.configure(text="This can't be empty.")
        elif len(value) > self.max_len:
            self.error.configure(text=f"Keep it under {self.max_len} characters.")
        else:
            self.finish(value)


class CardEditor(Modal):
    """Create or edit one card. Result: (deck_id, front, back)."""

    def __init__(self, master, decks, deck_id=None, front="", back="", title="New card"):
        super().__init__(master, title, 520, 470)
        self.decks = {d["name"]: d["id"] for d in decks}
        label(self, "Deck", 13, color=C.MUTED).pack(anchor="w", padx=24, pady=(22, 4))
        names = list(self.decks)
        current = next((d["name"] for d in decks if d["id"] == deck_id), names[0] if names else "")
        self.deck = option_menu(self, names, width=472)
        self.deck.set(current)
        self.deck.pack(padx=24)
        label(self, "Front (term or question)", 13, color=C.MUTED).pack(anchor="w", padx=24, pady=(14, 4))
        self.front = textbox(self, 14, height=90, width=472)
        self.front.pack(padx=24)
        self.front.insert("1.0", front)
        label(self, "Back (answer)", 13, color=C.MUTED).pack(anchor="w", padx=24, pady=(14, 4))
        self.back = textbox(self, 14, height=110, width=472)
        self.back.pack(padx=24)
        self.back.insert("1.0", back)
        self.error = label(self, "", 12, color=C.BAD)
        self.error.pack(anchor="w", padx=24, pady=(6, 0))
        self.footer("Save card", self._ok)
        self.after(150, self.front.focus_set)

    def _ok(self):
        front, back = self.front.get("1.0", "end-1c").strip(), self.back.get("1.0", "end-1c").strip()
        if not self.decks:
            self.error.configure(text="Create a deck first.")
        elif not front or not back:
            self.error.configure(text="Both sides need text.")
        elif max(len(front), len(back)) > 1000:
            self.error.configure(text="Each side can hold up to 1000 characters.")
        else:
            self.finish((self.decks[self.deck.get()], front, back))


class PairPicker(Modal):
    """Review pairs detected in a note and choose which become cards. Result: (deck_id, pairs)."""

    def __init__(self, master, pairs, decks, default_deck_name=""):
        super().__init__(master, "Make flashcards", 640, 600)
        self.pairs, self.decks = pairs, {d["name"]: d["id"] for d in decks}
        label(self, f"{len(pairs)} possible cards found", 16, "bold").pack(anchor="w", padx=24, pady=(22, 2))
        label(self, "Untick anything that isn't a real term and definition.", 13, color=C.MUTED).pack(anchor="w", padx=24)
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=24, pady=14)
        label(row, "Add to deck", 13, color=C.MUTED).pack(side="left", padx=(0, 10))
        names = list(self.decks) + ["+ New deck..."]
        self.deck = option_menu(row, names, width=250)
        self.deck.set(default_deck_name if default_deck_name in self.decks else names[0])
        self.deck.pack(side="left")
        self.footer("Create cards", self._ok)
        self.error = label(self, "", 12, color=C.BAD)
        self.error.pack(side="bottom", anchor="w", padx=24)
        box = scroll_frame(self)
        box.pack(fill="both", expand=True, padx=18)
        self.vars = []
        for front, back in pairs:
            var = ctk.BooleanVar(value=True)
            self.vars.append(var)
            line = ctk.CTkFrame(box, fg_color="transparent")
            line.pack(fill="x", pady=4)
            ctk.CTkCheckBox(line, text="", variable=var, width=24, checkbox_width=18, checkbox_height=18,
                            corner_radius=3, border_width=1, fg_color=C.ACCENT, hover_color=C.ACCENT_HOVER,
                            border_color=C.FAINT, checkmark_color=C.ON_ACCENT).pack(side="left", padx=(6, 8), anchor="n")
            text = ctk.CTkFrame(line, fg_color="transparent")
            text.pack(side="left", fill="x", expand=True)
            label(text, front, 13, "bold", anchor="w", justify="left", wraplength=520).pack(anchor="w")
            label(text, back, 12, color=C.MUTED, anchor="w", justify="left", wraplength=520).pack(anchor="w")

    def _ok(self):
        chosen = [p for p, v in zip(self.pairs, self.vars) if v.get()]
        if not chosen:
            self.error.configure(text="Select at least one card.")
            return
        name = self.deck.get()
        if name == "+ New deck...":
            self.finish((None, chosen))
        else:
            self.finish((self.decks[name], chosen))


def ensure_decks(master, db):
    """Return the deck list, asking for a first deck name when none exist. None if the user cancels."""
    decks = db.list_decks()
    if decks:
        return decks
    name = TextPrompt(master, "Create a deck", "Cards live in decks. Name your first deck:", ok_text="Create").run()
    if not name:
        return None
    try:
        db.add_deck(name)
    except ValueError as exc:
        from tkinter import messagebox
        messagebox.showerror("Couldn't create deck", str(exc), parent=master.winfo_toplevel())
        return None
    return db.list_decks()
