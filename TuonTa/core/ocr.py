"""Offline OCR through Tesseract, with Pillow pre-processing."""
from __future__ import annotations

import re
import shutil
from pathlib import Path

from PIL import Image, ImageFilter, ImageOps, ImageStat, UnidentifiedImageError

from ..config import MAX_IMAGE_MB, SUPPORTED_SUFFIXES

try:
    import pytesseract
except ImportError:  # handled with a friendly message at call time
    pytesseract = None

_COMMON = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    "/usr/bin/tesseract", "/usr/local/bin/tesseract", "/opt/homebrew/bin/tesseract",
)
INSTALL_HINT = (
    "Tesseract OCR was not found. Install it (Windows: github.com/UB-Mannheim/tesseract/wiki, "
    "macOS: brew install tesseract, Linux: apt install tesseract-ocr) or set its path in Settings."
)
LAYOUTS = {"Full page": 3, "Single block": 6, "Sparse text": 11}


class OCRError(Exception):
    """A problem the user can act on."""


def locate_tesseract(custom: str = "") -> str | None:
    if custom and Path(custom).is_file():
        return custom
    found = shutil.which("tesseract")
    if found:
        return found
    return next((p for p in _COMMON if Path(p).is_file()), None)


def configure(custom: str = "") -> str | None:
    path = locate_tesseract(custom)
    if pytesseract and path:
        pytesseract.pytesseract.tesseract_cmd = path
    return path


def status() -> tuple[bool, str]:
    """(ready, message) for display in the UI."""
    if pytesseract is None:
        return False, "pytesseract is not installed. Run: pip install -r requirements.txt"
    try:
        return True, f"Tesseract {pytesseract.get_tesseract_version()} ready"
    except Exception:
        return False, INSTALL_HINT


def languages() -> list[str]:
    try:
        langs = [l for l in pytesseract.get_languages(config="") if l != "osd"]
        return langs or ["eng"]
    except Exception:
        return ["eng"]


def load_image(path: str | Path) -> Image.Image:
    p = Path(path)
    if p.suffix.lower() not in SUPPORTED_SUFFIXES:
        raise OCRError("Only PNG, JPG and JPEG images are supported.")
    if not p.is_file():
        raise OCRError("That file no longer exists.")
    if p.stat().st_size > MAX_IMAGE_MB * 1024 * 1024:
        raise OCRError(f"That image is larger than {MAX_IMAGE_MB} MB.")
    try:
        with Image.open(p) as img:
            img.load()
            return ImageOps.exif_transpose(img).convert("RGB")
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise OCRError("That file could not be opened as an image.") from exc


def preprocess(img: Image.Image) -> Image.Image:
    """Grayscale, upscale small screenshots, stretch contrast, fix dark themes, sharpen."""
    gray = ImageOps.grayscale(img)
    short = min(gray.size)
    if short < 1000:
        factor = min(3.0, 1000 / short)
        gray = gray.resize((round(gray.width * factor), round(gray.height * factor)), Image.LANCZOS)
    gray = ImageOps.autocontrast(gray, cutoff=1)
    if ImageStat.Stat(gray).mean[0] < 110:  # light text on dark background
        gray = ImageOps.invert(gray)
    return gray.filter(ImageFilter.SHARPEN)


def clean_text(text: str) -> str:
    text = "\n".join(line.rstrip() for line in text.replace("\x0c", "").splitlines())
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def extract_text(img: Image.Image, lang: str = "eng", layout: str = "Full page") -> str:
    if pytesseract is None:
        raise OCRError("pytesseract is not installed. Run: pip install -r requirements.txt")
    psm = LAYOUTS.get(layout, 3)
    try:
        raw = pytesseract.image_to_string(preprocess(img), lang=lang, config=f"--oem 3 --psm {psm}", timeout=90)
    except pytesseract.TesseractNotFoundError as exc:
        raise OCRError(INSTALL_HINT) from exc
    except pytesseract.TesseractError as exc:
        raise OCRError(f"Tesseract could not read this image ({str(exc).strip()[:120]}).") from exc
    except RuntimeError as exc:
        raise OCRError("OCR took too long and was stopped.") from exc
    text = clean_text(raw)
    if not text:
        raise OCRError("No text was found. Try another layout mode or a sharper image.")
    return text
