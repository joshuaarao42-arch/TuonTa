"""JSON export / import of the whole study library."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .. import APP_NAME, __version__
from .database import Database

FORMAT = 1


class TransferError(Exception):
    """Raised for unreadable or invalid import files."""


def export_json(db: Database, path: Path | str) -> dict:
    notes = [
        {k: r[k] for k in ("title", "body", "tags", "created_at", "updated_at")}
        for r in db.conn.execute("SELECT * FROM notes ORDER BY id")
    ]
    decks = []
    for d in db.list_decks():
        cards = [
            {k: c[k] for k in ("front", "back", "box", "seen", "correct")}
            for c in db.conn.execute("SELECT * FROM cards WHERE deck_id=? ORDER BY id", (d["id"],))
        ]
        decks.append({"name": d["name"], "cards": cards})
    quizzes = [
        {k: r[k] for k in ("deck_name", "total", "correct", "seconds", "taken_at")}
        for r in db.conn.execute("SELECT * FROM quiz_results ORDER BY id")
    ]
    payload = {
        "app": APP_NAME, "version": __version__, "format": FORMAT,
        "exported_at": datetime.now().isoformat(timespec="seconds"),
        "notes": notes, "decks": decks, "quiz_results": quizzes,
    }
    try:
        Path(path).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    except OSError as exc:
        raise TransferError(f"Could not write the file: {exc.strerror or exc}") from exc
    return {"notes": len(notes), "decks": len(decks), "cards": sum(len(d["cards"]) for d in decks)}


def _text(value, field: str, required: bool = True) -> str:
    if not isinstance(value, str):
        raise TransferError(f'Invalid data: "{field}" must be text.')
    if required and not value.strip():
        raise TransferError(f'Invalid data: "{field}" is empty.')
    return value


def _int(value, default: int, lo: int = 0, hi: int = 10**9) -> int:
    return max(lo, min(hi, value)) if isinstance(value, int) and not isinstance(value, bool) else default


def import_json(db: Database, path: Path | str) -> dict:
    """Merge a TuonTa export into the library. Existing items are kept, duplicates skipped."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except OSError as exc:
        raise TransferError(f"Could not read the file: {exc.strerror or exc}") from exc
    except ValueError as exc:
        raise TransferError("That file is not valid JSON.") from exc
    if not isinstance(data, dict) or data.get("app") != APP_NAME:
        raise TransferError("That file is not a TuonTa export.")
    notes, decks = data.get("notes", []), data.get("decks", [])
    if not isinstance(notes, list) or not isinstance(decks, list):
        raise TransferError("The export is missing its notes or decks list.")

    # validate everything first so a bad file never half-imports
    clean_notes = []
    for n in notes:
        if not isinstance(n, dict):
            raise TransferError("A note entry is malformed.")
        clean_notes.append((_text(n.get("title"), "note title"), _text(n.get("body", ""), "note body", False),
                            _text(n.get("tags", ""), "note tags", False)))
    clean_decks = []
    for d in decks:
        if not isinstance(d, dict) or not isinstance(d.get("cards", []), list):
            raise TransferError("A deck entry is malformed.")
        cards = []
        for c in d.get("cards", []):
            if not isinstance(c, dict):
                raise TransferError("A card entry is malformed.")
            cards.append((_text(c.get("front"), "card front"), _text(c.get("back"), "card back"),
                          _int(c.get("box"), 1, 1, 5), _int(c.get("seen"), 0), _int(c.get("correct"), 0)))
        clean_decks.append((_text(d.get("name"), "deck name"), cards))

    added = {"notes": 0, "decks": 0, "cards": 0}
    have = {(r["title"], r["body"]) for r in db.conn.execute("SELECT title, body FROM notes")}
    for title, body, tags in clean_notes:
        if (title, body) not in have:
            db.add_note(title, body, tags)
            have.add((title, body))
            added["notes"] += 1
    existing = {r["name"].lower() for r in db.list_decks()}
    for name, cards in clean_decks:
        if name.strip().lower() not in existing:
            added["decks"] += 1
            existing.add(name.strip().lower())
        deck_id = db.get_or_create_deck(name)
        known = {r["front"].lower() for r in db.conn.execute("SELECT front FROM cards WHERE deck_id=?", (deck_id,))}
        for front, back, box, seen, correct in cards:
            if front.strip().lower() in known:
                continue
            card_id = db.add_card(deck_id, front, back)
            db.conn.execute("UPDATE cards SET box=?, seen=?, correct=? WHERE id=?", (box, seen, correct, card_id))
            known.add(front.strip().lower())
            added["cards"] += 1
    db.conn.commit()
    return added
