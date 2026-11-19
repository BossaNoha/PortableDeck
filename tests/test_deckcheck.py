import json
import subprocess
import sys
import tempfile
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest.mock import Mock, patch

from portable_deck.app.deckcheck import check_deck
from portable_deck.app.newgame import create_game
from portable_deck.app.settingswindow import SettingsWindow


class DeckCheckTests(unittest.TestCase):
    def deck(self, folder):
        path = Path(folder) / "deck.json"
        path.write_text(json.dumps({"types": ["Test"], "cards": [[1, 1, 2, 3]]}), encoding="utf-8")
        return path

    def test_capacity_and_new_game_agree_without_shuffling_during_check(self):
        with tempfile.TemporaryDirectory() as folder:
            path = self.deck(folder)
            for players, hand, sufficient in ((2, 2, True), (2, 3, False), (20, 0, True)):
                with self.subTest(players=players, hand=hand):
                    with patch("portable_deck.core.deck.Deck.shuffle", side_effect=AssertionError("Check shuffled")):
                        result = check_deck(path, players, hand)
                    self.assertEqual((result.available, result.required, result.sufficient),
                                     (4, players * hand, sufficient))
                    with self.assertRaises(FrozenInstanceError):
                        result.available = 0
                    values = {"deck_path": str(path), "num_players": players, "cards_per_player": hand}
                    if sufficient:
                        game = create_game(values)
                        self.assertEqual([len(player.hand) for player in game.players], [hand] * players)
                    else:
                        with self.assertRaises(ValueError):
                            create_game(values)

    def test_invalid_counts_paths_and_decks_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = self.deck(folder)
            for players, hand in ((0, 1), (21, 0), (True, 1), (2.0, 1), ("2", 1),
                                  (2, -1), (2, True), (2, 1.0), (2, "1")):
                with self.subTest(players=players, hand=hand):
                    with self.assertRaises(ValueError):
                        check_deck(path, players, hand)
                    with self.assertRaises(ValueError):
                        create_game({"deck_path": str(path), "num_players": players, "cards_per_player": hand})
            with self.assertRaises(ValueError):
                check_deck("", 2, 1)
            with self.assertRaises(OSError):
                check_deck(Path(folder) / "missing.json", 2, 1)
            path.write_text("broken", encoding="utf-8")
            with self.assertRaises(ValueError):
                check_deck(path, 2, 1)

    def test_gui_displays_success_capacity_warning_or_validation_error(self):
        with tempfile.TemporaryDirectory() as folder:
            path = self.deck(folder)
            for players, hand, kind in ((2, 2, "info"), (2, 3, "warning"), (21, 0, "error"), (2, "x", "error")):
                with self.subTest(players=players, hand=hand):
                    window = Mock(root=None)
                    variable = lambda value: Mock(get=Mock(return_value=str(value)))
                    with patch("portable_deck.app.settingswindow.messagebox.showinfo") as info, patch(
                            "portable_deck.app.settingswindow.messagebox.showwarning") as warning, patch(
                            "portable_deck.app.settingswindow.messagebox.showerror") as error:
                        SettingsWindow.check_deck(window, variable(path), variable(players), variable(hand))
                    self.assertEqual(info.call_count, int(kind == "info"))
                    self.assertEqual(warning.call_count, int(kind == "warning"))
                    self.assertEqual(error.call_count, int(kind == "error"))

    def test_project_relative_deck_check_works_without_tkinter(self):
        script = ("import sys; from portable_deck.app.deckcheck import check_deck; "
                  "result=check_deck('decks/demodeck.json',2,3); "
                  "assert result.available==52 and result.required==6 and result.sufficient; "
                  "assert 'tkinter' not in sys.modules")
        result = subprocess.run([sys.executable, "-B", "-c", script],
                                cwd=Path(__file__).resolve().parents[1], capture_output=True,
                                text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
