import copy
import unittest
from pathlib import Path
from unittest.mock import Mock

from portable_deck.core.actionerrors import ActionValidationError
from portable_deck.core.game import Game


class ConfirmationValidationTests(unittest.TestCase):
    def game(self, action):
        game = Game(2, str(Path(__file__).resolve().parents[1] / "decks/demodeck.json"),
                    enable_undo=True, score_enabled=True, require_point_confirmation=True,
                    enable_chip_accounts=True, starting_balance=10,
                    require_pot_withdrawal_confirmation=True)
        if action == "confirm_point":
            self.assertTrue(game.session.execute("request_point").success)
        else:
            self.assertTrue(game.session.execute("play_chips", amount=3).success)
            self.assertTrue(game.session.execute("take_pot", player_index=0).success)
        self.assertTrue(game.session.execute("end_turn").success)
        game.session.checkpoint_callback = Mock(return_value=None)
        return game

    def test_invalid_and_missing_decisions_do_not_change_state_undo_or_checkpoint(self):
        for action in ("confirm_point", "confirm_pot"):
            game = self.game(action)
            before = game.capture_undo_state()
            undo = copy.deepcopy(game.undo_stack)
            invalid = (None, 0, 1, -1, 0.0, 1.0, "false", "true", "", [], [True], {}, {"approved": True})
            for parameters in ({}, *({"approved": value} for value in invalid)):
                with self.subTest(action=action, parameters=parameters):
                    result = game.session.execute(action, **parameters)
                    self.assertFalse(result.success)
                    self.assertFalse(result.changed)
                    self.assertEqual(result.code, "invalid_confirmation")
                    self.assertEqual(result.events, ())
                    self.assertEqual(result.messages, ())
                    self.assertEqual(game.capture_undo_state(), before)
                    self.assertEqual(game.undo_stack, undo)
                    game.session.checkpoint_callback.assert_not_called()

    def test_direct_model_calls_also_reject_non_boolean_decisions(self):
        for action in ("confirm_point", "confirm_pot"):
            game = self.game(action)
            confirm = game.confirm_point_request if action == "confirm_point" else game.confirm_pot_withdrawal
            before = game.capture_undo_state()
            for value in ("false", 1, 0, None, [], {}):
                with self.subTest(action=action, value=value):
                    with self.assertRaises(ActionValidationError) as error:
                        confirm(value)
                    self.assertEqual(error.exception.code, "invalid_confirmation")
                    self.assertEqual(game.capture_undo_state(), before)

    def test_boolean_approval_and_rejection_keep_existing_behavior_and_undo(self):
        for action in ("confirm_point", "confirm_pot"):
            for approved in (True, False):
                with self.subTest(action=action, approved=approved):
                    game = self.game(action)
                    before = game.capture_undo_state()
                    result = game.session.execute(action, approved=approved)
                    self.assertTrue(result.success)
                    self.assertTrue(result.changed)
                    game.session.checkpoint_callback.assert_called_once_with(game)
                    if action == "confirm_point":
                        self.assertIsNone(game.pending_point_request)
                        self.assertEqual(game.scores, [int(approved), 0])
                    else:
                        self.assertIsNone(game.pending_pot_withdrawal)
                        self.assertEqual(game.chip_pot, 0 if approved else 3)
                        self.assertEqual(game.chip_balance(0), 10 if approved else 7)
                    self.assertTrue(game.session.undo())
                    self.assertEqual(game.capture_undo_state(), before)
