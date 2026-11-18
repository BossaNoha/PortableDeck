import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from portable_deck.app.deckfiles import (InvalidDeckError, SameDeckFileError,
                                        import_deck, export_deck, import_deck_target)
from portable_deck.app.decklibrary import DeckLibrary


class DeckFileTests(unittest.TestCase):
    def source(self, folder, name="source.json"):
        path = Path(folder) / name
        path.write_text(json.dumps({"types": ["Žaludy"], "cards": [[1, 1, "A"]]},
                                   ensure_ascii=False), encoding="utf-8")
        return path

    def test_import_and_export_preserve_file_bytes_and_normalize_extension(self):
        with tempfile.TemporaryDirectory() as folder:
            source = self.source(folder, "source.deck")
            library = Path(folder) / "library"
            library.mkdir()
            target = import_deck(source, library)
            self.assertEqual(target, str(library / "source.deck.json"))
            self.assertEqual(Path(target).read_bytes(), source.read_bytes())
            exported = export_deck(target, Path(folder) / "exported")
            self.assertEqual(exported, str(Path(folder) / "exported.json"))
            self.assertEqual(Path(exported).read_bytes(), source.read_bytes())

    def test_same_file_and_overwrite_rules_preserve_contents(self):
        with tempfile.TemporaryDirectory() as folder:
            source = self.source(folder)
            original = source.read_bytes()
            for operation in (lambda: import_deck(source, folder, overwrite=True),
                              lambda: export_deck(source, source, overwrite=True)):
                with self.assertRaises(SameDeckFileError):
                    operation()
                self.assertEqual(source.read_bytes(), original)
            library = Path(folder) / "library"
            library.mkdir()
            target = library / source.name
            for operation in (lambda overwrite: import_deck(source, library, overwrite=overwrite),
                              lambda overwrite: export_deck(source, target, overwrite=overwrite)):
                target.write_bytes(b"previous")
                for consent in (False, 1, "yes"):
                    with self.assertRaises(FileExistsError):
                        operation(consent)
                    self.assertEqual(target.read_bytes(), b"previous")
                self.assertEqual(operation(True), str(target))
                self.assertEqual(target.read_bytes(), original)

    def test_invalid_source_and_copy_failure_do_not_report_success(self):
        with tempfile.TemporaryDirectory() as folder:
            source = self.source(folder)
            target = Path(folder) / "target.json"
            target.write_bytes(b"previous")
            for data in ("broken", '{"types": [], "cards": []}'):
                source.write_text(data, encoding="utf-8")
                with self.assertRaises(InvalidDeckError):
                    export_deck(source, target, overwrite=True)
                self.assertEqual(target.read_bytes(), b"previous")
            source = self.source(folder)
            with patch("portable_deck.app.deckfiles.shutil.copy2", side_effect=OSError("Denied")):
                with self.assertRaises(OSError):
                    export_deck(source, target, overwrite=True)
            self.assertEqual(target.read_bytes(), b"previous")
            library = Path(folder) / "library"
            library.mkdir()
            import_deck_target(source, library)
            source.write_text("changed during dialog", encoding="utf-8")
            with self.assertRaises(InvalidDeckError):
                import_deck(source, library)
            self.assertEqual(list(library.iterdir()), [])

    def test_gui_import_cancellation_overwrite_and_success(self):
        with tempfile.TemporaryDirectory() as folder:
            source = self.source(folder)
            library = Path(folder) / "library"
            library.mkdir()
            target = library / source.name
            target.write_bytes(b"previous")
            for chosen, consent in (("", False), (str(source), False), (str(source), True)):
                menu = Mock(decks_dir=str(library), window=None)
                with patch("portable_deck.app.decklibrary.filedialog.askopenfilename", return_value=chosen), patch(
                        "portable_deck.app.decklibrary.messagebox.askyesno", return_value=consent):
                    DeckLibrary.import_deck(menu)
                if consent:
                    self.assertEqual(target.read_bytes(), source.read_bytes())
                    menu.on_use.assert_called_once_with(str(target))
                    menu.refresh.assert_called_once_with(select_path=str(target))
                else:
                    self.assertEqual(target.read_bytes(), b"previous")
                    menu.on_use.assert_not_called()
                    menu.refresh.assert_not_called()

    def test_gui_export_cancellation_same_file_copy_error_and_success(self):
        with tempfile.TemporaryDirectory() as folder:
            source = self.source(folder)
            target = Path(folder) / "exported.json"
            menu = Mock(window=None)
            menu.selected_path.return_value = str(source)
            for chosen in ("", str(source), str(target)):
                with patch("portable_deck.app.decklibrary.filedialog.asksaveasfilename", return_value=chosen), patch(
                        "portable_deck.app.decklibrary.messagebox.showinfo") as info:
                    DeckLibrary.export_selected(menu)
                if not chosen:
                    self.assertFalse(target.exists())
                    info.assert_not_called()
                elif chosen == str(source):
                    self.assertEqual(info.call_args.args[0], "Already exported")
                else:
                    self.assertEqual(target.read_bytes(), source.read_bytes())
                    self.assertEqual(info.call_args.args[0], "Deck exported")
            with patch("portable_deck.app.decklibrary.filedialog.asksaveasfilename", return_value=str(target)), patch(
                    "portable_deck.app.deckfiles.shutil.copy2", side_effect=OSError("Denied")), patch(
                    "portable_deck.app.decklibrary.messagebox.showerror") as error:
                DeckLibrary.export_selected(menu)
            self.assertEqual(error.call_args.args[:2], ("Could not export deck", "Denied"))

    def test_transfers_work_without_tkinter(self):
        with tempfile.TemporaryDirectory() as folder:
            source = self.source(folder)
            library = Path(folder) / "library"
            library.mkdir()
            script = ("import sys; from portable_deck.app.deckfiles import import_deck,export_deck; "
                      "path=import_deck(sys.argv[1],sys.argv[2]); "
                      "export_deck(path,sys.argv[3]); assert 'tkinter' not in sys.modules")
            result = subprocess.run([sys.executable, "-B", "-c", script, str(source), str(library),
                                     str(Path(folder) / "exported.json")],
                                    capture_output=True, text=True, timeout=30,
                                    cwd=Path(__file__).resolve().parents[1])
            self.assertEqual(result.returncode, 0, result.stderr)
