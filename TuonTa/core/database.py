"""SQLite persistence layer."""
from __future__ import annotations

import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

from ..config import MASTERED_BOX, MAX_BOX

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS notes(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    body TEXT NOT NULL DEFAULT '',
    tags TEXT NOT NULL DEFAULT '',
    source_image TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS decks(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE COLLATE NOCASE,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS cards(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    deck_id INTEGER NOT NULL REFERENCES decks(id) ON DELETE CASCADE,
    note_id INTEGER REFERENCES notes(id) ON DELETE SET NULL,
    front TEXT NOT NULL,
    back TEXT NOT NULL,
    box INTEGER NOT NULL DEFAULT 1,
    seen INTEGER NOT NULL DEFAULT 0,
    correct INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    last_reviewed TEXT
);
CREATE TABLE IF NOT EXISTS reviews(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    card_id INTEGER REFERENCES cards(id) ON DELETE SET NULL,
    known INTEGER NOT NULL,
    reviewed_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS quiz_results(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    deck_id INTEGER REFERENCES decks(id) ON DELETE SET NULL,
    deck_name TEXT NOT NULL,
    total INTEGER NOT NULL,
    correct INTEGER NOT NULL,
    seconds INTEGER NOT NULL DEFAULT 0,
    taken_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cards_deck ON cards(deck_id);
CREATE INDEX IF NOT EXISTS idx_reviews_at ON reviews(reviewed_at);
"""


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _like(term: str) -> str:
    esc = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{esc}%"


def normalize_tags(tags: str) -> str:
    seen, out = set(), []
    for t in tags.replace(";", ",").split(","):
        t = t.strip().lower()
        if t and t not in seen:
            seen.add(t)
            out.append(t)
    return ", ".join(out)


class Database:
    def __init__(self, path: Path | str = ":memory:"):
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    # ------------------------------------------------------------- notes
    def add_note(self, title: str, body: str = "", tags: str = "", source_image: str | None = None) -> int:
        title = title.strip()
        if not title:
            raise ValueError("A note needs a title.")
        now = _now()
        cur = self.conn.execute(
            "INSERT INTO notes(title, body, tags, source_image, created_at, updated_at) VALUES (?,?,?,?,?,?)",
            (title[:200], body, normalize_tags(tags), source_image, now, now),
        )
        self.conn.commit()
        return cur.lastrowid

    def update_note(self, note_id: int, title: str, body: str, tags: str) -> None:
        title = title.strip()
        if not title:
            raise ValueError("A note needs a title.")
        self.conn.execute(
            "UPDATE notes SET title=?, body=?, tags=?, updated_at=? WHERE id=?",
            (title[:200], body, normalize_tags(tags), _now(), note_id),
        )
        self.conn.commit()

    def delete_note(self, note_id: int) -> None:
        self.conn.execute("DELETE FROM notes WHERE id=?", (note_id,))
        self.conn.commit()

    def get_note(self, note_id: int):
        return self.conn.execute("SELECT * FROM notes WHERE id=?", (note_id,)).fetchone()

    def list_notes(self, search: str = "", tag: str = ""):
        sql, args = "SELECT * FROM notes WHERE 1=1", []
        if search.strip():
            sql += " AND (title LIKE ? ESCAPE '\\' OR body LIKE ? ESCAPE '\\' OR tags LIKE ? ESCAPE '\\')"
            args += [_like(search.strip())] * 3
        if tag:
            sql += " AND (', ' || tags || ',') LIKE ? ESCAPE '\\'"
            args.append(f"%, {tag.replace('%', '').replace('_', '')},%")
        sql += " ORDER BY updated_at DESC, id DESC"
        return self.conn.execute(sql, args).fetchall()

    def all_tags(self) -> list[str]:
        tags = set()
        for row in self.conn.execute("SELECT tags FROM notes WHERE tags != ''"):
            tags.update(t.strip() for t in row["tags"].split(",") if t.strip())
        return sorted(tags)

    # ------------------------------------------------------------- decks
    def add_deck(self, name: str) -> int:
        name = name.strip()
        if not name:
            raise ValueError("A deck needs a name.")
        try:
            cur = self.conn.execute("INSERT INTO decks(name, created_at) VALUES (?,?)", (name[:80], _now()))
        except sqlite3.IntegrityError:
            raise ValueError(f'A deck named "{name}" already exists.') from None
        self.conn.commit()
        return cur.lastrowid

    def get_or_create_deck(self, name: str) -> int:
        row = self.conn.execute("SELECT id FROM decks WHERE name=?", (name.strip(),)).fetchone()
        return row["id"] if row else self.add_deck(name)

    def rename_deck(self, deck_id: int, name: str) -> None:
        name = name.strip()
        if not name:
            raise ValueError("A deck needs a name.")
        try:
            self.conn.execute("UPDATE decks SET name=? WHERE id=?", (name[:80], deck_id))
        except sqlite3.IntegrityError:
            raise ValueError(f'A deck named "{name}" already exists.') from None
        self.conn.commit()

    def delete_deck(self, deck_id: int) -> None:
        self.conn.execute("DELETE FROM decks WHERE id=?", (deck_id,))
        self.conn.commit()

    def get_deck(self, deck_id: int):
        return self.conn.execute("SELECT * FROM decks WHERE id=?", (deck_id,)).fetchone()

    def list_decks(self):
        return self.conn.execute(
            "SELECT d.id, d.name, COUNT(c.id) AS card_count FROM decks d "
            "LEFT JOIN cards c ON c.deck_id = d.id GROUP BY d.id ORDER BY d.name COLLATE NOCASE"
        ).fetchall()

    # ------------------------------------------------------------- cards
    def add_card(self, deck_id: int, front: str, back: str, note_id: int | None = None) -> int:
        front, back = front.strip(), back.strip()
        if not front or not back:
            raise ValueError("Both sides of a card need text.")
        cur = self.conn.execute(
            "INSERT INTO cards(deck_id, note_id, front, back, created_at) VALUES (?,?,?,?,?)",
            (deck_id, note_id, front, back, _now()),
        )
        self.conn.commit()
        return cur.lastrowid

    def add_cards(self, deck_id: int, pairs, note_id: int | None = None) -> int:
        """Insert many (front, back) pairs, skipping blanks and duplicates. Returns number added."""
        existing = {r["front"].lower() for r in self.conn.execute("SELECT front FROM cards WHERE deck_id=?", (deck_id,))}
        added = 0
        for front, back in pairs:
            front, back = front.strip(), back.strip()
            if not front or not back or front.lower() in existing:
                continue
            self.conn.execute(
                "INSERT INTO cards(deck_id, note_id, front, back, created_at) VALUES (?,?,?,?,?)",
                (deck_id, note_id, front, back, _now()),
            )
            existing.add(front.lower())
            added += 1
        self.conn.commit()
        return added

    def update_card(self, card_id: int, deck_id: int, front: str, back: str) -> None:
        front, back = front.strip(), back.strip()
        if not front or not back:
            raise ValueError("Both sides of a card need text.")
        self.conn.execute("UPDATE cards SET deck_id=?, front=?, back=? WHERE id=?", (deck_id, front, back, card_id))
        self.conn.commit()

    def delete_card(self, card_id: int) -> None:
        self.conn.execute("DELETE FROM cards WHERE id=?", (card_id,))
        self.conn.commit()

    def list_cards(self, deck_id: int | None = None, search: str = ""):
        sql = "SELECT c.*, d.name AS deck_name FROM cards c JOIN decks d ON d.id = c.deck_id WHERE 1=1"
        args: list = []
        if deck_id is not None:
            sql += " AND c.deck_id=?"
            args.append(deck_id)
        if search.strip():
            sql += " AND (c.front LIKE ? ESCAPE '\\' OR c.back LIKE ? ESCAPE '\\')"
            args += [_like(search.strip())] * 2
        sql += " ORDER BY c.id DESC"
        return self.conn.execute(sql, args).fetchall()

    def review_queue(self, deck_id: int | None = None, limit: int = 30):
        """Weakest cards first (lowest Leitner box), random order inside a box."""
        sql, args = "SELECT * FROM cards", []
        if deck_id is not None:
            sql += " WHERE deck_id=?"
            args.append(deck_id)
        sql += " ORDER BY box ASC, RANDOM() LIMIT ?"
        args.append(limit)
        return self.conn.execute(sql, args).fetchall()

    def record_review(self, card_id: int, known: bool) -> None:
        now = _now()
        box_sql = f"MIN(box + 1, {MAX_BOX})" if known else "1"
        self.conn.execute(
            f"UPDATE cards SET box={box_sql}, seen=seen+1, correct=correct+?, last_reviewed=? WHERE id=?",
            (1 if known else 0, now, card_id),
        )
        self.conn.execute("INSERT INTO reviews(card_id, known, reviewed_at) VALUES (?,?,?)", (card_id, int(known), now))
        self.conn.commit()

    # -------------------------------------------------------------- quiz
    def save_quiz(self, deck_id: int | None, deck_name: str, total: int, correct: int, seconds: int) -> None:
        self.conn.execute(
            "INSERT INTO quiz_results(deck_id, deck_name, total, correct, seconds, taken_at) VALUES (?,?,?,?,?,?)",
            (deck_id, deck_name, total, correct, seconds, _now()),
        )
        self.conn.commit()

    def recent_quizzes(self, limit: int = 6):
        return self.conn.execute("SELECT * FROM quiz_results ORDER BY id DESC LIMIT ?", (limit,)).fetchall()

    # ------------------------------------------------------------- stats
    def _activity_by_day(self) -> dict[str, int]:
        days: dict[str, int] = {}
        for r in self.conn.execute("SELECT substr(reviewed_at,1,10) d, COUNT(*) n FROM reviews GROUP BY d"):
            days[r["d"]] = days.get(r["d"], 0) + r["n"]
        for r in self.conn.execute("SELECT substr(taken_at,1,10) d, SUM(total) n FROM quiz_results GROUP BY d"):
            days[r["d"]] = days.get(r["d"], 0) + (r["n"] or 0)
        return days

    def stats(self) -> dict:
        one = lambda sql: self.conn.execute(sql).fetchone()[0] or 0  # noqa: E731
        activity = self._activity_by_day()
        today = date.today()
        streak, cursor = 0, today
        if activity.get(today.isoformat(), 0) == 0:
            cursor = today - timedelta(days=1)  # today not studied yet: don't break the streak
        while activity.get(cursor.isoformat(), 0) > 0:
            streak += 1
            cursor -= timedelta(days=1)
        week = []
        for i in range(6, -1, -1):
            d = today - timedelta(days=i)
            week.append((d.strftime("%a"), activity.get(d.isoformat(), 0)))
        total_q, total_c = self.conn.execute("SELECT SUM(total), SUM(correct) FROM quiz_results").fetchone()
        return {
            "notes": one("SELECT COUNT(*) FROM notes"),
            "decks": one("SELECT COUNT(*) FROM decks"),
            "cards": one("SELECT COUNT(*) FROM cards"),
            "mastered": one(f"SELECT COUNT(*) FROM cards WHERE box >= {MASTERED_BOX}"),
            "quizzes": one("SELECT COUNT(*) FROM quiz_results"),
            "avg_score": round(100 * (total_c or 0) / total_q) if total_q else None,
            "streak": streak,
            "week": week,
        }

    def wipe(self) -> None:
        for table in ("reviews", "quiz_results", "cards", "decks", "notes"):
            self.conn.execute(f"DELETE FROM {table}")
        self.conn.commit()
