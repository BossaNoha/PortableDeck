import json
import subprocess
import sys
import tempfile
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest.mock import Mock, patch

from portable_deck.app.deckcatalog import DeckEntry, list_decks
from portable_deck.app.decklibrary import DeckLibrary


class DeckCatalogTests(unittest.TestCase):
    def test_metadata_order_invalid_files_and_immutable_entries(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            definition = {"types": ["Žaludy", "Hearts"], "cards": [[1, 1, 2], ["A"]]}
            (base / "a.JSON").write_text(json.dumps(definition), encoding="utf-8")
            (base / "broken.json").write_text("broken", encoding="utf-8")
            (base / "shape.json").write_text('{"types": []}', encoding="utf-8")
            (base / "encoding.json").write_bytes(b'\xff')
            (base / "directory.json").mkdir()
            (base / "ignored.txt").write_text("ignored")
            entries = list_decks(folder)
            self.assertEqual([entry.filename for entry in entries],
                             ["a.JSON", "broken.json", "directory.json", "encoding.json", "shape.json"])
            good = entries[0]
            self.assertEqual(good, DeckEntry("a.JSON", str(base / "a.JSON"), "a", 4,
                                             ("Žaludy", "Hearts"), None))
            for entry in entries[1:]:
                self.assertTrue(entry.error)
                self.assertIsNone(entry.card_count)
                self.assertEqual(entry.symbols, ())
            with self.assertRaises(FrozenInstanceError):
                good.card_count = 0
            (base / "a.JSON").write_text("changed", encoding="utf-8")
            self.assertEqual(good.card_count, 4)
            self.assertEqual(good.symbols, ("Žaludy", "Hearts"))

    def test_missing_directory_is_not_created_and_listing_errors_propagate(self):
        with tempfile.TemporaryDirectory() as folder:
            missing = Path(folder) / "missing"
            self.assertEqual(list_decks(missing), ())
            self.assertFalse(missing.exists())
            with patch("portable_deck.app.deckcatalog.Path.iterdir", side_effect=PermissionError("Denied")):
                with self.assertRaises(PermissionError):
                    list_decks(folder)

    def test_gui_renders_catalog_and_reselects_filename(self):
        library = Mock(decks_dir="library")
        library.tree.get_children.return_value = ("old",)
        entries = (DeckEntry("a.json", "library/a.json", "a", 4, ("Hearts",), None),
                   DeckEntry("bad.json", "library/bad.json", "bad", None, (), "Broken"))
        with patch("portable_deck.app.decklibrary.list_decks", return_value=entries) as catalog, patch(
                "portable_deck.app.decklibrary.Deck", side_effect=AssertionError("GUI loaded a deck")):
            DeckLibrary.refresh(library, select_path=str(Path("library") / "a.json"))
        catalog.assert_called_once_with("library")
        library.tree.delete.assert_called_once_with("old")
        self.assertEqual([call.kwargs for call in library.tree.insert.call_args_list], [
            {"iid": "a.json", "values": ("a", "4", "Hearts")},
            {"iid": "bad.json", "values": ("bad", "Invalid", "Could not read this deck")},
        ])
        library.tree.selection_set.assert_called_once_with("a.json")
        library.tree.focus.assert_called_once_with("a.json")

    def test_catalog_can_be_used_without_tkinter(self):
        script = ("import sys; from portable_deck.app.deckcatalog import list_decks; "
                  "entries=list_decks('decks'); assert entries; "
                  "assert any(e.card_count for e in entries); assert 'tkinter' not in sys.modules")
        result = subprocess.run([sys.executable, "-B", "-c", script],
                                cwd=Path(__file__).resolve().parents[1], capture_output=True,
                                text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
