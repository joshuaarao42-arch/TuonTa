"""Pure-Pillow artwork: the TuonTa logo and the sidebar icon set (no Tk imports)."""
from __future__ import annotations

from PIL import Image, ImageDraw

PAPER, INK, BLUE, BLUE_DIM, CHARCOAL = "#e9e6df", "#e9e6df", "#5b8def", "#2b3f6b", "#141619"
SS = 4  # supersampling factor


# ----------------------------------------------------------------------------- logo
def draw_logo(px: int, tile: bool = False) -> Image.Image:
    """The mark: a page with a folded corner and a T. A blue scan beam crosses it - above the
    beam the T is still paper, below it the T has been captured (blue). A ghost page behind it
    is the flashcard it becomes. Designed on a 100-unit grid."""
    n = px * SS
    k = n / 100
    img = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if tile:
        d.rounded_rectangle((0, 0, n - 1, n - 1), radius=18 * k, fill=CHARCOAL)

    def pts(*p):
        return [(x * k, y * k) for x, y in p]

    page = ((24, 10), (58, 10), (74, 26), (74, 86), (24, 86))
    ghost = tuple((x + 9, y + 8) for x, y in page)
    d.polygon(pts(*ghost), outline=BLUE_DIM, fill=CHARCOAL, width=round(3 * k))
    d.polygon(pts(*page), fill=CHARCOAL)
    d.line(pts(*page, page[0]), fill=PAPER, width=round(3.6 * k), joint="curve")
    d.polygon(pts((58, 10), (58, 26), (74, 26)), fill=BLUE_DIM)            # folded corner
    d.rectangle((36 * k, 30 * k, 62 * k, 38.5 * k), fill=INK)              # T bar
    d.rectangle((45 * k, 38.5 * k, 53 * k, 51 * k), fill=INK)              # T stem, paper half
    d.rectangle((45 * k, 55.5 * k, 53 * k, 72 * k), fill=BLUE)             # T stem, captured half
    d.rectangle((14 * k, 51 * k, 86 * k, 55 * k), fill=BLUE)               # scan beam
    return img.resize((px, px), Image.LANCZOS)


# ----------------------------------------------------------------------------- icons
class _Pen:
    def __init__(self, px: int, color: str):
        self.s = px * SS / 24
        self.img = Image.new("RGBA", (px * SS, px * SS), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.img)
        self.color = color
        self.w = max(2, round(1.9 * self.s))

    def line(self, *pts):
        flat = [v for pt in pts for v in (pt if isinstance(pt, tuple) else (pt,))]
        p = [(flat[i] * self.s, flat[i + 1] * self.s) for i in range(0, len(flat), 2)]
        self.d.line(p, fill=self.color, width=self.w, joint="curve")
        r = self.w / 2
        for x, y in (p[0], p[-1]):
            self.d.ellipse((x - r, y - r, x + r, y + r), fill=self.color)

    def rect(self, x0, y0, x1, y1):
        s = self.s
        self.d.rectangle((x0 * s, y0 * s, x1 * s, y1 * s), outline=self.color, width=self.w)

    def clear(self, x0, y0, x1, y1):
        s = self.s
        self.d.rectangle((x0 * s, y0 * s, x1 * s, y1 * s), fill=(0, 0, 0, 0))

    def circ(self, cx, cy, r, fill=False):
        s = self.s
        box = ((cx - r) * s, (cy - r) * s, (cx + r) * s, (cy + r) * s)
        if fill:
            self.d.ellipse(box, fill=self.color)
        else:
            self.d.ellipse(box, outline=self.color, width=self.w)


def _dashboard(p): p.rect(3, 3, 10, 12); p.rect(14, 3, 21, 8); p.rect(14, 12, 21, 21); p.rect(3, 16, 10, 21)
def _scan(p):
    for a in (((3, 8), (3, 3), (8, 3)), ((16, 3), (21, 3), (21, 8)), ((21, 16), (21, 21), (16, 21)), ((8, 21), (3, 21), (3, 16))):
        p.line(*a)
    p.line(7, 12, 17, 12)
