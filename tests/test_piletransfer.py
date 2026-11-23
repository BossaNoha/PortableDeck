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
from portable_deck.core.piletransfer import transfer_pile_options
from tests.test_turnhandoff import HandoffGUI


class PileTransferTests(unittest.TestCase):
    def game(self):
        game = Game(3, str(Path(__file__).resolve().parents[1] / "decks/demodeck.json"),
                    enable_personal_piles=True, personal_pile_count=2, allow_transfer_personal_piles=True,
                    personal_pile_settings=[[{"access": "everyone"}] * 2 for _ in range(3)], enable_undo=True)
        game.start(0)
        game.personal_piles[0][0] = ["SECRET_A", "SECRET_B"]
        game.personal_piles[1][0] = ["OLD"]
        game.session.checkpoint_callback = Mock(return_value=None)
        return game

    def execute(self, game, **overrides):
        parameters = dict(source_owner=0, source_pile=0, target_owner=1, target_pile=0)
        parameters.update(overrides)
        return game.session.execute("transfer_personal_pile", **parameters)

    def test_transfer_preserves_block_order_and_one_undo_checkpoint(self):
        for bottom in (False, True):
            game = self.game()
            rule = game.personal_pile_settings[1][0]
            rule.update(ordered=True, order_by="time", new_card="bottom" if bottom else "top")
            before = game.capture_undo_state()
            result = self.execute(game)
            self.assertTrue(result.success)
            self.assertEqual(result.value, 2)
            self.assertEqual(game.personal_piles[0][0], [])
            expected = ["SECRET_A", "SECRET_B", "OLD"] if bottom else ["OLD", "SECRET_A", "SECRET_B"]
            self.assertEqual(game.personal_piles[1][0], expected)
            self.assertNotIn("SECRET", repr(result.events) + repr(result.messages))
            self.assertEqual(len(game.undo_stack), 1)
            game.session.checkpoint_callback.assert_called_once_with(game)
            self.assertTrue(game.session.undo())
            self.assertEqual(game.capture_undo_state(), before)

    def test_size_order_accepts_only_order_preserving_merge(self):
        game = self.game()
        game.personal_piles[0][0] = ["2 of Test", "3 of Test"]
        game.personal_piles[1][0] = ["4 of Test"]
        game.personal_pile_settings[1][0].update(ordered=True, order_by="size", size_order="up")
        before = game.capture_undo_state()
        self.assertEqual(self.execute(game).code, "ordering_conflict")
        self.assertEqual(game.capture_undo_state(), before)
        game.session.checkpoint_callback.assert_not_called()
        game.personal_piles[1][0] = ["1 of Test"]
        self.assertTrue(self.execute(game).success)
        self.assertEqual(game.personal_piles[1][0], ["1 of Test", "2 of Test", "3 of Test"])

    def test_invalid_or_unavailable_transfer_leaves_state_unchanged(self):
        for parameters in ({"source_owner": True}, {"source_pile": -1}, {"target_owner": 3},
                           {"target_pile": 2}, {"target_owner": 0, "target_pile": 0}):
            game = self.game()
            before = game.capture_undo_state()
            self.assertFalse(self.execute(game, **parameters).success)
            self.assertEqual(game.capture_undo_state(), before)
            game.session.checkpoint_callback.assert_not_called()
        for reason in ("disabled", "table", "piles", "actor", "target", "source_access", "target_access", "empty", "confirmation"):
            game = self.game()
            if reason == "disabled": game.allow_transfer_personal_piles = False
            elif reason == "table": game.enable_table = False
            elif reason == "piles": game.enable_personal_piles = False
            elif reason == "actor": game.left_players = [0]
            elif reason == "target": game.left_players = [1]
            elif reason == "source_access": game.personal_pile_settings[0][0]["access"] = "everyone_but_owner"
            elif reason == "target_access": game.personal_pile_settings[1][0]["access"] = "owner"
            elif reason == "empty": game.personal_piles[0][0].clear()
            else: game.current_player_must_confirm_point = lambda: True
            before = game.capture_undo_state()
            self.assertFalse(self.execute(game).success, reason)
            self.assertEqual(game.capture_undo_state(), before)
            game.session.checkpoint_callback.assert_not_called()

    def test_failed_log_rolls_back_both_piles(self):
        game = self.game()
        before = game.capture_undo_state()
        with patch.object(game, "log_action", side_effect=ValueError("log failed")):
            self.assertFalse(self.execute(game).success)
        self.assertEqual(game.capture_undo_state(), before)
        self.assertFalse(game.undo_stack)
        game.session.checkpoint_callback.assert_not_called()

    def test_options_are_private_and_allow_same_owner_different_pile(self):
        game = self.game()
        game.personal_pile_settings[2][0]["access"] = "owner"
        sources, targets = transfer_pile_options(game)
        self.assertNotIn("SECRET", repr((sources, targets)))
        self.assertFalse(any(p.owner == 2 and p.pile_index == 0 for p in targets))
        self.assertTrue(self.execute(game, target_owner=0, target_pile=1).success)

    def test_rule_save_preset_restart_and_legacy_defaults(self):
        game = self.game()
        self.execute(game)
        state = export_session(game)
        loaded = restore_session(Game, state)
        self.assertTrue(loaded.allow_transfer_personal_piles)
        self.assertEqual(loaded.capture_undo_state(), game.capture_undo_state())
        self.assertTrue(loaded.session.undo())
        self.assertEqual(loaded.personal_piles[0][0], ["SECRET_A", "SECRET_B"])
        self.assertTrue(game.restart().allow_transfer_personal_piles)
        del state["allow_transfer_personal_piles"]
        self.assertFalse(restore_session(Game, state).allow_transfer_personal_piles)
        with self.assertRaises(ValueError): restore_session(Game, dict(state, allow_transfer_personal_piles=1))
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "transfer.json"
            saved = save_preset(path, {"allow_transfer_personal_piles": True})
            self.assertTrue(load_preset(path, saved).settings["allow_transfer_personal_piles"])

    def test_gui_destination_is_revalidated(self):
        game = self.game()
        gui = HandoffGUI(game, enabled=False)
        source, target = Mock(), Mock()
        source.curselection.return_value = (0,)
        target.curselection.return_value = (2,)
        commands = {}
        def button(*args, **kwargs):
            commands[kwargs["text"]] = kwargs["command"]
            return Mock()
        with ExitStack() as stack:
            for widget in ("Toplevel", "Label"):
                stack.enter_context(patch("portable_deck.ui.gameguiactions.tk." + widget))
            stack.enter_context(patch("portable_deck.ui.gameguiactions.tk.Listbox", side_effect=[source, target]))
            stack.enter_context(patch("portable_deck.ui.gameguiactions.tk.Button", side_effect=button))
            warning = stack.enter_context(patch("portable_deck.ui.gameguiactions.messagebox.showwarning"))
            gui.transfer_personal_pile()
            game.left_players = [1]
            self.assertFalse(commands["Transfer pile"]().success)
            warning.assert_called_once()
            self.assertFalse(game.undo_stack)
            game.left_players = []
            self.assertTrue(commands["Transfer pile"]().success)

    def test_cli_privacy_handoff_and_flag(self):
        game = self.game()
        output = io.StringIO()
        client = CLIClient(game, output, structured=True, confirm_next_turn=True)
        client.command("end")
        client.command("transfer-pile 1 1 2 1")
        self.assertTrue(game.personal_piles[0][0])
        client.command("cancel")
        client.command("transfer-pile 1 1 2 1")
        self.assertFalse(game.personal_piles[0][0])
        self.assertNotIn("SECRET", output.getvalue())
        script = ("import sys; from portable_deck.cli import main; "
                  "main(['--transfer-personal-piles','--hand','0','--json']); "
                  "assert 'tkinter' not in sys.modules")
        result = subprocess.run([sys.executable, "-B", "-c", script], input="show\nquit\n",
                                text=True, capture_output=True, timeout=30, cwd=Path(__file__).resolve().parents[1])
        self.assertEqual(result.returncode, 0, result.stderr)
        view = next(json.loads(line)["view"] for line in result.stdout.splitlines() if json.loads(line)["type"] == "view")
        self.assertTrue(view["personal_piles"]["enabled"])
