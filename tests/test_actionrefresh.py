import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from portable_deck.core.game import Game
from portable_deck.core.selection import SelectionState
from portable_deck.core.selectionsnapshot import build_selection_snapshot
from portable_deck.ui.gameguiactions import GameGUIActions
from portable_deck.ui.cardactions import draw_card, end_turn, _discard_to_destination, _finish_table_discard
from portable_deck.ui.chipbankui import ChipBankUI
from portable_deck.ui.cardactions import play_selected, play_selected_face_down, play_at_selected_spot
from portable_deck.ui.carddrag import CardDrag
from portable_deck.ui.cardactions import take_selected_from_table, move_selected_table_card
from portable_deck.ui.cardactions import flip_selected_table_card, recycle_discard_into_deck, clear_table
from portable_deck.ui.cardactions import request_point
from portable_deck.ui.cardactions import _take_discard_card
from portable_deck.core.playerview import build_player_discard_view


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
    def test_gui_undo_returns_result_and_preserves_selection_on_refusal(self):
        game = self.game()
        game.players[0].hand = ["HAND"]
        gui = HeadlessGUI(game)
        gui.selection.synchronize(build_selection_snapshot(game))
        gui.selection.hand_index = 0
        gui.handle_turn_start = Mock()
        saved = game.session.checkpoint_callback = Mock(return_value=None)
        with patch("portable_deck.ui.gameguiactions.messagebox.showwarning") as warning:
            result = gui.undo()
        self.assertEqual(result.code, "empty_undo")
        warning.assert_called_once_with("Cannot undo", result.message, parent=None)
        self.assertEqual(gui.selection.hand_index, 0)
        gui.handle_turn_start.assert_not_called()
        saved.assert_not_called()
        before = game.capture_undo_state()
        game.session.execute("draw_card")
        saved.reset_mock()
        result = gui.undo()
        self.assertTrue(result.success)
        self.assertIsNone(gui.selection.hand_index)
        gui.handle_turn_start.assert_called_once()
        saved.assert_called_once_with(game)
        self.assertEqual(game.capture_undo_state(), before)

    def test_cross_feature_results_pending_refusal_and_grouped_decisions(self):
        game = self.game(score_enabled=True, require_point_confirmation=True,
                         enable_chip_accounts=True, require_pot_withdrawal_confirmation=True,
                         enable_player_leaving=True, enable_player_return=True)
        game.players[0].hand = ["HAND"]
        game.players[1].hand = ["OTHER"]
        gui = HeadlessGUI(game)
        chip = object.__new__(ChipBankUI)
        chip.gui = gui
        saved = game.session.checkpoint_callback = Mock(return_value=None)
        point = gui.run_action(request_point, game, gui.hand_frame, gui.render_log, gui.status_panel)
        self.assertTrue(point.success)
        with patch("portable_deck.ui.chipbankui.simpledialog.askinteger", return_value=5):
            self.assertTrue(chip.play_chips().success)
        with patch("portable_deck.ui.chipbankui.ask_pot_recipient", return_value=0):
            self.assertTrue(chip.take_pot().success)
        self.assertEqual(saved.call_count, 3)
        self.assertEqual(len(game.undo_stack), 3)
        self.assertTrue(gui.run_action(end_turn, game, gui.hand_frame, gui.render_log, gui.status_panel).success)
        gui.selection.hand_index = 0
        before = game.capture_undo_state()
        callback = Mock()
        saved.reset_mock()
        undo_count = len(game.undo_stack)
        with patch("portable_deck.ui.cardactions.messagebox.showwarning") as warning:
            refused = gui.run_action(end_turn, game, gui.hand_frame, gui.render_log, gui.status_panel, callback)
        self.assertEqual(refused.code, "confirmation_required")
        self.assertEqual(warning.call_args.args[1], refused.message)
        self.assertEqual(game.capture_undo_state(), before)
        self.assertEqual(gui.selection.hand_index, 0)
        self.assertEqual(len(game.undo_stack), undo_count)
        saved.assert_not_called()
        callback.assert_not_called()
        with patch("portable_deck.ui.gameguiactions.messagebox.askyesno", side_effect=[False, True]) as prompt:
            gui.run_action(gui.handle_turn_start)
        self.assertEqual(prompt.call_count, 2)
        self.assertEqual(game.scores, [0, 0])
        self.assertEqual(game.chip_pot, 0)
        self.assertIsNone(game.pending_point_request)
        self.assertIsNone(game.pending_pot_withdrawal)
        saved.assert_called_once_with(game)
        self.assertEqual(len(game.undo_stack), undo_count + 1)
        self.assertTrue(game.session.undo())
        self.assertEqual(game.capture_undo_state(), before)

    def chip_action(self, action, answer, confirmations=False):
        game = self.game(enable_chip_accounts=True, require_pot_withdrawal_confirmation=confirmations)
        game.chip_pot = 5
        game.players[0].hand = ["HAND"]
        gui = HeadlessGUI(game)
        gui.selection.synchronize(build_selection_snapshot(game))
        gui.selection.hand_index = 0
        chip = object.__new__(ChipBankUI)
        chip.gui = gui
        path = {"buy_chips": "ask_chip_purchase", "play_chips": "simpledialog.askinteger",
                "take_pot": "ask_pot_recipient"}[action]
        before = game.capture_undo_state()
        saved = game.session.checkpoint_callback = Mock(return_value=None)
        with patch("portable_deck.ui.chipbankui." + path, return_value=answer), patch(
                "portable_deck.ui.chipbankui.messagebox.showwarning") as warning, patch(
                "portable_deck.ui.chipbankui.messagebox.showerror") as error:
            result = getattr(chip, action)()
        return game, gui, before, saved, result, warning, error

    def test_chip_handlers_return_results_and_single_checkpoint_undo(self):
        for action, answer, confirmations in (("buy_chips", (0, 5), False), ("play_chips", 5, False),
                                              ("take_pot", 0, False), ("take_pot", 0, True)):
            with self.subTest(action=action, confirmations=confirmations):
                game, gui, before, saved, result, warning, error = self.chip_action(action, answer, confirmations)
                self.assertTrue(result.success, result.message)
                if action == "buy_chips":
                    self.assertEqual(result.value, 105)
                    self.assertEqual(game.chip_balance(0), 105)
                elif action == "play_chips":
                    self.assertEqual(game.chip_pot, 10)
                    self.assertEqual(game.chip_balance(0), 95)
                elif confirmations:
                    self.assertEqual(game.pending_pot_withdrawal["recipient"], 0)
                    self.assertEqual(game.chip_pot, 5)
                else:
                    self.assertEqual(game.chip_pot, 0)
                    self.assertEqual(game.chip_balance(0), 105)
                self.assertEqual(gui.selection.hand_index, 0)
                warning.assert_not_called()
                error.assert_not_called()
                saved.assert_called_once_with(game)
                self.assertEqual(len(game.undo_stack), 1)
                self.assert_single_refresh(gui)
                self.assertTrue(game.session.undo())
                self.assertEqual(game.capture_undo_state(), before)

    def test_chip_failures_keep_exact_message_code_and_state(self):
        for action, answer, code in (("buy_chips", (0, -1), "invalid_amount"),
                                     ("play_chips", 101, "insufficient_chips"),
                                     ("take_pot", 2, "invalid_target")):
            with self.subTest(action=action):
                game, gui, before, saved, result, warning, error = self.chip_action(action, answer)
                self.assertFalse(result.success)
                self.assertEqual(result.code, code)
                shown = error if action == "buy_chips" else warning
                self.assertEqual(shown.call_args.args[1], result.message)
                self.assertEqual(gui.selection.hand_index, 0)
                self.assertEqual(game.capture_undo_state(), before)
                self.assertEqual(game.undo_stack, [])
                saved.assert_not_called()
                self.assert_single_refresh(gui)

    def test_canceled_chip_dialogs_do_not_execute_or_persist(self):
        for action in ("buy_chips", "play_chips", "take_pot"):
            with self.subTest(action=action):
                game, gui, before, saved, result, warning, error = self.chip_action(action, None)
                self.assertIsNone(result)
                self.assertEqual(game.capture_undo_state(), before)
                self.assertEqual(gui.selection.hand_index, 0)
                self.assertEqual(game.undo_stack, [])
                saved.assert_not_called()
                warning.assert_not_called()
                error.assert_not_called()

    def test_hand_flip_and_score_reduction_failures_preserve_result_selection_and_state(self):
        for flip in (False, True):
            with self.subTest(flip=flip):
                game = self.game(score_enabled=True)
                game.players[0].hand = ["HAND"]
                gui = HeadlessGUI(game)
                gui.selection.synchronize(build_selection_snapshot(game))
                gui.selection.hand_index = 0
                saved = game.session.checkpoint_callback = Mock(return_value=None)
                before = game.capture_undo_state()
                with patch("portable_deck.ui.gameguiactions.messagebox.showwarning") as warning:
                    result = gui.flip_current_hand_card() if flip else gui.reduce_current_score()
                self.assertFalse(result.success)
                self.assertEqual(result.code, "action_disabled")
                warning.assert_called_once_with("Cannot flip card" if flip else "Cannot change score",
                                                result.message, parent=None)
                self.assertEqual(gui.selection.hand_index, 0)
                self.assertEqual(game.capture_undo_state(), before)
                self.assertEqual(game.undo_stack, [])
                saved.assert_not_called()
                self.assert_single_refresh(gui)

    def test_hand_flip_and_score_reduction_success_keep_single_transaction(self):
        for flip in (False, True):
            for confirmations in ((False,) if flip else (False, True)):
                with self.subTest(flip=flip, confirmations=confirmations):
                    game = self.game(score_enabled=True, allow_reduce_score=True,
                                     require_point_confirmation=confirmations,
                                     enable_flipping=True, allow_flip_hand=True)
                    game.players[0].hand = ["HAND"]
                    gui = HeadlessGUI(game)
                    gui.selection.synchronize(build_selection_snapshot(game))
                    gui.selection.hand_index = 0
                    saved = game.session.checkpoint_callback = Mock(return_value=None)
                    before = game.capture_undo_state()
                    with patch("portable_deck.ui.gameguiactions.messagebox.showwarning") as warning:
                        result = gui.flip_current_hand_card() if flip else gui.reduce_current_score()
                    self.assertTrue(result.success, result.message)
                    if flip:
                        self.assertEqual(result.value, "HAND")
                        self.assertEqual(game.players[0].revealed_indices, {0})
                    elif confirmations:
                        self.assertEqual(game.pending_point_request["delta"], -1)
                        self.assertEqual(game.scores, [0, 0])
                    else:
                        self.assertEqual(game.scores, [-1, 0])
                    self.assertEqual(gui.selection.hand_index, 0)
                    warning.assert_not_called()
                    saved.assert_called_once_with(game)
                    self.assertEqual(len(game.undo_stack), 1)
                    self.assert_single_refresh(gui)
                    self.assertTrue(game.session.undo())
                    self.assertEqual(game.capture_undo_state(), before)

    def test_player_leave_preserves_result_and_only_starts_turn_after_success(self):
        for allowed in (False, True):
            with self.subTest(allowed=allowed):
                game = self.game(enable_player_leaving=allowed)
                game.players[0].hand = ["HAND"]
                gui = HeadlessGUI(game)
                gui.selection.synchronize(build_selection_snapshot(game))
                gui.selection.hand_index = 0
                gui.handle_turn_start = Mock()
                before = game.capture_undo_state()
                saved = game.session.checkpoint_callback = Mock(return_value=None)
                with patch("portable_deck.ui.gameguiactions.messagebox.showwarning") as warning:
                    result = gui.leave_current_player()
                self.assertEqual(result.success, allowed)
                self.assert_single_refresh(gui)
                if allowed:
                    gui.handle_turn_start.assert_called_once()
                    self.assertEqual(game.left_players, [0])
                    self.assertIsNone(gui.selection.hand_index)
                    saved.assert_called_once_with(game)
                    self.assertEqual(len(game.undo_stack), 1)
                    warning.assert_not_called()
                    self.assertTrue(game.session.undo())
                    self.assertEqual(game.capture_undo_state(), before)
                else:
                    self.assertEqual(result.code, "action_disabled")
                    warning.assert_called_once_with("Cannot leave session", result.message, parent=None)
                    self.assertEqual(gui.selection.hand_index, 0)
                    gui.handle_turn_start.assert_not_called()
                    self.assertEqual(game.capture_undo_state(), before)
                    self.assertEqual(game.undo_stack, [])
                    saved.assert_not_called()

    def test_return_dialog_keeps_result_and_only_closes_or_starts_turn_on_success(self):
        for stale in (False, True):
            with self.subTest(stale=stale):
                game = self.game(enable_player_leaving=True, enable_player_return=True)
                game.left_players = [1]
                game.players[0].hand = ["HAND"]
                gui = HeadlessGUI(game)
                gui.selection.synchronize(build_selection_snapshot(game))
                gui.selection.hand_index = 0
                gui.handle_turn_start = Mock()
                dialog, choices = Mock(), Mock()
                choices.curselection.return_value = (0,)
                commands = {}
                def button(*args, **kwargs):
                    commands[kwargs["text"]] = kwargs["command"]
                    return Mock()
                with patch("portable_deck.ui.gameguiactions.tk.Toplevel", return_value=dialog), patch(
                        "portable_deck.ui.gameguiactions.tk.Listbox", return_value=choices), patch(
                        "portable_deck.ui.gameguiactions.tk.Button", side_effect=button), patch(
                        "portable_deck.ui.gameguiactions.messagebox.showwarning") as warning:
                    gui.choose_returning_player()
                    if stale:
                        game.left_players.clear()
                    before = game.capture_undo_state()
                    saved = game.session.checkpoint_callback = Mock(return_value=None)
                    result = commands["Return player"]()
                self.assertEqual(result.success, not stale)
                self.assert_single_refresh(gui)
                if stale:
                    self.assertEqual(result.code, "return_unavailable")
                    warning.assert_called_once_with("Cannot return player", result.message, parent=dialog)
                    dialog.destroy.assert_not_called()
                    gui.handle_turn_start.assert_not_called()
                    self.assertEqual(gui.selection.hand_index, 0)
                    self.assertEqual(game.capture_undo_state(), before)
                    self.assertEqual(game.undo_stack, [])
                    saved.assert_not_called()
                else:
                    dialog.destroy.assert_called_once()
                    gui.handle_turn_start.assert_called_once()
                    self.assertIsNone(gui.selection.hand_index)
                    self.assertEqual(game.left_players, [])
                    saved.assert_called_once_with(game)
                    self.assertEqual(len(game.undo_stack), 1)
                    warning.assert_not_called()
                    self.assertTrue(game.session.undo())
                    self.assertEqual(game.capture_undo_state(), before)

    def test_last_player_leave_does_not_start_another_turn(self):
        game = self.game(enable_player_leaving=True)
        game.left_players = [1]
        gui = HeadlessGUI(game)
        gui.handle_turn_start = Mock()
        result = gui.leave_current_player()
        self.assertTrue(result.success)
        self.assertFalse(game.active_player_indices())
        gui.handle_turn_start.assert_not_called()

    def test_discard_draw_returns_result_for_top_any_shared_and_personal_piles(self):
        for mode in ("top", "any"):
            for personal in (False, True):
                with self.subTest(mode=mode, personal=personal):
                    game = self.game(allow_draw_from_discard=True, draw_from_discard_mode=mode,
                                     personal_discard_pile_count=1)
                    game.players[0].hand = ["HAND"]
                    pile = game.personal_discard_piles[1][0] if personal else game.discard_pile
                    pile.extend(["DEEP", "TOP"])
                    source = 2 if personal else 0
                    index = 1 if mode == "top" else 0
                    gui = HeadlessGUI(game)
                    gui.selection.synchronize(build_selection_snapshot(game))
                    gui.selection.hand_index = 0
                    before = game.capture_undo_state()
                    saved = game.session.checkpoint_callback = Mock(return_value=None)
                    with patch("portable_deck.ui.cardactions.messagebox.showwarning") as warning:
                        result = gui.run_action(_take_discard_card, game, source, index,
                                                gui.hand_frame, gui.render_log, gui.status_panel)
                    self.assertTrue(result.success)
                    self.assertEqual(result.value, "TOP" if mode == "top" else "DEEP")
                    self.assertEqual(game.players[0].hand, ["HAND", result.value])
                    self.assertIsNone(gui.selection.hand_index)
                    warning.assert_not_called()
                    saved.assert_called_once_with(game)
                    self.assertEqual(len(game.undo_stack), 1)
                    self.assert_single_refresh(gui)
                    self.assertTrue(game.session.undo())
                    self.assertEqual(game.capture_undo_state(), before)

    def test_changed_discard_snapshot_is_rejected_without_clearing_hand_selection(self):
        for mode in ("top", "any"):
            with self.subTest(mode=mode):
                game = self.game(allow_draw_from_discard=True, draw_from_discard_mode=mode)
                game.players[0].hand = ["HAND"]
                game.discard_pile.extend(["DEEP", "TOP"])
                offered = build_player_discard_view(game, 0).piles[0].cards[0]
                game.discard_pile.pop()
                gui = HeadlessGUI(game)
                gui.selection.synchronize(build_selection_snapshot(game))
                gui.selection.hand_index = 0
                before = game.capture_undo_state()
                saved = game.session.checkpoint_callback = Mock(return_value=None)
                with patch("portable_deck.ui.cardactions.messagebox.showwarning") as warning:
                    result = gui.run_action(_take_discard_card, game, 0, offered.index,
                                            gui.hand_frame, gui.render_log, gui.status_panel)
                self.assertFalse(result.success)
                self.assertEqual(result.code, "invalid_parameters")
                warning.assert_called_once_with("Cannot draw from discard", result.message)
                self.assertEqual(gui.selection.hand_index, 0)
                self.assertEqual(game.capture_undo_state(), before)
                self.assertEqual(game.undo_stack, [])
                saved.assert_not_called()
                self.assert_single_refresh(gui)

    def turn_action(self, game, gui, action, callback):
        helper = {"draw_card": draw_card, "end_turn": end_turn, "request_point": request_point}[action]
        args = (game, gui.hand_frame, gui.render_log, gui.status_panel)
        return gui.run_action(helper, *args, *((callback,) if action == "end_turn" else ()))

    def test_turn_handlers_reject_pending_confirmation_without_selection_or_turn_side_effects(self):
        for action in ("draw_card", "end_turn", "request_point"):
            with self.subTest(action=action):
                game = self.game(score_enabled=True, require_point_confirmation=True)
                game.session.execute("request_point")
                game.session.execute("end_turn")
                game.players[1].hand = ["HAND"]
                gui = HeadlessGUI(game)
                gui.selection.synchronize(build_selection_snapshot(game))
                gui.selection.hand_index = 0
                before = game.capture_undo_state()
                undo_count = len(game.undo_stack)
                saved = game.session.checkpoint_callback = Mock(return_value=None)
                callback = Mock()
                with patch("portable_deck.ui.cardactions.messagebox.showwarning") as warning:
                    result = self.turn_action(game, gui, action, callback)
                self.assertFalse(result.success)
                self.assertEqual(result.code, "confirmation_required")
                self.assertEqual(warning.call_args.args[1], result.message)
                self.assertEqual(gui.selection.hand_index, 0)
                self.assertEqual(game.capture_undo_state(), before)
                self.assertEqual(len(game.undo_stack), undo_count)
                saved.assert_not_called()
                callback.assert_not_called()
                self.assert_single_refresh(gui)

    def test_draw_empty_and_score_disabled_report_original_failure(self):
        for action in ("draw_card", "request_point"):
            with self.subTest(action=action):
                game = self.game()
                game.deck.flat_deck.clear()
                gui = HeadlessGUI(game)
                saved = game.session.checkpoint_callback = Mock(return_value=None)
                before = game.capture_undo_state()
                with patch("portable_deck.ui.cardactions.messagebox.showwarning") as warning:
                    result = self.turn_action(game, gui, action, Mock())
                self.assertEqual(result.code, "empty_deck" if action == "draw_card" else "action_disabled")
                self.assertEqual(warning.call_args.args[1], result.message)
                self.assertEqual(game.capture_undo_state(), before)
                self.assertEqual(game.undo_stack, [])
                saved.assert_not_called()

    def test_turn_handler_success_returns_result_and_single_checkpoint_undo(self):
        for action in ("draw_card", "end_turn", "request_point"):
            with self.subTest(action=action):
                game = self.game(score_enabled=True)
                game.players[0].hand = ["HAND"]
                gui = HeadlessGUI(game)
                gui.selection.synchronize(build_selection_snapshot(game))
                gui.selection.hand_index = 0
                before = game.capture_undo_state()
                saved = game.session.checkpoint_callback = Mock(return_value=None)
                callback = Mock()
                with patch("portable_deck.ui.cardactions.messagebox.showwarning") as warning:
                    result = self.turn_action(game, gui, action, callback)
                self.assertTrue(result.success)
                if action == "end_turn":
                    self.assertEqual(game.current_player_index, 1)
                    self.assertIsNone(gui.selection.hand_index)
                    callback.assert_called_once()
                elif action == "draw_card":
                    self.assertEqual(len(game.players[0].hand), 2)
                    self.assertEqual(result.value, game.players[0].hand[-1])
                    callback.assert_not_called()
                else:
                    self.assertEqual(game.scores[0], 1)
                    callback.assert_not_called()
                warning.assert_not_called()
                saved.assert_called_once_with(game)
                self.assertEqual(len(game.undo_stack), 1)
                self.assert_single_refresh(gui)
                self.assertTrue(game.session.undo())
                self.assertEqual(game.capture_undo_state(), before)

    def remaining_table_action(self, game, gui, action):
        if action == "recycle_discard":
            return gui.run_action(recycle_discard_into_deck, game, gui.render_log, gui.status_panel, gui.root)
        helper = flip_selected_table_card if action == "flip_table_card" else clear_table
        return gui.run_action(helper, game, gui.table_frame, gui.render_log, gui.status_panel)

    def test_remaining_table_failures_report_result_without_clearing_valid_selection(self):
        for action in ("flip_table_card", "recycle_discard", "clear_table"):
            with self.subTest(action=action):
                game, gui = self.table_gui()
                if action == "flip_table_card":
                    game.allow_flip_table = False
                elif action == "recycle_discard":
                    game.allow_recycle_discard_to_deck = True
                    game.discard_pile.append("DISCARD")
                # Clear-table permission is disabled in this fixture.
                before = game.capture_undo_state()
                selection = (gui.selection.hand_index, gui.selection.table_index, gui.selection.target_position)
                saved = game.session.checkpoint_callback = Mock(return_value=None)
                with patch("portable_deck.ui.cardactions.messagebox.showwarning") as warning, patch(
                        "portable_deck.ui.cardactions.messagebox.showinfo") as info:
                    result = self.remaining_table_action(game, gui, action)
                self.assertFalse(result.success)
                self.assertEqual(result.code, "deck_not_empty" if action == "recycle_discard" else "action_disabled")
                if action == "recycle_discard":
                    info.assert_called_once_with("Cannot recycle", result.message, parent=gui.root)
                    warning.assert_not_called()
                else:
                    warning.assert_called_once_with("Invalid flip" if action == "flip_table_card" else "Cannot clear table", result.message)
                    info.assert_not_called()
                self.assertEqual((gui.selection.hand_index, gui.selection.table_index, gui.selection.target_position), selection)
                self.assertEqual(game.capture_undo_state(), before)
                self.assertEqual(game.undo_stack, [])
                saved.assert_not_called()
                self.assert_single_refresh(gui)

    def test_remaining_table_success_returns_result_and_one_checkpoint_undo_refresh(self):
        for action in ("flip_table_card", "recycle_discard", "clear_table"):
            with self.subTest(action=action):
                game, gui = self.table_gui()
                if action == "recycle_discard":
                    game.allow_recycle_discard_to_deck = True
                    game.deck.flat_deck.clear()
                    game.discard_pile.extend(["D1", "D2"])
                elif action == "clear_table":
                    game.allow_manual_table_cleanup = True
                before = game.capture_undo_state()
                saved = game.session.checkpoint_callback = Mock(return_value=None)
                with patch("portable_deck.ui.cardactions.messagebox.showwarning") as warning, patch(
                        "portable_deck.ui.cardactions.messagebox.showinfo") as info:
                    result = self.remaining_table_action(game, gui, action)
                self.assertTrue(result.success, result.message)
                if action == "flip_table_card":
                    self.assertEqual(result.value, "BASE")
                    self.assertFalse(game.table_cards[0]["face_up"])
                elif action == "clear_table":
                    self.assertEqual(result.value, 1)
                    self.assertEqual(game.table_cards, [])
                    self.assertEqual(game.discard_pile, ["BASE"])
                else:
                    self.assertEqual(result.value, 2)
                    self.assertCountEqual(game.deck.flat_deck, ["D1", "D2"])
                    self.assertEqual(game.discard_pile, [])
                    self.assertEqual(gui.selection.table_index, 0)
                if action != "recycle_discard":
                    self.assertIsNone(gui.selection.table_index)
                warning.assert_not_called()
                info.assert_not_called()
                saved.assert_called_once_with(game)
                self.assertEqual(len(game.undo_stack), 1)
                self.assert_single_refresh(gui)
                self.assertTrue(game.session.undo())
                self.assertEqual(game.capture_undo_state(), before)

    def table_gui(self, sequences=False):
        game, gui = self.play_gui("positioned")
        game.allow_take_from_table = True
        game.allow_move_cards_on_table = True
        game.allow_move_table_sequences = sequences
        if sequences:
            game.table_cards.append({"player": "Player1", "card": "BOTTOM", "position": [1, 0], "face_up": True})
        gui.selection.synchronize(build_selection_snapshot(game))
        gui.selection.table_index = 0
        gui.selection.target_position = (0, 1)
        return game, gui

    def table_action(self, game, gui, move):
        if move:
            return gui.run_action(move_selected_table_card, game, gui.table_frame, gui.render_log, gui.status_panel)
        return gui.run_action(take_selected_from_table, game, gui.table_frame, gui.hand_frame, gui.render_log, gui.status_panel)

    def test_table_handlers_report_core_failure_and_preserve_selection(self):
        for move, blocked in ((False, "disabled"), (True, "disabled"), (True, "occupied")):
            with self.subTest(move=move, blocked=blocked):
                game, gui = self.table_gui()
                if blocked == "occupied":
                    gui.selection.target_position = (0, 0)
                elif move:
                    game.allow_move_cards_on_table = False
                else:
                    game.allow_take_from_table = False
                before = game.capture_undo_state()
                target = gui.selection.target_position
                saved = game.session.checkpoint_callback = Mock(return_value=None)
                with patch("portable_deck.ui.cardactions.messagebox.showwarning") as warning:
                    result = self.table_action(game, gui, move)
                self.assertFalse(result.success)
                self.assertEqual(result.code, "invalid_target" if blocked == "occupied" else "action_disabled")
                warning.assert_called_once_with("Invalid move" if move else "Invalid", result.message)
                self.assertEqual(gui.selection.table_index, 0)
                self.assertEqual(gui.selection.target_position, target)
                self.assertEqual(game.capture_undo_state(), before)
                self.assertEqual(game.undo_stack, [])
                saved.assert_not_called()
                self.assert_single_refresh(gui)

    def test_table_handler_success_and_sequence_move_keep_single_transaction(self):
        for move, sequences in ((False, False), (True, False), (True, True)):
            with self.subTest(move=move, sequences=sequences):
                game, gui = self.table_gui(sequences)
                before = game.capture_undo_state()
                saved = game.session.checkpoint_callback = Mock(return_value=None)
                with patch("portable_deck.ui.cardactions.messagebox.showwarning") as warning:
                    result = self.table_action(game, gui, move)
                self.assertTrue(result.success, result.message)
                if move:
                    self.assertEqual(game.table_cards[0]["position"], [0, 1])
                    if sequences:
                        self.assertEqual(result.value, ["BASE", "BOTTOM"])
                        self.assertEqual(game.table_cards[1]["position"], [1, 1])
                else:
                    self.assertEqual(result.value, "BASE")
                    self.assertEqual(game.players[0].hand, ["HAND", "SECOND", "BASE"])
                self.assertIsNone(gui.selection.table_index)
                warning.assert_not_called()
                saved.assert_called_once_with(game)
                self.assertEqual(len(game.undo_stack), 1)
                self.assert_single_refresh(gui)
                self.assertTrue(game.session.undo())
                self.assertEqual(game.capture_undo_state(), before)

    def test_table_drag_routes_card_and_sequence_through_move_handler(self):
        for sequences in (False, True):
            with self.subTest(sequences=sequences):
                game, gui = self.table_gui(sequences)
                before = game.capture_undo_state()
                saved = game.session.checkpoint_callback = Mock(return_value=None)
                drag = object.__new__(CardDrag)
                drag.gui = gui
                self.assertTrue(drag.drop("table", 0, (0, 1)))
                self.assertEqual(game.table_cards[0]["position"], [0, 1])
                if sequences:
                    self.assertEqual(game.table_cards[1]["position"], [1, 1])
                saved.assert_called_once_with(game)
                self.assertEqual(len(game.undo_stack), 1)
                self.assert_single_refresh(gui)
                self.assertTrue(game.session.undo())
                self.assertEqual(game.capture_undo_state(), before)

    def play_gui(self, mode):
        game = self.game(enable_table=mode != "fallback", enable_discard_pile=mode != "fallback",
                         allow_positioned_play=mode in {"positioned", "hidden", "swap"},
                         enable_flipping=True, allow_flip_table=True, allow_face_down_table_cards=mode == "hidden",
                         occupied_slot_action="swap")
        game.players[0].hand = ["HAND", "SECOND"]
        game.players[0].revealed_indices = {0}
        if mode != "fallback":
            game.table_cards = [{"player": "Player1", "card": "BASE", "position": [0, 0], "face_up": True}]
        gui = HeadlessGUI(game)
        gui.table_frame.selection = gui.selection
        gui.selection.synchronize(build_selection_snapshot(game))
        gui.selection.hand_index = 0
        gui.selection.table_index = 0 if mode == "swap" else None
        gui.selection.target_position = None if mode == "swap" else (0, 1)
        return game, gui

    def play_action(self, game, gui, mode):
        helper = (play_selected_face_down if mode == "hidden" else
                  play_at_selected_spot if mode in {"positioned", "swap"} else play_selected)
        return gui.run_action(helper, game, gui.hand_frame, gui.table_frame, gui.render_log, gui.status_panel)

    def test_play_failures_preserve_core_reason_and_valid_selection(self):
        for mode in ("normal", "positioned", "hidden", "fallback", "swap"):
            with self.subTest(mode=mode):
                game, gui = self.play_gui(mode)
                if mode == "normal":
                    game.enable_table = False
                elif mode == "positioned":
                    gui.selection.target_position = (99, 99)
                elif mode == "hidden":
                    game.allow_face_down_table_cards = False
                elif mode == "fallback":
                    game.enable_interactions = True
                else:
                    game.occupied_slot_action = "invalid"
                before = game.capture_undo_state()
                selection = (gui.selection.hand_index, gui.selection.table_index, gui.selection.target_position)
                saved = game.session.checkpoint_callback = Mock(return_value=None)
                with patch("portable_deck.ui.cardactions.messagebox.showwarning") as warning:
                    result = self.play_action(game, gui, mode)
                self.assertFalse(result.success)
                self.assertEqual(result.code, "invalid_target" if mode == "positioned" else "action_disabled")
                warning.assert_called_once_with("Cannot swap cards" if mode == "swap" else "Invalid", result.message)
                self.assertEqual((gui.selection.hand_index, gui.selection.table_index, gui.selection.target_position), selection)
                self.assertEqual(game.capture_undo_state(), before)
                self.assertEqual(game.undo_stack, [])
                saved.assert_not_called()
                self.assert_single_refresh(gui)

    def test_play_success_returns_result_with_one_checkpoint_refresh_and_undo(self):
        for mode in ("normal", "positioned", "hidden", "fallback", "swap"):
            with self.subTest(mode=mode):
                game, gui = self.play_gui(mode)
                before = game.capture_undo_state()
                saved = game.session.checkpoint_callback = Mock(return_value=None)
                with patch("portable_deck.ui.cardactions.messagebox.showwarning") as warning:
                    result = self.play_action(game, gui, mode)
                self.assertTrue(result.success, result.message)
                self.assertIsNone(gui.selection.hand_index)
                self.assertEqual(result.value, ("HAND", "BASE") if mode == "swap" else "HAND")
                if mode == "fallback":
                    self.assertIn("HAND", game.deck.flat_deck)
                elif mode == "swap":
                    self.assertEqual(game.table_cards[0]["card"], "HAND")
                    self.assertEqual(game.players[0].hand, ["SECOND", "BASE"])
                else:
                    self.assertEqual(game.table_cards[-1]["card"], "HAND")
                    self.assertEqual(game.table_cards[-1]["face_up"], mode != "hidden")
                warning.assert_not_called()
                saved.assert_called_once_with(game)
                self.assertEqual(len(game.undo_stack), 1)
                self.assert_single_refresh(gui)
                self.assertTrue(game.session.undo())
                self.assertEqual(game.capture_undo_state(), before)

    def test_drag_hand_drop_uses_play_handler_once_with_occupied_table(self):
        for mode, position in (("normal", None), ("positioned", (0, 1))):
            with self.subTest(mode=mode):
                game, gui = self.play_gui(mode)
                before = game.capture_undo_state()
                saved = game.session.checkpoint_callback = Mock(return_value=None)
                drag = object.__new__(CardDrag)
                drag.gui = gui
                self.assertTrue(drag.drop("hand", 0, position))
                self.assertEqual([entry["card"] for entry in game.table_cards], ["BASE", "HAND"])
                self.assertEqual(game.table_cards[-1]["position"], [0, 1])
                saved.assert_called_once_with(game)
                self.assertEqual(len(game.undo_stack), 1)
                self.assert_single_refresh(gui)
                self.assertTrue(game.session.undo())
                self.assertEqual(game.capture_undo_state(), before)

    def discard_gui(self):
        game = self.game(allow_move_table_card_to_discard=True, personal_discard_pile_count=1)
        game.players[0].hand = ["HAND"]
        game.players[0].revealed_indices = {0}
        game.table_cards = [{"player": "Player1", "card": "TABLE", "position": [0, 0], "face_up": True}]
        gui = HeadlessGUI(game)
        gui.table_frame.selection = gui.selection
        gui.selection.synchronize(build_selection_snapshot(game))
        gui.selection.hand_index = gui.selection.table_index = 0
        gui.selection.target_position = (0, 1)
        return game, gui

    def discard_action(self, game, gui, table, destination):
        helper = _finish_table_discard if table else _discard_to_destination
        frame = gui.table_frame if table else gui.hand_frame
        return gui.run_action(helper, game, frame, gui.render_log, gui.status_panel, 0, destination)

    def test_discard_failures_display_core_message_and_preserve_valid_selection(self):
        for table in (False, True):
            for disabled in (False, True):
                with self.subTest(table=table, disabled=disabled):
                    game, gui = self.discard_gui()
                    destination = ("Missing", 99, False)
                    if disabled:
                        destination = ("Shared discard 1", 0, False)
                        if table:
                            game.allow_move_table_card_to_discard = False
                        else:
                            game.enable_discard_pile = False
                    saved = game.session.checkpoint_callback = Mock(return_value=None)
                    before = game.capture_undo_state()
                    with patch("portable_deck.ui.cardactions.messagebox.showwarning") as warning:
                        result = self.discard_action(game, gui, table, destination)
                    self.assertFalse(result.success)
                    self.assertEqual(result.code, "action_disabled" if disabled else "invalid_pile")
                    warning.assert_called_once_with("Invalid", result.message)
                    self.assertEqual((gui.selection.hand_index, gui.selection.table_index, gui.selection.target_position),
                                     (0, 0, (0, 1)))
                    self.assertEqual(game.capture_undo_state(), before)
                    self.assertEqual(game.undo_stack, [])
                    saved.assert_not_called()
                    self.assert_single_refresh(gui)

    def test_discard_success_has_one_checkpoint_undo_and_final_refresh(self):
        for table in (False, True):
            for personal in (False, True):
                with self.subTest(table=table, personal=personal):
                    game, gui = self.discard_gui()
                    before = game.capture_undo_state()
                    saved = game.session.checkpoint_callback = Mock(return_value=None)
                    with patch("portable_deck.ui.cardactions.messagebox.showwarning") as warning:
                        result = self.discard_action(game, gui, table, ("Destination", 0, personal))
                    self.assertTrue(result.success)
                    self.assertEqual(result.value, "TABLE" if table else "HAND")
                    self.assertIsNone(gui.selection.table_index if table else gui.selection.hand_index)
                    destination = game.personal_discard_piles[0][0] if personal else game.discard_piles[0]
                    self.assertEqual(destination, [result.value])
                    warning.assert_not_called()
                    saved.assert_called_once_with(game)
                    self.assertEqual(len(game.undo_stack), 1)
                    self.assert_single_refresh(gui)
                    self.assertTrue(game.session.undo())
                    self.assertEqual(game.capture_undo_state(), before)

    def test_discard_stale_source_is_cleared_by_existing_selection_sync(self):
        for table in (False, True):
            with self.subTest(table=table):
                game, gui = self.discard_gui()
                if table:
                    game.table_cards.clear()
                else:
                    game.players[0].hand.clear()
                    game.players[0].revealed_indices.clear()
                before = game.capture_undo_state()
                saved = game.session.checkpoint_callback = Mock(return_value=None)
                with patch("portable_deck.ui.cardactions.messagebox.showwarning") as warning:
                    result = self.discard_action(game, gui, table, ("Shared discard 1", 0, False))
                self.assertEqual(result.code, "invalid_selection")
                warning.assert_called_once_with("Invalid", result.message)
                self.assertIsNone(gui.selection.table_index if table else gui.selection.hand_index)
                self.assertEqual(game.capture_undo_state(), before)
                self.assertEqual(game.undo_stack, [])
                saved.assert_not_called()

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
