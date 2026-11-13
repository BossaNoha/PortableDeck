import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from dataclasses import FrozenInstanceError
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
        g.acknowledge_score_notifications(notices)
        self.assertEqual(len(g.score_notifications()), 1)
        g.current_player_index = 1
        g.acknowledge_score_notifications(notices)
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
        g.session.run(g.acknowledge_score_notifications, notices)
        self.assertFalse(g.score_notifications())
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as folder:
            path = str(Path(folder) / 'session.json')
            g.save_session(path)
            loaded = Game.load_session(path)
            self.assertFalse(loaded.score_notifications())
        self.assertTrue(g.session.undo())
        self.assertEqual(g.score_notifications(), notices)

    def test_disabled_scoring_and_no_active_players(self):
        g = self.game()
        g.scores[1] = 10
        g.score_enabled = False
        self.assertFalse(g.score_notifications())
        g.score_enabled = True
        g.left_players = [0, 1]
        self.assertFalse(g.score_notifications())

    def test_cli_has_no_gui_dependency(self):
        script = "from portable_deck.core.game import Game; import sys; g=Game(2,'decks/demodeck.json',score_enabled=True,enable_target_score=True,target_score=10,enable_score_warning=True,score_warning=7); g.scores[1]=7; notices=g.score_notifications(); assert notices[0].recipient==0; g.acknowledge_score_notifications(notices); assert not g.score_notifications(); assert 'tkinter' not in sys.modules"
        result = subprocess.run([sys.executable, '-B', '-c', script], cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
