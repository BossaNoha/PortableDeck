import tempfile
import unittest
from pathlib import Path
from portable_deck.core.game import Game

class TeamResourceTests(unittest.TestCase):
    def game(self, **options):
        return Game(3, str(Path(__file__).resolve().parents[1] / "decks/demodeck.json"),
                    enable_roles_teams=True, enable_teams=True, team_count=2,
                    player_teams=["team_1", "team_1", "team_2"], enable_chip_accounts=True,
                    score_enabled=True, enable_undo=True, **options)

    def test_shared_chips_and_conservation(self):
        game = self.game(share_team_chips=True)
        self.assertEqual(game.chip_balance(1), 200)
        self.assertTrue(game.play_chips(150)[0])
        game.current_player_index = 1
        self.assertEqual(game.chip_balance(1), 50)
        self.assertFalse(game.play_chips(51)[0])
        game.buy_chips(1, 10)
        self.assertEqual(game.chip_balance(0), 60)
        game.request_pot_withdrawal(1)
        self.assertEqual(game.chip_balance(0), 210)
        self.assertEqual(sum(game.chip_balances) + game.chip_pot, 310)

    def test_shared_score_and_separate_team_score(self):
        game = self.game(share_team_score=True, enable_team_score=True)
        game.request_point()
        self.assertEqual(game.scores, [1, 1, 0])
        self.assertEqual(game.team_scores["team_1"], 1)
        other = self.game(enable_team_score=True)
        other.request_point()
        self.assertEqual(other.scores, [1, 0, 0])
        self.assertEqual(other.team_scores["team_1"], 1)

    def test_undo_save_load_and_restart(self):
        game = self.game(share_team_chips=True, share_team_score=True, enable_team_score=True)
        state = game.capture_undo_state()
        game.undo_stack.append(state)
        game.play_chips(10)
        game.request_point()
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as directory:
            path = str(Path(directory) / "save.json")
            game.save_session(path)
            loaded = Game.load_session(path)
            self.assertEqual(loaded.chip_balance(1), 190)
            self.assertEqual(loaded.team_scores["team_1"], 1)
            self.assertEqual(loaded.restart(keep_scores=True).team_scores, loaded.team_scores)
            self.assertTrue(loaded.undo_last_action())
            self.assertEqual(loaded.capture_undo_state(), state)
