"""Tiny JSON-backed settings store that survives a corrupt file."""
from __future__ import annotations

import json
from pathlib import Path

DEFAULTS = {"tesseract_cmd": "", "ocr_lang": "eng", "last_dir": ""}


class Settings:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.data = dict(DEFAULTS)
        self.load()

    def load(self) -> None:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                self.data.update({k: v for k, v in raw.items() if k in DEFAULTS})
        except (OSError, ValueError):
            pass

    def get(self, key: str):
        return self.data.get(key, DEFAULTS.get(key))

    def set(self, key: str, value) -> None:
        self.data[key] = value
        self.save()

    def save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self.data, indent=2), encoding="utf-8")
        except OSError:
            pass
