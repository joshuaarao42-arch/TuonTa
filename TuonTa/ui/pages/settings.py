"""Settings: OCR engine, data import/export and housekeeping."""
from __future__ import annotations

import os
import subprocess
import sys
from tkinter import filedialog, messagebox

import customtkinter as ctk

from ... import APP_NAME, __version__
from ...config import DATA_DIR
from ...core import ocr
from ...core.transfer import TransferError, export_json, import_json
from ..components import Page, button, divider, entry, label
from ..icons import logo
from ..theme import C, PAD


class SettingsPage(Page):
    def __init__(self, app):
        super().__init__(app)
        self.header("Settings", "Everything stays on this computer.")
        col = ctk.CTkFrame(self, fg_color="transparent")
        col.pack(fill="both", expand=True, padx=PAD, pady=(24, 28), anchor="w")

        label(col, "Text recognition", 16, "bold").pack(anchor="w")
        self.ocr_status = label(col, "", 13, color=C.MUTED, wraplength=640, justify="left")
        self.ocr_status.pack(anchor="w", pady=(4, 10))
        row = ctk.CTkFrame(col, fg_color="transparent")
        row.pack(anchor="w")
        self.path = entry(row, "Path to tesseract (leave empty to auto-detect)", width=440)
        self.path.pack(side="left")
        button(row, "Browse", self.browse, "secondary", width=80).pack(side="left", padx=8)
        button(row, "Apply", self.apply_ocr, "primary", width=80).pack(side="left")

        divider(col).pack(fill="x", pady=26)
        label(col, "Library", 16, "bold").pack(anchor="w")
        label(col, f"Notes, decks, cards and scores live in {DATA_DIR}", 13, color=C.MUTED, wraplength=640, justify="left").pack(anchor="w", pady=(4, 10))
        row = ctk.CTkFrame(col, fg_color="transparent")
        row.pack(anchor="w")
        button(row, "Export to JSON", self.export, "secondary", "export").pack(side="left", padx=(0, 8))
        button(row, "Import from JSON", self.import_, "secondary", "import").pack(side="left", padx=(0, 8))
        button(row, "Open data folder", self.open_folder, "ghost", "folder").pack(side="left")
        button(col, "Delete all data", self.wipe, "danger", "trash").pack(anchor="w", pady=(14, 0))

        divider(col).pack(fill="x", pady=26)
        about = ctk.CTkFrame(col, fg_color="transparent")
        about.pack(anchor="w")
        ctk.CTkLabel(about, text="", image=logo(44)).pack(side="left")
        text = ctk.CTkFrame(about, fg_color="transparent")
        text.pack(side="left", padx=14)
        label(text, f"{APP_NAME} {__version__}", 14, "bold").pack(anchor="w")
        label(text, "Text comes from Tesseract. Flashcards are found with plain pattern rules.\nNo AI services, no accounts and no network requests.", 12,
              color=C.MUTED, justify="left").pack(anchor="w")

    def on_show(self, **_):
        self.path.delete(0, "end")
        self.path.insert(0, self.app.settings.get("tesseract_cmd") or "")
        self._status()

    def _status(self):
        ready, msg = ocr.status()
        found = ocr.locate_tesseract(self.app.settings.get("tesseract_cmd") or "")
        self.ocr_status.configure(text=msg + (f"\n{found}" if ready and found else ""), text_color=C.OK if ready else C.BAD)

    def browse(self):
        path = filedialog.askopenfilename(parent=self, title="Locate the tesseract program")
        if path:
            self.path.delete(0, "end")
            self.path.insert(0, path)

    def apply_ocr(self):
        value = self.path.get().strip()
        if value and not os.path.isfile(value):
            self.app.notify("That path doesn't point to a file.", "error")
            return
        self.app.settings.set("tesseract_cmd", value)
        ocr.configure(value)
        self._status()
        self.app.notify("Text recognition settings applied")

    def export(self):
        path = filedialog.asksaveasfilename(parent=self, defaultextension=".json", initialfile="tuonta-library.json",
                                            filetypes=[("JSON", "*.json")])
        if not path:
            return
        try:
            n = export_json(self.db, path)
        except TransferError as exc:
            self.app.notify(str(exc), "error")
            return
        self.app.notify(f"Exported {n['notes']} notes and {n['cards']} cards")

    def import_(self):
        path = filedialog.askopenfilename(parent=self, filetypes=[("JSON", "*.json")], title="Choose a TuonTa export")
        if not path:
            return
        try:
            n = import_json(self.db, path)
        except TransferError as exc:
            self.app.notify(str(exc), "error")
            return
        self.app.notify(f"Imported {n['notes']} notes, {n['decks']} decks and {n['cards']} cards")

    def open_folder(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        try:
            if sys.platform.startswith("win"):
                os.startfile(DATA_DIR)  # noqa: S606
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(DATA_DIR)])
            else:
                subprocess.Popen(["xdg-open", str(DATA_DIR)])
        except OSError:
            self.app.notify(f"Could not open the folder. It is at {DATA_DIR}", "error")

    def wipe(self):
        if messagebox.askyesno("Delete all data", "Delete every note, deck, card and quiz score? Export first if you might want them back.",
                               icon="warning", parent=self):
            self.db.wipe()
            self.app.notify("All data deleted")
