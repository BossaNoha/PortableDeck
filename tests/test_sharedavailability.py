import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from portable_deck.core.game import Game
from portable_deck.core.actionavailability import ACTIONS, ActionAvailability, ActionContext, action_availability, drop_availability, available_move_targets
from portable_deck.ui.chipbankui import ChipBankUI
from portable_deck.ui.carddrag import CardDrag


class SharedAvailabilityTests(unittest.TestCase):
    def test_every_registered_gameplay_command_checks_availability_before_execution(self):
        for action in ACTIONS:
            with self.subTest(action=action):
                g = self.game()
                before = g.capture_undo_state()
                with patch("portable_deck.core.session.action_availability",
                           return_value=ActionAvailability(False, "Blocked by current rules")) as check:
                    result = g.session.execute(action)
                check.assert_called_once()
                self.assertFalse(result.success)
                self.assertEqual(result.message, "Blocked by current rules")
                self.assertEqual(g.capture_undo_state(), before)
                self.assertEqual(g.undo_stack, [])

    def game(self, positioned=True):
        g = Game(2, str(Path(__file__).resolve().parents[1] / "decks/demodeck.json"),
                 enable_chip_accounts=True, minimum_bet=5, allow_positioned_play=positioned,
                 allow_move_cards_on_table=True, enable_undo=True,
                 enable_interactions=True, interaction_options={"give_card": True})
        g.players[0].hand = ["A"]
        return g

    def test_chip_buttons_use_shared_checks_on_every_refresh(self):
        g = self.game()
        ui = object.__new__(ChipBankUI)
        ui.gui = Mock(game=g)
        ui.buy_button, ui.play_button, ui.take_button = Mock(), Mock(), Mock()
        ui.buttons = [ui.buy_button, ui.play_button, ui.take_button]
        for state in ("normal", "empty_balance", "pending", "confirmation", "departed"):
            g.chip_balances[0] = 0 if state == "empty_balance" else 100
            g.chip_pot = 10
            g.pending_pot_withdrawal = {"requester": 0, "recipient": 1, "confirmed_by": []} if state == "pending" else None
            g.current_player_must_confirm_point = lambda: state == "confirmation"
            g.left_players = [0] if state == "departed" else []
            ui.update_action_buttons()
            for button, action in zip(ui.buttons, ("buy_chips", "play_chips", "take_pot")):
                button.config.assert_called_with(state="normal" if action_availability(g, action).allowed else "disabled")

    def test_chip_dialog_rechecks_after_user_input(self):
        g = self.game()
        ui = object.__new__(ChipBankUI)
        ui.gui = Mock(game=g, session=g.session)
        ui._finish_action = Mock()
        saved = Mock(return_value=None)
        g.session.checkpoint_callback = saved
        def choose_amount(*args, **kwargs):
            g.current_player_must_confirm_point = lambda: True
            return 5
        before = g.capture_undo_state()
        with patch("portable_deck.ui.chipbankui.simpledialog.askinteger", side_effect=choose_amount), patch(
                "portable_deck.ui.chipbankui.messagebox.showwarning") as warning:
            ui.play_chips()
        warning.assert_called_once()
        self.assertEqual(g.capture_undo_state(), before)
        self.assertEqual(g.undo_stack, [])
        saved.assert_not_called()

    def test_drop_checks_indices_and_respects_automatic_or_positioned_mode(self):
        for positioned in (False, True):
            g = self.game(positioned)
            self.assertTrue(drop_availability(g, "hand", 0, (0, 0)).availability.allowed)
            for source, index, target in (("hand", True, (0, 0)), ("hand", 99, (0, 0)),
                                          ("hand", 0, (True, 0)),
                                          ("invalid", 0, (0, 0))):
                self.assertFalse(drop_availability(g, source, index, target).availability.allowed)
            g.table_cards = [{"card": "B", "player": "Player2", "position": [0, 0]}]
            target = g.default_table_position()
            self.assertTrue(drop_availability(g, "hand", 0, target).availability.allowed)
            self.assertEqual(drop_availability(g, "hand", 0, (0, 0)).availability.allowed, not positioned)
            self.assertEqual(drop_availability(g, "hand", 0, None).availability.allowed, not positioned)

    def test_changed_state_is_rechecked_by_controller(self):
        for action, parameters, context in (
            ("play_chips", {"amount": 5}, ActionContext()),
            ("give_card", {"target": 1, "card_index": 0}, ActionContext(hand_index=0)),
            ("play_at_position", {"card_index": 0, "target_position": (0, 0)},
             ActionContext(hand_index=0, target_position=(0, 0))),
        ):
            with self.subTest(action=action):
                g = self.game()
                self.assertTrue(action_availability(g, action, context).allowed)
                g.current_player_must_confirm_point = lambda: True
                before = g.capture_undo_state()
                saved = Mock(return_value=None)
                g.session.checkpoint_callback = saved
                result = g.session.execute(action, **parameters)
                self.assertFalse(result.success)
                self.assertEqual(g.capture_undo_state(), before)
                self.assertEqual(g.undo_stack, [])
                saved.assert_not_called()

    def test_move_targets_and_gui_drop_reject_pending_confirmation(self):
        g = self.game()
        g.table_cards = [{"card": "B", "player": "Player2", "position": [0, 0]}]
        self.assertTrue(available_move_targets(g, 0))
        g.current_player_must_confirm_point = lambda: True
        self.assertEqual(available_move_targets(g, 0), ())
        drag = object.__new__(CardDrag)
        drag.gui = Mock(game=g)
        self.assertFalse(drag.drop("table", 0, (0, 1)))
        drag.gui.run_action.assert_not_called()
