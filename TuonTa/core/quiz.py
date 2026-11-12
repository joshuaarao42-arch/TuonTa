"""Multiple-choice quiz generation from saved flashcards."""
from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass
class Question:
    card_id: int
    prompt: str
    options: list[str]
    answer_index: int


def build_quiz(cards, count: int = 10, choices: int = 4, rng: random.Random | None = None) -> list[Question]:
    """Pick `count` cards; wrong options are other cards' answers."""
    rng = rng or random.Random()
    usable = [c for c in cards if str(c["front"]).strip() and str(c["back"]).strip()]
    backs = list({str(c["back"]).strip().lower(): str(c["back"]).strip() for c in usable}.values())
    if len(usable) < 2 or len(backs) < 2:
        raise ValueError("A quiz needs at least two cards with different answers.")
    chosen = rng.sample(usable, min(count, len(usable)))
    questions = []
    for card in chosen:
        right = str(card["back"]).strip()
        pool = [b for b in backs if b.lower() != right.lower()]
        options = rng.sample(pool, min(choices - 1, len(pool))) + [right]
        rng.shuffle(options)
        questions.append(Question(card["id"], str(card["front"]).strip(), options, options.index(right)))
    return questions
