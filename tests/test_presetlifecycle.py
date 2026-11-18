import copy
import json
import tempfile
import unittest
from pathlib import Path

from portable_deck.app.configurationinfo import configuration_info
from portable_deck.app.newgame import create_game
from portable_deck.app.settings import DEFAULT_SETTINGS
from portable_deck.app.settingspresets import load_preset, save_preset


class PresetLifecycleTests(unittest.TestCase):
    def test_saved_legacy_preset_current_preferences_and_new_game_metadata(self):
        settings = copy.deepcopy(DEFAULT_SETTINGS)
        settings.update(num_players=2, cards_per_player=2, enable_score_counter=True,
                        enable_undo=True, autosave_count=12)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "Friday.json"
            saved = save_preset(path, settings)
            self.assertEqual(configuration_info(saved), {"name": "Friday", "modified": False})
            current = copy.deepcopy(saved)
            current.update(num_players=4, cards_per_player=1, enable_score_counter=False,
                           enable_undo=False, autosave_count=7)
            before = copy.deepcopy(current)
            loaded = load_preset(path, current)
            self.assertEqual(loaded.notices, ())
            self.assertEqual(loaded.settings["num_players"], 4)
            self.assertEqual(loaded.settings["autosave_count"], 7)
            self.assertFalse(loaded.settings["enable_undo"])
            self.assertEqual(loaded.settings["cards_per_player"], 2)
            self.assertTrue(loaded.settings["enable_score_counter"])
            legacy = json.loads(path.read_text(encoding="utf-8"))
            del legacy["settings"]["enable_table"]
            legacy["settings"]["future_rule"] = True
            path.write_text(json.dumps(legacy), encoding="utf-8")
            loaded = load_preset(path, current)
            self.assertTrue(loaded.notices)
            self.assertIn("enable_table", loaded.compatibility.missing)
            self.assertIn("future_rule", loaded.compatibility.unknown)
            self.assertEqual(current, before)
            game = create_game(loaded.settings)
            self.assertEqual([len(player.hand) for player in game.players], [2] * 4)
            self.assertTrue(game.score_enabled)
            self.assertFalse(game.enable_undo)
            self.assertEqual(game.configuration_info, {"name": "Friday", "modified": False})
            loaded.settings["cards_per_player"] = 3
            changed = create_game(loaded.settings)
            self.assertEqual([len(player.hand) for player in changed.players], [3] * 4)
            self.assertEqual(changed.configuration_info, {"name": "Friday", "modified": True})
