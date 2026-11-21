import io
import json
import subprocess
import sys
import tempfile
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest.mock import Mock

from portable_deck.app.settingspresets import load_preset, save_preset
from portable_deck.app.sessionstorage import load_session, save_session
from portable_deck.app.turnhandoff import TurnHandoffController
from portable_deck.cli import CLIClient
from portable_deck.core.actionerrors import ActionValidationError
from portable_deck.core.game import Game
from portable_deck.core.rulesoverview import build_rules_overview


class TurnOrderTests(unittest.TestCase):
    def game(self, enabled=True):
        game = Game(3, str(Path(__file__).resolve().parents[1] / "decks/demodeck.json"),
                    allow_choose_next_player=enabled, enable_undo=True,
                    clear_table_on_round_end=True, score_enabled=True)
        game.start(1)
        game.table_cards = [{"player": "Player1", "card": "TABLE", "position": [0, 0], "face_up": True}]
        game.session.checkpoint_callback = Mock(return_value=None)
        return game

    def test_manual_pass_does_not_end_round_or_clear_table_and_is_undoable(self):
        for target in (0, 2):
            with self.subTest(target=target):
                game = self.game()
                game.current_player_index = 2
                before = game.capture_undo_state()
                result = game.session.execute("end_turn", next_player=target)
                self.assertTrue(result.success)
                self.assertEqual(result.value, (False, 0))
                self.assertEqual(game.current_player_index, target)
                self.assertEqual(game.table_cards, before["table_cards"])
                self.assertNotIn("round_ended", [event["action"] for event in result.events])
                self.assertIn("turn_passed", [event["action"] for event in result.events])
                game.session.checkpoint_callback.assert_called_once_with(game)
                self.assertEqual(len(game.undo_stack), 1)
                self.assertTrue(game.session.undo())
                self.assertEqual(game.capture_undo_state(), before)
        automatic = game.session.execute("end_turn")
        self.assertTrue(automatic.success)
        self.assertEqual(automatic.value, (True, 1))
        self.assertEqual(game.table_cards, [])

    def test_disabled_invalid_or_departed_targets_leave_state_unchanged(self):
        for enabled in (False, True):
            game = self.game(enabled)
            before = game.capture_undo_state()
            for target in (0, True, False, 1.0, -1, 3, "1", [], {}):
                if enabled and type(target) is int and target == 0:
                    continue
                with self.subTest(enabled=enabled, target=target):
                    expected = "invalid_target" if enabled else "action_disabled"
                    with self.assertRaises(ActionValidationError) as error:
                        game.finish_turn(target)
                    self.assertEqual(error.exception.code, expected)
                    result = game.session.execute("end_turn", next_player=target)
                    self.assertEqual(result.code, expected)
                    self.assertEqual(game.capture_undo_state(), before)
                    self.assertEqual(game.undo_stack, [])
                    game.session.checkpoint_callback.assert_not_called()
        game.left_players = [1]
        before = game.capture_undo_state()
        self.assertEqual(game.session.execute("end_turn", next_player=1).code, "target_left")
        self.assertEqual(game.capture_undo_state(), before)

    def test_options_are_immutable_and_pending_vote_blocks_manual_handoff(self):
        game = self.game()
        game.left_players = [1]
        options = game.session.next_player_options()
        self.assertIn("turn_order", [section.key for section in build_rules_overview(game).sections])
        self.assertTrue(options.allowed)
        self.assertEqual([player.index for player in options.players], [0, 2])
        with self.assertRaises(FrozenInstanceError):
            options.players[0].name = "Changed"
        game.players[0].name = "Updated"
        self.assertEqual(options.players[0].name, "Player1")
        game.pending_point_request = {"requester": 2, "confirmed_by": [], "delta": 1}
        before = game.capture_undo_state()
        self.assertEqual(game.session.next_player_options().code, "confirmation_required")
        self.assertEqual(game.session.execute("end_turn", next_player=2).code, "confirmation_required")
        with self.assertRaises(ActionValidationError):
            game.finish_turn(2)
        self.assertEqual(game.capture_undo_state(), before)

    def test_rule_persists_through_preset_save_load_restart_and_legacy_defaults(self):
        game = self.game()
        self.assertTrue(game.session.execute("end_turn", next_player=2).success)
        with tempfile.TemporaryDirectory() as folder:
            preset = Path(folder) / "Rules.json"
            saved = save_preset(preset, {"allow_choose_next_player": True})
            self.assertTrue(load_preset(preset, saved).settings["allow_choose_next_player"])
            path = Path(folder) / "session.json"
            save_session(game, path)
            loaded = load_session(Game, path)
            self.assertTrue(loaded.allow_choose_next_player)
            self.assertEqual(loaded.capture_undo_state(), game.capture_undo_state())
            self.assertTrue(loaded.restart().allow_choose_next_player)
            self.assertTrue(loaded.session.undo())
            self.assertEqual(loaded.current_player_index, 0)
            state = json.loads(path.read_text(encoding="utf-8"))
            del state["allow_choose_next_player"]
            path.write_text(json.dumps(state), encoding="utf-8")
            legacy = load_session(Game, path)
            self.assertFalse(legacy.allow_choose_next_player)
            self.assertEqual(legacy.session.execute("end_turn", next_player=0).code, "action_disabled")

    def test_hotseat_confirmation_revalidates_the_chosen_target(self):
        game = self.game()
        flow = TurnHandoffController(game.session, enabled=True)
        result = flow.request(lambda: game.session.execute("end_turn", next_player=2), next_player=2)
        self.assertEqual(result.code, "handoff_required")
        self.assertEqual(game.current_player_index, 0)
        game.left_players = [2]
        before = game.capture_undo_state()
        self.assertEqual(flow.confirm().code, "target_left")
        self.assertTrue(flow.pending)
        self.assertEqual(game.capture_undo_state(), before)
        game.session.checkpoint_callback.assert_not_called()
        self.assertTrue(flow.cancel().success)

    def test_cli_manual_end_is_optional_and_waits_for_ready(self):
        game = self.game()
        game.score_alerts_seen = {str(i): [] for i in range(3)}
        output = io.StringIO()
        client = CLIClient(game, output, structured=True, confirm_next_turn=True)
        client.command("end 3")
        self.assertEqual(game.current_player_index, 0)
        game.session.checkpoint_callback.assert_not_called()
        client.command("ready")
        self.assertEqual(game.current_player_index, 2)
        self.assertEqual(len(game.undo_stack), 1)
        game.session.checkpoint_callback.assert_called_once_with(game)
        game.allow_choose_next_player = False
        client.command("end 1")
        self.assertFalse(client.turn_flow.pending)
        self.assertEqual(json.loads(output.getvalue().splitlines()[-1])["code"], "action_disabled")

    def test_cli_process_exposes_manual_turn_flag_without_tkinter(self):
        script = ("import sys; from portable_deck.cli import main; "
                  "assert main(['--choose-next-player','--confirm-next-turn','--players','3','--hand','0','--json'])==0; "
                  "assert 'tkinter' not in sys.modules")
        result = subprocess.run([sys.executable, "-B", "-c", script],
                                input="end 3\nready\nshow\nquit\n", text=True, capture_output=True,
                                timeout=30, cwd=Path(__file__).resolve().parents[1])
        self.assertEqual(result.returncode, 0, result.stderr)
        records = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual(next(record["view"]["viewer"] for record in records if record["type"] == "view"), 2)
