import copy
import unittest
from pathlib import Path
from unittest.mock import Mock

from portable_deck.core.actionerrors import ActionValidationError
from portable_deck.core.game import Game


class ScoreValidationTests(unittest.TestCase):
    def game(self, confirmations):
        game = Game(2, str(Path(__file__).resolve().parents[1] / "decks/demodeck.json"),
                    enable_undo=True, score_enabled=True, allow_reduce_score=True,
                    require_point_confirmation=confirmations)
        game.session.checkpoint_callback = Mock(return_value=None)
        return game

    def test_invalid_deltas_never_mutate_direct_or_transactional_calls(self):
        for confirmations in (False, True):
            game = self.game(confirmations)
            before = game.capture_undo_state()
            undo = copy.deepcopy(game.undo_stack)
            for delta in (True, False, 1.0, -1.0, 0, 2, -2, "1", None, [], {}):
                for transactional in (False, True):
                    with self.subTest(confirmations=confirmations, delta=delta, transactional=transactional):
                        with self.assertRaises(ActionValidationError) as error:
                            if transactional:
                                game.session.run(game.request_point, delta)
                            else:
                                game.request_point(delta)
                        self.assertEqual(error.exception.code, "invalid_score_change")
                        self.assertEqual(game.capture_undo_state(), before)
                        self.assertEqual(game.undo_stack, undo)
                        game.session.checkpoint_callback.assert_not_called()

    def test_integer_changes_keep_scoring_confirmations_and_undo(self):
        for confirmations in (False, True):
            for delta in (-1, 1):
                with self.subTest(confirmations=confirmations, delta=delta):
                    game = self.game(confirmations)
                    before = game.capture_undo_state()
                    success, _ = game.session.run(game.request_point, delta)
                    self.assertTrue(success)
                    if confirmations:
                        self.assertEqual(game.scores, [0, 0])
                        self.assertEqual(game.pending_point_request["delta"], delta)
                        self.assertIs(type(game.pending_point_request["delta"]), int)
                        game.session.execute("end_turn")
                        self.assertTrue(game.session.execute("confirm_point", approved=True).success)
                    self.assertEqual(game.scores, [delta, 0])
                    if confirmations:
                        self.assertTrue(game.session.undo())
                        self.assertTrue(game.session.undo())
                    self.assertTrue(game.session.undo())
                    self.assertEqual(game.capture_undo_state(), before)

    def test_valid_reduction_still_respects_disabled_option(self):
        game = self.game(False)
        game.allow_reduce_score = False
        before = game.capture_undo_state()
        success, _ = game.session.run(game.request_point, -1)
        self.assertFalse(success)
        self.assertEqual(game.capture_undo_state(), before)
        game.session.checkpoint_callback.assert_not_called()
