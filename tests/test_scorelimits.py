import unittest
import tempfile
from pathlib import Path
from portable_deck.core.game import Game

class ScoreLimitTests(unittest.TestCase):
    def game(self):
        return Game(2, str(Path(__file__).resolve().parents[1] / "decks/demodeck.json"),
                    score_enabled=True, enable_target_score=True, target_score=10,
                    enable_score_warning=True, score_warning=7)

    def test_threshold_and_once_per_viewer(self):
        g = self.game()
        g.scores[1] = 6
        self.assertEqual(g.turn_score_alerts(), [])
        g.scores[1] = 7
        self.assertEqual(len(g.turn_score_alerts()), 1)
        self.assertEqual(g.turn_score_alerts(), [])
        g.finish_turn()
        self.assertEqual(g.turn_score_alerts(), [])
        g.finish_turn()
        g.scores[1] = 10
        self.assertIn("target score", g.turn_score_alerts()[0])
        self.assertEqual(g.turn_score_alerts(), [])
        g.scores[1] = 0
        g.turn_score_alerts()
        g.scores[1] = 8
        self.assertEqual(len(g.turn_score_alerts()), 1)

    def test_shared_team_does_not_warn_its_own_members(self):
        g = Game(3, str(Path(__file__).resolve().parents[1] / "decks/demodeck.json"),
                 score_enabled=True, enable_target_score=True, target_score=10,
                 enable_score_warning=True, score_warning=7,
                 enable_roles_teams=True, enable_teams=True, team_count=2,
                 player_teams=["team_1", "team_1", "team_2"], share_team_score=True,
                 enable_team_score=True)
        g.scores = [7, 7, 0]
        g.team_scores["team_1"] = 7
        self.assertEqual(g.turn_score_alerts(), [])
        g.finish_turn()
        self.assertEqual(g.turn_score_alerts(), [])
        g.finish_turn()
        self.assertTrue(g.turn_score_alerts())
        self.assertEqual(g.turn_score_alerts(), [])

    def test_persistence_and_disabled(self):
        g = self.game()
        g.scores[0] = 8
        g.turn_score_alerts()
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as folder:
            path = str(Path(folder) / "save.json")
            g.save_session(path)
            loaded = Game.load_session(path)
            self.assertEqual(loaded.turn_score_alerts(), [])
            self.assertEqual(loaded.restart().target_score, 10)
        g.enable_target_score = False
        self.assertEqual(g.turn_score_alerts(), [])
