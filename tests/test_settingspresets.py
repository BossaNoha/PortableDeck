import copy
import json
from pathlib import Path
import tempfile
import unittest
import subprocess
import sys
import warnings
from unittest.mock import Mock, patch
from portable_deck.app.settings import DEFAULT_SETTINGS
from portable_deck.app.settingspresets import load_preset, read_preset, save_preset, write_preset
from portable_deck.app.settingswindow import SettingsWindow

class SettingsPresetTests(unittest.TestCase):
    def test_save_returns_independent_metadata_and_keeps_application_preferences(self):
        from portable_deck.app.configurationinfo import APP_SETTINGS, configuration_info
        settings = copy.deepcopy(DEFAULT_SETTINGS)
        settings.update(num_players=4, autosave_count=12)
        before = copy.deepcopy(settings)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "Friday.json"
            saved = save_preset(path, settings)
            self.assertEqual(configuration_info(saved), {"name": "Friday", "modified": False})
            self.assertEqual(saved["num_players"], 4)
            self.assertEqual(saved["autosave_count"], 12)
            stored = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(stored["name"], "Friday")
            self.assertFalse(APP_SETTINGS.intersection(stored["settings"]))
            self.assertNotIn("configuration_baseline", stored["settings"])
            saved["cards_per_player"] += 1
            self.assertTrue(configuration_info(saved)["modified"])
            saved["interaction_options"]["give_card"] = True
            self.assertEqual(settings, before)

    def test_save_failure_preserves_file_input_and_cleans_temporary_file(self):
        settings = copy.deepcopy(DEFAULT_SETTINGS)
        before = copy.deepcopy(settings)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "Friday.json"
            path.write_bytes(b"previous")
            with patch("portable_deck.app.settingspresets.os.replace", side_effect=OSError("Disk full")):
                with self.assertRaises(OSError):
                    save_preset(path, settings)
            self.assertEqual(path.read_bytes(), b"previous")
            self.assertFalse(Path(str(path) + ".tmp").exists())
            self.assertEqual(settings, before)

    def test_gui_save_uses_returned_metadata_after_success(self):
        from portable_deck.app.configurationinfo import configuration_info
        with tempfile.TemporaryDirectory() as folder:
            path = str(Path(folder) / "Friday.json")
            window = Mock(root=None, form_settings={"previous": True})
            settings = copy.deepcopy(DEFAULT_SETTINGS)
            with patch("portable_deck.app.settingspresets.PRESETS_DIR", folder), patch(
                    "portable_deck.app.settingswindow.filedialog.asksaveasfilename", return_value=path), patch(
                    "portable_deck.app.settingswindow.messagebox.showinfo") as info:
                SettingsWindow.save_named_settings(window, settings)
            self.assertEqual(configuration_info(window.form_settings), {"name": "Friday", "modified": False})
            info.assert_called_once_with("Settings saved", "Saved as Friday.", parent=None)

    def test_canceled_or_failed_gui_save_preserves_form(self):
        with tempfile.TemporaryDirectory() as folder:
            for chosen in ("", str(Path(folder) / "Friday.json")):
                with self.subTest(chosen=chosen):
                    window = Mock(root=None, form_settings={"previous": True})
                    with patch("portable_deck.app.settingspresets.PRESETS_DIR", folder), patch(
                            "portable_deck.app.settingswindow.filedialog.asksaveasfilename", return_value=chosen), patch(
                            "portable_deck.app.settingspresets.os.replace", side_effect=OSError("Disk full")), patch(
                            "portable_deck.app.settingswindow.messagebox.showerror") as error, patch(
                            "portable_deck.app.settingswindow.messagebox.showinfo") as info:
                        SettingsWindow.save_named_settings(window, copy.deepcopy(DEFAULT_SETTINGS))
                    self.assertEqual(window.form_settings, {"previous": True})
                    self.assertEqual(error.call_count, int(bool(chosen)))
                    info.assert_not_called()

    def test_loading_returns_notices_as_data_and_preserves_adapter_behavior(self):
        current = copy.deepcopy(DEFAULT_SETTINGS)
        current.update(num_players=4, autosave_count=12)
        original = copy.deepcopy(current)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "Old.json"
            path.write_text(json.dumps({"settings": {"enable_table": "yes", "future_option": True}}), encoding="utf-8")
            with warnings.catch_warnings(record=True) as emitted:
                warnings.simplefilter("always")
                result = load_preset(path, current)
            self.assertEqual(emitted, [])
            self.assertTrue(result.notices)
            self.assertIn("enable_table", result.compatibility.wrong_types)
            self.assertIn("future_option", result.compatibility.unknown)
            self.assertEqual(result.settings["num_players"], 4)
            self.assertEqual(result.settings["autosave_count"], 12)
            self.assertEqual(result.settings["configuration_name"], "Old")
            callback = Mock()
            self.assertEqual(read_preset(path, current, on_warning=callback), result.settings)
            callback.assert_called_once_with("\n\n".join(result.notices))
            result.settings["interaction_options"]["give_card"] = True
            self.assertEqual(current, original)

    def test_gui_load_applies_service_result_and_displays_notices(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "Old.json"
            path.write_text('{"settings":{"enable_table":"yes"}}', encoding="utf-8")
            window = Mock(root=None, settings=copy.deepcopy(DEFAULT_SETTINGS))
            window.current_app_settings.return_value = {"num_players": 4, "autosave_count": 12}
            with patch("portable_deck.app.settingspresets.PRESETS_DIR", folder), patch(
                    "portable_deck.app.settingswindow.filedialog.askopenfilename", return_value=str(path)), patch(
                    "portable_deck.app.settingswindow.messagebox.showwarning") as warning:
                SettingsWindow.load_named_settings(window)
            self.assertEqual(window.form_settings["num_players"], 4)
            self.assertEqual(window.form_settings["autosave_count"], 12)
            self.assertTrue(window.form_settings["enable_table"])
            self.assertEqual(warning.call_args.args[0], "Preset compatibility")
            window.show_settings.assert_called_once()

    def test_canceled_or_invalid_gui_load_preserves_form(self):
        with tempfile.TemporaryDirectory() as folder:
            invalid = Path(folder) / "invalid.json"
            invalid.write_text("broken", encoding="utf-8")
            for chosen in ("", str(invalid)):
                with self.subTest(chosen=chosen):
                    window = Mock(root=None, settings=copy.deepcopy(DEFAULT_SETTINGS), form_settings={"previous": True})
                    window.current_app_settings.return_value = {}
                    with patch("portable_deck.app.settingspresets.PRESETS_DIR", folder), patch(
                            "portable_deck.app.settingswindow.filedialog.askopenfilename", return_value=chosen), patch(
                            "portable_deck.app.settingswindow.messagebox.showwarning") as warning, patch(
                            "portable_deck.app.settingswindow.messagebox.showerror") as error:
                        SettingsWindow.load_named_settings(window)
                    self.assertEqual(window.form_settings, {"previous": True})
                    window.show_settings.assert_not_called()
                    warning.assert_not_called()
                    self.assertEqual(error.call_count, int(bool(chosen)))

    def test_loader_works_without_tkinter_or_warning_side_effects(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "old.json"
            path.write_text('{"settings":{}}', encoding="utf-8")
            script = ("import sys,warnings; from portable_deck.app.settingspresets import load_preset; "
                      "warnings.simplefilter('error'); result=load_preset(sys.argv[1]); "
                      "assert result.notices; assert 'tkinter' not in sys.modules")
            result = subprocess.run([sys.executable, "-B", "-c", script, str(path)],
                                    capture_output=True, text=True, timeout=30,
                                    cwd=Path(__file__).resolve().parents[1])
            self.assertEqual(result.returncode, 0, result.stderr)

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
