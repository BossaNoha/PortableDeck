import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from portable_deck.app.settingspresets import load_preset, save_preset
from portable_deck.app.turnhandoff import TurnHandoffController
from portable_deck.cli import CLIClient
from portable_deck.core.actionerrors import ActionValidationError
from portable_deck.core.game import Game
from portable_deck.core.gamesession import export_session, restore_session
from portable_deck.core.rulesoverview import build_rules_overview


class SkipNextPlayerTests(unittest.TestCase):
    def game(self, count=4, **kwargs):
        game = Game(count, str(Path(__file__).resolve().parents[1] / "decks/demodeck.json"),
                    allow_skip_next_player=True, enable_undo=True, **kwargs)
        game.start(0)
        game.session.checkpoint_callback = Mock(return_value=None)
        return game

    def test_skip_follows_direction_and_ignores_departed_players(self):
        for direction, start, skipped, target in ((1, 0, 1, 3), (-1, 3, 1, 0)):
            with self.subTest(direction=direction):
                game = self.game(allow_reverse_turn_order=True)
                game.turn_direction = direction
                game.current_player_index = start
                game.left_players = [2]
                result = game.session.execute("end_turn", skip_next=True)
                self.assertTrue(result.success)
                self.assertEqual(result.value, (False, 0))
                self.assertEqual(game.current_player_index, target)
                self.assertEqual(game.turn_direction, direction)
                event = next(e for e in result.events if e["action"] == "player_skipped")
                self.assertEqual(event["target"], game.players[skipped].name)
                self.assertEqual(len(game.undo_stack), 1)
                game.session.checkpoint_callback.assert_called_once_with(game)

    def test_crossing_boundary_on_either_step_cleans_once(self):
        for direction, start, target in ((1, 3, 1), (1, 2, 0), (-1, 0, 2), (-1, 1, 3)):
            with self.subTest(direction=direction, start=start):
                game = self.game(allow_reverse_turn_order=True, clear_table_on_round_end=True)
                game.turn_direction = direction
                game.current_player_index = start
                game.table_cards = [{"player": "Player1", "card": "TABLE", "position": [0, 0], "face_up": True}]
                before = game.capture_undo_state()
                result = game.session.execute("end_turn", skip_next=True)
                self.assertEqual(result.value, (True, 1))
                self.assertEqual(game.current_player_index, target)
                self.assertEqual(len([e for e in result.events if e["action"] == "round_ended"]), 1)
                self.assertEqual(len([e for e in result.events if e["action"] == "clear_table"]), 1)
                self.assertTrue(game.session.undo())
                self.assertEqual(game.capture_undo_state(), before)

    def test_two_active_players_repeat_current_turn(self):
        for direction in (1, -1):
            game = self.game(allow_reverse_turn_order=True)
            game.turn_direction = direction
            game.left_players = [1, 2]
            result = game.session.execute("end_turn", skip_next=True)
            self.assertTrue(result.success)
            self.assertTrue(result.value[0])
            self.assertEqual(game.current_player_index, 0)
            game.session.execute("end_turn")
            self.assertEqual(game.current_player_index, 3)

    def test_unavailable_or_invalid_skip_does_not_mutate(self):
        for case, code in (("disabled", "action_disabled"), ("one", "not_enough_players"),
                           ("none", "not_enough_players"), ("confirmation", "confirmation_required"),
                           ("manual", "invalid_parameters"), ("type", "invalid_parameters")):
            with self.subTest(case=case):
                game = self.game(allow_choose_next_player=True)
                parameters = {"skip_next": True}
                if case == "disabled":
                    game.allow_skip_next_player = False
                elif case == "one":
                    game.left_players = [1, 2, 3]
                elif case == "none":
                    game.left_players = list(range(4))
                elif case == "confirmation":
                    game.current_player_must_confirm_point = lambda: True
                elif case == "manual":
                    parameters["next_player"] = 2
                else:
                    parameters["skip_next"] = 1
                before = game.capture_undo_state()
                result = game.session.execute("end_turn", **parameters)
                self.assertFalse(result.success)
                self.assertEqual(result.code, code)
                with self.assertRaises(ActionValidationError):
                    game.finish_turn(**parameters)
                self.assertEqual(game.capture_undo_state(), before)
                self.assertFalse(game.undo_stack)
                game.session.checkpoint_callback.assert_not_called()

    def test_handoff_waits_for_ready_and_revalidates_skip_rule(self):
        game = self.game()
        flow = TurnHandoffController(game.session, enabled=True)
        advance = lambda: game.session.execute("end_turn", skip_next=True)
        before = game.capture_undo_state()
        self.assertEqual(flow.request(advance, skip_next=True).code, "handoff_required")
        self.assertEqual(game.capture_undo_state(), before)
        self.assertTrue(flow.cancel().success)
        game.session.checkpoint_callback.assert_not_called()
        flow.request(advance, skip_next=True)
        game.allow_skip_next_player = False
        self.assertEqual(flow.confirm().code, "action_disabled")
        self.assertTrue(flow.pending)
        self.assertEqual(game.capture_undo_state(), before)
        game.allow_skip_next_player = True
        self.assertTrue(flow.confirm().success)
        self.assertEqual(game.current_player_index, 2)
        self.assertEqual(len(game.undo_stack), 1)
        game.session.checkpoint_callback.assert_called_once_with(game)
        game.allow_skip_next_player = False
        self.assertEqual(flow.request(advance, skip_next=True).code, "action_disabled")
        self.assertFalse(flow.pending)

    def test_save_legacy_restart_and_preset_rule(self):
        game = self.game()
        game.session.execute("end_turn", skip_next=True)
        state = export_session(game)
        loaded = restore_session(Game, state)
        self.assertTrue(loaded.allow_skip_next_player)
        self.assertEqual(loaded.current_player_index, 2)
        self.assertTrue(loaded.session.undo())
        self.assertEqual(loaded.current_player_index, 0)
        self.assertTrue(game.restart().allow_skip_next_player)
        del state["allow_skip_next_player"]
        self.assertFalse(restore_session(Game, state).allow_skip_next_player)
        with self.assertRaises(ValueError):
            restore_session(Game, dict(state, allow_skip_next_player=1))
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "skip.json"
            saved = save_preset(path, {"allow_skip_next_player": True})
            self.assertTrue(load_preset(path, saved).settings["allow_skip_next_player"])
        entries = next(s.entries for s in build_rules_overview(game).sections if s.key == "turn_order")
        self.assertTrue(any(e.key == "allow_skip_next_player" for e in entries))

    def test_cli_skip_respects_pending_handoff(self):
        game = self.game()
        output = io.StringIO()
        client = CLIClient(game, output, structured=True, confirm_next_turn=True)
        client.command("skip")
        self.assertEqual(game.current_player_index, 0)
        self.assertTrue(client.turn_flow.pending)
        client.command("skip")
        self.assertEqual(json.loads(output.getvalue().splitlines()[-1])["code"], "handoff_pending")
        client.command("ready")
        self.assertEqual(game.current_player_index, 2)
        self.assertEqual(len(game.undo_stack), 1)

    def test_cli_flag_enables_skip_without_gui_dependencies(self):
        script = ("import sys; from portable_deck.cli import main; "
                  "main(['--skip-next-player','--players','3','--hand','0','--json']); "
                  "assert 'tkinter' not in sys.modules")
        result = subprocess.run([sys.executable, "-B", "-c", script],
                                input="skip\nshow\nquit\n", text=True, capture_output=True,
                                timeout=30, cwd=Path(__file__).resolve().parents[1])
        self.assertEqual(result.returncode, 0, result.stderr)
        view = next(json.loads(line)["view"] for line in result.stdout.splitlines()
                    if json.loads(line)["type"] == "view")
        self.assertEqual(view["viewer"], 2)
