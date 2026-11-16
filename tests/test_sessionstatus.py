import subprocess
import sys
import unittest
from dataclasses import FrozenInstanceError, asdict
from pathlib import Path
from portable_deck.core.game import Game
from portable_deck.core.sessionstatus import build_session_status


class SessionStatusTests(unittest.TestCase):
    def game(self, **options):
        return Game(3, str(Path(__file__).resolve().parents[1] / 'decks/demodeck.json'), **options)

    def test_disabled_resources_are_distinct_from_zero(self):
        g = self.game(enable_table=False, enable_discard_pile=False)
        status = build_session_status(g)
        self.assertIsNone(status.table_count)
        self.assertIsNone(status.discard_piles)
        self.assertIsNone(status.chip_pot)
        self.assertEqual(status.chip_accounts, ())
        self.assertIsNone(status.players[0].score)
        self.assertIsNone(status.players[0].chips)
        g = self.game(score_enabled=True, enable_chip_accounts=True, starting_balance=0)
        status = build_session_status(g)
        self.assertEqual(status.players[0].score, 0)
        self.assertEqual(status.players[0].chips, 0)
        self.assertEqual(status.chip_pot, 0)
        self.assertEqual(status.table_count, 0)

    def test_counts_include_each_enabled_area_without_card_identities(self):
        g = self.game(enable_personal_piles=True, personal_discard_pile_count=1)
        g.players[0].hand = ['PRIVATE HAND'] * 9
        g.table_cards = [{'card': 'SECRET TABLE', 'player': 'Player1'}]
        g.personal_piles[1][0] = ['A', 'B']
        g.discard_piles[0] = ['C']
        g.personal_discard_piles[0][0] = ['D', 'E']
        status = build_session_status(g)
        self.assertEqual(status.players[0].card_count, 9)
        self.assertEqual(status.draw_count, len(g.deck.flat_deck))
        self.assertEqual(status.table_count, 3)
        self.assertEqual(status.discard_piles[0].card_count, 1)
        self.assertEqual(status.discard_piles[1].card_count, 2)
        self.assertEqual(status.discard_piles[1].owner, 0)
        self.assertNotIn('PRIVATE HAND', repr(status))
        self.assertNotIn('SECRET TABLE', repr(status))

    def test_shared_accounts_team_scores_and_dealer(self):
        g = self.game(player_names=['Alice', 'Bob', 'Carol'], score_enabled=True,
            enable_chip_accounts=True, starting_balance=10, enable_roles_teams=True,
            enable_teams=True, enable_dealer=True, team_count=2, team_names=['Red'],
            player_teams=['team_1', 'team_1', None], dealer_players=[False, False, True],
            share_team_chips=True, share_team_score=True, enable_team_score=True)
        g.award_point(0)
        status = build_session_status(g)
        alice, bob, carol = status.players
        self.assertEqual(alice.chip_account, bob.chip_account)
        self.assertEqual(alice.chips, 20)
        self.assertEqual(alice.score_owner, bob.score_owner)
        self.assertEqual((alice.score, bob.score, alice.team_score), (1, 1, 1))
        self.assertTrue(carol.dealer)
        self.assertEqual(carol.score_owner, 'player:2')
        self.assertEqual(len(status.chip_accounts), 2)
        self.assertEqual(sum(account.balance for account in status.chip_accounts), 30)
        self.assertEqual(status.chip_accounts[0].members, (0, 1))
        self.assertEqual(status.chip_accounts[0].owner_name, 'Red')
        self.assertTrue(status.chip_accounts[0].shared)
        self.assertEqual(status.teams[0].members, (2,))
        self.assertTrue(status.teams[0].dealer)
        self.assertEqual(status.teams[1].score, 1)

    def test_same_team_can_have_individual_resources(self):
        g = self.game(score_enabled=True, enable_chip_accounts=True,
            enable_roles_teams=True, enable_teams=True, team_count=1,
            player_teams=['team_1', 'team_1', None])
        status = build_session_status(g)
        self.assertNotEqual(status.players[0].chip_account, status.players[1].chip_account)
        self.assertNotEqual(status.players[0].score_owner, status.players[1].score_owner)
        self.assertFalse(any(account.shared for account in status.chip_accounts))
        self.assertIsNone(status.players[0].team_score)

    def test_departed_and_current_players(self):
        g = self.game()
        g.left_players = [0]
        g.current_player_index = 1
        status = build_session_status(g)
        self.assertFalse(status.players[0].active)
        self.assertFalse(status.players[0].is_current)
        self.assertTrue(status.players[1].is_current)
        g.left_players = [0, 1, 2]
        self.assertFalse(any(player.is_current for player in build_session_status(g).players))

    def test_snapshot_is_read_only_and_independent(self):
        g = self.game(enable_chip_accounts=True)
        before = g.capture_undo_state()
        status = build_session_status(g)
        self.assertEqual(before, g.capture_undo_state())
        data = asdict(status)
        g.players[0].hand.append('A')
        g.buy_chips(0, 1)
        self.assertEqual(asdict(status), data)
        self.assertNotEqual(build_session_status(g), status)
        with self.assertRaises(FrozenInstanceError):
            status.draw_count = 0

    def test_core_status_works_without_tkinter(self):
        script = "from portable_deck.core.game import Game; from portable_deck.core.sessionstatus import build_session_status; from dataclasses import asdict; import json,sys; g=Game(2,'decks/demodeck.json'); print(json.dumps(asdict(build_session_status(g)))); assert 'tkinter' not in sys.modules"
        result = subprocess.run([sys.executable, '-B', '-c', script], cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('card_count', result.stdout)
