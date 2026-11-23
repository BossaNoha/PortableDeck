import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from portable_deck.app.settingspresets import load_preset, save_preset
from portable_deck.cli import CLIClient
from portable_deck.core.game import Game
from portable_deck.core.gamesession import export_session, restore_session
from tests.test_turnhandoff import HandoffGUI


class BulkDrawTests(unittest.TestCase):
    def game(self):
        game = Game(3, str(Path(__file__).resolve().parents[1] / "decks/demodeck.json"),
                    enable_special_actions=True, allow_draw_multiple_cards=True, enable_undo=True)
        game.start(0)
        game.deck.flat_deck = ["SECRET_A", "SECRET_B", "SECRET_C"]
        game.session.checkpoint_callback = Mock(return_value=None)
        return game

    def test_batch_matches_single_draw_order_counter_and_one_undo_checkpoint(self):
        game, singles = self.game(), self.game()
        before = game.capture_undo_state()
        result = game.session.execute("draw_cards", count=2)
        for _ in range(2):
            singles.session.execute("draw_card")
        self.assertTrue(result.success)
        self.assertEqual(game.players[0].hand, singles.players[0].hand)
        self.assertEqual(game.deck.flat_deck, singles.deck.flat_deck)
        self.assertEqual(game.cards_drawn_this_turn, 2)
        self.assertNotIn("SECRET", repr(result.events) + repr(result.messages))
        self.assertEqual(len(game.undo_stack), 1)
        game.session.checkpoint_callback.assert_called_once_with(game)
        self.assertTrue(game.session.undo())
        self.assertEqual(game.capture_undo_state(), before)

    def test_one_or_entire_remaining_deck_is_allowed(self):
        for count in (1, 3):
            game = self.game()
            self.assertTrue(game.session.execute("draw_cards", count=count).success)
            self.assertEqual(len(game.deck.flat_deck), 3 - count)
            self.assertEqual(len(game.players[0].hand), count)
            game.session.execute("end_turn")
            summaries = [e for e in game.history if e["action"] == "draw_multiple"]
            self.assertEqual(summaries[-1]["count"], count)

    def test_invalid_count_or_insufficient_deck_rejected_before_first_draw(self):
        for count in (None, 0, -1, True, 1.5, "2", 4):
            game = self.game()
            before = game.capture_undo_state()
            with patch.object(game, "deal_card_to_current", wraps=game.deal_card_to_current) as draw:
                self.assertFalse(game.session.execute("draw_cards", count=count).success)
            draw.assert_not_called()
            self.assertEqual(game.capture_undo_state(), before)
            game.session.checkpoint_callback.assert_not_called()

    def test_unavailable_action_preserves_state(self):
        for reason in ("disabled", "option", "empty", "departed", "point", "pot"):
            game = self.game()
            if reason == "disabled":
                game.enable_special_actions = False
            elif reason == "option":
                game.allow_draw_multiple_cards = False
            elif reason == "empty":
                game.deck.flat_deck.clear()
            elif reason == "departed":
                game.left_players = [0]
            elif reason == "point":
                game.pending_point_request = {"requester": 0}
            else:
                game.pending_pot_withdrawal = {"requester": 0}
            before = game.capture_undo_state()
            self.assertFalse(game.session.execute("draw_cards", count=2).success)
            self.assertEqual(game.capture_undo_state(), before)
            game.session.checkpoint_callback.assert_not_called()

    def test_later_failure_rolls_back_entire_draw(self):
        game = self.game()
        before = game.capture_undo_state()
        draw = game.deal_card_to_current
        calls = []
        def fail_second():
            calls.append(1)
            return draw() if len(calls) == 1 else None
        with patch.object(game, "deal_card_to_current", side_effect=fail_second):
            result = game.session.execute("draw_cards", count=2)
        self.assertFalse(result.success)
        self.assertFalse(result.events)
        self.assertEqual(game.capture_undo_state(), before)
        game.session.checkpoint_callback.assert_not_called()

    def test_rule_preset_save_restart_and_legacy_defaults(self):
        game = self.game()
        game.session.execute("draw_cards", count=2)
        state = export_session(game)
        loaded = restore_session(Game, state)
        self.assertTrue(loaded.allow_draw_multiple_cards)
        self.assertEqual(loaded.capture_undo_state(), game.capture_undo_state())
        self.assertTrue(loaded.session.undo())
        self.assertEqual(len(loaded.deck.flat_deck), 3)
        self.assertTrue(game.restart().allow_draw_multiple_cards)
        del state["allow_draw_multiple_cards"]
        self.assertFalse(restore_session(Game, state).allow_draw_multiple_cards)
        with self.assertRaises(ValueError):
            restore_session(Game, dict(state, allow_draw_multiple_cards=1))
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "draw.json"
            saved = save_preset(path, {"enable_special_actions": True, "allow_draw_multiple_cards": True})
            self.assertTrue(load_preset(path, saved).settings["allow_draw_multiple_cards"])

    def test_gui_cancel_accept_and_revalidation(self):
        game = self.game()
        gui = HandoffGUI(game, enabled=False)
        before = game.capture_undo_state()
        with patch("tkinter.simpledialog.askinteger", return_value=None):
            gui.draw_multiple_cards()
        self.assertEqual(game.capture_undo_state(), before)
        with patch("tkinter.simpledialog.askinteger", return_value=2) as question:
            self.assertTrue(gui.draw_multiple_cards().success)
        self.assertEqual(question.call_args.kwargs["maxvalue"], 3)
        self.assertEqual(len(game.undo_stack), 1)
        def change_rule(*args, **kwargs):
            game.allow_draw_multiple_cards = False
            return 1
        with patch("tkinter.simpledialog.askinteger", side_effect=change_rule), patch(
                "portable_deck.ui.gameguiactions.messagebox.showwarning"):
            self.assertFalse(gui.draw_multiple_cards().success)
        self.assertEqual(len(game.players[0].hand), 2)

    def test_cli_privacy_handoff_and_new_game_flag(self):
        game = self.game()
        output = io.StringIO()
        client = CLIClient(game, output, structured=True, confirm_next_turn=True)
        client.command("end")
        client.command("draw-many 2")
        self.assertFalse(game.players[0].hand)
        client.command("cancel")
        client.command("draw-many 2")
        self.assertEqual(len(game.players[0].hand), 2)
        self.assertNotIn("SECRET", output.getvalue())
        script = ("import sys; from portable_deck.cli import main; "
                  "main(['--draw-multiple-cards','--hand','0','--json']); "
                  "assert 'tkinter' not in sys.modules")
        result = subprocess.run([sys.executable, "-B", "-c", script],
                                input="draw-many 2\nquit\n", text=True, capture_output=True,
                                timeout=30, cwd=Path(__file__).resolve().parents[1])
        self.assertEqual(result.returncode, 0, result.stderr)
        records = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertTrue(next(r["success"] for r in records if r["type"] == "result"))
