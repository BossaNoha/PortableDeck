import io
import json
import unittest
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock

from portable_deck.cli import CLIClient
from portable_deck.core.game import Game
from portable_deck.core.gamesession import export_session, restore_session
from portable_deck.core.rulesoverview import build_rules_overview
from portable_deck.app.settingspresets import load_preset, save_preset
from portable_deck.core.sessionstatus import build_session_status


class ReverseTurnOrderTests(unittest.TestCase):
    def game(self, **kwargs):
        game = Game(4, str(Path(__file__).resolve().parents[1] / "decks/demodeck.json"),
                    allow_reverse_turn_order=True, enable_undo=True, **kwargs)
        game.start(0)
        game.session.checkpoint_callback = Mock(return_value=None)
        return game

    def test_reverse_keeps_current_turn_and_undo_restores_direction(self):
        game = self.game()
        before = game.capture_undo_state()
        result = game.session.execute("reverse_turn_order")
        self.assertTrue(result.success)
        self.assertTrue(result.changed)
        self.assertEqual(game.current_player_index, 0)
        self.assertEqual(game.turn_direction, -1)
        self.assertEqual(build_session_status(game).turn_direction, -1)
        self.assertEqual(result.events[0]["action"], "turn_direction_changed")
        self.assertIn("reverse", result.messages[0])
        game.session.checkpoint_callback.assert_called_once_with(game)
        self.assertEqual(len(game.undo_stack), 1)
        self.assertTrue(game.session.undo())
        self.assertEqual(game.capture_undo_state(), before)

    def test_reverse_skips_departed_and_only_wrap_clears_table(self):
        game = self.game(clear_table_on_round_end=True)
        game.current_player_index = 3
        game.left_players = [2]
        game.table_cards = [{"player": "Player1", "card": "TABLE", "position": [0, 0], "face_up": True}]
        game.session.execute("reverse_turn_order")
        self.assertEqual(game.session.execute("end_turn").value, (False, 0))
        self.assertEqual(game.current_player_index, 1)
        self.assertEqual(game.session.execute("end_turn").value, (False, 0))
        self.assertEqual(game.current_player_index, 0)
        self.assertEqual(game.session.execute("end_turn").value, (True, 1))
        self.assertEqual(game.current_player_index, 3)

    def test_manual_handoff_preserves_direction_and_double_reverse_restores_it(self):
        game = self.game(allow_choose_next_player=True)
        game.session.execute("reverse_turn_order")
        self.assertEqual(game.session.execute("end_turn", next_player=2).value, (False, 0))
        game.session.execute("end_turn")
        self.assertEqual(game.current_player_index, 1)
        game.session.execute("reverse_turn_order")
        self.assertEqual(game.turn_direction, 1)
        game.session.execute("end_turn")
        self.assertEqual(game.current_player_index, 2)

    def test_unavailable_actions_do_not_mutate_or_checkpoint(self):
        for reason in ("disabled", "departed", "none", "confirmation"):
            with self.subTest(reason=reason):
                game = self.game()
                if reason == "disabled":
                    game.allow_reverse_turn_order = False
                elif reason == "departed":
                    game.left_players = [0]
                elif reason == "none":
                    game.left_players = list(range(4))
                else:
                    game.current_player_must_confirm_point = lambda: True
                before = game.capture_undo_state()
                self.assertFalse(game.session.execute("reverse_turn_order").success)
                self.assertEqual(game.capture_undo_state(), before)
                game.session.checkpoint_callback.assert_not_called()

    def test_save_restart_and_legacy_defaults(self):
        game = self.game()
        game.session.execute("reverse_turn_order")
        state = export_session(game)
        loaded = restore_session(Game, state)
        self.assertTrue(loaded.allow_reverse_turn_order)
        self.assertEqual(loaded.turn_direction, -1)
        self.assertTrue(loaded.session.undo())
        self.assertEqual(loaded.turn_direction, 1)
        restarted = game.restart()
        self.assertTrue(restarted.allow_reverse_turn_order)
        self.assertEqual(restarted.turn_direction, 1)
        del state["allow_reverse_turn_order"]
        del state["turn_direction"]
        legacy = restore_session(Game, state)
        self.assertFalse(legacy.allow_reverse_turn_order)
        self.assertEqual(legacy.turn_direction, 1)
        self.assertIsNone(build_session_status(legacy).turn_direction)

    def test_preset_and_cli_flag_enable_rule_without_gui_dependencies(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "reverse.json"
            saved = save_preset(path, {"allow_reverse_turn_order": True})
            self.assertTrue(load_preset(path, saved).settings["allow_reverse_turn_order"])
        script = ("import sys; from portable_deck.cli import main; "
                  "main(['--reverse-turn-order','--players','3','--hand','0','--json']); "
                  "assert 'tkinter' not in sys.modules")
        result = subprocess.run([sys.executable, "-B", "-c", script],
                                input="reverse\nend\nshow\nquit\n", text=True, capture_output=True,
                                timeout=30, cwd=Path(__file__).resolve().parents[1])
        self.assertEqual(result.returncode, 0, result.stderr)
        view = next(json.loads(line)["view"] for line in result.stdout.splitlines()
                    if json.loads(line)["type"] == "view")
        self.assertEqual(view["viewer"], 2)
        self.assertEqual(view["status"]["turn_direction"], -1)

    def test_invalid_saved_direction_and_rule_are_rejected(self):
        state = export_session(self.game())
        for field, value in (("turn_direction", True), ("turn_direction", 0),
                             ("turn_direction", "-1"), ("allow_reverse_turn_order", 1)):
            with self.subTest(field=field, value=value):
                with self.assertRaises(ValueError):
                    restore_session(Game, dict(state, **{field: value}))

    def test_cli_reverse_respects_handoff_and_reports_public_direction(self):
        game = self.game()
        output = io.StringIO()
        client = CLIClient(game, output, structured=True, confirm_next_turn=True)
        client.command("end")
        client.command("reverse")
        self.assertEqual(game.turn_direction, 1)
        self.assertEqual(json.loads(output.getvalue().splitlines()[-1])["code"], "handoff_pending")
        client.command("cancel")
        client.command("reverse")
        self.assertEqual(game.turn_direction, -1)
        rules = build_rules_overview(game)
        entries = next(s.entries for s in rules.sections if s.key == "turn_order")
        self.assertEqual(next(e.value for e in entries if e.key == "turn_direction"), "reverse")
