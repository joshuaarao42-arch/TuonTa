"""Rule-based detection of flashcard pairs in plain text (no AI, just patterns)."""
from __future__ import annotations

import re

_BULLET = re.compile(r"^\s*(?:[\u2022\u00b7*\-\u2013]|\d+[.)])\s+")
_SEPARATORS = (" \u2014 ", " \u2013 ", " - ", " = ", " -> ", "::", ": ")
_Q = re.compile(r"^(?:q|question)\s*[:.)]\s*(.+)$", re.I)
_A = re.compile(r"^(?:a|answer)\s*[:.)]\s*(.+)$", re.I)


def extract_pairs(text: str) -> list[tuple[str, str]]:
    """Find (front, back) pairs.

    Recognised shapes, one per line unless noted:
      Term: definition      Term - definition      Term = definition
      Q: question  /  A: answer          (two lines)
      A line ending in "?" followed by its answer   (two lines)
    """
    lines = [_BULLET.sub("", ln).strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln]
    pairs: list[tuple[str, str]] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        nxt = lines[i + 1] if i + 1 < len(lines) else ""
        q, a = _Q.match(line), _A.match(nxt)
        if q and a:
            pairs.append((q.group(1).strip(), a.group(1).strip()))
            i += 2
            continue
        if line.endswith("?") and nxt and not nxt.endswith("?") and len(nxt) < 300 and len(line) > 5:
            pairs.append((line, nxt))
            i += 2
            continue
        for sep in _SEPARATORS:
            if sep in line:
                left, right = (s.strip() for s in line.split(sep, 1))
                if 1 < len(left) <= 100 and len(left.split()) <= 10 and len(right) >= 2:
                    pairs.append((left, right))
                    break
        i += 1
    seen, unique = set(), []
    for f, b in pairs:
        if f.lower() not in seen:
            seen.add(f.lower())
            unique.append((f, b))
    return unique
