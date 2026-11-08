import unittest
import tempfile
from pathlib import Path
from portable_deck.core.game import Game

class PlayerLeavingTests(unittest.TestCase):
    def game(self, rules, **kwargs):
        return Game(3, str(Path(__file__).resolve().parents[1] / "decks/demodeck.json"),
                    enable_player_leaving=True, leave_conditions=rules, enable_undo=True, **kwargs)

    def test_conditions_and_opponents_exclude_teammates(self):
        g = self.game({"own_score": True, "own_score_at": "warning"},
                      score_enabled=True, enable_target_score=True, target_score=10,
                      enable_score_warning=True, score_warning=7)
        self.assertFalse(g.can_leave_session())
        g.scores[0] = 7
        self.assertTrue(g.can_leave_session())
        g.leave_conditions.update(own_score=False, opponent_score=True, opponent_score_at="target")
        g.initialize_roles_teams(True, False, True, 2, [], ["team_1", "team_1", "team_2"])
        g.scores[1] = 10
        self.assertFalse(g.can_leave_session())
        g.scores[2] = 10
        self.assertTrue(g.can_leave_session())

    def test_chip_condition_and_unavailable_dependency(self):
        g = self.game({"no_chips": True}, enable_chip_accounts=True, starting_balance=0)
        self.assertTrue(g.can_leave_session())
        g.enable_chip_accounts = False
        self.assertTrue(g.can_leave_session())
        g.leave_conditions["no_chips"] = False
        self.assertTrue(g.can_leave_session())

    def test_skip_departed_players_persist_and_undo(self):
        g = self.game({"any_time": True})
        state = g.capture_undo_state()
        g.undo_stack.append(state)
        self.assertTrue(g.leave_session()[0])
        self.assertEqual(g.current_player_index, 1)
        g.finish_turn()
        g.finish_turn()
        self.assertEqual(g.current_player_index, 1)
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as folder:
            path = str(Path(folder) / "save.json")
            g.save_session(path)
            loaded = Game.load_session(path)
            self.assertEqual(loaded.left_players, [0])
            self.assertTrue(loaded.undo_last_action())
            self.assertEqual(loaded.capture_undo_state(), state)
        self.assertEqual(g.restart().left_players, [])
        g.leave_session()
        g.leave_session()
        self.assertEqual(g.active_player_indices(), [])
        self.assertFalse(g.leave_session()[0])

    def test_all_enabled_restrictions_must_be_satisfied(self):
        g = self.game({"own_score": True, "no_chips": True}, score_enabled=True,
                      enable_target_score=True, target_score=10, enable_chip_accounts=True)
        self.assertFalse(g.can_leave_session())
        g.scores[0] = 10
        self.assertFalse(g.can_leave_session())
        g.chip_balances[0] = 0
        self.assertTrue(g.can_leave_session())
        g.initialize_leaving(True, {})
        self.assertTrue(g.can_leave_session())

    def test_any_condition_and_persistence(self):
        g = self.game({"own_score": True, "no_chips": True, "match": "any"},
                      score_enabled=True, enable_target_score=True, target_score=10, enable_chip_accounts=True)
        self.assertFalse(g.can_leave_session())
        g.scores[0] = 10
        self.assertTrue(g.can_leave_session())
        g.leave_conditions["match"] = "all"
        self.assertFalse(g.can_leave_session())
        g.leave_conditions["match"] = "any"
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as folder:
            path = str(Path(folder) / "save.json")
            g.save_session(path)
            loaded = Game.load_session(path)
            self.assertTrue(loaded.can_leave_session())
            self.assertEqual(loaded.restart().leave_conditions["match"], "any")
        g.leave_conditions.update(own_score=False, no_chips=False)
        self.assertTrue(g.can_leave_session())

    def test_return_keeps_state_and_supports_undo_and_persistence(self):
        g = self.game({}, enable_player_return=True)
        g.players[0].hand = ["A of Test"]
        g.leave_session()
        current = g.current_player_index
        before = g.capture_undo_state()
        g.undo_stack.append(before)
        self.assertTrue(g.return_player(0)[0])
        self.assertEqual(g.current_player_index, current)
        self.assertEqual(g.players[0].hand, ["A of Test"])
        self.assertFalse(g.return_player(0)[0])
        self.assertTrue(g.undo_last_action())
        self.assertEqual(g.capture_undo_state(), before)
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as folder:
            path = str(Path(folder) / "save.json")
            g.save_session(path)
            loaded = Game.load_session(path)
            self.assertTrue(loaded.enable_player_return)
            self.assertTrue(loaded.return_player(0)[0])
            self.assertTrue(loaded.restart().enable_player_return)

    def test_return_to_empty_session(self):
        g = self.game({}, enable_player_return=True)
        for _ in range(3):
            g.leave_session()
        self.assertEqual(g.active_player_indices(), [])
        self.assertTrue(g.return_player(1)[0])
        self.assertEqual(g.current_player_index, 1)
        g.enable_player_return = False
        self.assertFalse(g.return_player(0)[0])

    def test_pending_confirmation_blocks_departure(self):
        g = self.game({"any_time": True}, score_enabled=True, require_point_confirmation=True)
        g.request_point()
        self.assertFalse(g.can_leave_session())
