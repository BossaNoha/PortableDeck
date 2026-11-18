import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from portable_deck.app.deckbuilder import DeckBuilder
from portable_deck.app.deckstorage import prepare_deck_definition, save_deck_definition


class DeckStorageTests(unittest.TestCase):
    def data(self):
        return {"types": ["Žaludy"], "cards": [[1, 1, "A"]]}

    def editor(self, edit_path=None):
        editor = Mock(edit_path=edit_path, decks_dir="decks", window=Mock())
        editor.name_var.get.return_value = "my_deck"
        symbol, cards = Mock(), Mock()
        symbol.get.return_value = "Žaludy"
        cards.get.return_value = "1, 1\nA"
        editor.groups = [{"symbol": symbol, "cards": cards}]
        editor._parse_cards = DeckBuilder._parse_cards
        return editor

    def test_preparation_copies_data_and_save_preserves_format(self):
        data = self.data()
        prepared = prepare_deck_definition(data["types"], data["cards"])
        data["cards"][0].append("other")
        self.assertEqual(prepared["cards"], [[1, 1, "A"]])
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "new" / "deck.json"
            self.assertEqual(save_deck_definition(path, prepared), str(path))
            text = path.read_text(encoding="utf-8")
            self.assertEqual(json.loads(text), prepared)
            self.assertIn("Žaludy", text)
            self.assertTrue(text.endswith("\n"))
            self.assertFalse(Path(str(path) + ".tmp").exists())
            with self.assertRaises(FileExistsError):
                save_deck_definition(path, prepared)
            save_deck_definition(path, prepared, overwrite=True)

    def test_invalid_definition_and_failed_replacement_preserve_existing_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "deck.json"
            path.write_bytes(b"previous")
            for data in ({}, {"types": [], "cards": []}, {"types": ["A"], "cards": [[]]}, None):
                with self.subTest(data=data), self.assertRaises(ValueError):
                    save_deck_definition(path, data, overwrite=True)
                self.assertEqual(path.read_bytes(), b"previous")
                self.assertFalse(Path(str(path) + ".tmp").exists())
            with patch("portable_deck.app.deckstorage.os.replace", side_effect=OSError("Disk full")):
                with self.assertRaises(OSError):
                    save_deck_definition(path, self.data(), overwrite=True)
            self.assertEqual(path.read_bytes(), b"previous")
            self.assertFalse(Path(str(path) + ".tmp").exists())

    def test_editor_new_duplicate_and_edit_save_through_service(self):
        with tempfile.TemporaryDirectory() as folder:
            for mode in ("new", "duplicate", "edit"):
                with self.subTest(mode=mode):
                    path = Path(folder) / f"{mode}.json"
                    editor = self.editor(str(path) if mode == "edit" else None)
                    if mode == "duplicate":
                        editor.name_var.get.return_value = "custom_original"
                    if mode == "edit":
                        path.write_bytes(b"previous")
                    with patch("portable_deck.app.deckbuilder.filedialog.asksaveasfilename", return_value=str(path)), patch(
                            "portable_deck.app.deckbuilder.messagebox.askyesno", return_value=True):
                        DeckBuilder.save_deck(editor)
                    self.assertEqual(json.loads(path.read_text(encoding="utf-8")),
                                     {"types": ["Žaludy"], "cards": [["1", "1", "A"]]})
                    editor.on_created.assert_called_once_with(str(path))
                    editor.window.destroy.assert_called_once()

    def test_editor_cancellation_and_failure_leave_window_open_without_callback(self):
        for mode in ("cancel_new", "decline_edit", "failure"):
            with self.subTest(mode=mode):
                editor = self.editor("existing.json" if mode == "decline_edit" else None)
                with patch("portable_deck.app.deckbuilder.filedialog.asksaveasfilename",
                           return_value="new.json" if mode == "failure" else ""), patch(
                        "portable_deck.app.deckbuilder.messagebox.askyesno", return_value=False), patch(
                        "portable_deck.app.deckbuilder.save_deck_definition", side_effect=OSError("Denied")) as save, patch(
                        "portable_deck.app.deckbuilder.messagebox.showerror") as error:
                    DeckBuilder.save_deck(editor)
                if mode == "failure":
                    save.assert_called_once()
                    self.assertEqual(error.call_args.args[:2], ("Could not save deck", "Denied"))
                else:
                    save.assert_not_called()
                editor.on_created.assert_not_called()
                editor.window.destroy.assert_not_called()

    def test_storage_works_without_tkinter(self):
        with tempfile.TemporaryDirectory() as folder:
            script = ("import sys; from portable_deck.app.deckstorage import save_deck_definition; "
                      "save_deck_definition(sys.argv[1],{'types':['A'],'cards':[[1]]}); "
                      "assert 'tkinter' not in sys.modules")
            result = subprocess.run([sys.executable, "-B", "-c", script, str(Path(folder) / "deck.json")],
                                    capture_output=True, text=True, timeout=30,
                                    cwd=Path(__file__).resolve().parents[1])
            self.assertEqual(result.returncode, 0, result.stderr)
