import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from portable_deck.core.game import Game
from portable_deck.core.playersessionview import build_player_session_view
from portable_deck.ui.gameguiactions import GameGUIActions
from portable_deck.ui.statuspanel import StatusPanel
from portable_deck.ui.personalpilesui import PersonalPilesUI


class PanelRefreshTests(unittest.TestCase):
    def game(self):
        return Game(2, str(Path(__file__).resolve().parents[1] / "decks/demodeck.json"),
                    enable_personal_piles=True)

    def test_refresh_builds_once_and_passes_same_snapshot_parts(self):
        g = self.game()
        g.players[0].hand = ["A"]
        gui = SimpleNamespace(game=g, selection=SimpleNamespace(hand_index=0),
                              status_panel=Mock(), personal_piles_ui=Mock())
        with patch("portable_deck.ui.gameguiactions.build_player_session_view",
                   wraps=build_player_session_view) as build:
            GameGUIActions.refresh_session_panels(gui)
        build.assert_called_once_with(g, 0, hand_index=0)
        status = gui.status_panel.update_status.call_args.args[0]
        piles = gui.personal_piles_ui.update.call_args.args[0]
        self.assertEqual(status.players[0].card_count, 1)
        self.assertTrue(piles.piles[0].play.allowed)
        g.session.execute("play_personal_pile", card_index=0, owner=0, pile_index=0)
        gui.selection.hand_index = None
        GameGUIActions.refresh_session_panels(gui)
        status = gui.status_panel.update_status.call_args.args[0]
        piles = gui.personal_piles_ui.update.call_args.args[0]
        self.assertEqual(status.players[0].card_count, 0)
        self.assertEqual(status.table_count, 1)
        self.assertEqual(piles.piles[0].cards, ("A",))

    def test_status_renderer_uses_supplied_snapshot_without_game_access(self):
        g = self.game()
        status = build_player_session_view(g, 0).status
        panel = SimpleNamespace(player_labels=[Mock(), Mock()], deck_label=Mock(),
                                discard_label=Mock(), table_label=Mock(), chip_pot_label=None)
        with patch("portable_deck.ui.statuspanel.build_session_status", side_effect=AssertionError("unexpected query")):
            StatusPanel.update_status(panel, status)
        panel.table_label.config.assert_called_once_with(text="Cards on Table: 0")

    def test_pile_renderer_uses_supplied_snapshot_without_game_access(self):
        g = self.game()
        g.personal_piles[0][0] = ["BOTTOM", "TOP"]
        piles = build_player_session_view(g, 0).personal_piles
        contents = Mock()
        contents.winfo_children.return_value = []
        panel = SimpleNamespace(contents=contents, scroll_area=Mock(), gui=object())
        with patch("portable_deck.ui.personalpilesui.build_player_personal_piles_view",
                   side_effect=AssertionError("unexpected query")), patch(
                "portable_deck.ui.personalpilesui.tk.LabelFrame"), patch(
                "portable_deck.ui.personalpilesui.tk.Listbox") as listing, patch(
                "portable_deck.ui.personalpilesui.tk.Scrollbar"), patch(
                "portable_deck.ui.personalpilesui.tk.Label"), patch(
                "portable_deck.ui.personalpilesui.tk.Button"):
            PersonalPilesUI.update(panel, piles)
        self.assertEqual(listing.return_value.insert.call_args_list[0].args, ("end", "TOP (top)"))
        panel.scroll_area.schedule_resize.assert_called_once_with()
