import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from portable_deck.app.sessionview import TableViewState, load_table_view, save_with_view
from portable_deck.app.savemanager import SaveManager
from portable_deck.app.mainmenu import MainMenu
from portable_deck.app.sessionstorage import load_session_with_view
from portable_deck.core.game import Game
from portable_deck.ui.tableframe import TableFrame


class SessionViewTests(unittest.TestCase):
    def game(self):
        return Game(2, str(Path(__file__).resolve().parents[1] / "decks/demodeck.json"), enable_undo=True)

    def test_combined_load_reads_once_and_preserves_current_and_legacy_views(self):
        game = self.game()
        game.start(1)
        game.session.execute("draw_card")
        view = TableViewState(150, .25, .75)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "named.json"
            save_with_view(game, path, view)
            base = json.loads(path.read_text(encoding="utf-8"))
            for metadata, expected in (
                ({"client_state": base["client_state"]}, view),
                ({"table_view_state": {"zoom": 125, "x": .5, "y": 1}}, TableViewState(125, .5, 1)),
                ({}, TableViewState()),
                ({"client_state": {"table_view": {"zoom": True, "x": -1}}}, TableViewState()),
            ):
                with self.subTest(metadata=metadata):
                    state = {key: value for key, value in base.items() if key != "client_state"}
                    state.update(metadata)
                    path.write_text(json.dumps(state), encoding="utf-8")
                    with patch("builtins.open", wraps=open) as source:
                        loaded, loaded_view = load_session_with_view(Game, path)
                    source.assert_called_once_with(path, "r", encoding="utf-8")
                    self.assertEqual(loaded_view, expected)
                    self.assertEqual(loaded.capture_undo_state(), game.capture_undo_state())
                    self.assertEqual(loaded.named_save_path, str(path.absolute()))
                    self.assertFalse(hasattr(loaded, "table_view_state"))
                    self.assertTrue(loaded.session.undo())
                    self.assertEqual(loaded.capture_undo_state(), game.undo_stack[-1])

    def test_gui_load_and_resume_use_the_combined_read(self):
        with tempfile.TemporaryDirectory() as folder:
            for name, method in (("named.json", MainMenu.load_game),
                                 ("last_session.json", MainMenu.resume_game)):
                with self.subTest(name=name):
                    path = str(Path(folder) / name)
                    view = TableViewState(125, .1, .2)
                    save_with_view(self.game(), path, view)
                    menu = Mock(root=None)
                    with patch("portable_deck.app.mainmenu.SessionBrowser") as browser, patch(
                            "portable_deck.app.mainmenu.AUTOSAVE_PATH", path), patch(
                            "builtins.open", wraps=open) as source:
                        browser.return_value.show.return_value = path
                        method(menu)
                    source.assert_called_once_with(path, "r", encoding="utf-8")
                    menu.clear_window.assert_called_once()
                    loaded = menu.show_game.call_args.args[0]
                    self.assertEqual(menu.show_game.call_args.kwargs, {"table_view": view})
                    self.assertEqual(hasattr(loaded, "named_save_path"), name == "named.json")

    def test_view_roundtrip_is_separate_from_game_and_undo(self):
        g = self.game()
        view = TableViewState(150, .25, .75)
        before = g.capture_undo_state()
        with tempfile.TemporaryDirectory() as folder:
            path = str(Path(folder) / "save.json")
            save_with_view(g, path, view)
            self.assertEqual(load_table_view(path), view)
            self.assertFalse(hasattr(Game.load_session(path), "table_view_state"))
            state = json.loads(Path(path).read_text())
            self.assertNotIn("table_view_state", state)
            self.assertEqual(state["client_state"]["table_view"]["zoom"], 150)
        self.assertEqual(g.capture_undo_state(), before)
        g.session.execute("draw_card")
        view.zoom = 200
        g.session.undo()
        self.assertEqual(view.zoom, 200)
        self.assertEqual(g.capture_undo_state(), before)

    def test_legacy_and_invalid_values(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "legacy.json"
            path.write_text(json.dumps({"table_view_state": {"zoom": 125, "x": .5, "y": 1}}))
            self.assertEqual(load_table_view(path), TableViewState(125, .5, 1))
            for values in (None, [], {"zoom": True, "x": -1, "y": 2}, {"zoom": float("nan")}):
                self.assertEqual(TableViewState.from_saved(values), TableViewState())

    def test_capture_updates_client_without_touching_game(self):
        g = self.game()
        before = g.capture_undo_state()
        frame = Mock(game=g, restoring_view=False, zoom_percent=175, view_state=TableViewState())
        frame.canvas.xview.return_value = (.2, .8)
        frame.canvas.yview.return_value = (.4, 1)
        TableFrame.capture_view(frame)
        self.assertEqual(frame.view_state, TableViewState(175, .2, .4))
        self.assertEqual(g.capture_undo_state(), before)
        self.assertFalse(hasattr(g, "table_view_state"))

    def test_named_save_uses_client_state(self):
        g = self.game()
        with tempfile.TemporaryDirectory() as folder:
            manager = SaveManager(None, folder)
            manager.table_view = TableViewState(125, .1, .2)
            g.named_save_path = str(Path(folder) / "named.json")
            with patch("portable_deck.app.savemanager.messagebox.showinfo"):
                self.assertTrue(manager.save_session(g))
            self.assertEqual(load_table_view(g.named_save_path), manager.table_view)

    def test_checkpoint_and_archive_keep_their_own_views(self):
        g = self.game()
        with tempfile.TemporaryDirectory() as folder:
            latest = str(Path(folder) / "last_session.json")
            menu = Mock(settings={"autosave_enabled": True, "autosave_count": 2})
            menu.save_manager.table_view = TableViewState(125, .1, .2)
            with patch("portable_deck.app.mainmenu.SAVES_DIR", folder), patch(
                    "portable_deck.app.mainmenu.AUTOSAVE_PATH", latest):
                self.assertIsNone(MainMenu.checkpoint_game(menu, g))
                menu.save_manager.table_view.zoom = 175
                self.assertIsNone(MainMenu.checkpoint_game(menu, g))
            self.assertEqual(load_table_view(latest).zoom, 175)
            archived = list((Path(folder) / "autosaves").glob("*.json"))
            self.assertEqual(len(archived), 1)
            self.assertEqual(load_table_view(archived[0]).zoom, 125)
