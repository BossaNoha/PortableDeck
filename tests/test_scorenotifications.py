import tempfile
import unittest
from pathlib import Path
from dataclasses import FrozenInstanceError
from unittest.mock import Mock
from portable_deck.core.game import Game


class ScoreNotificationTests(unittest.TestCase):
    def game(self, **options):
        return Game(2, str(Path(__file__).resolve().parents[1] / 'decks/demodeck.json'),
                    score_enabled=True, enable_target_score=True, target_score=10,
                    enable_score_warning=True, score_warning=7, **options)

    def test_read_only_query_and_explicit_acknowledgment(self):
        g = self.game()
        g.scores[1] = 7
        before = g.capture_undo_state()
        notices = g.score_notifications()
        self.assertEqual(before, g.capture_undo_state())
        self.assertEqual(notices, g.score_notifications())
        notice = notices[0]
        self.assertEqual((notice.recipient, notice.kind, notice.score, notice.threshold), (0, 'warning', 7, 7))
        self.assertTrue(notice.requires_confirmation)
        with self.assertRaises(FrozenInstanceError):
            notice.message = 'changed'
        g.acknowledge_score_notifications(notices)
        self.assertEqual(g.score_notifications(), ())

    def test_stale_or_wrong_recipient_cannot_acknowledge(self):
        g = self.game()
        g.scores[1] = 7
        notices = g.score_notifications()
        g.scores[1] = 8
        g.session.acknowledge_score_notifications(notices)
        self.assertEqual(len(g.score_notifications()), 1)
        g.current_player_index = 1
        g.session.acknowledge_score_notifications(notices)
        g.current_player_index = 0
        self.assertEqual(len(g.score_notifications()), 1)

    def test_owner_exclusion_target_and_recrossing(self):
        g = self.game()
        g.scores[0] = 7
        self.assertEqual(g.score_notifications(), ())
        g.scores[0] = 10
        self.assertEqual(g.score_notifications()[0].kind, 'target')
        g.acknowledge_score_notifications(g.score_notifications())
        g.scores[0] = 0
        g.acknowledge_score_notifications(())
        g.scores[0] = 10
        self.assertEqual(len(g.score_notifications()), 1)

    def test_pending_approval_is_prepared_for_current_voter(self):
        g = self.game(require_point_confirmation=True, allow_reduce_score=True)
        g.session.execute('reduce_score')
        self.assertIsNone(g.score_confirmation_notification())
        g.finish_turn()
        before = g.capture_undo_state()
        notice = g.score_confirmation_notification()
        self.assertEqual(before, g.capture_undo_state())
        self.assertEqual((notice.kind, notice.recipient, notice.requester, notice.delta), ('score_approval', 1, 0, -1))
        self.assertIn('-1', notice.message)
        self.assertIn(g.players[1].name, notice.message)
        self.assertTrue(g.session.execute('confirm_point', approved=True).success)
        self.assertIsNone(g.score_confirmation_notification())

    def test_acknowledgments_survive_save_and_are_undoable(self):
        g = self.game(enable_undo=True)
        g.scores[1] = 7
        notices = g.score_notifications()
        def action():
            g.session.execute('draw_card')
            g.session.acknowledge_score_notifications(notices)
        g.session.run(action)
        self.assertFalse(g.score_notifications())
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as folder:
            path = str(Path(folder) / 'session.json')
            g.save_session(path)
            loaded = Game.load_session(path)
            self.assertFalse(loaded.score_notifications())
        self.assertTrue(g.session.undo())
        self.assertEqual(g.score_notifications(), notices)

    def test_standalone_acknowledgment_checkpoints_without_undo_step(self):
        for nested in (False, True):
            with self.subTest(nested=nested):
                g = self.game(enable_undo=True)
                g.scores[1] = 7
                notices = g.score_notifications()
                saved = Mock(return_value=None)
                g.session.checkpoint_callback = saved
                operation = lambda: g.session.acknowledge_score_notifications(notices)
                result = g.session.run(operation) if nested else operation()
                self.assertTrue(result.changed)
                self.assertEqual(g.undo_stack, [])
                saved.assert_called_once_with(g)
                result = g.session.acknowledge_score_notifications(notices)
                self.assertFalse(result.changed)
                saved.assert_called_once()

    def test_grouped_acknowledgment_shares_gameplay_checkpoint_and_undo(self):
        g = self.game(enable_undo=True)
        g.scores[1] = 7
        before = g.capture_undo_state()
        saved = Mock(return_value=None)
        g.session.checkpoint_callback = saved
        def operation():
            g.session.execute('draw_card')
            g.session.acknowledge_score_notifications(g.score_notifications())
        g.session.run(operation)
        saved.assert_called_once_with(g)
        self.assertEqual(len(g.undo_stack), 1)
        self.assertTrue(g.session.undo())
        self.assertEqual(g.capture_undo_state(), before)

    def test_acknowledgment_failure_is_reported_without_losing_seen_state(self):
        g = self.game()
        g.scores[1] = 7
        g.session.checkpoint_callback = Mock(return_value='Disk full')
        result = g.session.acknowledge_score_notifications(g.score_notifications())
        self.assertTrue(result.success)
        self.assertTrue(result.changed)
        self.assertEqual(result.checkpoint_error, 'Disk full')
        self.assertEqual(g.score_notifications(), ())

    def test_empty_acknowledgment_prunes_expired_events_without_undo(self):
        g = self.game(enable_undo=True)
        g.scores[1] = 7
        g.session.acknowledge_score_notifications(g.score_notifications())
        g.scores[1] = 0
        saved = Mock(return_value=None)
        g.session.checkpoint_callback = saved
        result = g.session.acknowledge_score_notifications(())
        self.assertTrue(result.changed)
        saved.assert_called_once_with(g)
        self.assertEqual(g.undo_stack, [])
        g.scores[1] = 7
        self.assertEqual(len(g.score_notifications()), 1)

    def test_disabled_scoring_and_no_active_players(self):
        g = self.game()
        g.scores[1] = 10
        g.score_enabled = False
        self.assertFalse(g.score_notifications())
        g.score_enabled = True
        g.left_players = [0, 1]
        self.assertFalse(g.score_notifications())
