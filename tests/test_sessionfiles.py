import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from portable_deck.app.sessionfiles import rename_session, delete_session
from portable_deck.app.sessionbrowser import SessionBrowser


class SessionFileTests(unittest.TestCase):
    def test_rename_preserves_contents_and_directory_for_named_and_archived_saves(self):
        with tempfile.TemporaryDirectory() as folder:
            for directory in (Path(folder), Path(folder) / "autosaves"):
                directory.mkdir(exist_ok=True)
                source = directory / "before.json"
                source.write_bytes(b'{"saved": true}')
                result = rename_session(source, " after ")
                self.assertEqual(result, directory / "after.json")
                self.assertEqual(result.read_bytes(), b'{"saved": true}')
                self.assertFalse(source.exists())

    def test_invalid_and_reserved_names_do_not_change_files(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "before.json"
            source.write_text("original")
            for name in ("", ".", "..", "../outside", "sub/file", "sub\\file", "bad:name",
                         "bad\x00name", "last_session", "LAST_SESSION.JSON", None):
                with self.subTest(name=name), self.assertRaises(ValueError):
                    rename_session(source, name)
                self.assertEqual(source.read_text(), "original")
                self.assertEqual(list(Path(folder).iterdir()), [source])
            latest = Path(folder) / "last_session.json"
            latest.write_text("checkpoint")
            with self.assertRaises(ValueError):
                rename_session(latest, "another")
            self.assertEqual(latest.read_text(), "checkpoint")

    def test_collisions_missing_sources_and_io_failures_preserve_files(self):
        with tempfile.TemporaryDirectory() as folder:
            source, existing = Path(folder) / "before.json", Path(folder) / "existing.json"
            source.write_text("source")
            existing.write_text("destination")
            with self.assertRaises(FileExistsError):
                rename_session(source, "existing")
            with self.assertRaises(FileNotFoundError):
                rename_session(Path(folder) / "missing.json", "other")
            with patch("portable_deck.app.sessionfiles.Path.rename", side_effect=OSError("Denied")):
                with self.assertRaises(OSError):
                    rename_session(source, "other")
            with patch("portable_deck.app.sessionfiles.Path.unlink", side_effect=OSError("Denied")):
                with self.assertRaises(OSError):
                    delete_session(source, confirmed=True)
            self.assertEqual(source.read_text(), "source")
            self.assertEqual(existing.read_text(), "destination")

    def test_delete_requires_explicit_confirmation_and_does_not_recurse(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "last_session.json"
            source.write_text("checkpoint")
            for confirmation in (False, None, 1, "yes"):
                self.assertFalse(delete_session(source, confirmed=confirmation))
                self.assertTrue(source.exists())
            self.assertTrue(delete_session(source, confirmed=True))
            self.assertFalse(source.exists())
            nested = Path(folder) / "directory"
            nested.mkdir()
            with self.assertRaises(OSError):
                delete_session(nested, confirmed=True)
            self.assertTrue(nested.is_dir())

    def test_browser_cancel_and_declined_deletion_leave_file_untouched(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "session.json"
            source.write_text("original")
            browser = object.__new__(SessionBrowser)
            browser.window = None
            browser.selected_filename = Mock(return_value=source.name)
            browser.session_path = Mock(return_value=str(source))
            browser.refresh = Mock()
            with patch("portable_deck.app.sessionbrowser.simpledialog.askstring", return_value=None), patch(
                    "portable_deck.app.sessionbrowser.messagebox.askyesno", return_value=False):
                browser.rename_selected()
                browser.delete_selected()
            browser.refresh.assert_not_called()
            self.assertEqual(source.read_text(), "original")

    def test_service_runs_without_tkinter(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "before.json"
            source.write_text("original")
            script = ("import sys; from portable_deck.app.sessionfiles import rename_session,delete_session; "
                      "target=rename_session(sys.argv[1],'after'); assert delete_session(target,confirmed=True); "
                      "assert 'tkinter' not in sys.modules")
            result = subprocess.run([sys.executable, "-B", "-c", script, str(source)],
                                    cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(list(Path(folder).iterdir()), [])
