import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from portable_deck.core.actionavailability import action_availability
from portable_deck.core.game import Game
from portable_deck.core.selection import SelectionState
from portable_deck.ui.gameguiactions import GameGUIActions
from portable_deck.ui.actionavailability import action_reason, selected_action_available


class Button:
    def __init__(self):
        self.state = "normal"
        self._availability_tooltip = True

    def configure(self, **values):
        self.state = values["state"]

    config = configure


class ControlsGUI(GameGUIActions):
    def __init__(self, game):
        self.game, self.session = game, game.session
        self.root = None
        self.selection = SelectionState()
        self.point_button, self.reduce_score_button, self.leave_session_button = Button(), Button(), Button()
        self.refresh_session_panels = Mock()
        self.update_chip_action_buttons = Mock()
        self.render_log = Mock()

    def _turn_action_buttons(self):
        return [self.point_button, self.reduce_score_button, self.leave_session_button]


class ControlAvailabilityTests(unittest.TestCase):
    def test_return_button_and_reason_track_options_pending_requests_and_undo(self):
        game = self.game()
        gui = ControlsGUI(game)
        gui.return_player_button = Button()
        def check(allowed):
            gui.update_leave_button()
            options = game.session.return_player_options()
            self.assertEqual(options.allowed, allowed)
            self.assertEqual(gui.return_player_button.state, "normal" if allowed else "disabled")
            self.assertEqual(action_reason(gui, gui.return_player_button), options.reason)
            self.assertEqual(selected_action_available(gui, "return_player"), allowed)
        check(False)
        game.session.execute("leave_session")
        check(True)
        snapshot = game.session.return_player_options()
        game.session.execute("request_point")
        # One remaining player scores immediately, so explicitly prepare a
        # pending request to check the same return restriction for both types.
        for field in ("pending_point_request", "pending_pot_withdrawal"):
            setattr(game, field, {"requester": 1, "confirmed_by": []})
            check(False)
            setattr(game, field, None)
        check(True)
        game.enable_player_return = False
        check(False)
        game.enable_player_return = True
        self.assertTrue(game.session.execute("leave_session").success)
        check(True)  # Return remains usable when all turn actions are blocked.
        self.assertTrue(game.session.execute("return_player", player_index=0).success)
        self.assertTrue(game.session.execute("return_player", player_index=1).success)
        check(False)
        self.assertTrue(game.session.undo())
        check(True)
        self.assertEqual([player.index for player in snapshot.players], [0])
        self.assertTrue(snapshot.allowed)

    def test_next_turn_tracks_pending_votes_all_left_return_and_undo(self):
        game = self.game()
        gui = ControlsGUI(game)
        gui.next_button = Button()
        def check(allowed):
            gui.update_leave_button()
            availability = game.session.end_turn_availability()
            self.assertEqual(availability.allowed, allowed)
            self.assertEqual(gui.next_button.state, "normal" if allowed else "disabled")
            self.assertEqual(action_reason(gui, gui.next_button), availability.reason)
            self.assertEqual(selected_action_available(gui, "end_turn"), allowed)
        check(True)
        game.session.execute("request_point")
        game.session.execute("play_chips", amount=3)
        game.session.execute("take_pot", player_index=0)
        check(True)  # Requester need not vote on their own request.
        game.session.execute("end_turn")
        check(False)
        game.session.execute("confirm_point", approved=False)
        check(False)  # Pot vote is still pending.
        game.session.execute("confirm_pot", approved=True)
        check(True)
        game.session.execute("leave_session")
        game.session.execute("leave_session")
        check(False)
        game.session.execute("return_player", player_index=0)
        check(True)
        self.assertTrue(game.session.undo())
        check(False)

    def test_undo_button_uses_session_query_for_empty_available_and_disabled_states(self):
        game = self.game()
        gui = SimpleNamespace(session=game.session, undo_button=Button())
        GameGUIActions.update_undo_button(gui)
        self.assertEqual(gui.undo_button.state, "disabled")
        self.assertTrue(game.session.execute("draw_card").success)
        GameGUIActions.update_undo_button(gui)
        self.assertEqual(gui.undo_button.state, "normal")
        game.enable_undo = False
        GameGUIActions.update_undo_button(gui)
        self.assertEqual(gui.undo_button.state, "disabled")
        game.enable_undo = True
        self.assertTrue(game.session.undo())
        GameGUIActions.update_undo_button(gui)
        self.assertEqual(gui.undo_button.state, "disabled")

    def game(self):
        return Game(2, str(Path(__file__).resolve().parents[1] / "decks/demodeck.json"),
                    enable_undo=True, score_enabled=True, allow_reduce_score=True,
                    require_point_confirmation=True, enable_player_leaving=True, enable_player_return=True,
                    enable_chip_accounts=True, require_pot_withdrawal_confirmation=True)

    def assert_states(self, gui, expected):
        gui.update_point_button()
        gui.update_leave_button()
        buttons = gui._turn_action_buttons()
        self.assertEqual(tuple(button.state for button in buttons), expected)
        for button, action in zip(buttons, ("request_point", "reduce_score", "leave_session")):
            self.assertEqual(button.state == "normal", action_availability(gui.game, action).allowed)

    def test_rule_and_pending_changes_match_core_availability(self):
        game = self.game()
        gui = ControlsGUI(game)
        self.assert_states(gui, ("normal", "normal", "normal"))
        game.allow_reduce_score = False
        self.assert_states(gui, ("normal", "disabled", "normal"))
        game.allow_reduce_score = True
        self.assertTrue(game.session.execute("request_point").success)
        self.assert_states(gui, ("disabled", "disabled", "disabled"))
        self.assertTrue(game.session.execute("end_turn").success)
        self.assert_states(gui, ("disabled", "disabled", "disabled"))
        self.assertTrue(game.session.execute("confirm_point", approved=False).success)
        self.assert_states(gui, ("normal", "normal", "normal"))
        game.leave_conditions["no_chips"] = True
        self.assert_states(gui, ("normal", "normal", "disabled"))

    def test_all_left_return_and_undo_recompute_controls(self):
        game = self.game()
        gui = ControlsGUI(game)
        for _ in range(2):
            self.assertTrue(game.session.execute("leave_session").success)
        self.assert_states(gui, ("disabled", "disabled", "disabled"))
        self.assertTrue(game.session.execute("return_player", player_index=0).success)
        self.assert_states(gui, ("normal", "normal", "normal"))
        self.assertTrue(game.session.undo())
        self.assert_states(gui, ("disabled", "disabled", "disabled"))
        self.assertTrue(game.session.undo())
        self.assert_states(gui, ("normal", "normal", "normal"))

    def test_dialogs_keep_controls_blocked_and_restore_core_state(self):
        game = self.game()
        for action, parameters in (("request_point", {}), ("play_chips", {"amount": 3}),
                                   ("take_pot", {"player_index": 0}), ("end_turn", {})):
            self.assertTrue(game.session.execute(action, **parameters).success)
        gui = ControlsGUI(game)
        decisions = iter((False, True))
        def decide(*args, **kwargs):
            self.assertTrue(all(button.state == "disabled" for button in gui._turn_action_buttons()))
            return next(decisions)
        with patch("portable_deck.ui.gameguiactions.messagebox.askyesno", side_effect=decide) as prompt:
            gui.handle_turn_start()
        self.assertEqual(prompt.call_count, 2)
        self.assertIsNone(game.pending_point_request)
        self.assertIsNone(game.pending_pot_withdrawal)
        self.assert_states(gui, ("normal", "normal", "normal"))
        self.assertTrue(game.session.undo())
        self.assert_states(gui, ("disabled", "disabled", "disabled"))
