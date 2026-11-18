import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path

from portable_deck.core.game import Game
from portable_deck.core.turnstart import build_turn_start_view


class TurnStartTests(unittest.TestCase):
    def game(self):
        g = Game(2, str(Path(__file__).resolve().parents[1] / "decks/demodeck.json"),
                 score_enabled=True, require_point_confirmation=True,
                 enable_target_score=True, target_score=10, enable_score_warning=True, score_warning=7,
                 enable_chip_accounts=True, require_pot_withdrawal_confirmation=True, enable_undo=True)
        g.session.execute("request_point")
        g.session.execute("play_chips", amount=5)
        g.session.execute("take_pot", player_index=0)
        g.session.execute("end_turn")
        return g

    def test_ordered_read_only_work_and_immutable_snapshot(self):
        g = self.game()
        g.scores[0] = 7
        before = g.capture_undo_state()
        work = build_turn_start_view(g)
        self.assertTrue(work.active)
        self.assertEqual(work.player, 1)
        self.assertEqual(work.notifications[0].kind, "warning")
        self.assertEqual([p.action for p in work.confirmations], ["confirm_point", "confirm_pot"])
        self.assertEqual(g.capture_undo_state(), before)
        self.assertEqual(build_turn_start_view(g), work)
        with self.assertRaises(FrozenInstanceError):
            work.player = 0
        with self.assertRaises(FrozenInstanceError):
            work.confirmations[0].action = "changed"

    def test_requery_after_decisions_and_undo(self):
        for approved in (False, True):
            with self.subTest(approved=approved):
                g = self.game()
                original = build_turn_start_view(g)
                prompt = original.next_confirmation
                self.assertTrue(g.session.execute(prompt.action, approved=approved).success)
                remaining = build_turn_start_view(g)
                self.assertEqual(remaining.next_confirmation.action, "confirm_pot")
                self.assertEqual(g.scores[0], 1 if approved else 0)
                self.assertTrue(g.session.undo())
                self.assertEqual(build_turn_start_view(g), original)
                g.session.execute(prompt.action, approved=approved)
                prompt = build_turn_start_view(g).next_confirmation
                g.session.execute(prompt.action, approved=approved)
                self.assertEqual(build_turn_start_view(g).confirmations, ())
                self.assertEqual(g.chip_pot, 0 if approved else 5)

    def test_notifications_require_acknowledgment_and_inactive_player_has_no_work(self):
        g = self.game()
        g.scores[0] = 7
        work = build_turn_start_view(g)
        self.assertTrue(work.notifications)
        self.assertEqual(build_turn_start_view(g).notifications, work.notifications)
        g.session.acknowledge_score_notifications(work.notifications)
        self.assertEqual(build_turn_start_view(g).notifications, ())
        g.left_players = [1]
        work = build_turn_start_view(g)
        self.assertFalse(work.active)
        self.assertEqual((work.notifications, work.confirmations), ((), ()))
