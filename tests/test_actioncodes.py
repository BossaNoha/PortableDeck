import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from portable_deck.core.game import Game
from portable_deck.core.actionavailability import ActionAvailability, action_availability


class ActionCodeTests(unittest.TestCase):
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
