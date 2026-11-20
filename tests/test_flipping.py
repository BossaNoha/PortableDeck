import unittest
import tempfile
from pathlib import Path
from unittest.mock import Mock
from portable_deck.core.game import Game
from portable_deck.app.sessionstorage import save_session, load_session

class FlippingTests(unittest.TestCase):
    def test_invalid_hand_indices_preserve_reveals_undo_and_checkpoint(self):
        g = self.game()
        g.players[0].hand = ["A", "B"]
        g.players[0].revealed_indices = {0}
        g.session.checkpoint_callback = saved = Mock(return_value=None)
        before = g.capture_undo_state()
        for index in (True, False, 0.0, 1.0, -1, 2, "0", None, [], {}):
            with self.subTest(index=index):
                self.assertIsNone(g.flip_hand_card(index))
                result = g.session.execute("flip_hand_card", card_index=index)
                self.assertFalse(result.success)
                self.assertEqual(result.code, "selection_required" if index is None else "invalid_selection")
                self.assertEqual(g.capture_undo_state(), before)
                self.assertEqual(g.undo_stack, [])
                saved.assert_not_called()

    def test_hand_reveal_and_hide_commands_remain_undoable(self):
        g = self.game()
        g.players[0].hand = ["A"]
        g.session.checkpoint_callback = saved = Mock(return_value=None)
        before = g.capture_undo_state()
        self.assertTrue(g.session.execute("flip_hand_card", card_index=0).success)
        self.assertEqual(g.players[0].revealed_indices, {0})
        self.assertTrue(g.session.execute("flip_hand_card", card_index=0).success)
        self.assertEqual(g.players[0].revealed_indices, set())
        self.assertEqual(saved.call_count, 2)
        self.assertTrue(g.session.undo())
        self.assertEqual(g.players[0].revealed_indices, {0})
        self.assertTrue(g.session.undo())
        self.assertEqual(g.capture_undo_state(), before)

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
            save_session(g, path)
            loaded = load_session(Game, path)
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
