import unittest
from pathlib import Path
from unittest.mock import Mock

from portable_deck.core.game import Game


class SessionTests(unittest.TestCase):
    def test_end_turn_query_is_read_only_and_execution_rechecks_pending_decisions(self):
        game = self.game
        game.require_point_confirmation = True
        self.assertTrue(game.session.end_turn_availability().allowed)
        self.assertTrue(game.session.execute("request_point").success)
        self.assertTrue(game.session.end_turn_availability().allowed)
        self.assertTrue(game.session.execute("end_turn").success)
        before = game.capture_undo_state()
        count = len(game.undo_stack)
        self.saved.reset_mock()
        blocked = game.session.end_turn_availability()
        self.assertFalse(blocked.allowed)
        self.assertEqual(blocked.code, "confirmation_required")
        result = game.session.execute("end_turn")
        self.assertEqual((result.code, result.message), (blocked.code, blocked.reason))
        self.assertEqual(game.capture_undo_state(), before)
        self.assertEqual(len(game.undo_stack), count)
        self.saved.assert_not_called()
        self.assertTrue(game.session.execute("confirm_point", approved=True).success)
        self.assertTrue(game.session.end_turn_availability().allowed)
        game.left_players = [0, 1]
        unavailable = game.session.end_turn_availability()
        self.assertEqual(unavailable.code, "no_active_players")
        self.assertEqual(game.session.execute("end_turn").code, unavailable.code)

    def test_checkpoint_result_has_status_and_no_gameplay_undo_step(self):
        before = self.game.capture_undo_state()
        result = self.game.session.checkpoint_result()
        self.assertTrue(result.success)
        self.assertFalse(result.changed)
        self.assertEqual(result.code, "")
        self.assertIsNone(result.checkpoint_error)
        self.saved.assert_called_once_with(self.game)
        self.assertEqual(self.game.capture_undo_state(), before)
        self.assertEqual(self.game.undo_stack, [])

    def test_checkpoint_result_handles_error_and_exception_and_clears_stale_error(self):
        for raises in (False, True):
            with self.subTest(raises=raises):
                self.saved.reset_mock()
                self.saved.side_effect = OSError("Disk full") if raises else None
                self.saved.return_value = "Disk full"
                result = self.game.session.checkpoint_result()
                self.assertFalse(result.success)
                self.assertFalse(result.changed)
                self.assertEqual((result.code, result.message, result.checkpoint_error),
                                 ("checkpoint_failed", "Disk full", "Disk full"))
                self.assertIn("Disk full", self.game.game_log[-1])
                self.assertEqual(self.game.undo_stack, [])
                self.saved.assert_called_once_with(self.game)
                self.saved.side_effect = None
                self.saved.return_value = None
                recovered = self.game.session.checkpoint_result()
                self.assertTrue(recovered.success)
                self.assertIsNone(recovered.checkpoint_error)
                self.assertIsNone(self.game.session.last_checkpoint_error)
        self.game.session.checkpoint_callback = None
        self.assertTrue(self.game.session.checkpoint_result().success)
        self.assertIsNone(self.game.session.checkpoint())

    def test_structured_undo_reports_refusal_success_and_checkpoint_failure(self):
        empty = self.game.session.undo_result()
        self.assertFalse(empty.success)
        self.assertFalse(empty.changed)
        self.assertEqual(empty.code, "empty_undo")
        self.saved.assert_not_called()
        before = self.game.capture_undo_state()
        self.assertTrue(self.game.session.execute("draw_card").success)
        self.saved.reset_mock()
        result = self.game.session.undo_result()
        self.assertTrue(result.success)
        self.assertTrue(result.changed)
        self.assertIsNone(result.checkpoint_error)
        self.assertEqual(self.game.capture_undo_state(), before)
        self.saved.assert_called_once_with(self.game)
        self.game.session.execute("draw_card")
        self.saved.return_value = "Disk full"
        result = self.game.session.undo_result()
        self.assertTrue(result.success)
        self.assertTrue(result.changed)
        self.assertEqual(result.checkpoint_error, "Disk full")
        self.assertEqual(self.game.players[0].hand, [])
        self.assertEqual(self.game.deck.flat_deck, before["remaining_deck"])
        self.assertEqual(self.game.undo_stack, [])
        self.assertEqual(result.events, ())
        self.saved.reset_mock()
        refused = self.game.session.undo_result()
        self.assertEqual(refused.code, "empty_undo")
        self.assertIsNone(refused.checkpoint_error)
        self.assertIsNone(self.game.session.last_checkpoint_error)
        self.saved.assert_not_called()

    def test_undo_availability_is_read_only_and_tracks_history(self):
        from dataclasses import FrozenInstanceError
        before = self.game.capture_undo_state()
        empty = self.game.session.undo_availability()
        self.assertFalse(empty.allowed)
        self.assertEqual(empty.code, "empty_undo")
        self.assertTrue(empty.reason)
        self.assertEqual(self.game.capture_undo_state(), before)
        self.saved.assert_not_called()
        with self.assertRaises(FrozenInstanceError):
            empty.allowed = True
        self.assertTrue(self.game.session.execute("draw_card").success)
        available = self.game.session.undo_availability()
        self.assertTrue(available.allowed)
        self.assertEqual((available.reason, available.code), ("", ""))
        self.assertFalse(empty.allowed)
        self.assertTrue(self.game.session.undo())
        self.assertEqual(self.game.session.undo_availability(), empty)
        self.assertEqual(self.game.capture_undo_state(), before)

    def test_undo_revalidates_after_availability_changes_without_checkpoint(self):
        self.assertFalse(self.game.session.undo())
        self.saved.assert_not_called()
        self.assertTrue(self.game.session.execute("draw_card").success)
        self.assertTrue(self.game.session.undo_availability().allowed)
        self.game.enable_undo = False
        before = self.game.capture_undo_state()
        history = list(self.game.undo_stack)
        self.saved.reset_mock()
        disabled = self.game.session.undo_availability()
        self.assertFalse(disabled.allowed)
        self.assertEqual(disabled.code, "action_disabled")
        self.assertFalse(self.game.session.undo())
        self.assertEqual(self.game.capture_undo_state(), before)
        self.assertEqual(self.game.undo_stack, history)
        self.saved.assert_not_called()
        self.game.enable_undo = True
        self.assertTrue(self.game.session.undo())
        self.saved.assert_called_once_with(self.game)

    def setUp(self):
        self.game = Game(2, str(Path(__file__).resolve().parents[1] / 'decks/demodeck.json'),
                         enable_undo=True, score_enabled=True, enable_chip_accounts=True)
        self.saved = Mock()
        self.game.session.checkpoint_callback = self.saved
        self.saved.return_value = None

    def test_draw_and_undo_checkpoint_once_each(self):
        before = self.game.capture_undo_state()
        result = self.game.session.execute('draw_card')
        self.assertTrue(result.success)
        self.assertTrue(result.changed)
        self.assertEqual(len(self.game.undo_stack), 1)
        self.saved.assert_called_once_with(self.game)
        self.assertTrue(self.game.session.undo())
        self.assertEqual(self.saved.call_count, 2)
        self.assertEqual(before, self.game.capture_undo_state())

    def test_nested_operations_share_one_undo_and_save(self):
        def operation():
            self.game.session.execute('draw_card')
            self.game.session.execute('draw_card')
            self.game.gui_log.append('Two cards drawn')
        self.game.session.run(operation)
        self.assertEqual(len(self.game.players[0].hand), 2)
        self.assertEqual(len(self.game.undo_stack), 1)
        self.saved.assert_called_once()
        self.game.session.undo()
        self.assertEqual(self.game.players[0].hand, [])
        self.assertEqual(self.game.gui_log, [])

    def test_rejected_action_and_noop_do_not_save(self):
        result = self.game.session.execute('play_card', card_index=99)
        self.assertFalse(result.success)
        self.assertFalse(result.changed)
        self.game.session.run(lambda: None)
        self.assertEqual(self.game.undo_stack, [])
        self.saved.assert_not_called()

    def test_partial_failure_restores_state(self):
        before = self.game.capture_undo_state()
        def broken():
            self.game.deal_card_to_current()
            raise RuntimeError('failed')
        with self.assertRaises(RuntimeError):
            self.game.session.run(broken)
        self.assertEqual(before, self.game.capture_undo_state())
        self.assertEqual(self.game.undo_stack, [])
        self.saved.assert_not_called()

    def test_bad_parameters_restore_and_report_failure(self):
        before = self.game.capture_undo_state()
        result = self.game.session.execute('play_chips', amount=-1)
        self.assertFalse(result.success)
        self.assertEqual(before, self.game.capture_undo_state())
        self.saved.assert_not_called()

    def test_save_failure_does_not_undo_successful_action(self):
        self.saved.side_effect = OSError('Disk full')
        result = self.game.session.execute('draw_card')
        self.assertTrue(result.success)
        self.assertEqual(result.checkpoint_error, 'Disk full')
        self.assertEqual(len(self.game.players[0].hand), 1)
        self.assertEqual(len(self.game.undo_stack), 1)

    def test_end_turn_and_score_without_gui(self):
        self.assertTrue(self.game.session.execute('request_point').success)
        self.assertTrue(self.game.session.execute('end_turn').success)
        self.assertEqual(self.game.current_player_index, 1)


    def test_discard_draw_and_table_move(self):
        g = self.game
        g.allow_draw_from_discard = True
        g.discard_piles[0].append('A')
        self.assertTrue(g.session.execute('draw_from_discard').success)
        self.assertTrue(g.session.execute('play_card', card_index=0).success)
        g.allow_move_cards_on_table = True
        self.assertTrue(g.session.execute('move_table_card', card_index=0,
                                         target_position=(0, 1)).success)
        after = g.capture_undo_state()
        self.assertTrue(g.session.undo())
        self.assertNotEqual(after, g.capture_undo_state())

    def test_score_confirmation_is_shared(self):
        g = self.game
        g.require_point_confirmation = True
        self.assertTrue(g.session.execute('request_point').success)
        self.assertTrue(g.session.execute('end_turn').success)
        self.assertFalse(g.session.execute('draw_card').success)
        self.assertTrue(g.session.execute('confirm_point', approved=True).success)
        self.assertIsNone(g.pending_point_request)
        self.assertTrue(g.session.execute('draw_card').success)
