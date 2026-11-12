"""Regenerate logo.png and icon.ico from the Pillow drawing code.  Run: python scripts/make_assets.py"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tuonta.ui.drawing import draw_logo  # noqa: E402

out = Path(__file__).resolve().parents[1] / "assets"
draw_logo(512, tile=True).save(out / "logo.png")
draw_logo(256, tile=True).save(out / "icon.ico", sizes=[(s, s) for s in (16, 32, 48, 64, 128, 256)])
print("wrote", out / "logo.png", "and", out / "icon.ico")
