"""OCR workspace: image on the left, editable text on the right."""
from __future__ import annotations

import queue
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk
from PIL import Image, ImageGrab

from ...config import IMAGE_TYPES, IMAGES_DIR
from ...core import ocr
from ..components import Page, button, label, option_menu, textbox
from ..dialogs import TextPrompt
from ..theme import C, PAD, font


class ScanPage(Page):
    def __init__(self, app):
        super().__init__(app)
        self.image: Image.Image | None = None
        self.source: Path | None = None
        self.busy = False
        self._resize_job = None
        self._results: queue.Queue = queue.Queue()

        actions = self.header("Scan", "Turn a screenshot or photo of study material into text.")
        button(actions, "Open image", self.open_image, "secondary", "image").pack(side="left", padx=(0, 8))
        button(actions, "Paste screenshot", self.paste, "secondary", "paste").pack(side="left")

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=PAD, pady=(22, 28))
        body.grid_columnconfigure((0, 1), weight=1, uniform="pane")
        body.grid_rowconfigure(0, weight=1)

        self.frame = ctk.CTkFrame(body, fg_color=C.SURFACE, border_width=1, border_color=C.BORDER, corner_radius=4)
        self.frame.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        self.frame.pack_propagate(False)
        self.preview = ctk.CTkLabel(self.frame, text=self.EMPTY, font=font(13), text_color=C.FAINT, justify="center")
        self.preview.pack(expand=True, fill="both", padx=12, pady=12)
        self.frame.bind("<Configure>", self._on_resize)

        right = ctk.CTkFrame(body, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew")
        bar = ctk.CTkFrame(right, fg_color="transparent")
        bar.pack(fill="x")
        self.layout = option_menu(bar, list(ocr.LAYOUTS), width=130)
        self.layout.pack(side="left")
        self.lang = option_menu(bar, ["eng"], command=lambda v: app.settings.set("ocr_lang", v), width=90)
        self.lang.pack(side="left", padx=8)
        self.run_btn = button(bar, "Extract text", self.run_ocr, "primary", "scan")
        self.run_btn.pack(side="right")
        self.text = textbox(right, 14)
        self.text.pack(fill="both", expand=True, pady=(10, 0))
        self.progress = ctk.CTkProgressBar(right, height=3, corner_radius=0, fg_color=C.BG, progress_color=C.ACCENT,
                                           mode="indeterminate")
        self.progress.pack(fill="x", pady=(10, 0))
        foot = ctk.CTkFrame(right, fg_color="transparent")
        foot.pack(fill="x", pady=(8, 0))
        self.status = label(foot, "", 12, color=C.MUTED, wraplength=300, justify="left")
        self.status.pack(side="left")
        button(foot, "Save as note", self.save_note, "primary", "save").pack(side="right")
        button(foot, "Copy", self.copy, "secondary", "copy", width=80).pack(side="right", padx=8)
        button(foot, "Clear", self.clear, "ghost", width=70).pack(side="right")
        app.bind("<Control-v>", self._ctrl_v, add="+")

    EMPTY = "No image yet.\n\nOpen a PNG or JPG, or press Ctrl+V\nto paste a screenshot."

    def on_show(self, **_):
        ready, msg = ocr.status()
        self.status.configure(text=msg, text_color=C.MUTED if ready else C.BAD)
        langs = ocr.languages()
        self.lang.configure(values=langs)
        saved = self.app.settings.get("ocr_lang")
        self.lang.set(saved if saved in langs else langs[0])
        self._render_preview()

    # ---------------------------------------------------------------- loading images
    def open_image(self):
        path = filedialog.askopenfilename(parent=self, title="Choose an image", filetypes=IMAGE_TYPES,
                                          initialdir=self.app.settings.get("last_dir") or None)
        if not path:
            return
        self.app.settings.set("last_dir", str(Path(path).parent))
        try:
            self.image = ocr.load_image(path)
        except ocr.OCRError as exc:
            self.app.notify(str(exc), "error")
            return
        self.source = Path(path)
        self._render_preview()
        self.run_ocr()

    def paste(self):
        try:
            clip = ImageGrab.grabclipboard()
        except Exception:
            clip = None
        if isinstance(clip, Image.Image):
            self.image, self.source = clip.convert("RGB"), None
        elif isinstance(clip, list) and clip and Path(clip[0]).suffix.lower() in (".png", ".jpg", ".jpeg"):
            try:
                self.image, self.source = ocr.load_image(clip[0]), Path(clip[0])
            except ocr.OCRError as exc:
                self.app.notify(str(exc), "error")
                return
        else:
            self.app.notify("The clipboard has no image. Take a screenshot first (Win+Shift+S, Cmd+Shift+Ctrl+4).", "info")
            return
        self._render_preview()
        self.run_ocr()

    def _ctrl_v(self, _event):
        if self.app.current != "scan":
            return None
        try:
            if str(self.app.focus_get()).startswith(str(self.text)):
                return None  # normal text paste inside the editor
        except (KeyError, tk.TclError):
            pass
        self.paste()
        return "break"

    # ---------------------------------------------------------------- preview
    def _on_resize(self, _event):
        if self._resize_job:
            self.after_cancel(self._resize_job)
        self._resize_job = self.after(80, self._render_preview)

    def _render_preview(self):
        if self.image is None:
            blank = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
            self._photo = ctk.CTkImage(light_image=blank, dark_image=blank, size=(1, 1))
            self.preview.configure(image=self._photo, text=self.EMPTY)
            return
        w, h = max(self.frame.winfo_width() - 24, 50), max(self.frame.winfo_height() - 24, 50)
        scale = min(w / self.image.width, h / self.image.height, 1.0)
        size = (max(1, int(self.image.width * scale)), max(1, int(self.image.height * scale)))
        shown = self.image.resize((size[0] * 2, size[1] * 2), Image.LANCZOS) if scale < 1 else self.image
        self._photo = ctk.CTkImage(light_image=shown, dark_image=shown, size=size)
        self.preview.configure(image=self._photo, text="")

    # ---------------------------------------------------------------- OCR
    def run_ocr(self):
        if self.image is None:
            self.app.notify("Open or paste an image first.", "info")
            return
        if self.busy:
            return
        self.busy = True
        self.run_btn.configure(state="disabled", text="Reading...")
        self.status.configure(text="Reading text. Large images can take a few seconds.", text_color=C.MUTED)
        self.progress.start()
        img, lang, layout = self.image, self.lang.get(), self.layout.get()

        def work():
            try:
                self._results.put(("ok", ocr.extract_text(img, lang, layout)))
            except ocr.OCRError as exc:
                self._results.put(("error", str(exc)))
            except Exception as exc:  # never let a worker die silently
                self._results.put(("error", f"Unexpected OCR problem: {exc}"))

        threading.Thread(target=work, daemon=True).start()
        self.after(120, self._poll)

    def _poll(self):
        try:
            kind, payload = self._results.get_nowait()
        except queue.Empty:
            self.after(120, self._poll)
            return
        self.busy = False
        self.progress.stop()
        self.progress.set(0)
        self.run_btn.configure(state="normal", text="Extract text")
        if kind == "ok":
            self.text.delete("1.0", "end")
            self.text.insert("1.0", payload)
            words = len(payload.split())
            self.status.configure(text=f"{words} words found. Fix any mistakes, then save as a note.", text_color=C.MUTED)
        else:
            self.status.configure(text=payload, text_color=C.BAD)
            self.app.notify(payload, "error")

    # ---------------------------------------------------------------- actions
    def _text(self) -> str:
        return self.text.get("1.0", "end-1c").strip()

    def copy(self):
        text = self._text()
        if not text:
            self.app.notify("There is no text to copy.", "info")
            return
        self.clipboard_clear()
        self.clipboard_append(text)
        self.app.notify("Text copied")

    def clear(self):
        self.text.delete("1.0", "end")
        self.image, self.source = None, None
        self._render_preview()
        self.status.configure(text="")

    def save_note(self):
        text = self._text()
        if not text:
            self.app.notify("Extract or type some text first.", "info")
            return
        first = next((ln.strip() for ln in text.splitlines() if ln.strip()), "Scanned note")
        default = first[:60]
        title = TextPrompt(self, "Save as note", "Note title", initial=default, ok_text="Save note", max_len=200).run()
        if not title:
            return
        stored = None
        if self.image is not None:
            try:
                IMAGES_DIR.mkdir(parents=True, exist_ok=True)
                stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                dest = IMAGES_DIR / f"{stamp}.png"
                self.image.save(dest)
                stored = str(dest)
            except OSError:
                stored = None  # the note is still worth saving without its source image
        try:
            note_id = self.db.add_note(title, text, "scan", stored)
        except ValueError as exc:
            self.app.notify(str(exc), "error")
            return
        self.app.notify("Saved to Notes")
        self.app.show("notes", note_id=note_id)
