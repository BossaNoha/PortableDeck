import copy
import json
import subprocess
import sys
import unittest
from dataclasses import FrozenInstanceError, asdict
from pathlib import Path

from portable_deck.core.deck import Deck
from portable_deck.core.deckpreview import build_deck_preview


class DeckPreviewTests(unittest.TestCase):
    def deck(self):
        return Deck(str(Path(__file__).resolve().parents[1] / "decks/demodeck.json"))

    def test_preview_preserves_symbols_duplicates_and_existing_value_sort(self):
        deck = self.deck()
        deck.types = ["Second", "First", "Empty"]
        deck.cards = [["zebra", "A", "Q", "J", "K", "10", 2, "2", "ace", "Apple"], [3.5, 1], []]
        before = copy.deepcopy(deck.__dict__)
        view = build_deck_preview(deck)
        self.assertEqual([s.name for s in view.symbols], ["Second", "First", "Empty"])
        self.assertEqual(view.symbols[0].values,
                         ("2", "2", "10", "J", "Q", "K", "A", "ace", "Apple", "zebra"))
        self.assertEqual(view.symbols[1].values, ("1", "3.5"))
        self.assertEqual(view.symbols[2].values, ())
        self.assertEqual(view.card_count, 12)
        self.assertEqual(deck.__dict__, before)

    def test_preview_is_independent_of_remaining_deck_and_mutations(self):
        deck = self.deck()
        view = build_deck_preview(deck)
        deck.shuffle()
        deck.draw_card()
        self.assertEqual(build_deck_preview(deck), view)
        deck.flat_deck = ["SECRET DRAW ORDER"]
        self.assertEqual(build_deck_preview(deck), view)
        self.assertNotIn("SECRET DRAW ORDER", json.dumps(asdict(view)))
        data = asdict(view)
        deck.types[0] = "changed"
        deck.cards[0].clear()
        self.assertEqual(asdict(view), data)
        with self.assertRaises(FrozenInstanceError):
            view.symbols[0].name = "changed"

    def test_invalid_definitions_are_rejected(self):
        deck = self.deck()
        deck.cards = []
        with self.assertRaises(ValueError):
            build_deck_preview(deck)

    def test_preview_is_available_without_tkinter(self):
        script = ("from portable_deck.core.deck import Deck; "
                  "from portable_deck.core.deckpreview import build_deck_preview; import sys; "
                  "assert build_deck_preview(Deck('decks/demodeck.json')).card_count>0; "
                  "assert 'tkinter' not in sys.modules")
        result = subprocess.run([sys.executable, "-B", "-c", script],
                                cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
