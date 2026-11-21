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


class BulkTakeTests(unittest.TestCase):
    def game(self):
        game = Game(3, str(Path(__file__).resolve().parents[1] / "decks/demodeck.json"),
                    allow_take_from_table=True, allow_take_multiple_cards=True, enable_undo=True)
        game.start(0)
        game.players[0].hand = ["OLD"]
        game.players[0].revealed_indices = {0}
        game.table_cards = [dict(player="Player2", card=card, position=[0, i * 2], face_up=i != 2)
                            for i, card in enumerate(["A", "B", "HIDDEN_SECRET", "D"])]
        game.session.checkpoint_callback = Mock(return_value=None)
        return game

    def test_batch_order_positions_privacy_and_single_undo_checkpoint(self):
        game = self.game()
        before = game.capture_undo_state()
        result = game.session.execute("take_table_cards", card_indices=[3, 0, 2])
        self.assertTrue(result.success)
        self.assertEqual(game.players[0].hand, ["OLD", "A", "HIDDEN_SECRET", "D"])
        self.assertEqual(game.players[0].revealed_indices, {0})
        self.assertEqual(game.table_cards, [before["table_cards"][1]])
        self.assertNotIn("HIDDEN_SECRET", repr(result.events) + repr(result.messages))
        self.assertEqual(len(game.undo_stack), 1)
        game.session.checkpoint_callback.assert_called_once_with(game)
        self.assertTrue(game.session.undo())
        self.assertEqual(game.capture_undo_state(), before)

    def test_invalid_indices_fail_before_any_removal(self):
        for indices in (None, [], [0], [0, 0], [True, 1], [0, 4], [0, -1], [0, "1"]):
            game = self.game()
            before = game.capture_undo_state()
            with patch.object(game, "take_from_table", wraps=game.take_from_table) as take:
                result = game.session.execute("take_table_cards", card_indices=indices)
            self.assertEqual(result.code, "invalid_selection")
            take.assert_not_called()
            self.assertEqual(game.capture_undo_state(), before)
            game.session.checkpoint_callback.assert_not_called()

    def test_unavailable_batch_preserves_state(self):
        for reason in ("disabled", "single_disabled", "no_table", "departed", "confirmation", "one_card"):
            game = self.game()
            if reason == "disabled":
                game.allow_take_multiple_cards = False
            elif reason == "single_disabled":
                game.allow_take_from_table = False
            elif reason == "no_table":
                game.enable_table = False
            elif reason == "departed":
                game.left_players = [0]
            elif reason == "confirmation":
                game.current_player_must_confirm_point = lambda: True
            else:
                game.table_cards = game.table_cards[:1]
            before = game.capture_undo_state()
            self.assertFalse(game.session.execute("take_table_cards", card_indices=[0, 1]).success)
            self.assertEqual(game.capture_undo_state(), before)
            game.session.checkpoint_callback.assert_not_called()

    def test_later_failure_rolls_back_entire_batch(self):
        game = self.game()
        before = game.capture_undo_state()
        take = game.take_from_table
        calls = []
        def fail_second(index):
            calls.append(index)
            return take(index) if len(calls) == 1 else None
        with patch.object(game, "take_from_table", side_effect=fail_second):
            result = game.session.execute("take_table_cards", card_indices=[0, 2])
        self.assertFalse(result.success)
        self.assertFalse(result.events)
        self.assertEqual(game.capture_undo_state(), before)
        self.assertFalse(game.undo_stack)
        game.session.checkpoint_callback.assert_not_called()

    def test_save_preset_restart_and_legacy_default(self):
        game = self.game()
        game.session.execute("take_table_cards", card_indices=[0, 2])
        state = export_session(game)
        loaded = restore_session(Game, state)
        self.assertTrue(loaded.allow_take_multiple_cards)
        self.assertEqual(loaded.capture_undo_state(), game.capture_undo_state())
        self.assertTrue(loaded.session.undo())
        self.assertEqual(len(loaded.table_cards), 4)
        self.assertTrue(game.restart().allow_take_multiple_cards)
        del state["allow_take_multiple_cards"]
        self.assertFalse(restore_session(Game, state).allow_take_multiple_cards)
        with self.assertRaises(ValueError):
            restore_session(Game, dict(state, allow_take_multiple_cards=1))
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "take.json"
            saved = save_preset(path, {"allow_take_multiple_cards": True, "allow_take_from_table": True})
            self.assertTrue(load_preset(path, saved).settings["allow_take_multiple_cards"])

    def test_gui_uses_hidden_projection_and_rejects_stale_table(self):
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
            choices.curselection.return_value = (0, 2)
            stack.enter_context(patch("portable_deck.ui.gameguiactions.tk.Button", side_effect=button))
            warning = stack.enter_context(patch("portable_deck.ui.gameguiactions.messagebox.showwarning"))
            gui.take_multiple_cards()
            self.assertNotIn("HIDDEN_SECRET", repr(choices.insert.call_args_list))
            self.assertTrue(commands["Take selected cards"]().success)
            gui.take_multiple_cards()
            game.table_cards.reverse()
            before = game.capture_undo_state()
            commands["Take selected cards"]()
            warning.assert_called_once()
            self.assertEqual(game.capture_undo_state(), before)

    def test_cli_handoff_blocks_take_and_never_prints_private_results(self):
        game = self.game()
        output = io.StringIO()
        client = CLIClient(game, output, structured=True, confirm_next_turn=True)
        client.command("end")
        client.command("take-many 1 3")
        self.assertEqual(len(game.table_cards), 4)
        client.command("cancel")
        client.command("take-many 1 3")
        self.assertEqual(len(game.table_cards), 2)
        self.assertNotIn("HIDDEN_SECRET", output.getvalue())

    def test_cli_flag_works_without_tkinter(self):
        script = ("import sys; from portable_deck.cli import main; "
                  "main(['--take-multiple-cards','--play-multiple-cards','--hand','3','--json']); "
                  "assert 'tkinter' not in sys.modules")
        result = subprocess.run([sys.executable, "-B", "-c", script],
                                input="play-many 1 3\ntake-many 1 2\nshow\nquit\n", text=True, capture_output=True,
                                timeout=30, cwd=Path(__file__).resolve().parents[1])
        self.assertEqual(result.returncode, 0, result.stderr)
        records = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertTrue(all(r["success"] for r in records if r["type"] == "result"))
        view = next(r["view"] for r in records if r["type"] == "view")
        self.assertEqual(view["status"]["table_count"], 0)
