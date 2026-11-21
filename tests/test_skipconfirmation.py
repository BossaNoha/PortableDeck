import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from portable_deck.app.settings import DEFAULT_SETTINGS
from portable_deck.app.settingspresets import load_preset, save_preset
from portable_deck.app.turnhandoff import TurnHandoffController
from portable_deck.cli import CLIClient
from portable_deck.core.game import Game
from tests.test_turnhandoff import HandoffGUI


class SkipConfirmationTests(unittest.TestCase):
    def game(self):
        game = Game(3, str(Path(__file__).resolve().parents[1] / "decks/demodeck.json"),
                    allow_skip_next_player=True, enable_undo=True)
        game.start(0)
        game.session.checkpoint_callback = Mock(return_value=None)
        return game

    def test_confirm_and_cancel_are_non_mutating_until_accepted(self):
        game = self.game()
        flow = TurnHandoffController(game.session, confirm_skip=True)
        before = game.capture_undo_state()
        advance = lambda: game.session.execute("end_turn", skip_next=True)
        self.assertEqual(flow.request(advance, skip_next=True).code, "skip_confirmation_required")
        self.assertEqual(flow.confirm().code, "skip_confirmation_required")
        self.assertFalse(flow.confirm().success)
        self.assertEqual(flow.request(advance, skip_next=True).code, "handoff_pending")
        self.assertEqual(game.capture_undo_state(), before)
        self.assertEqual(flow.cancel().code, "skip_cancelled")
        self.assertFalse(flow.pending)
        game.session.checkpoint_callback.assert_not_called()
        flow.request(advance, skip_next=True)
        self.assertTrue(flow.confirm_skip().success)
        self.assertEqual(game.current_player_index, 2)
        self.assertEqual(len(game.undo_stack), 1)
        game.session.checkpoint_callback.assert_called_once_with(game)
        self.assertEqual(flow.confirm_skip().code, "skip_not_pending")
        self.assertTrue(game.session.undo())
        self.assertEqual(game.capture_undo_state(), before)

    def test_skip_confirmation_precedes_hotseat_handoff(self):
        game = self.game()
        flow = TurnHandoffController(game.session, enabled=True, confirm_skip=True)
        advance = lambda: game.session.execute("end_turn", skip_next=True)
        flow.request(advance, skip_next=True)
        self.assertEqual(flow.confirm_skip().code, "handoff_required")
        self.assertFalse(flow.awaiting_skip)
        self.assertEqual(game.current_player_index, 0)
        game.session.checkpoint_callback.assert_not_called()
        self.assertEqual(flow.cancel().code, "handoff_cancelled")
        flow.request(advance, skip_next=True)
        flow.confirm_skip()
        self.assertTrue(flow.confirm().success)
        self.assertEqual(game.current_player_index, 2)
        self.assertEqual(len(game.undo_stack), 1)

    def test_availability_is_rechecked_at_confirmation_and_ready(self):
        for hotseat in (False, True):
            with self.subTest(hotseat=hotseat):
                game = self.game()
                flow = TurnHandoffController(game.session, enabled=hotseat, confirm_skip=True)
                advance = lambda: game.session.execute("end_turn", skip_next=True)
                flow.request(advance, skip_next=True)
                game.allow_skip_next_player = False
                self.assertEqual(flow.confirm_skip().code, "action_disabled")
                self.assertTrue(flow.awaiting_skip)
                self.assertEqual(game.current_player_index, 0)
                game.session.checkpoint_callback.assert_not_called()
                game.allow_skip_next_player = True
                if hotseat:
                    flow.confirm_skip()
                    game.left_players = [1, 2]
                    self.assertEqual(flow.confirm().code, "not_enough_players")
                    self.assertTrue(flow.pending)
                    game.session.checkpoint_callback.assert_not_called()
                flow.cancel()

    def test_gui_cancel_accept_and_ordinary_turn(self):
        for accepted in (False, True):
            with self.subTest(accepted=accepted):
                game = self.game()
                gui = HandoffGUI(game, enabled=False)
                gui.confirm_skip = True
                with patch("portable_deck.ui.gameguiactions.messagebox.askyesno", return_value=accepted) as question:
                    result = gui.next_turn(skip_next=True)
                question.assert_called_once()
                self.assertTrue(result.success)
                self.assertEqual(game.current_player_index, 2 if accepted else 0)
                self.assertFalse(gui.turn_flow.pending)
                if not accepted:
                    game.session.checkpoint_callback.assert_not_called()
                with patch("portable_deck.ui.gameguiactions.messagebox.askyesno") as question:
                    gui.next_turn()
                question.assert_not_called()

    def test_cli_requires_explicit_confirmation_and_blocks_other_commands(self):
        game = self.game()
        output = io.StringIO()
        client = CLIClient(game, output, structured=True, confirm_skip=True)
        client.command("skip")
        self.assertEqual(json.loads(output.getvalue().splitlines()[-1])["code"], "skip_confirmation_required")
        for command in ("draw", "end", "show", "undo", "ready"):
            client.command(command)
            self.assertEqual(game.current_player_index, 0)
        game.session.checkpoint_callback.assert_not_called()
        client.command("cancel")
        self.assertFalse(client.turn_flow.pending)
        client.command("skip")
        client.command("confirm-skip")
        self.assertEqual(game.current_player_index, 2)
        self.assertEqual(len(game.undo_stack), 1)

    def test_confirmation_preference_is_preserved_when_loading_presets(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "preset.json"
            save_preset(path, dict(DEFAULT_SETTINGS, confirm_skip=False))
            self.assertNotIn("confirm_skip", json.loads(path.read_text(encoding="utf-8"))["settings"])
            loaded = load_preset(path, dict(DEFAULT_SETTINGS, confirm_skip=True))
            self.assertTrue(loaded.settings["confirm_skip"])

    def test_cli_flags_combine_skip_confirmation_with_hotseat(self):
        script = ("import sys; from portable_deck.cli import main; "
                  "main(['--skip-next-player','--confirm-skip','--confirm-next-turn','--players','3','--hand','0','--json']); "
                  "assert 'tkinter' not in sys.modules")
        result = subprocess.run([sys.executable, "-B", "-c", script],
                                input="skip\nconfirm-skip\nready\nshow\nquit\n", text=True, capture_output=True,
                                timeout=30, cwd=Path(__file__).resolve().parents[1])
        self.assertEqual(result.returncode, 0, result.stderr)
        records = [json.loads(line) for line in result.stdout.splitlines()]
        codes = [record.get("code") for record in records if record["type"] == "result"]
        self.assertEqual(codes[:2], ["skip_confirmation_required", "handoff_required"])
        self.assertEqual(next(record["view"]["viewer"] for record in records if record["type"] == "view"), 2)
