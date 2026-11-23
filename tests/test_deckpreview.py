import json
import unittest
from dataclasses import FrozenInstanceError, asdict
from pathlib import Path
from types import SimpleNamespace

from portable_deck.core.deck import Deck
from portable_deck.core.deckpreview import build_deck_preview


class DeckPreviewTests(unittest.TestCase):
    def deck(self):
        return Deck(str(Path(__file__).resolve().parents[1] / "decks/demodeck.json"))

    def test_preview_preserves_symbols_duplicates_and_existing_value_sort(self):
        deck = Deck.from_definition({"types": ["Second", "First", "Empty"],
            "cards": [["zebra", "A", "Q", "J", "K", "10", 2, "2", "ace", "Apple"], [3.5, 1], []]})
        before = (deck.definition, deck.flat_deck.copy(), deck.path)
        view = build_deck_preview(deck)
        self.assertEqual([s.name for s in view.symbols], ["Second", "First", "Empty"])
        self.assertEqual(view.symbols[0].values,
                         ("2", "2", "10", "J", "Q", "K", "A", "ace", "Apple", "zebra"))
        self.assertEqual(view.symbols[1].values, ("1", "3.5"))
        self.assertEqual(view.symbols[2].values, ())
        self.assertEqual(view.card_count, 12)
        self.assertEqual((deck.definition, deck.flat_deck, deck.path), before)

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
        deck = SimpleNamespace(types=["Test"], cards=[])
        with self.assertRaises(ValueError):
            build_deck_preview(deck)
