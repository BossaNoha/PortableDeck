import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from portable_deck.core.selection import SelectionState
from portable_deck.core.selectionsnapshot import SelectionSnapshot
from portable_deck.ui.handframe import HandFrame
from portable_deck.ui.tableframe import TableFrame
from portable_deck.ui.cardcontextmenu import show_card_menu


class SelectionHandlerTests(unittest.TestCase):
    def snapshot(self):
        return SelectionSnapshot("session", 0, "hand", "table", 2, 1)

    def test_index_checks_reject_invalid_locations_and_boolean_indices(self):
        view = self.snapshot()
        self.assertTrue(view.contains("hand", 1))
        self.assertTrue(view.contains("table", 0))
        for location, index in (("hand", 2), ("table", 1), ("hand", -1),
                                ("hand", True), ("table", "0"), ("unknown", 0)):
            self.assertFalse(view.contains(location, index))

    def test_hand_click_toggles_using_only_snapshot(self):
        state = SelectionState()
        gui = SimpleNamespace(game=object(), selection=state, refresh_action_availability=Mock())
        frame = SimpleNamespace(game_gui=gui, card_buttons=[])
        # No player or hand exists on this client-side game placeholder.
        with patch("portable_deck.ui.handframe.build_selection_snapshot", return_value=self.snapshot()):
            HandFrame.select_card(frame, 1)
            self.assertEqual(state.hand_index, 1)
            HandFrame.select_card(frame, 1)
            self.assertIsNone(state.hand_index)
            HandFrame.select_card(frame, 99)
            HandFrame.select_card(frame, True)
        self.assertEqual(gui.refresh_action_availability.call_count, 2)

    def test_table_click_preserves_target_and_rejects_removed_card(self):
        state = SelectionState()
        state.synchronize(self.snapshot())
        state.select_target((0, 1))
        frame = SimpleNamespace(game=SimpleNamespace(allow_move_cards_on_table=True),
                                selection=state, update_table=Mock())
        with patch("portable_deck.ui.tableframe.build_selection_snapshot", return_value=self.snapshot()):
            TableFrame.select_card(frame, 0)
            self.assertEqual(state.table_index, 0)
            self.assertEqual(state.target_position, (0, 1))
            TableFrame.select_card(frame, 1)
        frame.update_table.assert_called_once_with()

    def test_invalid_context_click_never_opens_menu_or_reads_model(self):
        gui = SimpleNamespace(game=object(), selection=SelectionState())
        for location, index in (("hand", 2), ("table", 1), ("hand", True), ("invalid", 0)):
            with self.subTest(location=location, index=index), patch(
                    "portable_deck.ui.cardcontextmenu.build_selection_snapshot", return_value=self.snapshot()), patch(
                    "portable_deck.ui.cardcontextmenu.tk.Menu") as menu:
                self.assertEqual(show_card_menu(gui, None, location, index), "break")
                menu.assert_not_called()

    def test_repeated_valid_context_click_keeps_card_selected(self):
        state = SelectionState()
        gui = SimpleNamespace(game=object(), selection=state, root=object(),
                              hand_frame=SimpleNamespace(select_card=state.select_hand),
                              table_frame=SimpleNamespace(update_table=Mock()))
        event = SimpleNamespace(x_root=10, y_root=20)
        with patch("portable_deck.ui.cardcontextmenu.build_selection_snapshot", return_value=self.snapshot()), patch(
                "portable_deck.ui.cardcontextmenu.card_menu_entries", return_value=[]), patch(
                "portable_deck.ui.cardcontextmenu.tk.Menu") as menu:
            show_card_menu(gui, event, "hand", 1)
            show_card_menu(gui, event, "hand", 1)
        self.assertEqual(state.hand_index, 1)
        self.assertEqual(menu.return_value.tk_popup.call_count, 2)
