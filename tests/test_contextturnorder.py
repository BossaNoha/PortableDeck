import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from portable_deck.ui.contextactions import ContextActions


class ContextTurnOrderTests(unittest.TestCase):
    def test_contextual_layout_restores_optional_manual_turn_button(self):
        for enabled in (False, True):
            with self.subTest(enabled=enabled):
                gui = SimpleNamespace(card_actions_frame=Mock(), turn_actions_frame=Mock(),
                                      next_button=Mock(), undo_button=Mock(), table_frame=Mock(),
                                      chip_bank_ui=SimpleNamespace(buttons=[]), view_deck_button=Mock())
                gui.card_actions_frame.winfo_children.return_value = []
                buttons = [gui.next_button, gui.undo_button]
                if enabled:
                    gui.choose_next_button = Mock()
                    buttons.append(gui.choose_next_button)
                    gui.reverse_turn_button = Mock()
                    buttons.append(gui.reverse_turn_button)
                gui.turn_actions_frame.winfo_children.return_value = buttons
                with patch.object(ContextActions, "add_menu"), patch.object(ContextActions, "refresh"):
                    ContextActions(gui)
                for button in buttons:
                    button.pack_forget.assert_called_once()
                    button.pack.assert_called_once_with(side="left", padx=5)
