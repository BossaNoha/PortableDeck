import unittest
import tempfile
from pathlib import Path
from portable_deck.core.game import Game

class CardsVisibilityTests(unittest.TestCase):
    def game(self, **kwargs):
        return Game(3, str(Path(__file__).resolve().parents[1] / "decks/demodeck.json"), **kwargs)

    def test_default_private_hands(self):
        game = self.game()
        for viewer in range(3):
            for owner in range(3):
                self.assertEqual(game.can_view_hand(viewer, owner), viewer == owner)

    def test_directional_player_team_and_dealer_permissions(self):
        game = self.game(enable_cards_visibility=True, enable_roles_teams=True, enable_teams=True,
                         enable_dealer=True, team_count=2, player_teams=["team_1", "team_1", None],
                         dealer_players=[False, False, True], cards_visibility=[
                             {"players": [0], "teams": ["dealer"]},
                             {"players": [], "teams": ["team_1"]},
                             {"players": [0], "teams": []}])
        self.assertTrue(game.can_view_hand(2, 0))
        self.assertFalse(game.can_view_hand(1, 0))
        self.assertTrue(game.can_view_hand(0, 1))
        self.assertTrue(game.can_view_hand(1, 1))
        self.assertTrue(game.can_view_hand(0, 2))
        self.assertFalse(game.can_view_hand(2, 2))
        game.players[1].hand = ["A of Test"]
        self.assertIsNone(game.visible_hand(2, 1))
        visible = game.visible_hand(0, 1)
        visible.clear()
        self.assertEqual(game.players[1].hand, ["A of Test"])
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as folder:
            path = str(Path(folder) / "session.json")
            game.save_session(path)
            loaded = Game.load_session(path)
            self.assertTrue(loaded.can_view_hand(2, 0))
            self.assertEqual(loaded.restart().cards_visibility, game.cards_visibility)
