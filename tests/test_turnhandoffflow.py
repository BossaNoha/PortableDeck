import io
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock

from portable_deck.app.turnhandoff import TurnHandoffController
from portable_deck.cli import CLIClient
from portable_deck.core.game import Game


class HandoffFlowTests(unittest.TestCase):
    def game(self):
        game = Game(2, str(Path(__file__).resolve().parents[1] / "decks/demodeck.json"),
                    enable_undo=True, score_enabled=True, require_point_confirmation=True)
        game.players[0].hand = ["FIRST SECRET"]
        game.players[1].hand = ["SECOND SECRET"]
        game.score_alerts_seen = {"0": [], "1": []}
        game.session.checkpoint_callback = Mock(return_value=None)
        return game

    def test_shared_flow_request_cancel_confirm_and_duplicate_confirmation(self):
        game = self.game()
        flow = TurnHandoffController(game.session, enabled=True)
        advance = Mock(side_effect=lambda: game.session.execute("end_turn"))
        before = game.capture_undo_state()
        self.assertEqual(flow.request(advance).code, "handoff_required")
        self.assertEqual(flow.request(advance).code, "handoff_pending")
        advance.assert_not_called()
        self.assertEqual(flow.cancel().code, "handoff_cancelled")
        self.assertEqual(game.capture_undo_state(), before)
        self.assertEqual(flow.confirm().code, "handoff_not_pending")
        flow.request(advance)
        self.assertTrue(flow.confirm().success)
        self.assertFalse(flow.pending)
        advance.assert_called_once()
        self.assertEqual(game.current_player_index, 1)
        game.session.checkpoint_callback.assert_called_once_with(game)
        self.assertEqual(len(game.undo_stack), 1)
        self.assertEqual(flow.confirm().code, "handoff_not_pending")

    def test_shared_flow_revalidates_and_retains_pending_request_on_failure(self):
        game = self.game()
        flow = TurnHandoffController(game.session, enabled=True)
        flow.request(lambda: game.session.execute("end_turn"))
        game.pending_point_request = {"requester": 1, "confirmed_by": [], "delta": 1}
        before = game.capture_undo_state()
        self.assertEqual(flow.confirm().code, "confirmation_required")
        self.assertTrue(flow.pending)
        self.assertEqual(game.capture_undo_state(), before)
        game.session.checkpoint_callback.assert_not_called()
        self.assertTrue(flow.cancel().success)

    def test_cli_handoff_blocks_output_and_actions_until_ready_or_cancel(self):
        game = self.game()
        output = io.StringIO()
        client = CLIClient(game, output, structured=True, confirm_next_turn=True)
        before = game.capture_undo_state()
        client.command("end")
        for command in ("show", "draw", "play 1", "undo", "point", "pending", "end"):
            client.command(command)
        records = [json.loads(line) for line in output.getvalue().splitlines()]
        self.assertEqual(records[0]["code"], "handoff_required")
        self.assertTrue(all(record["code"] == "handoff_pending" for record in records[1:]))
        self.assertEqual(game.capture_undo_state(), before)
        game.session.checkpoint_callback.assert_not_called()
        client.command("cancel")
        self.assertFalse(client.turn_flow.pending)
        self.assertEqual(game.capture_undo_state(), before)
        game.session.checkpoint_callback.assert_not_called()
        client.command("end")
        client.command("ready")
        self.assertEqual(game.current_player_index, 1)
        self.assertFalse(client.turn_flow.pending)
        self.assertEqual(len(game.undo_stack), 1)
        game.session.checkpoint_callback.assert_called_once_with(game)
        self.assertNotIn("SECRET", output.getvalue())
        self.assertNotIn("\x1b", output.getvalue())
        self.assertTrue(game.session.undo())
        self.assertEqual(game.capture_undo_state(), before)

    def test_cli_ready_precedes_score_confirmation_and_failure_keeps_handoff(self):
        game = self.game()
        client = CLIClient(game, io.StringIO(), structured=True, confirm_next_turn=True)
        self.assertTrue(game.session.execute("request_point").success)
        client.command("end")
        self.assertEqual(game.current_player_index, 0)
        client.command("ready")
        self.assertEqual(game.current_player_index, 1)
        client.command("end")
        self.assertFalse(client.turn_flow.pending)
        client.command("approve")
        self.assertEqual(game.scores, [1, 0])
        client.command("end")
        game.pending_point_request = {"requester": 0, "confirmed_by": [], "delta": 1}
        client.command("ready")
        self.assertTrue(client.turn_flow.pending)
        self.assertEqual(game.current_player_index, 1)
        client.command("cancel")
        self.assertFalse(client.turn_flow.pending)

    def test_cli_process_flag_works_for_text_and_json_without_tkinter(self):
        for structured in (False, True):
            script = ("import sys; from portable_deck.cli import main; "
                      "assert main(['--confirm-next-turn','--hand','0'] + "
                      "(['--json'] if sys.argv[1]=='json' else [])) == 0; "
                      "assert 'tkinter' not in sys.modules")
            result = subprocess.run([sys.executable, "-B", "-c", script, "json" if structured else "text"],
                                    input="end\nshow\ncancel\nend\nready\nready\nquit\n", text=True,
                                    capture_output=True, timeout=30, cwd=Path(__file__).resolve().parents[1])
            self.assertEqual(result.returncode, 0, result.stderr)
            if structured:
                records = [json.loads(line) for line in result.stdout.splitlines()]
                results = [record for record in records if record["type"] == "result"]
                self.assertEqual([record["code"] for record in results],
                                 ["handoff_required", "handoff_pending", "handoff_cancelled", "handoff_required", "", "handoff_not_pending"])
                self.assertFalse(any(record["type"] == "view" for record in records))
            else:
                self.assertIn("use ready", result.stdout)
                self.assertIn("Handoff cancelled", result.stdout)
            self.assertNotIn("\x1b", result.stdout)
