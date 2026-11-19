import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from portable_deck.app.settings import DEFAULT_SETTINGS
from portable_deck.app.settingsapplication import SettingsWriteError, apply_settings, prepare_settings, restore_default_settings
from portable_deck.app.settingswindow import SettingsWindow


class SettingsApplicationTests(unittest.TestCase):
    def test_restore_validates_and_persists_saved_defaults_with_their_metadata(self):
        defaults = copy.deepcopy(DEFAULT_SETTINGS)
        defaults.update(num_players=2, cards_per_player=2, configuration_name="Default",
                        configuration_baseline={"cards_per_player": 2})
        before = copy.deepcopy(defaults)
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "defaults.json"
            target = Path(folder) / "settings.json"
            source.write_text(json.dumps(defaults), encoding="utf-8")
            with patch("portable_deck.app.settings.DEFAULT_CONFIG_PATH", str(source)), patch(
                    "portable_deck.app.settings.CONFIG_PATH", str(target)), patch(
                    "portable_deck.app.settings.CONFIG_DIR", folder):
                restored = restore_default_settings()
            self.assertEqual(restored["cards_per_player"], 2)
            self.assertEqual(restored["configuration_name"], "Default")
            self.assertEqual(json.loads(target.read_text(encoding="utf-8")), restored)
            restored["configuration_baseline"]["cards_per_player"] = 9
            self.assertEqual(json.loads(source.read_text(encoding="utf-8")), before)

    def test_restore_preserves_missing_default_fallback_and_rejects_invalid_defaults(self):
        with tempfile.TemporaryDirectory() as folder, patch(
                "portable_deck.app.settings.DEFAULT_CONFIG_PATH", str(Path(folder) / "missing.json")), patch(
                "portable_deck.app.settingsapplication.save_settings") as save:
            restored = restore_default_settings()
            self.assertEqual(restored, prepare_settings(DEFAULT_SETTINGS, DEFAULT_SETTINGS))
            save.assert_called_once_with(restored)
        with patch("portable_deck.app.settingsapplication.load_default_settings", return_value={"num_players": 0}), patch(
                "portable_deck.app.settingsapplication.save_settings") as save:
            with self.assertRaises(ValueError):
                restore_default_settings()
            save.assert_not_called()

    def test_gui_restore_cancellation_and_errors_preserve_form_and_active_settings(self):
        for failure in (None, OSError("Read failed"), SettingsWriteError("Write failed"), ValueError("Invalid defaults")):
            with self.subTest(failure=failure):
                menu = SimpleNamespace(root=None, settings=self.current())
                window = SettingsWindow(menu)
                window.form_settings = {**self.current(), "cards_per_player": 8}
                before_form = copy.deepcopy(window.form_settings)
                window.show_settings = Mock()
                with patch("portable_deck.app.settingswindow.messagebox.askyesno", return_value=failure is not None), patch(
                        "portable_deck.app.settingswindow.restore_default_settings", side_effect=failure) as restore, patch(
                        "portable_deck.app.settingswindow.messagebox.showerror") as error:
                    window.restore_defaults()
                self.assertEqual(window.form_settings, before_form)
                self.assertEqual(menu.settings, self.current())
                window.show_settings.assert_not_called()
                self.assertEqual(error.call_count, int(failure is not None))
                if failure is None:
                    restore.assert_not_called()

    def test_gui_restore_commits_only_after_successful_service_call(self):
        menu = SimpleNamespace(root=None, settings=self.current())
        window = SettingsWindow(menu)
        window.form_settings = {**self.current(), "cards_per_player": 8}
        window.show_settings = Mock()
        restored = copy.deepcopy(DEFAULT_SETTINGS)
        def restore():
            self.assertEqual(menu.settings, self.current())
            self.assertEqual(window.form_settings["cards_per_player"], 8)
            return restored
        with patch("portable_deck.app.settingswindow.messagebox.askyesno", return_value=True), patch(
                "portable_deck.app.settingswindow.restore_default_settings", side_effect=restore):
            window.restore_defaults()
        self.assertIs(menu.settings, restored)
        self.assertIsNone(window.form_settings)
        window.show_settings.assert_called_once()

    def current(self):
        current = copy.deepcopy(DEFAULT_SETTINGS)
        current.update(configuration_name="Friday", configuration_baseline={"cards_per_player": 2})
        return current

    def test_apply_validates_copies_metadata_and_persists_without_starting_game(self):
        values = {"num_players": 2, "cards_per_player": 3, "enable_undo": True}
        current = self.current()
        before = copy.deepcopy(current)
        with tempfile.TemporaryDirectory() as folder, patch(
                "portable_deck.app.settings.CONFIG_DIR", folder), patch(
                "portable_deck.app.settings.CONFIG_PATH", str(Path(folder) / "settings.json")), patch(
                "portable_deck.core.game.Game.start", side_effect=AssertionError("Settings started a game")):
            prepared = prepare_settings(values, current)
            self.assertEqual(list(Path(folder).iterdir()), [])
            result = apply_settings(values, current)
            self.assertEqual(result, prepared)
            self.assertEqual(json.loads((Path(folder) / "settings.json").read_text()), result)
        self.assertEqual(result["configuration_name"], "Friday")
        result["configuration_baseline"]["cards_per_player"] = 9
        self.assertEqual(current, before)
        self.assertEqual(values, {"num_players": 2, "cards_per_player": 3, "enable_undo": True})

    def test_validation_and_write_failure_leave_inputs_unchanged(self):
        current = self.current()
        before = copy.deepcopy(current)
        with patch("portable_deck.app.settingsapplication.save_settings") as save:
            with self.assertRaises(ValueError):
                apply_settings({"num_players": 0}, current)
            save.assert_not_called()
        with patch("portable_deck.app.settingsapplication.save_settings", side_effect=OSError("Denied")):
            with self.assertRaises(SettingsWriteError) as error:
                apply_settings({"num_players": 2}, current)
            self.assertEqual(str(error.exception), "Denied")
        self.assertEqual(current, before)

    def submit(self, window, mode="use", balance=100):
        var = lambda value: SimpleNamespace(get=lambda: value)
        window.save_form(var("2"), var("3"), var("decks/demodeck.json"), var(False), [],
                         SimpleNamespace(values=lambda: {"starting_balance": balance}),
                         SimpleNamespace(values=lambda: {"enable_undo": True}), mode=mode)

    def test_gui_use_persists_before_updating_menu_while_named_only_prepares(self):
        for mode in ("use", "named"):
            with self.subTest(mode=mode):
                menu = SimpleNamespace(root=None, settings=self.current(), show_main_menu=Mock())
                window = SettingsWindow(menu)
                window.save_named_settings = Mock()
                with patch("portable_deck.app.settingsapplication.save_settings") as save:
                    self.submit(window, mode)
                if mode == "use":
                    save.assert_called_once_with(menu.settings)
                    self.assertEqual(menu.settings["cards_per_player"], 3)
                    menu.show_main_menu.assert_called_once()
                    window.save_named_settings.assert_not_called()
                else:
                    save.assert_not_called()
                    menu.show_main_menu.assert_not_called()
                    prepared = window.save_named_settings.call_args.args[0]
                    self.assertEqual(prepared["configuration_name"], "Friday")
                    self.assertEqual(prepared["cards_per_player"], 3)
                    self.assertEqual(menu.settings, self.current())

    def test_gui_failures_preserve_form_and_menu_with_specific_error_titles(self):
        for validation_error in (False, True):
            with self.subTest(validation_error=validation_error):
                menu = SimpleNamespace(root=None, settings=self.current(), show_main_menu=Mock())
                window = SettingsWindow(menu)
                window.form_settings = self.current()
                before = copy.deepcopy(window.form_settings)
                with patch("portable_deck.app.settingsapplication.save_settings", side_effect=OSError("Denied")) as save, patch(
                        "portable_deck.app.settingswindow.messagebox.showerror") as error:
                    self.submit(window, balance=-1 if validation_error else 100)
                self.assertEqual(error.call_args.args[0], "Invalid settings" if validation_error else "Could not save")
                self.assertEqual(window.form_settings, before)
                self.assertEqual(menu.settings, self.current())
                menu.show_main_menu.assert_not_called()
                if validation_error:
                    save.assert_not_called()

    def test_application_service_works_without_tkinter(self):
        with tempfile.TemporaryDirectory() as folder:
            script = ("import sys; from portable_deck.app import settings; "
                      "from portable_deck.app.settingsapplication import apply_settings; "
                      "settings.CONFIG_DIR=sys.argv[1]; settings.CONFIG_PATH=sys.argv[2]; "
                      "result=apply_settings({'num_players':2},{}); "
                      "assert result['num_players']==2; assert 'tkinter' not in sys.modules")
            result = subprocess.run([sys.executable, "-B", "-c", script, folder,
                                     str(Path(folder) / "settings.json")],
                                    cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
