import json
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from portable_deck.app import settings


class SettingsStorageTests(unittest.TestCase):
    def test_startup_result_preserves_loaded_settings_when_save_fails(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(settings, "CONFIG_DIR", folder), patch.object(
                settings, "CONFIG_PATH", str(Path(folder) / "settings.json")), patch.object(
                settings, "DEFAULT_CONFIG_PATH", str(Path(folder) / "missing.json")):
            path = Path(settings.CONFIG_PATH)
            original = b'{"num_players": 2, "cards_per_player": 0}\n'
            path.write_bytes(original)
            with patch.object(settings.os, "replace", side_effect=PermissionError("Denied")), patch.object(
                    settings, "save_settings", wraps=settings.save_settings) as save:
                result = settings.load_settings_result()
            self.assertEqual(result.settings["num_players"], 2)
            self.assertEqual(result.settings["cards_per_player"], 0)
            self.assertEqual(result.error, "Denied")
            save.assert_called_once()
            self.assertEqual(path.read_bytes(), original)
            self.assertFalse(Path(str(path) + ".tmp").exists())

    def test_first_start_returns_defaults_even_if_directory_cannot_be_created(self):
        with tempfile.TemporaryDirectory() as folder:
            missing = Path(folder) / "unwritable"
            with patch.object(settings, "CONFIG_DIR", str(missing)), patch.object(
                    settings, "CONFIG_PATH", str(missing / "settings.json")), patch.object(
                    settings, "DEFAULT_CONFIG_PATH", str(Path(folder) / "missing.json")), patch.object(
                    settings.os, "makedirs", side_effect=PermissionError("Denied")):
                result = settings.load_settings_result()
            self.assertEqual(result.settings, settings.DEFAULT_SETTINGS)
            self.assertEqual(result.error, "Denied")
            self.assertFalse(missing.exists())

    def test_main_menu_opens_and_can_start_game_after_settings_write_failure(self):
        from portable_deck.app.mainmenu import MainMenu
        with tempfile.TemporaryDirectory() as folder, patch.object(settings, "CONFIG_DIR", folder), patch.object(
                settings, "CONFIG_PATH", str(Path(folder) / "settings.json")), patch.object(
                settings, "DEFAULT_CONFIG_PATH", str(Path(folder) / "missing.json")):
            path = Path(settings.CONFIG_PATH)
            original = b'{"num_players": 2, "cards_per_player": 0}\n'
            path.write_bytes(original)
            root = Mock()
            with patch("portable_deck.app.mainmenu.SAVES_DIR", str(Path(folder) / "saves")), patch.object(
                    MainMenu, "migrate_discard_data"), patch.object(MainMenu, "show_main_menu") as show, patch.object(
                    settings.os, "replace", side_effect=PermissionError("Denied")), patch(
                    "portable_deck.app.mainmenu.messagebox.showwarning") as warning:
                menu = MainMenu(root)
            show.assert_called_once()
            warning.assert_called_once()
            self.assertIn("Denied", warning.call_args.args[1])
            self.assertEqual(menu.settings["num_players"], 2)
            self.assertEqual(path.read_bytes(), original)
            with patch.object(menu, "clear_window"), patch.object(menu, "show_game") as game:
                menu.play()
            self.assertEqual(len(game.call_args.args[0].players), 2)

    def test_atomic_write_preserves_format_and_leaves_no_temporary_file(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(settings, "CONFIG_DIR", folder), patch.object(
                settings, "CONFIG_PATH", str(Path(folder) / "settings.json")):
            settings.save_settings({"name": "Žaludy", "players": 2})
            path = Path(settings.CONFIG_PATH)
            self.assertEqual(path.read_text(encoding="utf-8"), json.dumps({"name": "Žaludy", "players": 2}, indent=2) + "\n")
            settings.save_settings({"players": 3})
            self.assertEqual(json.loads(path.read_text()), {"players": 3})
            self.assertEqual([entry.name for entry in Path(folder).iterdir()], ["settings.json"])

    def test_partial_write_and_replace_failure_preserve_previous_settings(self):
        real_open = open
        with tempfile.TemporaryDirectory() as folder, patch.object(settings, "CONFIG_DIR", folder), patch.object(
                settings, "CONFIG_PATH", str(Path(folder) / "settings.json")):
            path = Path(settings.CONFIG_PATH)
            previous = b'{"previous": true}\n'
            path.write_bytes(previous)
            @contextmanager
            def interrupted_open(target, mode, **kwargs):
                with real_open(target, mode, **kwargs) as destination:
                    def fail_write(text):
                        destination.write(text[:5])
                        raise OSError("Disk full")
                    yield SimpleNamespace(write=fail_write)
            with patch("portable_deck.app.settings.open", side_effect=interrupted_open):
                with self.assertRaisesRegex(OSError, "Disk full"):
                    settings.save_settings({"new": True})
            self.assertEqual(path.read_bytes(), previous)
            self.assertFalse(Path(str(path) + ".tmp").exists())
            with patch.object(settings.os, "replace", side_effect=PermissionError("Denied")):
                with self.assertRaisesRegex(OSError, "Denied"):
                    settings.save_settings({"new": True})
            self.assertEqual(path.read_bytes(), previous)
            self.assertFalse(Path(str(path) + ".tmp").exists())

    def test_invalid_serialization_does_not_touch_existing_file(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(settings, "CONFIG_DIR", folder), patch.object(
                settings, "CONFIG_PATH", str(Path(folder) / "settings.json")):
            path = Path(settings.CONFIG_PATH)
            path.write_bytes(b"previous")
            with self.assertRaises(TypeError):
                settings.save_settings({"unsupported": object()})
            self.assertEqual(path.read_bytes(), b"previous")
            self.assertEqual(len(list(Path(folder).iterdir())), 1)
