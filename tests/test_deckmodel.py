import json
import tempfile
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest.mock import patch

from portable_deck.app.sessionstorage import load_session, save_session
from portable_deck.core.deck import Deck
from portable_deck.core.deckdefinition import DeckDefinition
from portable_deck.core.drawpile import DrawPile
from portable_deck.core.game import Game


class DeckModelTests(unittest.TestCase):
    def data(self):
        return {"types": ["First", "Empty", "Second"], "cards": [[1, "1", "A"], [], [2.5, "A"]]}

    def test_definition_is_immutable_and_json_values_are_independent(self):
        data = self.data()
        definition = DeckDefinition.from_data(data)
        original = definition.to_data()
        data["types"][0] = "changed"
        data["cards"][0].clear()
        exported = definition.to_data()
        exported["cards"][0].append("external")
        self.assertEqual(definition.to_data(), original)
        self.assertEqual(json.loads(json.dumps(definition.to_data())), original)
        self.assertEqual(definition.expanded_cards(), ("1 of First", "1 of First", "A of First", "2.5 of Second", "A of Second"))
        with self.assertRaises(FrozenInstanceError): definition.types = ("changed",)
        with self.assertRaises(TypeError): definition.cards[0][0] = "changed"

    def test_shared_definition_supports_independent_draw_orders(self):
        definition = DeckDefinition.from_data(self.data())
        first = Deck.from_definition(definition)
        second = Deck.from_definition(definition)
        self.assertIs(first.definition, second.definition)
        with patch("portable_deck.core.drawpile.random.shuffle", side_effect=lambda cards: cards.reverse()):
            first.shuffle()
        first.draw_card()
        first.flat_deck.insert(0, "INSERTED")
        self.assertEqual(second.flat_deck, list(definition.expanded_cards()))
        self.assertEqual(definition.to_data(), self.data())
        self.assertIsNot(first.draw_pile, second.draw_pile)
        self.assertIsNot(first.flat_deck, second.flat_deck)

    def test_draw_pile_works_without_definition_and_keeps_duplicate_cards(self):
        cards = ["A", "A", "B"]
        pile = DrawPile(cards)
        cards.clear()
        self.assertEqual([pile.draw_card() for _ in range(4)], ["A", "A", "B", None])
        pile.cards.extend(["C", "D"])
        with patch("portable_deck.core.drawpile.random.shuffle", side_effect=lambda items: items.reverse()):
            pile.shuffle()
        self.assertEqual(pile.draw_card(), "D")

    def test_legacy_deck_access_uses_one_authoritative_pile(self):
        deck = Deck.from_definition(self.data())
        external = ["A", "B", "C"]
        deck.flat_deck = external
        external.clear()
        self.assertIs(deck.flat_deck, deck.draw_pile.cards)
        self.assertEqual(deck.draw_card(), "A")
        deck.flat_deck.append("D")
        self.assertEqual(deck.draw_pile.draw_card(), "B")
        self.assertEqual(deck.flat_deck, ["C", "D"])
        deck.flatten()
        self.assertEqual(deck.flat_deck, list(deck.definition.expanded_cards()))
        names, groups = deck.types, deck.cards
        names[0] = "changed"
        groups[0].clear()
        self.assertEqual(deck.definition.to_data(), self.data())

    def test_game_restart_and_disk_save_keep_existing_format_and_undo(self):
        definition = DeckDefinition.from_data(self.data())
        source = Deck.from_definition(definition, path="missing-source.json")
        game = Game(2, source, enable_undo=True)
        game.start(1)
        before = game.capture_undo_state()
        self.assertTrue(game.session.execute("draw_card").success)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "game.json"
            save_session(game, path)
            state = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(state["deck_types"], self.data()["types"])
            self.assertEqual(state["deck_cards"], self.data()["cards"])
            self.assertEqual(state["remaining_deck"], game.deck.draw_pile.cards)
            self.assertNotIn("definition", state)
            self.assertNotIn("draw_pile", state)
            loaded = load_session(Game, path)
        self.assertEqual(loaded.capture_undo_state(), game.capture_undo_state())
        self.assertTrue(loaded.session.undo())
        self.assertEqual(loaded.capture_undo_state(), before)
        restarted = game.restart()
        self.assertEqual(restarted.deck.definition, game.deck.definition)
        self.assertIsNot(restarted.deck.draw_pile, game.deck.draw_pile)
        self.assertEqual(len(restarted.deck.flat_deck), 3)
        self.assertEqual(source.flat_deck, list(definition.expanded_cards()))

    def test_invalid_definitions_retain_validation_and_do_not_reset_a_pile(self):
        deck = Deck.from_definition(self.data())
        deck.draw_card()
        before = deck.flat_deck.copy()
        for data in ({}, {"types": ["X"], "cards": [[True]]}, {"types": ["X"], "cards": [[]]}):
            with self.assertRaises(ValueError): DeckDefinition.from_data(data)
            with self.assertRaises(ValueError): Deck.from_definition(data)
        self.assertEqual(deck.flat_deck, before)
