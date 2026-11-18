import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from portable_deck.app.namedsaves import next_session_number, save_named_session
from portable_deck.app.savemanager import SaveManager
from portable_deck.core.game import Game


class NamedSaveTests(unittest.TestCase):
    def game(self):
        return Game(2, str(Path(__file__).resolve().parents[1] / "decks/demodeck.json"))

    def test_suggestion_uses_existing_numbers_without_creating_directory(self):
        with tempfile.TemporaryDirectory() as folder:
            missing = Path(folder) / "new"
            self.assertEqual(next_session_number(missing), 1)
            self.assertFalse(missing.exists())
            for name in ("session1.json", "SESSION09.JSON", "sessionX.json", "session5.json.tmp"):
                (Path(folder) / name).write_text("existing")
            (Path(folder) / "session10.json").mkdir()
            self.assertEqual(next_session_number(folder), 11)

    def test_reserved_paths_and_implicit_overwrite_never_write(self):
        with tempfile.TemporaryDirectory() as folder:
            game = Mock(named_save_path="previous.json")
            for name in ("LAST_SESSION.JSON", "autosaves/named.json", "AUTOSAVES/named.json"):
                with self.assertRaises(ValueError):
                    save_named_session(game, Path(folder) / name, overwrite=True)
            existing = Path(folder) / "named.json"
            existing.write_text("original")
            with self.assertRaises(FileExistsError):
                save_named_session(game, existing)
            self.assertEqual(existing.read_text(), "original")
            self.assertEqual(game.named_save_path, "previous.json")
            game.save_session.assert_not_called()

    def test_success_and_explicit_overwrite_preserve_client_metadata(self):
        g = self.game()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "new" / "session1.json"
            metadata = {"table_view": {"zoom": 150, "x": 0, "y": 0}}
            save_named_session(g, path, client_state=metadata)
            self.assertEqual(g.named_save_path, str(path))
            self.assertEqual(json.loads(path.read_text())["client_state"], metadata)
            g.session.execute("draw_card")
            save_named_session(g, path, overwrite=True)
            self.assertEqual(len(Game.load_session(str(path)).players[0].hand), 1)

    def test_write_failure_preserves_file_and_previous_association(self):
        g = self.game()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "target.json"
            save_named_session(g, path)
            before = path.read_bytes()
            g.named_save_path = "previous.json"
            with patch("portable_deck.app.sessionstorage.os.replace", side_effect=OSError("Disk full")):
                with self.assertRaises(OSError):
                    save_named_session(g, path, overwrite=True)
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(g.named_save_path, "previous.json")
            self.assertFalse(Path(str(path) + ".tmp").exists())

    def test_gui_cancel_and_declined_overwrite_do_not_save(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "existing.json"
            path.write_text("original")
            manager = SaveManager(None, folder)
            for chosen in ("", str(path)):
                with self.subTest(chosen=chosen):
                    g = Mock(named_save_path="previous.json")
                    with patch("portable_deck.app.savemanager.filedialog.asksaveasfilename", return_value=chosen), patch(
                            "portable_deck.app.savemanager.messagebox.askyesno", return_value=False):
                        self.assertFalse(manager.save_session_as(g))
                    g.save_session.assert_not_called()
                    self.assertEqual(g.named_save_path, "previous.json")
                    self.assertEqual(path.read_text(), "original")

    def test_named_save_service_runs_without_tkinter(self):
        with tempfile.TemporaryDirectory() as folder:
            script = ("import sys; from portable_deck.app.namedsaves import save_named_session; "
                      "from portable_deck.core.game import Game; "
                      "save_named_session(Game(2,'decks/demodeck.json'),sys.argv[1]); "
                      "assert 'tkinter' not in sys.modules")
            path = Path(folder) / "session1.json"
            result = subprocess.run([sys.executable, "-B", "-c", script, str(path)],
                                    cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(path.exists())
