import json
import unittest
from dataclasses import FrozenInstanceError, asdict, replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from portable_deck.core.game import Game
from portable_deck.core.chipoptions import build_chip_options
from portable_deck.ui.chipbankui import ChipBankUI
from portable_deck.ui.chipdialogs import ask_chip_purchase, ask_pot_recipient


class ChipOptionsTests(unittest.TestCase):
    def game(self, **options):
        return Game(3, str(Path(__file__).resolve().parents[1] / "decks/demodeck.json"),
                    enable_chip_accounts=True, minimum_bet=5, enable_undo=True, **options)

    def test_shared_accounts_and_ranges_are_immutable_public_data(self):
        g = self.game(enable_roles_teams=True, enable_teams=True, team_count=1,
                      player_teams=["team_1", "team_1", None], share_team_chips=True)
        g.players[1].hand = ["PRIVATE CARD"]
        before = g.capture_undo_state()
        view = build_chip_options(g)
        self.assertEqual(view.minimum_bet, 5)
        self.assertEqual(view.maximum_bet, 200)
        self.assertEqual(view.players[0].account, view.players[1].account)
        self.assertEqual(len(view.accounts), 2)
        self.assertEqual(sum(account.balance for account in view.accounts), 300)
        self.assertEqual(view.default_purchase_amount, 5)
        self.assertTrue(view.play_chips.allowed)
        self.assertEqual(view.take_pot.code, "empty_pot")
        self.assertNotIn("PRIVATE CARD", json.dumps(asdict(view)))
        self.assertEqual(g.capture_undo_state(), before)
        g.chip_balances[0] = 1
        self.assertEqual(view.maximum_bet, 200)
        with self.assertRaises(FrozenInstanceError):
            view.players[0].name = "changed"

    def test_disabled_and_insufficient_resources_and_confirmations(self):
        g = self.game()
        g.chip_balances[0] = 3
        self.assertEqual(build_chip_options(g).play_chips.code, "insufficient_chips")
        g.current_player_must_confirm_point = lambda: True
        view = build_chip_options(g)
        self.assertTrue(all(getattr(view, action).code == "confirmation_required"
                            for action in ("buy_chips", "play_chips", "take_pot")))
        g.enable_chip_accounts = False
        view = build_chip_options(g)
        self.assertFalse(view.enabled)
        self.assertIsNone(view.maximum_bet)
        self.assertIsNone(view.minimum_bet)
        self.assertIsNone(view.pot)

    def test_changed_balance_is_revalidated_and_next_dialog_uses_new_limit(self):
        g = self.game()
        gui = SimpleNamespace(game=g, root=None, run_action=lambda operation: g.session.run(operation))
        ui = object.__new__(ChipBankUI)
        ui.gui = gui
        def choose(*args, **kwargs):
            g.chip_balances[0] = 10
            return 20
        with patch("portable_deck.ui.chipbankui.simpledialog.askinteger", side_effect=choose) as ask, patch(
                "portable_deck.ui.chipbankui.messagebox.showwarning") as warning:
            ui.play_chips()
            self.assertEqual(ask.call_args.kwargs["maxvalue"], 100)
            self.assertEqual(g.chip_pot, 0)
            self.assertEqual(g.chip_balances[0], 10)
            warning.assert_called_once()
            ask.side_effect = None
            ask.return_value = None
            ui.play_chips()
            self.assertEqual(ask.call_args.kwargs["maxvalue"], 10)
            self.assertEqual(ask.call_args.kwargs["minvalue"], 5)

    def test_dialogs_use_snapshot_ids_without_any_game_or_player_object(self):
        view = build_chip_options(self.game())
        # A filtered list must return the model ID, not its position in the menu.
        view = replace(view, current_player=2, players=(view.players[2],), pot=15)
        for function, confirm, expected in ((ask_chip_purchase, "Buy", (2, 5)),
                                             (ask_pot_recipient, "Request", 2)):
            with self.subTest(dialog=confirm), patch("portable_deck.ui.chipdialogs.tk") as tk:
                callbacks = {}
                tk.StringVar.side_effect = lambda value: SimpleNamespace(get=lambda: value)
                def button(*args, **kwargs):
                    callbacks[kwargs["text"]] = kwargs["command"]
                    return Mock()
                tk.Button.side_effect = button
                parent = Mock()
                parent.wait_window.side_effect = lambda dialog: callbacks[confirm]()
                self.assertEqual(function(parent, view), expected)
