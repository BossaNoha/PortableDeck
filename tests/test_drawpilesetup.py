import json
import subprocess
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from unittest.mock import patch

from portable_deck.app.newgame import create_game
from portable_deck.app.settingspresets import load_preset, save_preset
from portable_deck.app.sessionstorage import load_session, save_session
from portable_deck.core.deck import Deck
from portable_deck.core.game import Game
from portable_deck.core.settingsvalidation import SettingsValidationError, validate_settings


class DrawPileSetupTests(unittest.TestCase):
    def setup_data(self):
        return [{"id": "reserve", "name": "Reserve", "owner": None, "count": 3},
                {"id": "player-2", "name": "Player deck", "owner": 1, "count": 2}]

    def game(self, **kwargs):
        deck = Deck.from_definition({"types": ["Test"], "cards": [list(range(1, 13))]})
        return Game(2, deck, enable_undo=True, enable_draw_pile_setup=True,
                    draw_pile_setup=kwargs.pop("draw_pile_setup", self.setup_data()), **kwargs)

    def test_split_preserves_every_card_exactly_once_after_initial_hands(self):
        game = self.game()
        with patch.object(game.deck, "shuffle"):
            game.start(1)
        self.assertEqual([p.hand for p in game.players], [["1 of Test"], ["2 of Test"]])
        self.assertEqual(game.draw_piles.get("reserve").cards, ["3 of Test", "4 of Test", "5 of Test"])
        self.assertEqual(game.draw_piles.get("player-2").cards, ["6 of Test", "7 of Test"])
        self.assertEqual(game.deck.flat_deck, [f"{i} of Test" for i in range(8, 13)])
        cards = [card for player in game.players for card in player.hand]
        for pile in game.draw_piles.view(): cards.extend(game.draw_piles.get(pile.id).cards)
        self.assertEqual(Counter(cards), Counter(game.deck.definition.expanded_cards()))
        self.assertIs(game.draw_piles.get(), game.deck.draw_pile)

    def test_capacity_failure_happens_before_shuffle_or_dealing(self):
        game = self.game()
        before = game.capture_undo_state()
        with patch.object(game.deck, "shuffle") as shuffle:
            with self.assertRaises(ValueError): game.start(4)
        shuffle.assert_not_called()
        self.assertEqual(game.capture_undo_state(), before)

    def test_disabled_and_zero_count_setup(self):
        game = self.game()
        game.enable_draw_pile_setup = False
        game.start(1)
        self.assertEqual(len(game.draw_piles.view()), 1)
        self.assertEqual(len(game.deck.flat_deck), 10)
        game = self.game(draw_pile_setup=[{"id": "empty", "name": "Empty", "owner": 0, "count": 0}])
        game.start(0)
        self.assertFalse(game.draw_piles.get("empty").cards)
        self.assertEqual(len(game.deck.flat_deck), 12)

    def test_bad_setup_fields_and_duplicates_are_rejected(self):
        bad = ({}, {"id": "main", "name": "X", "owner": None, "count": 1},
               {"id": "x", "name": "X", "owner": True, "count": 1},
               {"id": "x", "name": "X", "owner": 2, "count": 1},
               {"id": "x", "name": "X", "owner": None, "count": -1},
               {"id": "x", "name": "X", "owner": None, "count": True})
        for entry in bad:
            with self.assertRaises(ValueError): self.game(draw_pile_setup=[entry])
        with self.assertRaises(ValueError): self.game(draw_pile_setup=self.setup_data() * 2)

    def test_settings_validation_accounts_for_setup_capacity_and_error_fields(self):
        values = {"num_players": 2, "cards_per_player": 1, "enable_draw_pile_setup": True,
                  "draw_pile_setup": [{"id": "reserve", "name": "Reserve", "owner": None, "count": 100000}]}
        with self.assertRaises(SettingsValidationError) as error: validate_settings(values)
        self.assertIn("draw_pile_setup", error.exception.fields)
        values["draw_pile_setup"][0]["count"] = 3
        game = create_game(values)
        self.assertEqual(len(game.draw_piles.get("reserve").cards), 3)
        self.assertEqual(values["draw_pile_setup"][0]["count"], 3)

    def test_save_load_undo_and_restart_repopulate_configured_piles(self):
        game = self.game()
        game.start(1)
        initial_main_count = len(game.deck.flat_deck)
        game.session.execute("draw_card", draw_pile_id="reserve")
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "game.json"
            save_session(game, path)
            loaded = load_session(Game, path)
        self.assertEqual(loaded.capture_undo_state(), game.capture_undo_state())
        self.assertEqual(loaded.draw_pile_setup, self.setup_data())
        self.assertTrue(loaded.session.undo())
        self.assertEqual(len(loaded.draw_piles.get("reserve").cards), 3)
        loaded.draw_piles.add("runtime", "Runtime", [loaded.deck.draw_card()])
        restarted = loaded.restart()
        self.assertEqual(len(restarted.draw_piles.get("reserve").cards), 3)
        self.assertEqual(len(restarted.draw_piles.get("player-2").cards), 2)
        self.assertFalse(restarted.draw_piles.get("runtime").cards)
        self.assertEqual(len(restarted.deck.flat_deck), initial_main_count)

    def test_presets_and_legacy_saves_preserve_or_default_setup(self):
        values = {"num_players": 2, "cards_per_player": 1, "enable_draw_pile_setup": True, "draw_pile_setup": self.setup_data()}
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "preset.json"
            saved = save_preset(path, values)
            settings = load_preset(path, saved).settings
        self.assertEqual(settings["draw_pile_setup"], self.setup_data())
        self.assertTrue(settings["enable_draw_pile_setup"])
        game = create_game(settings)
        from portable_deck.core.gamesession import export_session, restore_session
        state = export_session(game)
        del state["enable_draw_pile_setup"]
        del state["draw_pile_setup"]
        legacy = restore_session(Game, state)
        self.assertFalse(legacy.enable_draw_pile_setup)
        self.assertEqual(legacy.draw_pile_setup, [])

    def test_cli_repeated_flags_configure_shared_and_personal_piles_without_tk(self):
        script = ("import sys; from portable_deck.cli import main; "
                  "main(['--players','2','--hand','1','--draw-pile','reserve','Reserve','shared','3',"
                  "'--draw-pile','mine','My deck','1','2','--json']); assert 'tkinter' not in sys.modules")
        result = subprocess.run([sys.executable, "-B", "-c", script],
                                input="sources\nsource mine\ndraw\nshow\nquit\n", text=True, capture_output=True,
                                timeout=30, cwd=Path(__file__).resolve().parents[1])
        self.assertEqual(result.returncode, 0, result.stderr)
        records = [json.loads(line) for line in result.stdout.splitlines()]
        piles = next(r["piles"] for r in records if r["type"] == "draw_sources")
        self.assertEqual([(p["id"], p["card_count"]) for p in piles if p["id"] != "main"], [("reserve", 3), ("mine", 2)])
        self.assertTrue(next(r["success"] for r in records if r["type"] == "result"))
