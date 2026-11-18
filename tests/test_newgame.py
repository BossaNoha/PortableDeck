import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from portable_deck.app.newgame import create_game
from portable_deck.app.mainmenu import MainMenu
from portable_deck.core.deck import Deck
from portable_deck.core.game import Game


class NewGameTests(unittest.TestCase):
    def test_creation_loads_and_deals_once_without_changing_inputs(self):
        values = {"num_players": 2, "cards_per_player": 3, "enable_undo": True,
                  "enable_interactions": True, "interaction_options": {"give_card": True}}
        before = copy.deepcopy(values)
        with patch.object(Deck, "load", autospec=True, side_effect=Deck.load) as load, patch.object(
                Game, "start", autospec=True, side_effect=Game.start) as start:
            game = create_game(values)
        load.assert_called_once()
        start.assert_called_once_with(game, 3)
        self.assertEqual([len(p.hand) for p in game.players], [3, 3])
        self.assertEqual(len(game.deck.flat_deck), 46)
        self.assertEqual(game.game_log, ["Player1's turn starts."])
        self.assertEqual(game.undo_stack, [])
        self.assertEqual(values, before)
        game.interaction_options["give_card"] = False
        self.assertEqual(values, before)

    def test_custom_names_rules_and_configuration_metadata(self):
        game = create_game({"num_players": 2, "cards_per_player": 0,
                            "use_custom_player_names": True, "player_names": ["Alice", "Bob"],
                            "enable_score_counter": True, "enable_chip_accounts": True,
                            "enable_roles_teams": True, "enable_teams": True, "team_count": 1,
                            "player_teams": ["team_1", "team_1"], "share_team_chips": True,
                            "starting_balance": 12, "enable_personal_piles": True,
                            "personal_pile_count": 2, "configuration_name": "Friday"})
        self.assertEqual([p.name for p in game.players], ["Alice", "Bob"])
        self.assertTrue(game.score_enabled)
        self.assertEqual(game.chip_balance(1), 24)
        self.assertEqual(game.personal_pile_counts, [2, 2])
        self.assertEqual(game.configuration_info["name"], "Friday")
        self.assertEqual(game.game_log, ["Alice's turn starts."])
        default_names = create_game({"num_players": 2, "cards_per_player": 0,
                                     "player_names": ["Ignored", "Ignored"]})
        self.assertEqual([p.name for p in default_names.players], ["Player1", "Player2"])

    def test_insufficient_deck_and_invalid_settings_do_not_start_game(self):
        with tempfile.TemporaryDirectory() as folder:
            deck = Path(folder) / "tiny.json"
            deck.write_text(json.dumps({"types": ["Test"], "cards": [["A"]]}))
            for settings in ({"num_players": 2, "cards_per_player": 1, "deck_path": str(deck)},
                             {"num_players": 0}, {"num_players": "2"}):
                with self.subTest(settings=settings), patch.object(Game, "start") as start:
                    with self.assertRaises(ValueError):
                        create_game(settings)
                    start.assert_not_called()

    def test_menu_delegates_and_only_changes_screen_after_success(self):
        menu = SimpleNamespace(settings={"num_players": 2}, root=None,
                               clear_window=Mock(), show_game=Mock())
        game = object()
        with patch("portable_deck.app.mainmenu.create_game", return_value=game) as create:
            MainMenu.play(menu)
        create.assert_called_once_with(menu.settings)
        menu.show_game.assert_called_once_with(game)
        menu.clear_window.reset_mock()
        menu.show_game.reset_mock()
        with patch("portable_deck.app.mainmenu.create_game", side_effect=ValueError("Invalid")), patch(
                "portable_deck.app.mainmenu.messagebox.showerror") as error:
            MainMenu.play(menu)
        error.assert_called_once()
        menu.clear_window.assert_not_called()
        menu.show_game.assert_not_called()

    def test_service_starts_from_another_directory_without_tkinter(self):
        repo = str(Path(__file__).resolve().parents[1])
        script = ("import sys; sys.path.insert(0,sys.argv[1]); "
                  "from portable_deck.app.newgame import create_game; "
                  "g=create_game({'num_players':2,'cards_per_player':1}); "
                  "assert len(g.players[0].hand)==1; assert 'tkinter' not in sys.modules")
        with tempfile.TemporaryDirectory() as folder:
            result = subprocess.run([sys.executable, "-B", "-c", script, repo], cwd=folder,
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(list(Path(folder).iterdir()), [])
