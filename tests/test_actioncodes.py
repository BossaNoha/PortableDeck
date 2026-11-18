import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from portable_deck.core.game import Game
from portable_deck.core.actionavailability import ActionAvailability, action_availability
from portable_deck.core.interactions import INTERACTIONS, build_interaction_options
from portable_deck.core.chipvalidation import chip_action_error


class ActionCodeTests(unittest.TestCase):
    def test_interaction_option_codes_match_execution_and_stale_targets(self):
        for case, expected in (("left", "target_left"), ("empty", "target_hand_empty"),
                               ("shared", "shared_chip_account"), ("no_chips", "insufficient_chips")):
            with self.subTest(case=case):
                g = self.game()
                g.enable_interactions = True
                g.interaction_options = dict.fromkeys(INTERACTIONS, True)
                g.players[1].hand = ["B"]
                action = "steal_chips" if case in {"shared", "no_chips"} else "take_random_card"
                self.assertTrue(build_interaction_options(g, action).targets[0].allowed)
                if case == "left":
                    g.left_players = [1]
                elif case == "empty":
                    g.players[1].hand.clear()
                elif case == "shared":
                    g.player_teams = ["team_1", "team_1"]
                    g.share_team_chips = True
                else:
                    g.chip_balances[1] = 0
                target = build_interaction_options(g, action).targets[0]
                self.assertFalse(target.allowed)
                self.assertEqual(target.code, expected)
                before = g.capture_undo_state()
                saved = g.session.checkpoint_callback = Mock(return_value=None)
                result = g.session.execute(action, target=1, amount=5)
                self.assertEqual(result.code, expected)
                self.assertEqual(g.capture_undo_state(), before)
                saved.assert_not_called()

    def test_chip_parameter_codes_are_shared_with_model_validation(self):
        for action, parameters, expected in (
            ("play_chips", {"amount": 4}, "minimum_bet_not_met"),
            ("play_chips", {"amount": 101}, "insufficient_chips"),
            ("play_chips", {"amount": True}, "invalid_amount"),
            ("buy_chips", {"amount": 0, "player_index": 1}, "invalid_amount"),
            ("buy_chips", {"amount": 1, "player_index": True}, "invalid_target"),
            ("take_pot", {"player_index": 99}, "invalid_target"),
        ):
            with self.subTest(action=action, parameters=parameters):
                g = self.game()
                g.minimum_bet = 5
                g.chip_pot = 10
                error = chip_action_error(g, action, **parameters)
                self.assertEqual(error.code, expected)
                before = g.capture_undo_state()
                saved = g.session.checkpoint_callback = Mock(return_value=None)
                result = g.session.execute(action, **parameters)
                self.assertEqual(result.code, expected)
                self.assertEqual(result.message, str(error))
                self.assertEqual(g.capture_undo_state(), before)
                self.assertEqual(g.undo_stack, [])
                saved.assert_not_called()

    def test_steal_amount_changes_and_random_discard_have_specific_codes(self):
        g = self.game()
        g.enable_interactions = True
        g.interaction_options = dict.fromkeys(INTERACTIONS, True)
        original = build_interaction_options(g, "steal_chips").targets[0]
        self.assertEqual(original.max_amount, 100)
        g.chip_balances[1] = 3
        before = g.capture_undo_state()
        self.assertEqual(g.session.execute("steal_chips", target=1, amount=10).code, "insufficient_chips")
        self.assertEqual(g.session.execute("steal_chips", target=1, amount=False).code, "invalid_amount")
        self.assertEqual(g.session.execute("take_random_card", target=True).code, "invalid_target")
        options = build_interaction_options(g, "discard_random_card")
        self.assertEqual(options.code, "no_eligible_targets")
        self.assertEqual(g.session.execute("discard_random_card").code, options.code)
        self.assertEqual(g.capture_undo_state(), before)

    def game(self):
        g = Game(2, str(Path(__file__).resolve().parents[1] / "decks/demodeck.json"),
                 enable_undo=True, allow_positioned_play=True,
                 score_enabled=True, require_point_confirmation=True,
                 enable_chip_accounts=True, require_pot_withdrawal_confirmation=True)
        g.players[0].hand = ["A"]
        return g

    def test_draw_play_and_confirmation_failures_have_codes_without_mutation(self):
        cases = (
            ("empty", "draw_card", {}, "empty_deck"),
            ("normal", "play_card", {}, "selection_required"),
            ("normal", "play_card", {"card_index": 99}, "invalid_selection"),
            ("normal", "play_at_position", {"card_index": 0, "target_position": (99, 99)}, "invalid_target"),
            ("pending", "draw_card", {}, "confirmation_required"),
            ("pending", "end_turn", {}, "confirmation_required"),
            ("normal", "confirm_point", {"approved": True}, "confirmation_not_required"),
            ("normal", "confirm_pot", {"approved": True}, "confirmation_not_required"),
            ("pending", "confirm_point", {}, "invalid_parameters"),
        )
        for setup, action, parameters, expected in cases:
            with self.subTest(setup=setup, action=action):
                g = self.game()
                if setup == "empty":
                    g.deck.flat_deck.clear()
                elif setup == "pending":
                    g.session.execute("request_point")
                    g.session.execute("end_turn")
                before = g.capture_undo_state()
                undo = list(g.undo_stack)
                saved = Mock(return_value=None)
                g.session.checkpoint_callback = saved
                result = g.session.execute(action, **parameters)
                self.assertFalse(result.success)
                self.assertEqual(result.code, expected)
                self.assertTrue(result.message)
                self.assertEqual(g.capture_undo_state(), before)
                self.assertEqual(g.undo_stack, undo)
                saved.assert_not_called()

    def test_code_propagates_independently_of_display_wording(self):
        g = self.game()
        with patch("portable_deck.core.session.action_availability",
                   return_value=ActionAvailability(False, "Jiný jazyk", "empty_deck")):
            result = g.session.execute("draw_card")
        self.assertEqual(result.code, "empty_deck")
        self.assertEqual(result.message, "Jiný jazyk")
        g.deck.flat_deck.clear()
        self.assertEqual(action_availability(g, "draw_card").code, "empty_deck")

    def test_success_and_denial_have_no_error_code(self):
        g = self.game()
        self.assertEqual(g.session.execute("draw_card").code, "")
        g.session.execute("request_point")
        g.session.execute("end_turn")
        result = g.session.execute("confirm_point", approved=False)
        self.assertTrue(result.success)
        self.assertEqual(result.code, "")
        self.assertIsNone(g.pending_point_request)

    def test_save_failure_does_not_turn_success_into_a_command_error(self):
        g = self.game()
        g.session.checkpoint_callback = Mock(return_value="Disk full")
        result = g.session.execute("draw_card")
        self.assertTrue(result.success)
        self.assertEqual(result.code, "")
        self.assertEqual(result.checkpoint_error, "Disk full")
