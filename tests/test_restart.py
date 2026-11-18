import tempfile
import unittest
from pathlib import Path

from portable_deck.core.game import Game


class RestartTests(unittest.TestCase):
    def game(self, reset_chips=True):
        g = Game(3, str(Path(__file__).resolve().parents[1] / "decks/demodeck.json"),
                 player_names=["Alice", "Bob", "Carol"], enable_undo=True,
                 score_enabled=True, require_point_confirmation=True,
                 enable_chip_accounts=True, starting_balance=10,
                 reset_chip_accounts_on_restart=reset_chips, require_pot_withdrawal_confirmation=True,
                 enable_roles_teams=True, enable_teams=True, enable_dealer=True, team_count=2,
                 team_names=["Red"], player_teams=["team_1", "team_1", None],
                 dealer_players=[False, False, True], share_team_chips=True, share_team_score=True,
                 enable_team_score=True, enable_personal_piles=True, unequal_personal_piles=True,
                 personal_pile_counts=[2, 0, 1], enable_player_leaving=True, enable_player_return=True,
                 enable_cards_visibility=True, cards_visibility=[
                     {"players": [0], "teams": ["dealer"]},
                     {"players": [1], "teams": []}, {"players": [2], "teams": []}])
        g.start(1)
        g.configuration_info = {"name": "Friday", "modified": False}
        for action, args in (("play_card", {"card_index": 0}), ("draw_card", {}),
                             ("play_personal_pile", {"card_index": 0, "owner": 0, "pile_index": 1})):
            self.assertTrue(g.session.execute(action, **args).success)
        g.award_point(0, 2)
        for action, args in (("leave_session", {}), ("request_point", {}),
                             ("play_chips", {"amount": 5}), ("take_pot", {"player_index": 2})):
            self.assertTrue(g.session.execute(action, **args).success)
        return g

    def test_restart_loaded_session_preserves_rules_and_resets_transient_state(self):
        for keep_scores in (False, True):
            for reset_chips in (False, True):
                with self.subTest(keep_scores=keep_scores, reset_chips=reset_chips), tempfile.TemporaryDirectory() as folder:
                    original = self.game(reset_chips)
                    path = str(Path(folder) / "saved.json")
                    original.save_session(path)
                    loaded = Game.load_session(path)
                    before = loaded.capture_undo_state()
                    restarted = loaded.restart(keep_scores=keep_scores)
                    self.assertEqual(loaded.capture_undo_state(), before)
                    self.assertEqual([p.name for p in restarted.players], ["Alice", "Bob", "Carol"])
                    self.assertEqual([len(p.hand) for p in restarted.players], [1, 1, 1])
                    self.assertEqual(len(restarted.deck.flat_deck), 49)
                    self.assertEqual(restarted.current_player_index, 0)
                    self.assertEqual(restarted.left_players, [])
                    self.assertEqual(restarted.table_cards, [])
                    self.assertEqual(restarted.personal_piles, [[[], []], [], [[]]])
                    self.assertEqual(restarted.discard_piles, [[]])
                    self.assertEqual(restarted.undo_stack, [])
                    self.assertEqual(restarted.score_alerts_seen, {})
                    self.assertEqual(restarted.cards_drawn_this_turn, 0)
                    self.assertTrue(all(not player.revealed_indices for player in restarted.players))
                    self.assertIsNone(restarted.pending_point_request)
                    self.assertIsNone(restarted.pending_pot_withdrawal)
                    self.assertIsNone(restarted.session.checkpoint_callback)
                    self.assertFalse(hasattr(restarted, "named_save_path"))
                    self.assertEqual(restarted.game_log, ["Alice's turn starts."])
                    self.assertEqual(restarted.configuration_info, loaded.configuration_info)
                    self.assertEqual(restarted.player_teams, loaded.player_teams)
                    self.assertEqual(restarted.dealer_players, loaded.dealer_players)
                    self.assertEqual(restarted.cards_visibility, loaded.cards_visibility)
                    self.assertEqual(restarted.scores, loaded.scores if keep_scores else [0, 0, 0])
                    self.assertEqual(restarted.team_scores, loaded.team_scores if keep_scores else {"team_1": 0})
                    self.assertEqual(restarted.chip_balances, [20, 0, 10] if reset_chips else loaded.chip_balances)
                    self.assertEqual(restarted.chip_pot, 0 if reset_chips else 5)
                    self.assertTrue(restarted.require_point_confirmation)
                    self.assertTrue(restarted.require_pot_withdrawal_confirmation)

    def test_restart_configuration_collections_are_independent(self):
        original = self.game()
        restarted = original.restart()
        restarted.cards_visibility[0]["players"].clear()
        restarted.personal_pile_settings[0][0]["access"] = "everyone"
        restarted.player_teams[0] = None
        self.assertEqual(original.cards_visibility[0]["players"], [0])
        self.assertEqual(original.personal_pile_settings[0][0]["access"], "owner")
        self.assertEqual(original.player_teams[0], "team_1")
