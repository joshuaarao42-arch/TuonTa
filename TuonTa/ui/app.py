"""Main window: fixed sidebar plus a stack of pages."""
from __future__ import annotations

import sys
import traceback
import tkinter as tk
from pathlib import Path

import customtkinter as ctk

from .. import APP_NAME
from ..config import DB_PATH, IMAGES_DIR, SETTINGS_PATH
from ..core import ocr
from ..core.database import Database
from ..core.settings import Settings
from .components import Toast
from .drawing import draw_logo
from .sidebar import NAV, Sidebar
from .theme import C

ICON_FILE = Path(__file__).resolve().parents[2] / "assets" / "icon.ico"


class TuonTaApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        self.title(APP_NAME)
        self.geometry("1280x800")
        self.minsize(1120, 700)
        self.configure(fg_color=C.BG)

        IMAGES_DIR.mkdir(parents=True, exist_ok=True)
        self.db = Database(DB_PATH)
        self.settings = Settings(SETTINGS_PATH)
        ocr.configure(self.settings.get("tesseract_cmd"))

        self.grid_columnconfigure(2, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.sidebar = Sidebar(self, self.show)
        self.sidebar.grid(row=0, column=0, sticky="ns")
        ctk.CTkFrame(self, width=1, fg_color=C.BORDER, corner_radius=0).grid(row=0, column=1, sticky="ns")
        self.content = ctk.CTkFrame(self, fg_color=C.BG, corner_radius=0)
        self.content.grid(row=0, column=2, sticky="nsew")
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)
        self.toast = Toast(self)

        from .pages.dashboard import DashboardPage
        from .pages.flashcards import FlashcardsPage
        from .pages.notes import NotesPage
        from .pages.quiz import QuizPage
        from .pages.review import ReviewPage
        from .pages.scan import ScanPage
        from .pages.settings import SettingsPage

        self.pages = {
            "dashboard": DashboardPage(self), "scan": ScanPage(self), "notes": NotesPage(self),
            "flashcards": FlashcardsPage(self), "review": ReviewPage(self), "quiz": QuizPage(self),
            "settings": SettingsPage(self),
        }
        self.current: str | None = None
        for i, (key, *_rest) in enumerate(NAV, start=1):
            self.bind(f"<Control-Key-{i}>", lambda _e, k=key: self.show(k))
        self.protocol("WM_DELETE_WINDOW", self._close)
        self.after(250, self._set_icon)
        self.show("dashboard")

    def show(self, name: str, **kwargs) -> None:
        if self.current and name != self.current and not self.pages[self.current].on_hide():
            return
        if self.current and name != self.current:
            self.pages[self.current].grid_remove()
        page = self.pages[name]
        page.grid(row=0, column=0, sticky="nsew")
        page.tkraise()
        self.current = name
        self.sidebar.set_active(name)
        page.on_show(**kwargs)

    def notify(self, message: str, kind: str = "ok") -> None:
        self.toast.show(message, kind)

    def _set_icon(self) -> None:
        try:
            if sys.platform.startswith("win") and ICON_FILE.exists():
                self.iconbitmap(str(ICON_FILE))
            else:
                from PIL import ImageTk
                self._icon_ref = ImageTk.PhotoImage(draw_logo(64, tile=True))
                self.iconphoto(True, self._icon_ref)
        except Exception:
            pass

    def report_callback_exception(self, exc, val, tb):  # keep the window alive on unexpected errors
        traceback.print_exception(exc, val, tb)
        self.notify(f"Something went wrong: {val}", "error")

    def _close(self) -> None:
        page = self.pages.get(self.current)
        if page is not None and not page.on_hide():
            return
        self.db.close()
        self.destroy()
