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


class DiscardWholePileTests(unittest.TestCase):
    def game(self):
        game = Game(3, str(Path(__file__).resolve().parents[1] / "decks/demodeck.json"),
                    enable_personal_piles=True, personal_pile_count=2, allow_discard_whole_personal_pile=True,
                    personal_pile_settings=[[{"access": "everyone"}] * 2 for _ in range(3)],
                    shared_discard_pile_count=2, personal_discard_pile_count=2, enable_undo=True)
        game.start(0)
        game.personal_piles[1][0] = ["SECRET_A", "SECRET_B"]
        game.personal_piles[0][0] = ["OTHER"]
        game.session.checkpoint_callback = Mock(return_value=None)
        return game

    def execute(self, game, **overrides):
        parameters = dict(owner=1, pile_index=0, discard_pile_index=1)
        parameters.update(overrides)
        return game.session.execute("discard_whole_personal_pile", **parameters)

    def test_shared_personal_order_and_one_undo_checkpoint(self):
        for personal in (False, True):
            game = self.game()
            pile = game.personal_discard_piles[0][1] if personal else game.discard_piles[1]
            pile.append("OLD")
            before = game.capture_undo_state()
            result = self.execute(game, personal=personal)
            self.assertTrue(result.success)
            self.assertEqual(result.value, 2)
            self.assertEqual(pile, ["OLD", "SECRET_A", "SECRET_B"])
            self.assertEqual(game.personal_piles[1][0], [])
            self.assertEqual(game.personal_piles[0][0], ["OTHER"])
            self.assertEqual(game.personal_discard_piles[1], [[], []])
            self.assertNotIn("SECRET", repr(result.events) + repr(result.messages))
            self.assertEqual(len(game.undo_stack), 1)
            game.session.checkpoint_callback.assert_called_once_with(game)
            self.assertTrue(game.session.undo())
            self.assertEqual(game.capture_undo_state(), before)

    def test_one_card_pile_is_allowed(self):
        game = self.game()
        result = self.execute(game, owner=0)
        self.assertTrue(result.success)
        self.assertEqual(result.value, 1)
        self.assertEqual(game.discard_piles[1], ["OTHER"])

    def test_invalid_source_or_destination_preserves_state(self):
        for parameters in ({"owner": True}, {"owner": -1}, {"owner": 3}, {"pile_index": True},
                           {"pile_index": 2}, {"pile_index": 1}, {"discard_pile_index": -1},
                           {"discard_pile_index": True}, {"discard_pile_index": 2},
                           {"personal": 1}, {"personal": True, "discard_pile_index": 2}):
            game = self.game()
            before = game.capture_undo_state()
            self.assertFalse(self.execute(game, **parameters).success)
            self.assertEqual(game.capture_undo_state(), before)
            game.session.checkpoint_callback.assert_not_called()

    def test_disabled_features_access_empty_and_confirmation(self):
        for reason in ("disabled", "table", "piles", "discard", "actor", "access", "empty", "confirmation"):
            game = self.game()
            if reason == "disabled": game.allow_discard_whole_personal_pile = False
            elif reason == "table": game.enable_table = False
            elif reason == "piles": game.enable_personal_piles = False
            elif reason == "discard": game.enable_discard_pile = False
            elif reason == "actor": game.left_players = [0]
            elif reason == "access": game.personal_pile_settings[1][0]["access"] = "owner"
            elif reason == "empty": game.personal_piles = [[[], []] for _ in range(3)]
            else: game.current_player_must_confirm_point = lambda: True
            before = game.capture_undo_state()
            self.assertFalse(self.execute(game).success)
            self.assertEqual(game.capture_undo_state(), before)
            game.session.checkpoint_callback.assert_not_called()

    def test_failed_log_rolls_back_source_and_destination(self):
        game = self.game()
        before = game.capture_undo_state()
        with patch.object(game, "log_action", side_effect=ValueError("log failed")):
            self.assertFalse(self.execute(game).success)
        self.assertEqual(game.capture_undo_state(), before)
        self.assertFalse(game.undo_stack)
        game.session.checkpoint_callback.assert_not_called()

    def test_rule_save_preset_restart_and_legacy_defaults(self):
        game = self.game()
        self.execute(game, personal=True)
        state = export_session(game)
        loaded = restore_session(Game, state)
        self.assertTrue(loaded.allow_discard_whole_personal_pile)
        self.assertEqual(loaded.capture_undo_state(), game.capture_undo_state())
        self.assertTrue(loaded.session.undo())
        self.assertEqual(loaded.personal_piles[1][0], ["SECRET_A", "SECRET_B"])
        self.assertTrue(game.restart().allow_discard_whole_personal_pile)
        del state["allow_discard_whole_personal_pile"]
        self.assertFalse(restore_session(Game, state).allow_discard_whole_personal_pile)
        with self.assertRaises(ValueError): restore_session(Game, dict(state, allow_discard_whole_personal_pile=1))
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "discard.json"
            saved = save_preset(path, {"allow_discard_whole_personal_pile": True})
            self.assertTrue(load_preset(path, saved).settings["allow_discard_whole_personal_pile"])

    def test_gui_checks_source_access_again_and_uses_selected_destination(self):
        game = self.game()
        gui = HandoffGUI(game, enabled=False)
        source, destination = Mock(), Mock()
        source.curselection.return_value = (1,)
        destination.curselection.return_value = (3,)
        commands = {}
        def button(*args, **kwargs):
            commands[kwargs["text"]] = kwargs["command"]
            return Mock()
        with ExitStack() as stack:
            for widget in ("Toplevel", "Label"):
                stack.enter_context(patch("portable_deck.ui.gameguiactions.tk." + widget))
            stack.enter_context(patch("portable_deck.ui.gameguiactions.tk.Listbox", side_effect=[source, destination]))
            stack.enter_context(patch("portable_deck.ui.gameguiactions.tk.Button", side_effect=button))
            warning = stack.enter_context(patch("portable_deck.ui.gameguiactions.messagebox.showwarning"))
            gui.discard_whole_personal_pile()
            self.assertNotIn("SECRET", repr(source.insert.call_args_list))
            game.personal_pile_settings[1][0]["access"] = "owner"
            self.assertFalse(commands["Discard whole pile"]().success)
            warning.assert_called_once()
            self.assertFalse(game.undo_stack)
            game.personal_pile_settings[1][0]["access"] = "everyone"
            self.assertTrue(commands["Discard whole pile"]().success)
        self.assertEqual(game.personal_discard_piles[0][1], ["SECRET_A", "SECRET_B"])

    def test_cli_targets_privacy_handoff_and_flag(self):
        game = self.game()
        output = io.StringIO()
        client = CLIClient(game, output, structured=True, confirm_next_turn=True)
        client.command("end")
        client.command("discard-pile 2 1 shared 2")
        self.assertTrue(game.personal_piles[1][0])
        client.command("cancel")
        client.command("discard-pile 2 1 shared 2")
        self.assertEqual(game.discard_piles[1], ["SECRET_A", "SECRET_B"])
        client.command("discard-pile 1 1 personal 2")
        self.assertEqual(game.personal_discard_piles[0][1], ["OTHER"])
        self.assertNotIn("SECRET", output.getvalue())
        script = ("import sys; from portable_deck.cli import main; "
                  "main(['--discard-whole-personal-pile','--hand','0','--json']); "
                  "assert 'tkinter' not in sys.modules")
        result = subprocess.run([sys.executable, "-B", "-c", script], input="show\nquit\n",
                                text=True, capture_output=True, timeout=30, cwd=Path(__file__).resolve().parents[1])
        self.assertEqual(result.returncode, 0, result.stderr)
        view = next(json.loads(line)["view"] for line in result.stdout.splitlines() if json.loads(line)["type"] == "view")
        self.assertTrue(view["personal_piles"]["enabled"])
