import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from portable_deck.cli import CLIClient, run_cli
from portable_deck.core.game import Game


class CLITests(unittest.TestCase):
    def test_json_lines_expose_codes_and_public_results_only(self):
        g = self.game()
        output = io.StringIO()
        run_cli(g, io.StringIO("draw\nplay 99\nplay 0\napprove\nshow\nundo\nquit\n"),
                output, structured=True)
        records = [json.loads(line) for line in output.getvalue().splitlines()]
        results = [r for r in records if r["type"] == "result"]
        self.assertTrue(results[0]["success"])
        self.assertEqual(results[1]["code"], "invalid_selection")
        self.assertEqual(results[2]["code"], "confirmation_not_required")
        self.assertTrue(results[-1]["success"])
        self.assertTrue(any(r["type"] == "error" and r["code"] == "invalid_command" for r in records))
        for result in results:
            self.assertNotIn("value", result)
            self.assertNotIn("events", result)
            self.assertNotIn("DRAW SECRET", json.dumps(result))
        view = next(r["view"] for r in records if r["type"] == "view")
        self.assertNotIn("OTHER SECRET", json.dumps(view))

    def test_json_process_entrypoint_emits_parseable_command_stream(self):
        result = subprocess.run([sys.executable, "-B", "-m", "portable_deck.cli", "--json", "--hand", "0"],
                                input="draw\nplay 99\nquit\n", text=True, capture_output=True,
                                cwd=Path(__file__).resolve().parents[1])
        self.assertEqual(result.returncode, 0, result.stderr)
        records = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual([r["code"] for r in records if r["type"] == "result"], ["", "invalid_selection"])
    def game(self, **options):
        g = Game(2, str(Path(__file__).resolve().parents[1] / "decks/demodeck.json"),
                 enable_undo=True, **options)
        g.players[0].hand = ["OWN CARD"]
        g.players[1].hand = ["OTHER SECRET"]
        g.deck.flat_deck = ["DRAW SECRET"]
        return g

    def test_draw_play_turn_undo_and_player_view(self):
        g = self.game()
        output = io.StringIO()
        run_cli(g, io.StringIO("draw\nplay 1\nend\nundo\nshow\nquit\ndraw\n"), output)
        self.assertEqual(g.current_player_index, 0)
        self.assertEqual(g.table_cards[0]["card"], "OWN CARD")
        self.assertEqual(g.players[0].hand, ["DRAW SECRET"])
        self.assertNotIn("OTHER SECRET", output.getvalue())
        self.assertIn('"viewer": 0', output.getvalue())

    def test_command_results_do_not_print_private_draw_values(self):
        g = self.game()
        output = io.StringIO()
        client = CLIClient(g, output)
        client.command("draw")
        self.assertIn("drew a card", output.getvalue())
        self.assertNotIn("DRAW SECRET", output.getvalue())
        before = g.capture_undo_state()
        for command in ("play 0", "play 99", "play nope", "play 1 extra", "approve", "unknown"):
            client.command(command)
        self.assertEqual(g.capture_undo_state(), before)
        self.assertIn("Error:", output.getvalue())
        self.assertIn("Unavailable:", output.getvalue())

    def test_score_and_pot_prompts_follow_core_order(self):
        g = self.game(score_enabled=True, require_point_confirmation=True,
                      enable_chip_accounts=True, require_pot_withdrawal_confirmation=True)
        output = io.StringIO()
        run_cli(g, io.StringIO("point\nbet 5\npot 1\nend\nreject\napprove\nquit\n"), output)
        self.assertIsNone(g.pending_point_request)
        self.assertIsNone(g.pending_pot_withdrawal)
        self.assertEqual(g.scores[0], 0)
        self.assertEqual(g.chip_pot, 0)
        text = output.getvalue()
        self.assertLess(text.index("Confirm point request"), text.index("Confirm pot withdrawal"))

    def test_cli_load_works_without_tkinter_and_does_not_overwrite_save(self):
        g = self.game()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "session.json"
            g.save_session(str(path))
            before = path.read_bytes()
            script = ("import sys; from portable_deck.cli import main; "
                      "main(['--load',sys.argv[1]]); assert 'tkinter' not in sys.modules")
            result = subprocess.run([sys.executable, "-B", "-c", script, str(path)],
                                    input="draw\nquit\n", text=True, capture_output=True,
                                    cwd=Path(__file__).resolve().parents[1])
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(path.read_bytes(), before)
            self.assertNotIn("DRAW SECRET", result.stdout)
