"""Paths and application-wide constants."""
from __future__ import annotations

import os
from pathlib import Path

from . import APP_NAME, __version__  # noqa: F401  (re-exported)

DATA_DIR = Path(os.environ.get("TUONTA_HOME", Path.home() / ".tuonta"))
DB_PATH = DATA_DIR / "tuonta.db"
SETTINGS_PATH = DATA_DIR / "settings.json"
IMAGES_DIR = DATA_DIR / "images"

IMAGE_TYPES = [("Images", "*.png *.jpg *.jpeg"), ("PNG", "*.png"), ("JPEG", "*.jpg *.jpeg")]
SUPPORTED_SUFFIXES = {".png", ".jpg", ".jpeg"}
MAX_IMAGE_MB = 25

MASTERED_BOX = 4      # a card in box 4+ counts as mastered
MAX_BOX = 5
