from pathlib import Path
import tempfile
import unittest

from portable_deck.core.game import Game


class RolesTeamsTests(unittest.TestCase):
    def game(self, **kwargs):
        return Game(3, str(Path(__file__).resolve().parents[1] / "decks/demodeck.json"), **kwargs)

    def test_dealer_only_and_no_special_privileges(self):
        game = self.game(enable_roles_teams=True, enable_dealer=True,
                         player_teams=["dealer", None, None])
        self.assertEqual(game.teams, [{"id": "dealer", "name": "Dealer"}])
        self.assertTrue(game.player_is_dealer(0))
        self.assertFalse(game.player_is_dealer(1))
        self.assertIsNone(game.player_team_name(0))
        self.assertIsNotNone(game.deal_card_to_current())
        game.current_player_index = 1
        self.assertIsNotNone(game.deal_card_to_current())

    def test_total_team_limit_includes_dealer(self):
        game = self.game(enable_roles_teams=True, enable_teams=True, enable_dealer=True,
                         team_count=3, team_names=["Red", "Blue"],
                         player_teams=["team_1", "team_2", "dealer"])
        self.assertEqual([team["name"] for team in game.teams], ["Dealer", "Red", "Blue"])
        with self.assertRaises(ValueError):
            self.game(enable_dealer=True, enable_teams=True, team_count=4)
        with self.assertRaises(ValueError):
            self.game(enable_dealer=True, player_teams=["team_1", None, None])

    def test_dealer_can_also_belong_to_regular_team(self):
        game = self.game(enable_roles_teams=True, enable_teams=True, enable_dealer=True,
                         team_count=3, team_names=["Red", "Blue"],
                         player_teams=["team_1", "team_2", None], dealer_players=[True, False, False])
        self.assertEqual(game.teams[0]["id"], "dealer")
        self.assertTrue(game.player_is_dealer(0))
        self.assertEqual(game.player_team_name(0), "Red")
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as directory:
            path = str(Path(directory) / "save.json")
            game.save_session(path)
            loaded = Game.load_session(path)
            restarted = loaded.restart()
            for instance in (loaded, restarted):
                self.assertTrue(instance.player_is_dealer(0))
                self.assertEqual(instance.player_team_name(0), "Red")
                self.assertEqual(instance.teams[0]["id"], "dealer")

    def test_save_load_restart_and_disabled_roles(self):
        game = self.game(enable_roles_teams=True, enable_teams=True, enable_dealer=True,
                         team_count=2, team_names=["Red"], player_teams=["team_1", "team_1", "dealer"])
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as directory:
            path = str(Path(directory) / "save.json")
            game.save_session(path)
            loaded = Game.load_session(path)
            self.assertEqual(loaded.teams, game.teams)
            self.assertEqual(loaded.player_teams, game.player_teams)
            restarted = loaded.restart()
            self.assertEqual(restarted.player_teams, game.player_teams)
            self.assertTrue(restarted.player_is_dealer(2))
            loaded.enable_roles_teams = False
            self.assertIsNone(loaded.player_team_name(0))
            self.assertFalse(loaded.player_is_dealer(2))


if __name__ == "__main__":
    unittest.main()
