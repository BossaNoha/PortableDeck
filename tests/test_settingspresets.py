import copy
import json
from pathlib import Path
import tempfile
import unittest
from portable_deck.app.settings import DEFAULT_SETTINGS
from portable_deck.app.settingspresets import read_preset, write_preset

class SettingsPresetTests(unittest.TestCase):
    def test_named_configuration_round_trip_with_names(self):
        settings = copy.deepcopy(DEFAULT_SETTINGS)
        settings.update(num_players=2, use_custom_player_names=True, player_names=["Alice", "Bob"],
                        enable_roles_teams=True, enable_teams=True, team_count=1,
                        team_names=["Red"], player_teams=["team_1", "team_1"],
                        enable_interactions=True, interaction_options={"give_card": True})
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as folder:
            path = Path(folder) / "Friday.json"
            write_preset(path, settings)
            from portable_deck.app.configurationinfo import configuration_values, configuration_info
            loaded = read_preset(path, settings)
            self.assertEqual(configuration_values(loaded), configuration_values(settings))
            self.assertEqual(configuration_info(loaded), {"name": "Friday", "modified": False})
            loaded["cards_per_player"] += 1
            self.assertTrue(configuration_info(loaded)["modified"])
            self.assertEqual(json.loads(path.read_text())["name"], "Friday")
            self.assertFalse(Path(str(path) + ".tmp").exists())

    def test_application_settings_and_player_count_are_not_rules(self):
        from portable_deck.app.configurationinfo import APP_SETTINGS, configuration_info
        settings = copy.deepcopy(DEFAULT_SETTINGS)
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as folder:
            path = Path(folder) / "Rules.json"
            write_preset(path, settings)
            stored = json.loads(path.read_text())["settings"]
            self.assertFalse(APP_SETTINGS.intersection(stored))
            current = {**settings, "num_players": 4, "autosave_enabled": False,
                       "autosave_count": 12, "require_exit_confirmation": False, "enable_undo": True}
            loaded = read_preset(path, current)
            for key in APP_SETTINGS:
                self.assertEqual(loaded[key], current[key])
            self.assertFalse(configuration_info(loaded)["modified"])
            loaded.update(num_players=5, autosave_count=20, enable_undo=False)
            self.assertFalse(configuration_info(loaded)["modified"])
            loaded["cards_per_player"] += 1
            self.assertTrue(configuration_info(loaded)["modified"])

    def test_invalid_file_does_not_replace_existing_preset(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as folder:
            path = Path(folder) / "preset.json"
            write_preset(path, DEFAULT_SETTINGS)
            original = path.read_bytes()
            with self.assertRaises(ValueError):
                write_preset(path, {"num_players": -1})
            self.assertEqual(path.read_bytes(), original)
            path.write_text("[]")
            with self.assertRaises(ValueError):
                read_preset(path)
