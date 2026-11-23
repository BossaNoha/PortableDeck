import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import Mock, patch

from portable_deck.app.settingspresets import load_preset, save_preset
from portable_deck.cli import CLIClient
from portable_deck.core.game import Game
from portable_deck.core.gamesession import export_session, restore_session
from tests.test_turnhandoff import HandoffGUI


class TakeWholePileTests(unittest.TestCase):
    def game(self):
        game = Game(3, str(Path(__file__).resolve().parents[1] / "decks/demodeck.json"),
                    enable_personal_piles=True, personal_pile_count=2, allow_take_whole_personal_pile=True,
                    personal_pile_settings=[[{"access": "everyone"}] * 2 for _ in range(3)], enable_undo=True)
        game.start(0)
        game.players[0].hand = ["OLD"]
        game.players[0].revealed_indices = {0}
        game.personal_piles[1][0] = ["SECRET_A", "SECRET_B"]
        game.personal_piles[0][0] = ["OTHER"]
        game.session.checkpoint_callback = Mock(return_value=None)
        return game

    def test_whole_pile_preserves_order_visibility_and_one_undo_checkpoint(self):
        game = self.game()
        before = game.capture_undo_state()
        result = game.session.execute("take_whole_personal_pile", owner=1, pile_index=0)
        self.assertTrue(result.success)
        self.assertEqual(result.value, 2)
        self.assertEqual(game.personal_piles[1][0], [])
        self.assertEqual(game.players[0].hand, ["OLD", "SECRET_A", "SECRET_B"])
        self.assertEqual(game.players[0].revealed_indices, {0})
        self.assertEqual(game.personal_piles[0][0], ["OTHER"])
        self.assertNotIn("SECRET", repr(result.events) + repr(result.messages))
        self.assertEqual(len(game.undo_stack), 1)
        game.session.checkpoint_callback.assert_called_once_with(game)
        self.assertTrue(game.session.undo())
        self.assertEqual(game.capture_undo_state(), before)

    def test_one_card_pile_is_allowed(self):
        game = self.game()
        result = game.session.execute("take_whole_personal_pile", owner=0, pile_index=0)
        self.assertTrue(result.success)
        self.assertEqual(result.value, 1)
        self.assertEqual(game.players[0].hand, ["OLD", "OTHER"])

    def test_invalid_empty_or_inaccessible_pile_preserves_state(self):
        for owner, pile in ((True, 0), (-1, 0), (3, 0), (1, True), (1, -1), (1, 2), (1, 1)):
            game = self.game()
            before = game.capture_undo_state()
            self.assertFalse(game.session.execute("take_whole_personal_pile", owner=owner, pile_index=pile).success)
            self.assertEqual(game.capture_undo_state(), before)
            game.session.checkpoint_callback.assert_not_called()
        game = self.game()
        game.personal_pile_settings[1][0]["access"] = "owner"
        before = game.capture_undo_state()
        self.assertEqual(game.session.execute("take_whole_personal_pile", owner=1, pile_index=0).code, "access_denied")
        self.assertEqual(game.capture_undo_state(), before)
        game.session.checkpoint_callback.assert_not_called()

    def test_unavailable_action_preserves_state(self):
        for reason in ("disabled", "table", "piles", "actor", "empty", "confirmation"):
            game = self.game()
            if reason == "disabled": game.allow_take_whole_personal_pile = False
            elif reason == "table": game.enable_table = False
            elif reason == "piles": game.enable_personal_piles = False
            elif reason == "actor": game.left_players = [0]
            elif reason == "empty": game.personal_piles = [[[], []] for _ in range(3)]
            else: game.current_player_must_confirm_point = lambda: True
            before = game.capture_undo_state()
            self.assertFalse(game.session.execute("take_whole_personal_pile", owner=1, pile_index=0).success)
            self.assertEqual(game.capture_undo_state(), before)
            game.session.checkpoint_callback.assert_not_called()

    def test_failed_log_rolls_back_hand_and_pile(self):
        game = self.game()
        before = game.capture_undo_state()
        with patch.object(game, "log_action", side_effect=ValueError("log failed")):
            result = game.session.execute("take_whole_personal_pile", owner=1, pile_index=0)
        self.assertFalse(result.success)
        self.assertEqual(game.capture_undo_state(), before)
        self.assertFalse(game.undo_stack)
        game.session.checkpoint_callback.assert_not_called()

    def test_rule_save_preset_restart_and_legacy_defaults(self):
        game = self.game()
        game.session.execute("take_whole_personal_pile", owner=1, pile_index=0)
        state = export_session(game)
        loaded = restore_session(Game, state)
        self.assertTrue(loaded.allow_take_whole_personal_pile)
        self.assertEqual(loaded.capture_undo_state(), game.capture_undo_state())
        self.assertTrue(loaded.session.undo())
        self.assertEqual(loaded.personal_piles[1][0], ["SECRET_A", "SECRET_B"])
        self.assertTrue(game.restart().allow_take_whole_personal_pile)
        del state["allow_take_whole_personal_pile"]
        self.assertFalse(restore_session(Game, state).allow_take_whole_personal_pile)
        with self.assertRaises(ValueError): restore_session(Game, dict(state, allow_take_whole_personal_pile=1))
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "take.json"
            saved = save_preset(path, {"allow_take_whole_personal_pile": True})
            self.assertTrue(load_preset(path, saved).settings["allow_take_whole_personal_pile"])

    def test_gui_selector_checks_permissions_again(self):
        game = self.game()
        gui = HandoffGUI(game, enabled=False)
        commands = {}
        def button(*args, **kwargs):
            commands[kwargs["text"]] = kwargs["command"]
            return Mock()
        with ExitStack() as stack:
            for widget in ("Toplevel", "Label"):
                stack.enter_context(patch("portable_deck.ui.gameguiactions.tk." + widget))
            choices = stack.enter_context(patch("portable_deck.ui.gameguiactions.tk.Listbox")).return_value
            choices.curselection.return_value = (1,)
            stack.enter_context(patch("portable_deck.ui.gameguiactions.tk.Button", side_effect=button))
            warning = stack.enter_context(patch("portable_deck.ui.gameguiactions.messagebox.showwarning"))
            gui.take_whole_personal_pile()
            self.assertNotIn("SECRET", repr(choices.insert.call_args_list))
            game.personal_pile_settings[1][0]["access"] = "owner"
            self.assertFalse(commands["Take whole pile"]().success)
            warning.assert_called_once()
            self.assertFalse(game.undo_stack)
            game.personal_pile_settings[1][0]["access"] = "everyone"
            self.assertTrue(commands["Take whole pile"]().success)

    def test_cli_privacy_handoff_and_flag(self):
        game = self.game()
        output = io.StringIO()
        client = CLIClient(game, output, structured=True, confirm_next_turn=True)
        client.command("end")
        client.command("take-pile 2 1")
        self.assertTrue(game.personal_piles[1][0])
        client.command("cancel")
        client.command("take-pile 2 1")
        self.assertFalse(game.personal_piles[1][0])
        self.assertNotIn("SECRET", output.getvalue())
        script = ("import sys; from portable_deck.cli import main; "
                  "main(['--take-whole-personal-pile','--hand','0','--json']); "
                  "assert 'tkinter' not in sys.modules")
        result = subprocess.run([sys.executable, "-B", "-c", script], input="show\nquit\n",
                                text=True, capture_output=True, timeout=30, cwd=Path(__file__).resolve().parents[1])
        self.assertEqual(result.returncode, 0, result.stderr)
        view = next(json.loads(line)["view"] for line in result.stdout.splitlines() if json.loads(line)["type"] == "view")
        self.assertTrue(view["personal_piles"]["enabled"])
