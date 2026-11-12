"""Notes: searchable list on the left, editor on the right."""
from __future__ import annotations

import re
import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk

from ...core.parser import extract_pairs
from ..components import Page, bind_click, button, entry, label, option_menu, scroll_frame, textbox
from ..dialogs import CardEditor, PairPicker, TextPrompt, ensure_decks
from ..theme import C, PAD

ALL_TAGS = "All tags"


def _clip(text: str, n: int) -> str:
    text = " ".join(text.split())
    return text if len(text) <= n else text[: n - 1] + "\u2026"


class NotesPage(Page):
    def __init__(self, app):
        super().__init__(app)
        self.current_id: int | None = None
        self.snapshot = ("", "", "")
        self._search_job = None

        actions = self.header("Notes", "Edit, search and organise what you have scanned.")
        button(actions, "New note", self.new_note, "primary", "plus").pack()

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=PAD, pady=(22, 28))
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        left = ctk.CTkFrame(body, fg_color="transparent", width=320)
        left.grid(row=0, column=0, sticky="ns", padx=(0, 22))
        left.pack_propagate(False)
        self.search = entry(left, "Search notes", width=320)
        self.search.pack(fill="x")
        self.search.bind("<KeyRelease>", lambda _e: self._debounced())
        self.tag_menu = option_menu(left, [ALL_TAGS], command=lambda _v: self.refresh(), width=320)
        self.tag_menu.pack(fill="x", pady=8)
        self.listing = scroll_frame(left)
        self.listing.pack(fill="both", expand=True)

        right = ctk.CTkFrame(body, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew")
        self.empty = label(right, "Select a note, or create a new one.", 14, color=C.FAINT)
        self.empty.pack(expand=True)
        self.editor = ctk.CTkFrame(right, fg_color="transparent")
        self.title_entry = entry(self.editor, "Title")
        self.title_entry.pack(fill="x")
        self.tags_entry = entry(self.editor, "Tags, separated by commas")
        self.tags_entry.pack(fill="x", pady=8)
        self.body = textbox(self.editor, 14)
        self.body.pack(fill="both", expand=True)
        bar = ctk.CTkFrame(self.editor, fg_color="transparent")
        bar.pack(fill="x", pady=(10, 0))
        self.status = label(bar, "", 12, color=C.MUTED)
        self.status.pack(side="left")
        button(bar, "Save", self.save, "primary", "save", width=90).pack(side="right")
        button(bar, "Make flashcards", self.make_cards, "secondary", "wand").pack(side="right", padx=8)
        button(bar, "Export .txt", self.export_txt, "ghost", "export").pack(side="right")
        button(bar, "Delete", self.delete, "danger", "trash").pack(side="left", padx=(16, 0))
        for w in (self.title_entry, self.tags_entry, self.body):
            w.bind("<KeyRelease>", lambda _e: self._mark(), add="+")
        app.bind("<Control-s>", self._ctrl_s, add="+")

    # ------------------------------------------------------------ list
    def on_show(self, note_id: int | None = None, new: bool = False, **_):
        tags = [ALL_TAGS] + self.db.all_tags()
        keep = self.tag_menu.get()
        self.tag_menu.configure(values=tags)
        self.tag_menu.set(keep if keep in tags else ALL_TAGS)
        if new:
            self.new_note()
        elif note_id:
            self.current_id = None
            self._load(note_id)
        self.refresh()

    def _debounced(self):
        if self._search_job:
            self.after_cancel(self._search_job)
        self._search_job = self.after(180, self.refresh)

    def refresh(self):
        for child in self.listing.winfo_children():
            child.destroy()
        tag = "" if self.tag_menu.get() == ALL_TAGS else self.tag_menu.get()
        notes = self.db.list_notes(self.search.get(), tag)
        if not notes:
            msg = "No notes match your search." if (self.search.get().strip() or tag) else "No notes yet.\nScan an image or press New note."
            label(self.listing, msg, 13, color=C.FAINT, justify="left").pack(anchor="w", pady=14, padx=4)
        for note in notes[:200]:
            self._row(note)

    def _row(self, note):
        selected = note["id"] == self.current_id
        row = ctk.CTkFrame(self.listing, fg_color=C.RAISED if selected else "transparent", corner_radius=4)
        row.pack(fill="x", pady=1)
        if selected:
            ctk.CTkFrame(row, width=3, fg_color=C.ACCENT, corner_radius=0).pack(side="left", fill="y")
        col = ctk.CTkFrame(row, fg_color="transparent")
        col.pack(side="left", fill="x", expand=True, padx=12, pady=9)
        label(col, _clip(note["title"], 34), 13, "bold", anchor="w").pack(anchor="w")
        snippet = _clip(note["body"], 46) or "Empty note"
        label(col, snippet, 12, color=C.MUTED, anchor="w").pack(anchor="w")
        meta = note["updated_at"][:10] + (f'   {_clip(note["tags"], 22)}' if note["tags"] else "")
        label(col, meta, 11, color=C.FAINT, anchor="w").pack(anchor="w", pady=(2, 0))
        bind_click(row, lambda nid=note["id"]: self.select(nid))

    # ------------------------------------------------------------ editing
    def _fields(self):
        return (self.title_entry.get(), self.tags_entry.get(), self.body.get("1.0", "end-1c"))

    @property
    def dirty(self) -> bool:
        return self.editor.winfo_ismapped() and self._fields() != self.snapshot

    def _mark(self):
        self.status.configure(text="Unsaved changes" if self.dirty else "", text_color=C.ACCENT)

    def _show_editor(self, visible: bool):
        if visible:
            self.empty.pack_forget()
            self.editor.pack(fill="both", expand=True)
        else:
            self.editor.pack_forget()
            self.empty.pack(expand=True)

    def _confirm_discard(self) -> bool:
        if not self.dirty:
            return True
        answer = messagebox.askyesnocancel("Unsaved changes", "Save your changes to this note first?", parent=self)
        if answer is None:
            return False
        return self.save() if answer else True

    def on_hide(self) -> bool:
        return self._confirm_discard()

    def select(self, note_id: int):
        if note_id != self.current_id and self._confirm_discard():
            self._load(note_id)
            self.refresh()

    def _load(self, note_id: int):
        note = self.db.get_note(note_id)
        if note is None:
            self.app.notify("That note no longer exists.", "error")
            return
        self.current_id = note_id
        self.title_entry.delete(0, "end")
        self.title_entry.insert(0, note["title"])
        self.tags_entry.delete(0, "end")
        self.tags_entry.insert(0, note["tags"])
        self.body.delete("1.0", "end")
        self.body.insert("1.0", note["body"])
        try:
            self.body._textbox.edit_reset()
        except (AttributeError, tk.TclError):
            pass
        self.snapshot = self._fields()
        self.title_entry.configure(border_color=C.BORDER)
        self._show_editor(True)
        self._mark()

    def new_note(self):
        if not self._confirm_discard():
            return
        self.current_id = None
        self._show_editor(True)
        for w in (self.title_entry, self.tags_entry):
            w.delete(0, "end")
        self.body.delete("1.0", "end")
        self.snapshot = self._fields()
        self.title_entry.configure(border_color=C.BORDER)
        self._mark()
        self.title_entry.focus_set()
        self.refresh()

    def save(self) -> bool:
        title, tags, body = self._fields()
        if not title.strip():
            self.title_entry.configure(border_color=C.BAD)
            self.title_entry.focus_set()
            self.app.notify("Give the note a title before saving.", "error")
            return False
        try:
            if self.current_id is None:
                self.current_id = self.db.add_note(title, body, tags)
            else:
                self.db.update_note(self.current_id, title, body, tags)
        except ValueError as exc:
            self.app.notify(str(exc), "error")
            return False
        self.title_entry.configure(border_color=C.BORDER)
        self.snapshot = self._fields()
        self._mark()
        self.app.notify("Note saved")
        self.on_show()
        return True

    def _ctrl_s(self, _event):
        if self.app.current == "notes" and self.editor.winfo_ismapped():
            self.save()
            return "break"
        return None

    def delete(self):
        if self.current_id is None:
            self.snapshot = self._fields()  # unsaved draft: just discard it
            self.title_entry.delete(0, "end")
            self.tags_entry.delete(0, "end")
            self.body.delete("1.0", "end")
            self._show_editor(False)
            return
        if not messagebox.askyesno("Delete note", "Delete this note? Flashcards made from it are kept.", parent=self):
            return
        self.db.delete_note(self.current_id)
        self.current_id = None
        self.snapshot = ("", "", "")
        self._show_editor(False)
        self.app.notify("Note deleted")
        self.on_show()

    def export_txt(self):
        title, _tags, body = self._fields()
        if not (title.strip() or body.strip()):
            self.app.notify("There is nothing to export yet.", "info")
            return
        safe = re.sub(r"[^\w\- ]+", "", title).strip()[:50] or "note"
        path = filedialog.asksaveasfilename(parent=self, defaultextension=".txt", initialfile=f"{safe}.txt",
                                            filetypes=[("Text file", "*.txt")])
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(f"{title.strip()}\n\n{body}")
        except OSError as exc:
            self.app.notify(f"Could not save the file: {exc.strerror}", "error")
            return
        self.app.notify("Exported as text")

    # ------------------------------------------------------------ flashcards
    def make_cards(self):
        title, _tags, body = self._fields()
        try:
            selection = self.body.get("sel.first", "sel.last").strip()
        except tk.TclError:
            selection = ""
        note_id = self.current_id
        if selection:  # build one card by hand from the highlighted text
            decks = ensure_decks(self, self.db)
            if not decks:
                return
            result = CardEditor(self, decks, back=selection).run()
            if result:
                deck_id, front, back = result
                self.db.add_card(deck_id, front, back, note_id)
                self.app.notify("Card added")
            return
        pairs = extract_pairs(body)
        if not pairs:
            self.app.notify("No \"term: definition\" lines found. Highlight some text to build a card by hand.", "info")
            return
        result = PairPicker(self, pairs, self.db.list_decks(), default_deck_name=title.strip()).run()
        if not result:
            return
        deck_id, chosen = result
        if deck_id is None:
            name = TextPrompt(self, "New deck", "Deck name", initial=title.strip()[:80], ok_text="Create").run()
            if not name:
                return
            try:
                deck_id = self.db.add_deck(name)
            except ValueError as exc:
                self.app.notify(str(exc), "error")
                return
        added = self.db.add_cards(deck_id, chosen, note_id)
        deck = self.db.get_deck(deck_id)["name"]
        skipped = len(chosen) - added
        extra = f" ({skipped} already existed)" if skipped else ""
        self.app.notify(f"{added} cards added to {deck}{extra}")
