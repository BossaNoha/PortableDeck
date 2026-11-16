import json
import unittest
from dataclasses import FrozenInstanceError, asdict
from pathlib import Path
from unittest.mock import Mock

from portable_deck.core.game import Game
from portable_deck.core.playerleaving import build_player_return_options


class PlayerReturnOptionsTests(unittest.TestCase):
    def game(self):
        g = Game(3, str(Path(__file__).resolve().parents[1] / "decks/demodeck.json"),
                 enable_player_return=True, enable_undo=True)
        g.left_players = [2, 1]
        g.players[1].hand = ["SECRET"]
        return g

    def test_read_only_snapshot_preserves_ids_and_contains_no_cards(self):
        g = self.game()
        before = g.capture_undo_state()
        view = build_player_return_options(g)
        self.assertTrue(view.allowed)
        self.assertEqual([(p.index, p.name) for p in view.players], [(2, "Player3"), (1, "Player2")])
        self.assertTrue(all(p.allowed for p in view.players))
        self.assertNotIn("SECRET", json.dumps(asdict(view)))
        self.assertEqual(g.capture_undo_state(), before)
        g.players[1].name = "Changed"
        g.left_players.clear()
        self.assertEqual(view.players[1].name, "Player2")
        with self.assertRaises(FrozenInstanceError):
            view.players[0].name = "Changed"

    def test_disabled_empty_and_pending_options_have_reasons(self):
        for case in ("disabled", "empty", "score", "pot"):
            with self.subTest(case=case):
                g = self.game()
                if case == "disabled":
                    g.enable_player_return = False
                elif case == "empty":
                    g.left_players.clear()
                elif case == "score":
                    g.pending_point_request = {"requester": 0, "confirmed_by": []}
                else:
                    g.pending_pot_withdrawal = {"requester": 0, "recipient": 1, "confirmed_by": []}
                view = build_player_return_options(g)
                self.assertFalse(view.allowed)
                self.assertTrue(view.reason)
                self.assertTrue(all(not p.allowed for p in view.players))

    def test_stale_options_are_revalidated_without_undo_or_checkpoint(self):
        for case in ("returned", "disabled", "pending"):
            with self.subTest(case=case):
                g = self.game()
                target = build_player_return_options(g).players[0]
                self.assertTrue(target.allowed)
                if case == "returned":
                    g.left_players.remove(target.index)
                elif case == "disabled":
                    g.enable_player_return = False
                else:
                    g.pending_point_request = {"requester": 0, "confirmed_by": []}
                saved = Mock(return_value=None)
                g.session.checkpoint_callback = saved
                before = g.capture_undo_state()
                result = g.session.execute("return_player", player_index=target.index)
                self.assertFalse(result.success)
                self.assertTrue(result.message)
                self.assertEqual(g.capture_undo_state(), before)
                self.assertEqual(g.undo_stack, [])
                saved.assert_not_called()

    def test_return_from_all_departed_session_is_undoable_and_saves_once(self):
        g = self.game()
        g.left_players = [0, 1, 2]
        target = build_player_return_options(g).players[1]
        before = g.capture_undo_state()
        saved = Mock(return_value=None)
        g.session.checkpoint_callback = saved
        result = g.session.execute("return_player", player_index=target.index)
        self.assertTrue(result.success)
        self.assertEqual(g.current_player_index, target.index)
        self.assertEqual(g.active_player_indices(), [target.index])
        saved.assert_called_once_with(g)
        self.assertEqual(len(g.undo_stack), 1)
        self.assertTrue(g.session.undo())
        self.assertEqual(g.capture_undo_state(), before)
        for invalid in (True, "1", None, 99):
            self.assertFalse(g.session.execute("return_player", player_index=invalid).success)
