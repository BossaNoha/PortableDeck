import json
import subprocess
import sys
import tempfile
import unittest
from dataclasses import FrozenInstanceError, asdict
from pathlib import Path
from unittest.mock import Mock, patch

from portable_deck.app.sessioncatalog import list_sessions, read_session_metadata
from portable_deck.app.sessionbrowser import SessionBrowser


class SessionCatalogTests(unittest.TestCase):
    def write(self, path):
        path.write_text(json.dumps({"players": [{"name": "Alice", "hand": ["SECRET"]}, {"name": "Bob"}],
                                   "current_player_index": 1,
                                   "configuration_info": {"name": "Friday", "modified": False}}), encoding="utf-8")

    def test_named_catalog_is_sorted_immutable_and_excludes_checkpoint(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            for name in ("z.json", "A.JSON", "last_session.json", "ignore.txt"):
                self.write(base / name)
            (base / "directory.json").mkdir()
            entries = list_sessions(base)
            self.assertEqual([e.filename for e in entries], ["A.JSON", "z.json"])
            entry = entries[0]
            self.assertEqual(entry.player_names, ("Alice", "Bob"))
            self.assertEqual(entry.next_player, "Bob")
            self.assertEqual(entry.configuration, "Friday")
            self.assertIs(entry.modified, False)
            self.assertIsNotNone(entry.saved_at)
            self.assertIsNone(entry.error)
            self.assertNotIn("SECRET", json.dumps(asdict(entry)))
            with self.assertRaises(FrozenInstanceError):
                entry.next_player = "changed"

    def test_autosave_catalog_includes_latest_even_without_archive_directory(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            latest = base / "last_session.json"
            self.write(latest)
            self.assertEqual([e.path for e in list_sessions(base, "autosaves")], [str(latest)])
            self.assertFalse((base / "autosaves").exists())
            (base / "autosaves").mkdir()
            self.write(base / "autosaves" / "autosave_1.json")
            self.assertEqual([e.filename for e in list_sessions(base, "autosaves")],
                             ["last_session.json", "autosave_1.json"])

    def test_missing_directories_are_empty_and_not_created(self):
        with tempfile.TemporaryDirectory() as folder:
            missing = Path(folder) / "missing"
            self.assertEqual(list_sessions(missing), ())
            self.assertEqual(list_sessions(missing, "autosaves"), ())
            self.assertFalse(missing.exists())
            with self.assertRaises(ValueError):
                list_sessions(missing, "invalid")

    def test_corrupt_files_do_not_hide_healthy_rows(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            self.write(base / "healthy.json")
            for i, content in enumerate(("{", "[]", '{"players": [1]}',
                                         '{"players": [{"name": null}]}',
                                         '{"configuration_info": []}', '{"current_player_index": "bad"}')):
                (base / f"bad{i}.json").write_text(content)
            (base / "bad_utf8.json").write_bytes(b'\xff')
            entries = list_sessions(base)
            self.assertEqual(len(entries), 8)
            self.assertEqual(sum(entry.error is None for entry in entries), 1)
            self.assertTrue(all(entry.player_names == () for entry in entries if entry.error))

    def test_read_errors_and_directory_errors_are_distinguished(self):
        with tempfile.TemporaryDirectory() as folder:
            missing = Path(folder) / "missing.json"
            entry = read_session_metadata(missing)
            self.assertTrue(entry.error)
            self.assertIsNone(entry.saved_at)
            with patch("portable_deck.app.sessioncatalog.Path.iterdir", side_effect=PermissionError("Denied")):
                with self.assertRaises(PermissionError):
                    list_sessions(folder)

    def test_browser_renders_catalog_and_service_works_without_tkinter(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "session.json"
            self.write(path)
            before = path.read_bytes()
            browser = object.__new__(SessionBrowser)
            browser.tree = Mock()
            browser.tree.get_children.return_value = []
            browser.base_saves_dir = folder
            browser.source = Mock()
            browser.source.get.return_value = "saves"
            browser.refresh(select_name=path.name)
            row = browser.tree.insert.call_args.kwargs["values"]
            self.assertEqual(row[:5], (path.name, "Alice, Bob", "Bob", "Friday", "No"))
            script = ("import sys; from portable_deck.app.sessioncatalog import list_sessions; "
                      "assert len(list_sessions(sys.argv[1]))==1; assert 'tkinter' not in sys.modules")
            result = subprocess.run([sys.executable, "-B", "-c", script, folder],
                                    cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(path.read_bytes(), before)
