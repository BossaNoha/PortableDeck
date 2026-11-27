import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from portable_deck.core.deck import Deck
from portable_deck.core.game import Game
from portable_deck.app.sessionstorage import save_session, load_session
from portable_deck.core.drawpilesetup import normalize_draw_pile_setup
from portable_deck.core.settingsvalidation import validate_settings_and_game


class IndependentDrawPileTests(unittest.TestCase):
    def entry(self, definition=None):
        definition = definition or {"types": ["Other"], "cards": [[1, 2, 2, 3]]}
        return dict(id="own", name="Own", owner=None, count=4,
                    mode="independent", definition=definition)

    def game(self, entry=None, **kwargs):
        return Game(2, Deck.from_definition({"types": ["Main"], "cards": [[1, 2, 3, 4]]}),
                    enable_draw_pile_setup=True, draw_pile_setup=[entry or self.entry()],
                    enable_undo=True, **kwargs)

    def test_independent_set_does_not_consume_main_and_shuffles(self):
        for definition in (None, {"types": ["Main"], "cards": [[1, 2, 3, 4]]}):
            game = self.game(self.entry(definition))
            with patch('portable_deck.core.drawpile.DrawPile.shuffle') as shuffle:
                game.start(2)
            self.assertEqual(shuffle.call_count, 2)
            self.assertEqual(len(game.deck.flat_deck), 0)
            self.assertEqual(len(game.draw_piles.get('own').cards), 4)
            self.assertEqual(sum(len(p.hand) for p in game.players), 4)

    def test_selected_hands_use_independent_capacity(self):
        game = self.game(deal_starting_hands_from_piles=True, initial_hand_sources=['own', 'own'])
        game.start(2)
        self.assertEqual(len(game.deck.flat_deck), 4)
        self.assertFalse(game.draw_piles.get('own').cards)
        bad = self.game(deal_starting_hands_from_piles=True, initial_hand_sources=['own', 'own'])
        with patch.object(bad.deck, 'shuffle') as shuffle:
            with self.assertRaises(ValueError): bad.start(3)
        shuffle.assert_not_called()

    def test_settings_allow_hands_larger_than_main_when_independent(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'small.json'
            path.write_text('{"types":["Small"],"cards":[[1]]}', encoding='utf-8')
            settings, game = validate_settings_and_game(dict(num_players=2, cards_per_player=2,
                deck_path=str(path), enable_draw_pile_setup=True, draw_pile_setup=[self.entry()],
                deal_starting_hands_from_piles=True, initial_hand_sources=['own', 'own']))
            game.start(settings['cards_per_player'])
            self.assertEqual(len(game.deck.flat_deck), 1)

    def test_embedded_definition_is_copied_and_survives_save_undo_restart(self):
        entry = self.entry()
        game = self.game(entry)
        entry['definition']['cards'][0].clear()
        game.start(1)
        game.session.execute('draw_card', draw_pile_id='own')
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'save.json'
            save_session(game, path)
            loaded = load_session(Game, path)
        self.assertEqual(loaded.capture_undo_state(), game.capture_undo_state())
        self.assertTrue(loaded.session.undo())
        self.assertEqual(len(loaded.draw_piles.get('own').cards), 4)
        restarted = loaded.restart()
        self.assertEqual(len(restarted.draw_piles.get('own').cards), 4)
        self.assertEqual(len(restarted.deck.flat_deck), 2)
        self.assertEqual(restarted.draw_pile_setup, game.draw_pile_setup)

    def test_invalid_or_ambiguous_definitions_rejected(self):
        for change in ({'mode': 'copy'}, {'count': 3}, {'definition': {}}, {'definition': None}):
            with self.assertRaises(ValueError): normalize_draw_pile_setup([self.entry() | change], 2)
        entry = self.entry()
        del entry['mode']
        with self.assertRaises(ValueError): normalize_draw_pile_setup([entry], 2)

    def test_mixed_split_and_independent_sets_have_separate_budgets(self):
        game = self.game()
        game.draw_pile_setup.append(dict(id="split", name="Split", owner=0, count=2))
        game.start(1)
        self.assertFalse(game.deck.flat_deck)
        self.assertEqual(len(game.draw_piles.get("split").cards), 2)
        self.assertEqual(len(game.draw_piles.get("own").cards), 4)
        self.assertEqual(sum(len(p.hand) for p in game.players), 2)
