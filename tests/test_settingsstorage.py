import json
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from portable_deck.app import settings


class SettingsStorageTests(unittest.TestCase):
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
