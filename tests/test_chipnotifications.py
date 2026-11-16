import subprocess
import sys
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path

from portable_deck.core.game import Game


class ChipNotificationTests(unittest.TestCase):
    def game(self):
        g = Game(3, str(Path(__file__).resolve().parents[1] / "decks/demodeck.json"),
                 enable_chip_accounts=True, require_pot_withdrawal_confirmation=True, enable_undo=True)
        g.session.execute("play_chips", amount=10)
        g.session.execute("take_pot", player_index=2)
        return g

    def test_prompt_is_immutable_read_only_and_for_current_voter(self):
        g = self.game()
        self.assertIsNone(g.pot_confirmation_notification())
        g.session.execute("end_turn")
        before = g.capture_undo_state()
        notice = g.pot_confirmation_notification()
        self.assertEqual((notice.kind, notice.recipient, notice.requester, notice.beneficiary, notice.amount),
                         ("pot_approval", 1, 0, 2, 10))
        self.assertIn("Player1", notice.message)
        self.assertIn("Player3", notice.message)
        self.assertIn("As Player2", notice.message)
        self.assertEqual(g.capture_undo_state(), before)
        self.assertEqual(g.pot_confirmation_notification(), notice)
        with self.assertRaises(FrozenInstanceError):
            notice.amount = 0
        self.assertTrue(g.session.execute("confirm_pot", approved=True).success)
        self.assertIsNone(g.pot_confirmation_notification())
        self.assertTrue(g.session.undo())
        self.assertEqual(g.pot_confirmation_notification(), notice)

    def test_completion_or_denial_removes_prompt(self):
        for approved in (True, False):
            with self.subTest(approved=approved):
                g = self.game()
                g.session.execute("end_turn")
                g.session.execute("confirm_pot", approved=approved)
                if approved:
                    g.session.execute("end_turn")
                    self.assertEqual(g.pot_confirmation_notification().recipient, 2)
                    g.session.execute("confirm_pot", approved=True)
                self.assertIsNone(g.pending_pot_withdrawal)
                self.assertIsNone(g.pot_confirmation_notification())
                self.assertEqual(g.chip_pot, 0 if approved else 10)

    def test_disabled_or_departed_voter_gets_no_prompt(self):
        g = self.game()
        g.current_player_index = 1
        g.enable_chip_accounts = False
        self.assertIsNone(g.pot_confirmation_notification())
        g.enable_chip_accounts = True
        g.left_players = [1]
        self.assertIsNone(g.pot_confirmation_notification())

    def test_core_prompt_does_not_import_tkinter(self):
        script = ("from portable_deck.core.game import Game; import sys; "
                  "g=Game(2,'decks/demodeck.json',enable_chip_accounts=True,require_pot_withdrawal_confirmation=True); "
                  "g.session.execute('play_chips',amount=10); g.session.execute('take_pot',player_index=0); "
                  "g.session.execute('end_turn'); assert g.pot_confirmation_notification().amount==10; "
                  "assert 'tkinter' not in sys.modules")
        result = subprocess.run([sys.executable, "-B", "-c", script],
                                cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