def _notes(p): p.rect(5, 3, 19, 21); p.line(8.5, 9, 15.5, 9); p.line(8.5, 13, 15.5, 13); p.line(8.5, 17, 12, 17)
def _cards(p): p.rect(7, 3.5, 21, 15); p.clear(2, 8, 17, 21); p.rect(3, 8.5, 17, 20.5)
def _review(p): p.line(4, 9, 19, 9); p.line(15, 5, 19, 9, 15, 13); p.line(20, 15, 5, 15); p.line(9, 11, 5, 15, 9, 19)
def _quiz(p):
    p.line(4, 6.5, 6, 8.5, 9.5, 4.5); p.line(13, 6.5, 20, 6.5)
    p.line(4, 12.5, 6, 14.5, 9.5, 10.5); p.line(13, 12.5, 20, 12.5)
    p.circ(6.8, 18.5, 2.4); p.line(13, 18.5, 20, 18.5)
def _settings(p):
    for y, kx in ((6, 9), (12, 16), (18, 7)):
        p.line(4, y, 20, y); p.clear(kx - 3, y - 3, kx + 3, y + 3); p.circ(kx, y, 2.4)
def _search(p): p.circ(10.5, 10.5, 6); p.line(15, 15, 20.5, 20.5)
def _plus(p): p.line(12, 5, 12, 19); p.line(5, 12, 19, 12)
def _trash(p): p.line(4, 7, 20, 7); p.line(9, 7, 9, 4, 15, 4, 15, 7); p.line(6, 7, 7, 20, 17, 20, 18, 7)
def _edit(p): p.line(4, 20, 4.8, 15.5, 16, 4.3, 19.7, 8, 8.5, 19.2, 4, 20); p.line(13.5, 7, 17, 10.5)
def _save(p): p.rect(4, 4, 20, 20); p.rect(8, 4, 16, 9); p.rect(7, 13, 17, 20)
def _export(p): p.line(12, 15, 12, 4); p.line(7.5, 8.5, 12, 4, 16.5, 8.5); p.line(5, 14, 5, 20, 19, 20, 19, 14)
def _import(p): p.line(12, 4, 12, 15); p.line(7.5, 10.5, 12, 15, 16.5, 10.5); p.line(5, 14, 5, 20, 19, 20, 19, 14)
def _check(p): p.line(5, 12.5, 10, 17.5, 19, 7)
def _cross(p): p.line(6, 6, 18, 18); p.line(18, 6, 6, 18)
def _image(p): p.rect(3, 4, 21, 20); p.line(3.5, 17, 9, 11.5, 13, 15.5, 16, 12.5, 20.5, 17); p.circ(16.5, 8.5, 1.6, fill=True)
def _folder(p): p.line(3, 6, 3, 19, 21, 19, 21, 8, 11, 8, 9, 5.5, 3, 5.5, 3, 6)
def _paste(p): p.rect(5, 5, 19, 21); p.rect(9, 3, 15, 7); p.line(8.5, 13, 15.5, 13); p.line(8.5, 17, 13, 17)
def _copy(p): p.rect(8, 8, 20, 20); p.line(16, 8, 16, 4, 4, 4, 4, 16, 8, 16)
def _tag(p): p.line(3, 12, 3, 4, 4, 3, 12, 3, 21, 12, 12, 21, 3, 12); p.circ(7.5, 7.5, 1.3, fill=True)
def _wand(p): p.line(4, 20, 14, 10); p.line(14, 4, 14, 8); p.line(12, 6, 16, 6); p.line(19, 10, 19, 14); p.line(17, 12, 21, 12)
def _flip(p): _review(p)

ICONS = {
    "dashboard": _dashboard, "scan": _scan, "notes": _notes, "cards": _cards, "review": _review,
    "quiz": _quiz, "settings": _settings, "search": _search, "plus": _plus, "trash": _trash,
    "edit": _edit, "save": _save, "export": _export, "import": _import, "check": _check,
    "cross": _cross, "image": _image, "folder": _folder, "paste": _paste, "copy": _copy,
    "tag": _tag, "wand": _wand, "flip": _flip,
}


def draw_icon(name: str, px: int, color: str) -> Image.Image:
    pen = _Pen(px, color)
    ICONS[name](pen)
    return pen.img  # high-res (px * SS); the UI layer scales it down for crisp edges
