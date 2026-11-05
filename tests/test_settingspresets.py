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
            self.assertEqual(read_preset(path), settings)
            self.assertEqual(json.loads(path.read_text())["name"], "Friday")
            self.assertFalse(Path(str(path) + ".tmp").exists())

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
