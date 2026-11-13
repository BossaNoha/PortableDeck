import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock

from portable_deck.core.game import Game


class SessionTests(unittest.TestCase):
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

    def test_no_tkinter_dependency(self):
        script = "from portable_deck.core.game import Game; import sys; g=Game(2,'decks/demodeck.json'); assert g.session.execute('draw_card').success; assert 'tkinter' not in sys.modules"
        result = subprocess.run([sys.executable, '-B', '-c', script],
                                cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

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
