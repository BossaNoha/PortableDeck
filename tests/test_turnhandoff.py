import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from portable_deck.app.configurationinfo import configuration_info
from portable_deck.app.settings import DEFAULT_SETTINGS
from portable_deck.app.settingspresets import load_preset, save_preset
from portable_deck.core.game import Game
from portable_deck.core.selection import SelectionState
from portable_deck.core.selectionsnapshot import build_selection_snapshot
from portable_deck.ui.gameguiactions import GameGUIActions
from portable_deck.ui.turnhandoff import TurnHandoff


class HandoffGUI(GameGUIActions):
    def __init__(self, game, enabled=True):
        self.game, self.session = game, game.session
        self.confirm_next_turn = enabled
        self.selection = SelectionState()
        self.selection.synchronize(build_selection_snapshot(game))
        self.selection.hand_index = 0
        self.root, self.options_bar, self.layout_frame, self.next_button = Mock(), Mock(), Mock(), Mock()
        self.options_bar.pack_info.return_value = {"fill": "x"}
        self.layout_frame.pack_info.return_value = {"fill": "both", "expand": True}
        self.hand_frame = Mock()
        self.hand_frame.game_gui = self
        self.status_panel = Mock()
        for name in ("render_log", "refresh_session_panels", "update_undo_button", "update_leave_button",
                     "update_point_button", "update_chip_action_buttons", "refresh_action_availability"):
            setattr(self, name, Mock())
        self.turn_handoff = TurnHandoff(self)

    def _turn_action_buttons(self):
        return []


class TurnHandoffTests(unittest.TestCase):
    def setUp(self):
        for name in ("Frame", "Label", "Button"):
            patcher = patch("portable_deck.ui.turnhandoff.tk." + name)
            patcher.start()
            self.addCleanup(patcher.stop)

    def game(self, confirmations=False):
        game = Game(2, str(Path(__file__).resolve().parents[1] / "decks/demodeck.json"),
                    enable_undo=True, score_enabled=True, enable_chip_accounts=True,
                    require_point_confirmation=confirmations, require_pot_withdrawal_confirmation=confirmations)
        game.players[0].hand = ["FIRST SECRET"]
        game.players[1].hand = ["SECOND SECRET"]
        game.session.checkpoint_callback = Mock(return_value=None)
        return game

    def test_next_turn_hides_before_advancing_and_commits_only_when_ready(self):
        game = self.game()
        gui = HandoffGUI(game)
        before = game.capture_undo_state()
        self.assertIsNone(gui.next_turn())
        self.assertTrue(gui.turn_handoff.visible)
        gui.options_bar.pack_forget.assert_called_once()
        gui.layout_frame.pack_forget.assert_called_once()
        self.assertEqual(game.capture_undo_state(), before)
        self.assertEqual(game.undo_stack, [])
        game.session.checkpoint_callback.assert_not_called()
        def checkpoint(current):
            self.assertTrue(gui.turn_handoff.visible)
            return None
        game.session.checkpoint_callback.side_effect = checkpoint
        result = gui.turn_handoff.confirm()
        self.assertTrue(result.success)
        self.assertFalse(gui.turn_handoff.visible)
        self.assertEqual(game.current_player_index, 1)
        gui.layout_frame.pack.assert_called_once_with(fill="both", expand=True)
        game.session.checkpoint_callback.assert_called_once_with(game)
        self.assertEqual(len(game.undo_stack), 1)
        self.assertIsNone(gui.turn_handoff.confirm())
        game.session.checkpoint_callback.side_effect = None
        self.assertTrue(game.session.undo())
        self.assertEqual(game.capture_undo_state(), before)

    def test_cancel_and_repeated_next_click_do_not_advance_or_save(self):
        game = self.game()
        gui = HandoffGUI(game)
        before = game.capture_undo_state()
        gui.next_turn()
        gui.next_turn()
        gui.layout_frame.pack_forget.assert_called_once()
        gui.turn_handoff.cancel()
        self.assertFalse(gui.turn_handoff.visible)
        self.assertEqual(game.capture_undo_state(), before)
        self.assertEqual(gui.selection.hand_index, 0)
        self.assertEqual(game.undo_stack, [])
        game.session.checkpoint_callback.assert_not_called()

    def test_disabled_option_retains_immediate_turn_behavior(self):
        game = self.game()
        gui = HandoffGUI(game, enabled=False)
        self.assertTrue(gui.next_turn().success)
        self.assertEqual(game.current_player_index, 1)
        self.assertFalse(gui.turn_handoff.visible)
        gui.layout_frame.pack_forget.assert_not_called()
        game.session.checkpoint_callback.assert_called_once_with(game)

    def test_changed_availability_keeps_cover_and_selection_on_refusal(self):
        game = self.game(True)
        gui = HandoffGUI(game)
        gui.next_turn()
        game.pending_point_request = {"requester": 1, "confirmed_by": [], "delta": 1}
        before = game.capture_undo_state()
        with patch("portable_deck.ui.cardactions.messagebox.showwarning") as warning:
            result = gui.turn_handoff.confirm()
        self.assertEqual(result.code, "confirmation_required")
        self.assertEqual(warning.call_args.args[1], result.message)
        self.assertTrue(gui.turn_handoff.visible)
        self.assertEqual(gui.selection.hand_index, 0)
        self.assertEqual(game.capture_undo_state(), before)
        game.session.checkpoint_callback.assert_not_called()
        gui.turn_handoff.cancel()
        with patch("portable_deck.ui.cardactions.messagebox.showwarning"):
            self.assertEqual(gui.next_turn().code, "confirmation_required")
        self.assertFalse(gui.turn_handoff.visible)

    def test_score_and_pot_prompts_run_under_cover_in_one_transaction(self):
        game = self.game(True)
        for action, parameters in (("request_point", {}), ("play_chips", {"amount": 3}),
                                   ("take_pot", {"player_index": 0})):
            self.assertTrue(game.session.execute(action, **parameters).success)
        gui = HandoffGUI(game)
        count = len(game.undo_stack)
        game.session.checkpoint_callback.reset_mock()
        gui.next_turn()
        def approve(*args, **kwargs):
            self.assertTrue(gui.turn_handoff.visible)
            return True
        with patch("portable_deck.ui.gameguiactions.messagebox.askyesno", side_effect=approve) as prompt:
            self.assertTrue(gui.turn_handoff.confirm().success)
        self.assertEqual(prompt.call_count, 2)
        self.assertFalse(gui.turn_handoff.visible)
        self.assertEqual(game.scores, [1, 0])
        self.assertEqual(game.chip_pot, 0)
        self.assertEqual(len(game.undo_stack), count + 1)
        game.session.checkpoint_callback.assert_called_once_with(game)

    def test_preference_survives_preset_loading_without_changing_rule_metadata(self):
        settings = copy.deepcopy(DEFAULT_SETTINGS)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "Rules.json"
            saved = save_preset(path, settings)
            saved["confirm_next_turn"] = True
            self.assertFalse(configuration_info(saved)["modified"])
            loaded = load_preset(path, saved)
            self.assertTrue(loaded.settings["confirm_next_turn"])
            self.assertEqual(loaded.notices, ())
