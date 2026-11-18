import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from portable_deck.app.discardstorage import save_discard_pile
from portable_deck.app.mainmenu import MainMenu
from portable_deck.core.game import Game


class DiscardStorageTests(unittest.TestCase):
    def test_service_and_compatibility_method_preserve_format_and_game(self):
        game = Game(2, str(Path(__file__).resolve().parents[1] / "decks/demodeck.json"))
        game.discard_pile.extend(["A of Hearts", "Žaludy"])
        before = game.capture_undo_state()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "data" / "discard.json"
            for save in (save_discard_pile, Game.save_discard_pile):
                save(game, path)
                self.assertEqual(json.loads(path.read_text(encoding="utf-8")), game.discard_pile)
                self.assertEqual(game.capture_undo_state(), before)

    def test_exit_respects_discard_options(self):
        for enabled in (False, True):
            for save_on_exit in (False, True):
                with self.subTest(enabled=enabled, save_on_exit=save_on_exit):
                    menu = Mock(settings={"save_discard_on_exit": save_on_exit})
                    game = Mock(enable_discard_pile=enabled)
                    with patch("portable_deck.app.mainmenu.save_discard_pile") as save:
                        MainMenu.exit_to_desktop(menu, game, False)
                    self.assertEqual(save.call_count, int(enabled and save_on_exit))
                    game.save_discard_pile.assert_not_called()
                    menu.root.destroy.assert_called_once()

    def test_exit_reports_write_error_and_still_closes(self):
        menu = Mock(root=Mock(), settings={"save_discard_on_exit": True})
        game = Mock(enable_discard_pile=True)
        with patch("portable_deck.app.discardstorage.open", side_effect=OSError("Disk full")), patch(
                "portable_deck.app.discardstorage.os.makedirs"), patch(
                "portable_deck.app.mainmenu.messagebox.showerror") as error:
            MainMenu.exit_to_desktop(menu, game, False)
        error.assert_called_once_with("Could not save", "Disk full", parent=menu.root)
        menu.root.destroy.assert_called_once()

    def test_canceled_session_save_does_not_write_discard_or_close(self):
        menu = Mock(settings={"save_discard_on_exit": True})
        menu.save_manager.save_session.return_value = False
        with patch("portable_deck.app.mainmenu.save_discard_pile") as save:
            MainMenu.exit_to_desktop(menu, Mock(enable_discard_pile=True), True)
        save.assert_not_called()
        menu.root.destroy.assert_not_called()
