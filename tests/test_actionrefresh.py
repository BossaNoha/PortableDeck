import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from portable_deck.core.game import Game
from portable_deck.core.selection import SelectionState
from portable_deck.ui.gameguiactions import GameGUIActions
from portable_deck.ui.cardactions import draw_card, end_turn
from portable_deck.ui.chipbankui import ChipBankUI


class HeadlessGUI(GameGUIActions):
    def __init__(self, game):
        self.game, self.session = game, game.session
        self.selection = SelectionState()
        self.root = None
        self.hand_frame, self.table_frame = Mock(), Mock()
        self.hand_frame.game_gui = self
        self.status_panel, self.personal_piles_ui = Mock(), Mock()
        self.render_log = Mock()
        self.update_undo_button = Mock()
        self.update_leave_button = Mock()
        self.update_point_button = Mock()
        self.update_chip_action_buttons = Mock()
        self.refresh_action_availability = Mock()

    def _turn_action_buttons(self):
        return []


class ActionRefreshTests(unittest.TestCase):
    def game(self, **options):
        return Game(2, str(Path(__file__).resolve().parents[1] / "decks/demodeck.json"),
                    enable_undo=True, **options)

    def assert_single_refresh(self, gui):
        gui.hand_frame.update_hand.assert_called_once()
        gui.table_frame.update_table.assert_called_once()
        gui.status_panel.update_status.assert_called_once()
        gui.personal_piles_ui.update.assert_called_once()
        gui.render_log.assert_called_once()

    def test_draw_action_refreshes_once_after_checkpoint(self):
        g = self.game()
        gui = HeadlessGUI(g)
        def checkpoint(game):
            gui.hand_frame.update_hand.assert_not_called()
        saved = g.session.checkpoint_callback = Mock(side_effect=checkpoint)
        gui.run_action(draw_card, g, gui.hand_frame, gui.render_log, gui.status_panel)
        self.assert_single_refresh(gui)
        saved.assert_called_once_with(g)
        self.assertEqual(len(g.undo_stack), 1)
        self.assertEqual(gui.status_panel.update_status.call_args.args[0].players[0].card_count, 1)

    def test_nested_actions_refresh_once_and_preserve_one_undo(self):
        g = self.game()
        gui = HeadlessGUI(g)
        def outer():
            gui.run_action(draw_card, g, gui.hand_frame, gui.render_log, gui.status_panel)
            gui.run_action(draw_card, g, gui.hand_frame, gui.render_log, gui.status_panel)
            gui.hand_frame.update_hand.assert_not_called()
        gui.run_action(outer)
        self.assert_single_refresh(gui)
        self.assertEqual(len(g.players[0].hand), 2)
        self.assertEqual(len(g.undo_stack), 1)

    def test_turn_without_dialogs_refreshes_once_for_next_player(self):
        g = self.game()
        gui = HeadlessGUI(g)
        gui.run_action(end_turn, g, gui.hand_frame, gui.render_log, gui.status_panel, gui.handle_turn_start)
        self.assert_single_refresh(gui)
        self.assertEqual(gui.hand_frame.update_hand.call_args.args[0].viewer, 1)

    def test_confirmation_has_current_panels_before_prompt_and_final_refresh(self):
        g = self.game(score_enabled=True, require_point_confirmation=True)
        g.session.execute("request_point")
        gui = HeadlessGUI(g)
        def approve(*args, **kwargs):
            self.assertEqual(gui.hand_frame.update_hand.call_args.args[0].viewer, 1)
            self.assertEqual(gui.status_panel.update_status.call_count, 1)
            return True
        with patch("portable_deck.ui.gameguiactions.messagebox.askyesno", side_effect=approve):
            gui.run_action(end_turn, g, gui.hand_frame, gui.render_log, gui.status_panel, gui.handle_turn_start)
        self.assertEqual(gui.status_panel.update_status.call_count, 2)
        self.assertEqual(gui.status_panel.update_status.call_args.args[0].players[0].score, 1)
        self.assertIsNone(g.pending_point_request)

    def test_chip_action_uses_common_refresh(self):
        g = self.game(enable_chip_accounts=True)
        gui = HeadlessGUI(g)
        chip = object.__new__(ChipBankUI)
        chip.gui = gui
        with patch("portable_deck.ui.chipbankui.simpledialog.askinteger", return_value=5):
            chip.play_chips()
        self.assert_single_refresh(gui)
        self.assertEqual(g.chip_pot, 5)

    def test_turn_dialog_order_is_score_notice_then_score_and_pot_approval(self):
        g = self.game(score_enabled=True, require_point_confirmation=True,
                      enable_chip_accounts=True, require_pot_withdrawal_confirmation=True,
                      enable_target_score=True, target_score=10, enable_score_warning=True, score_warning=7)
        g.session.execute("request_point")
        g.session.execute("play_chips", amount=5)
        g.session.execute("take_pot", player_index=0)
        g.scores[0] = 7
        gui = HeadlessGUI(g)
        titles = []
        def notice(title, *args, **kwargs):
            titles.append(title)
        def decide(title, *args, **kwargs):
            titles.append(title)
            return False
        with patch("portable_deck.ui.gameguiactions.messagebox.showinfo", side_effect=notice), patch(
                "portable_deck.ui.gameguiactions.messagebox.askyesno", side_effect=decide):
            gui.run_action(end_turn, g, gui.hand_frame, gui.render_log, gui.status_panel, gui.handle_turn_start)
        self.assertEqual(titles, ["Score notice", "Confirm point request", "Confirm pot withdrawal"])
        self.assertIsNone(g.pending_point_request)
        self.assertIsNone(g.pending_pot_withdrawal)
        self.assertEqual(g.chip_pot, 5)

    def test_failed_transaction_restores_state_and_next_action_refreshes(self):
        g = self.game()
        gui = HeadlessGUI(g)
        before = g.capture_undo_state()
        def broken():
            g.session.execute("draw_card")
            raise RuntimeError("failure")
        with self.assertRaises(RuntimeError):
            gui.run_action(broken)
        self.assertEqual(g.capture_undo_state(), before)
        gui.hand_frame.update_hand.assert_not_called()
        gui.run_action(draw_card, g, gui.hand_frame, gui.render_log, gui.status_panel)
        self.assert_single_refresh(gui)
