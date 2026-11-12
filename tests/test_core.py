"""Tests for the UI-free logic.  Run: python -m pytest   (or: python -m unittest discover tests)"""
import json
import random
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from TuonTa.core.database import Database  # noqa: E402
from TuonTa.core.parser import extract_pairs  # noqa: E402
from TuonTa.core.quiz import build_quiz  # noqa: E402
from TuonTa.core.transfer import TransferError, export_json, import_json  # noqa: E402


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.db = Database()

    def test_notes_crud_and_search(self):
        a = self.db.add_note("Photosynthesis", "Plants make glucose", "Biology, bio ,biology")
        self.db.add_note("Algebra", "Solve for x", "math")
        self.assertEqual(self.db.get_note(a)["tags"], "biology, bio")
        self.assertEqual(len(self.db.list_notes("glucose")), 1)
        self.assertEqual(len(self.db.list_notes(tag="math")), 1)
        self.assertEqual(len(self.db.list_notes("100%")), 0)  # wildcard is escaped
        self.db.update_note(a, "Photosynthesis II", "x", "")
        self.assertEqual(self.db.get_note(a)["title"], "Photosynthesis II")
        self.db.delete_note(a)
        self.assertIsNone(self.db.get_note(a))
        self.assertEqual(self.db.all_tags(), ["math"])

    def test_validation(self):
        with self.assertRaises(ValueError):
            self.db.add_note("   ")
        d = self.db.add_deck("Bio")
        with self.assertRaises(ValueError):
            self.db.add_deck("bio")  # case-insensitive duplicate
        with self.assertRaises(ValueError):
            self.db.add_card(d, "front", "  ")

    def test_cards_and_leitner(self):
        d = self.db.add_deck("Bio")
        c = self.db.add_card(d, "Q", "A")
        self.db.record_review(c, True)
        self.db.record_review(c, True)
        self.assertEqual(self.db.list_cards(d)[0]["box"], 3)
        self.db.record_review(c, False)
        row = self.db.list_cards(d)[0]
        self.assertEqual((row["box"], row["seen"], row["correct"]), (1, 3, 2))
        self.assertEqual(self.db.add_cards(d, [("Q", "dup"), ("New", "Card"), ("", "x")]), 1)

    def test_delete_deck_cascades(self):
        d = self.db.add_deck("Bio")
        self.db.add_card(d, "Q", "A")
        self.db.delete_deck(d)
        self.assertEqual(self.db.list_cards(), [])

    def test_stats_and_streak(self):
        d = self.db.add_deck("Bio")
        c = self.db.add_card(d, "Q", "A")
        self.assertEqual(self.db.stats()["streak"], 0)
        self.db.record_review(c, True)
        self.db.save_quiz(d, "Bio", 10, 8, 60)
        s = self.db.stats()
        self.assertEqual((s["cards"], s["streak"], s["avg_score"]), (1, 1, 80))
        self.assertEqual(sum(v for _, v in s["week"]), 11)


class ParserTests(unittest.TestCase):
    def test_patterns(self):
        text = """
        - Mitosis: cell division producing two identical cells
        2) Osmosis - movement of water across a membrane
        Q: What is DNA?
        A: The molecule carrying genetic information
        What does ATP stand for?
        Adenosine triphosphate
        This is just a normal sentence without a pattern
        """
        fronts = [f for f, _ in extract_pairs(text)]
        self.assertEqual(fronts, ["Mitosis", "Osmosis", "What is DNA?", "What does ATP stand for?"])

    def test_dedupes_and_ignores_long_labels(self):
        pairs = extract_pairs("Term: one\nterm: two\nthis label is far too long to be a term really yes: nope")
        self.assertEqual(len([p for p in pairs if p[0].lower() == "term"]), 1)
        self.assertFalse(any(f.startswith("this label") for f, _ in pairs))


class QuizTests(unittest.TestCase):
    def cards(self, n):
        return [{"id": i, "front": f"Q{i}", "back": f"A{i}"} for i in range(n)]

    def test_options_contain_answer_once(self):
        for q in build_quiz(self.cards(8), 5, rng=random.Random(1)):
            self.assertEqual(len(q.options), 4)
            self.assertEqual(len(set(q.options)), 4)
            self.assertEqual(q.options[q.answer_index], f"A{q.card_id}")

    def test_small_decks_and_errors(self):
        qs = build_quiz(self.cards(3), 10)
        self.assertEqual(len(qs), 3)
        self.assertTrue(all(len(q.options) == 3 for q in qs))
        with self.assertRaises(ValueError):
            build_quiz(self.cards(1))
        same = [{"id": 1, "front": "a", "back": "x"}, {"id": 2, "front": "b", "back": "X"}]
        with self.assertRaises(ValueError):
            build_quiz(same)


class TransferTests(unittest.TestCase):
    def test_round_trip_and_merge(self):
        src = Database()
        d = src.add_deck("Bio")
        c = src.add_card(d, "Q", "A")
        src.record_review(c, True)
        src.add_note("N", "body", "t")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "lib.json"
            self.assertEqual(export_json(src, path), {"notes": 1, "decks": 1, "cards": 1})
            dst = Database()
            self.assertEqual(import_json(dst, path), {"notes": 1, "decks": 1, "cards": 1})
            self.assertEqual(dst.list_cards()[0]["box"], 2)
            self.assertEqual(import_json(dst, path), {"notes": 0, "decks": 0, "cards": 0})  # idempotent

    def test_rejects_bad_files(self):
        db = Database()
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "bad.json"
            for content in ("not json", json.dumps({"app": "Other"}),
                            json.dumps({"app": "TuonTa", "notes": [{"title": ""}], "decks": []})):
                bad.write_text(content)
                with self.assertRaises(TransferError):
                    import_json(db, bad)
            with self.assertRaises(TransferError):
                import_json(db, Path(tmp) / "missing.json")
        self.assertEqual(db.stats()["notes"], 0)


if __name__ == "__main__":
    unittest.main()
