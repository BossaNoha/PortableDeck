import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from portable_deck.core.game import Game
from portable_deck.core.interactions import build_interaction_options
from portable_deck.ui.interactionsui import InteractionsUI


class InteractionRefreshTests(unittest.TestCase):
    def test_balance_change_during_input_refreshes_targets_and_retry_limits(self):
        g = Game(2, str(Path(__file__).resolve().parents[1] / "decks/demodeck.json"),
                 enable_interactions=True, interaction_options={"steal_chips": True},
                 enable_chip_accounts=True, enable_undo=True)
        gui = SimpleNamespace(game=g, root=None, selection=SimpleNamespace(hand_index=None),
                              run_action=lambda operation: g.session.run(operation))
        ui = object.__new__(InteractionsUI)
        ui.gui = gui
        callbacks = {}
        def button(*args, **kwargs):
            callbacks[kwargs["text"]] = kwargs["command"]
            return Mock()
        variable = Mock()
        variable.get.return_value = "Steal chips from a chosen player"
        listing = Mock()
        listing.curselection.return_value = (0,)
        dialog = Mock()
        def amount(*args, **kwargs):
            g.chip_balances[1] = 1
            return 5
        with patch("portable_deck.ui.interactionsui.tk.Toplevel", return_value=dialog), patch(
                "portable_deck.ui.interactionsui.tk.StringVar", return_value=variable), patch(
                "portable_deck.ui.interactionsui.tk.OptionMenu"), patch(
                "portable_deck.ui.interactionsui.tk.Label"), patch(
                "portable_deck.ui.interactionsui.tk.Listbox", return_value=listing), patch(
                "portable_deck.ui.interactionsui.tk.Button", side_effect=button), patch(
                "portable_deck.ui.interactionsui.simpledialog.askinteger", side_effect=amount) as ask, patch(
                "portable_deck.ui.interactionsui.messagebox.showwarning") as warning, patch(
                "portable_deck.ui.interactionsui.build_interaction_options",
                wraps=build_interaction_options) as options:
            ui.show()
            callbacks["Perform"]()
            self.assertEqual(options.call_count, 3)  # initial, pre-input, rejected input
            self.assertEqual(options.call_args.args[1], "steal_chips")
            warning.assert_called_once()
            dialog.destroy.assert_not_called()
            ask.side_effect = None
            ask.return_value = None  # cancel the next attempt after inspecting its range
            callbacks["Perform"]()
            self.assertEqual(ask.call_args.kwargs["maxvalue"], 1)
        self.assertEqual(g.chip_balances, [100, 1])
        self.assertEqual(g.undo_stack, [])
