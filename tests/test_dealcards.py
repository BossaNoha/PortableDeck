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


class DealCardsTests(unittest.TestCase):
    def game(self):
        game = Game(4, str(Path(__file__).resolve().parents[1] / "decks/demodeck.json"),
                    enable_special_actions=True, allow_deal_cards=True, allow_reverse_turn_order=True,
                    enable_undo=True)
        game.start(0)
        game.deck.flat_deck = [f"SECRET_{i}" for i in range(12)]
        game.players[0].hand = ["OLD"]
        game.players[0].revealed_indices = {0}
        game.cards_drawn_this_turn = 1
        game.session.checkpoint_callback = Mock(return_value=None)
        return game

    def test_round_robin_order_direction_departed_and_one_undo_checkpoint(self):
        for direction, order in ((1, [2, 3, 0]), (-1, [2, 0, 3])):
            game = self.game()
            game.current_player_index = 2
            game.turn_direction = direction
            game.left_players = [1]
            before = game.capture_undo_state()
            result = game.session.execute("deal_cards", count=2)
            self.assertTrue(result.success)
            self.assertEqual(result.value, 6)
            for offset, player in enumerate(order):
                original = before["players"][player]["hand"]
                self.assertEqual(game.players[player].hand, original + [f"SECRET_{offset}", f"SECRET_{offset + 3}"])
                self.assertEqual(game.players[player].revealed_indices, set(before["players"][player]["revealed_indices"]))
            self.assertFalse(game.players[1].hand)
            self.assertEqual(game.deck.flat_deck, [f"SECRET_{i}" for i in range(6, 12)])
            self.assertEqual(game.cards_drawn_this_turn, 1)
            self.assertEqual(game.current_player_index, 2)
            self.assertNotIn("SECRET", repr(result.events) + repr(result.messages))
            self.assertEqual(len(game.undo_stack), 1)
            game.session.checkpoint_callback.assert_called_once_with(game)
            self.assertTrue(game.session.undo())
            self.assertEqual(game.capture_undo_state(), before)

    def test_exact_capacity_and_one_active_player_are_supported(self):
        game = self.game()
        self.assertTrue(game.session.execute("deal_cards", count=3).success)
        self.assertFalse(game.deck.flat_deck)
        game = self.game()
        game.left_players = [1, 2, 3]
        self.assertTrue(game.session.execute("deal_cards", count=12).success)
        self.assertEqual(len(game.players[0].hand), 13)

    def test_bad_count_or_insufficient_cards_fail_before_first_draw(self):
        for count in (None, True, 0, -1, "2", 1.5, 4):
            game = self.game()
            before = game.capture_undo_state()
            with patch.object(game.deck, "draw_card", wraps=game.deck.draw_card) as draw:
                self.assertFalse(game.session.execute("deal_cards", count=count).success)
            draw.assert_not_called()
            self.assertEqual(game.capture_undo_state(), before)
            game.session.checkpoint_callback.assert_not_called()

    def test_disabled_features_confirmation_and_no_players_preserve_state(self):
        for reason in ("disabled", "option", "actor", "all_left", "point", "pot", "short_deck"):
            game = self.game()
            if reason == "disabled": game.enable_special_actions = False
            elif reason == "option": game.allow_deal_cards = False
            elif reason == "actor": game.left_players = [0]
            elif reason == "all_left": game.left_players = [0, 1, 2, 3]
            elif reason == "point": game.pending_point_request = {"requester": 0}
            elif reason == "pot": game.pending_pot_withdrawal = {"requester": 0}
            else: game.deck.flat_deck = ["ONE"]
            before = game.capture_undo_state()
            self.assertFalse(game.session.execute("deal_cards", count=1).success)
            self.assertEqual(game.capture_undo_state(), before)
            game.session.checkpoint_callback.assert_not_called()

    def test_later_failure_rolls_back_all_hands_and_deck(self):
        game = self.game()
        before = game.capture_undo_state()
        draw = game.deck.draw_card
        calls = []
        def fail_third():
            calls.append(1)
            return draw() if len(calls) < 3 else None
        with patch.object(game.deck, "draw_card", side_effect=fail_third):
            result = game.session.execute("deal_cards", count=2)
        self.assertFalse(result.success)
        self.assertFalse(result.events)
        self.assertEqual(game.capture_undo_state(), before)
        self.assertFalse(game.undo_stack)
        game.session.checkpoint_callback.assert_not_called()

    def test_rule_save_preset_restart_and_legacy_defaults(self):
        game = self.game()
        game.session.execute("deal_cards", count=2)
        state = export_session(game)
        loaded = restore_session(Game, state)
        self.assertTrue(loaded.allow_deal_cards)
        self.assertEqual(loaded.capture_undo_state(), game.capture_undo_state())
        self.assertTrue(loaded.session.undo())
        self.assertEqual(len(loaded.deck.flat_deck), 12)
        self.assertTrue(game.restart().allow_deal_cards)
        del state["allow_deal_cards"]
        self.assertFalse(restore_session(Game, state).allow_deal_cards)
        with self.assertRaises(ValueError): restore_session(Game, dict(state, allow_deal_cards=1))
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "deal.json"
            saved = save_preset(path, {"enable_special_actions": True, "allow_deal_cards": True})
            self.assertTrue(load_preset(path, saved).settings["allow_deal_cards"])

    def test_gui_count_limit_cancel_and_accept(self):
        game = self.game()
        gui = HandoffGUI(game, enabled=False)
        before = game.capture_undo_state()
        with patch("tkinter.simpledialog.askinteger", return_value=None): gui.deal_cards()
        self.assertEqual(game.capture_undo_state(), before)
        with patch("tkinter.simpledialog.askinteger", return_value=2) as question:
            self.assertTrue(gui.deal_cards().success)
        self.assertEqual(question.call_args.kwargs["maxvalue"], 3)
        self.assertEqual(len(game.undo_stack), 1)

    def test_cli_handoff_privacy_and_flag(self):
        game = self.game()
        output = io.StringIO()
        client = CLIClient(game, output, structured=True, confirm_next_turn=True)
        client.command("end")
        client.command("deal 2")
        self.assertEqual(len(game.deck.flat_deck), 12)
        client.command("cancel")
        client.command("deal 2")
        self.assertEqual(len(game.deck.flat_deck), 4)
        self.assertNotIn("SECRET", output.getvalue())
        script = ("import sys; from portable_deck.cli import main; "
                  "main(['--deal-cards','--hand','0','--players','3','--json']); "
                  "assert 'tkinter' not in sys.modules")
        result = subprocess.run([sys.executable, "-B", "-c", script], input="deal 2\nshow\nquit\n",
                                text=True, capture_output=True, timeout=30, cwd=Path(__file__).resolve().parents[1])
        self.assertEqual(result.returncode, 0, result.stderr)
        records = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertTrue(next(r["success"] for r in records if r["type"] == "result"))
        view = next(r["view"] for r in records if r["type"] == "view")
        self.assertEqual([p["card_count"] for p in view["status"]["players"]], [2, 2, 2])
