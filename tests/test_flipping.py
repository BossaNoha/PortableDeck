import unittest
import tempfile
from pathlib import Path
from portable_deck.core.game import Game

class FlippingTests(unittest.TestCase):
    def game(self, **kwargs):
        return Game(2, str(Path(__file__).resolve().parents[1] / "decks/demodeck.json"),
                    enable_flipping=True, allow_flip_hand=True, enable_undo=True, **kwargs)

    def test_revealed_hand_visibility_shifts_and_hides(self):
        g = self.game()
        p = g.players[0]
        p.hand = ["A", "B", "B"]
        g.flip_hand_card(1)
        self.assertEqual(g.visible_hand(1,0), ["Hidden card", "B", "Hidden card"])
        p.play_card(1)
        self.assertEqual(p.revealed_indices, {0})
        self.assertEqual(g.visible_hand(1,0), ["B", "Hidden card"])
        g.flip_hand_card(0)
        self.assertIsNone(g.visible_hand(1,0))

    def test_undo_and_session_persistence(self):
        g = self.game()
        g.players[0].hand = ["A"]
        before = g.capture_undo_state()
        g.undo_stack.append(before)
        g.flip_hand_card(0)
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as folder:
            path = str(Path(folder) / "save.json")
            g.save_session(path)
            loaded = Game.load_session(path)
            self.assertEqual(loaded.visible_hand(1,0), ["A"])
            self.assertTrue(loaded.undo_last_action())
            self.assertEqual(loaded.capture_undo_state(), before)
            self.assertTrue(loaded.restart().allow_flip_hand)

    def test_table_and_player_lane_permissions(self):
        g = self.game(allow_flip_table=True)
        g.players[0].hand = ["A"]
        g.play_to_table(1)
        self.assertEqual(g.flip_table_card(0), "A")
        self.assertFalse(g.table_cards[0]["face_up"])
        g.flip_table_card(0)
        self.assertTrue(g.table_cards[0]["face_up"])
        g.allow_play_in_front_of_players = True
        self.assertIsNone(g.flip_table_card(0))
        g.allow_flip_player_cards = True
        self.assertEqual(g.flip_table_card(0), "A")
        g.enable_table = False
        self.assertIsNone(g.flip_table_card(0))
