import unittest
import tempfile
from pathlib import Path
from portable_deck.core.game import Game

class TableLimitTests(unittest.TestCase):
    def game(self, **kwargs):
        return Game(2, str(Path(__file__).resolve().parents[1] / "decks/demodeck.json"),
                    enable_table_limits=True, max_table_rows=2, max_table_columns=2,
                    allow_move_cards_on_table=True, **kwargs)

    def test_capacity_bounds_and_full_table(self):
        g = self.game()
        g.players[0].hand = [str(i) for i in range(5)]
        self.assertEqual(g.available_table_positions(), {(0,0),(0,1),(1,0),(1,1)})
        for position in ((-1,0),(2,0),(0,2)):
            self.assertIsNone(g.play_to_table(1, position))
        for _ in range(4):
            self.assertIsNotNone(g.play_to_table(1))
        self.assertEqual(g.available_table_positions(), set())
        self.assertIsNone(g.play_to_table(1))
        self.assertEqual(len(g.players[0].hand), 1)
        self.assertIsNone(g.move_table_card(0,(2,0)))

    def test_save_load_restart(self):
        g = self.game()
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as folder:
            path = str(Path(folder) / "save.json")
            g.save_session(path)
            loaded = Game.load_session(path)
            self.assertTrue(loaded.enable_table_limits)
            self.assertEqual(loaded.restart().max_table_columns, 2)

    def test_sequence_must_fit_completely(self):
        g = self.game(allow_move_table_sequences=True)
        g.table_cards = [{"card":"A", "player":"Player1", "position":[0,0], "face_up":True},
                         {"card":"B", "player":"Player1", "position":[1,0], "face_up":True}]
        self.assertIsNone(g.move_table_card(0,(1,1)))
        self.assertEqual(g.table_cards[0]["position"],[0,0])
