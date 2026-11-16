import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from portable_deck.core.game import Game
from portable_deck.ui.tableframe import TableFrame


class TableMigrationTests(unittest.TestCase):
    def game(self):
        return Game(2, str(Path(__file__).resolve().parents[1] / "decks/demodeck.json"), enable_undo=True)

    def test_load_upgrades_legacy_positions_without_gui(self):
        for spatial in (False, True):
            with self.subTest(spatial=spatial), tempfile.TemporaryDirectory() as folder:
                game = self.game()
                game.allow_positioned_play = spatial
                game.table_cards = [{"card": "A", "player": "Player1"},
                                    {"card": "B", "player": "Player2"}]
                path = str(Path(folder) / "legacy.json")
                game.save_session(path)
                loaded = Game.load_session(path)
                self.assertEqual([entry["position"] for entry in loaded.table_cards], [[0, 0], [0, 1]])
                self.assertNotIn((0, 0), loaded.available_table_positions())
                self.assertNotIn((0, 1), loaded.available_table_positions())

    def test_undo_upgrades_old_snapshot_and_preserves_valid_positions(self):
        game = self.game()
        game.table_cards = [{"card": "A", "player": "Player1"}]
        game.undo_stack.append(game.capture_undo_state())
        game.table_cards.clear()
        self.assertTrue(game.session.undo())
        self.assertEqual(game.table_cards[0]["position"], [0, 0])
        game.table_cards[0]["position"] = (-2, 3)
        before = copy.deepcopy(game.table_cards)
        game.normalize_table_positions()
        self.assertEqual(game.table_cards, before)

    def test_table_render_does_not_repair_or_mutate_game_state(self):
        game = self.game()
        game.table_cards = [{"card": "A", "player": "Player1"}]
        before = game.capture_undo_state()
        frame = Mock(game=game)
        frame.contents.winfo_children.return_value = []
        TableFrame.update_table(frame)
        self.assertEqual(game.capture_undo_state(), before)
        frame._draw_spatial_table.assert_called_once_with()
