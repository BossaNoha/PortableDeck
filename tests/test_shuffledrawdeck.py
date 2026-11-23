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
from portable_deck.core.actionerrors import ActionValidationError
from portable_deck.core.game import Game
from portable_deck.core.gamesession import export_session, restore_session
from portable_deck.core.rulesoverview import build_rules_overview


class ShuffleDrawDeckTests(unittest.TestCase):
    def game(self):
        game = Game(3, str(Path(__file__).resolve().parents[1] / "decks/demodeck.json"),
                    enable_special_actions=True, allow_shuffle_draw_deck=True, enable_undo=True)
        game.start(0)
        game.deck.flat_deck = ["SECRET_A", "SECRET_B", "SECRET_C"]
        game.session.checkpoint_callback = Mock(return_value=None)
        return game

    def test_only_draw_order_changes_with_one_undo_and_checkpoint(self):
        game = self.game()
        game.players[0].hand = ["HAND"]
        game.discard_pile.append("DISCARD")
        game.table_cards = [dict(player="Player1", card="TABLE", position=[0, 0], face_up=True)]
        before = game.capture_undo_state()
        with patch("portable_deck.core.specialactions.random.shuffle", side_effect=lambda cards: cards.reverse()):
            result = game.session.execute("shuffle_draw_deck")
        self.assertTrue(result.success)
        self.assertTrue(result.changed)
        self.assertEqual(result.value, 3)
        self.assertEqual(game.deck.flat_deck, list(reversed(before["remaining_deck"])))
        self.assertEqual(game.players[0].hand, ["HAND"])
        self.assertEqual(game.discard_pile, ["DISCARD"])
        self.assertEqual(game.table_cards, before["table_cards"])
        self.assertEqual(game.current_player_index, 0)
        self.assertNotIn("SECRET", repr(result.events) + repr(result.messages))
        self.assertEqual(len(game.undo_stack), 1)
        game.session.checkpoint_callback.assert_called_once_with(game)
        self.assertTrue(game.session.undo())
        self.assertEqual(game.capture_undo_state(), before)

    def test_same_order_still_records_one_shuffle_action(self):
        game = self.game()
        with patch("portable_deck.core.specialactions.random.shuffle") as shuffle:
            self.assertTrue(game.session.execute("shuffle_draw_deck").success)
        shuffle.assert_called_once_with(game.deck.flat_deck)
        self.assertEqual(len(game.undo_stack), 1)
        game.session.checkpoint_callback.assert_called_once_with(game)

    def test_unavailable_shuffle_never_changes_or_saves_state(self):
        for reason in ("disabled", "option", "empty", "one", "departed", "no_active", "point", "pot"):
            with self.subTest(reason=reason):
                game = self.game()
                if reason == "disabled":
                    game.enable_special_actions = False
                elif reason == "option":
                    game.allow_shuffle_draw_deck = False
                elif reason == "empty":
                    game.deck.flat_deck.clear()
                elif reason == "one":
                    game.deck.flat_deck = ["ONE"]
                elif reason == "departed":
                    game.left_players = [0]
                elif reason == "no_active":
                    game.left_players = [0, 1, 2]
                elif reason == "point":
                    game.pending_point_request = {"requester": 0}
                else:
                    game.pending_pot_withdrawal = {"requester": 0}
                before = game.capture_undo_state()
                with patch("portable_deck.core.specialactions.random.shuffle") as shuffle:
                    self.assertFalse(game.session.execute("shuffle_draw_deck").success)
                    with self.assertRaises(ActionValidationError):
                        game.shuffle_draw_deck()
                shuffle.assert_not_called()
                self.assertEqual(game.capture_undo_state(), before)
                self.assertFalse(game.undo_stack)
                game.session.checkpoint_callback.assert_not_called()

    def test_failed_shuffle_rolls_back_order(self):
        game = self.game()
        before = game.capture_undo_state()
        def fail(cards):
            cards.reverse()
            raise ValueError("shuffle failed")
        with patch("portable_deck.core.specialactions.random.shuffle", side_effect=fail):
            self.assertFalse(game.session.execute("shuffle_draw_deck").success)
        self.assertEqual(game.capture_undo_state(), before)
        game.session.checkpoint_callback.assert_not_called()

    def test_rule_save_preset_restart_and_legacy_defaults(self):
        game = self.game()
        with patch("portable_deck.core.specialactions.random.shuffle", side_effect=lambda cards: cards.reverse()):
            game.session.execute("shuffle_draw_deck")
        state = export_session(game)
        loaded = restore_session(Game, state)
        self.assertTrue(loaded.allow_shuffle_draw_deck)
        self.assertEqual(loaded.capture_undo_state(), game.capture_undo_state())
        self.assertTrue(loaded.session.undo())
        self.assertEqual(loaded.deck.flat_deck, ["SECRET_A", "SECRET_B", "SECRET_C"])
        self.assertTrue(game.restart().allow_shuffle_draw_deck)
        del state["allow_shuffle_draw_deck"]
        self.assertFalse(restore_session(Game, state).allow_shuffle_draw_deck)
        with self.assertRaises(ValueError):
            restore_session(Game, dict(state, allow_shuffle_draw_deck=1))
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "shuffle.json"
            saved = save_preset(path, {"enable_special_actions": True, "allow_shuffle_draw_deck": True})
            self.assertTrue(load_preset(path, saved).settings["allow_shuffle_draw_deck"])
        entries = next(s.entries for s in build_rules_overview(game).sections if s.key == "special_actions")
        self.assertTrue(any(e.key == "shuffle_draw_deck" for e in entries))

    def test_cli_shuffle_privacy_and_handoff_blocking(self):
        game = self.game()
        output = io.StringIO()
        client = CLIClient(game, output, structured=True, confirm_next_turn=True)
        client.command("end")
        with patch("portable_deck.core.specialactions.random.shuffle", side_effect=lambda cards: cards.reverse()) as shuffle:
            client.command("shuffle")
            shuffle.assert_not_called()
            client.command("cancel")
            client.command("shuffle")
            shuffle.assert_called_once()
        self.assertEqual(len(game.undo_stack), 1)
        self.assertNotIn("SECRET", output.getvalue())

    def test_cli_flag_works_without_tkinter(self):
        script = ("import sys; from portable_deck.cli import main; "
                  "main(['--shuffle-draw-deck','--hand','0','--json']); "
                  "assert 'tkinter' not in sys.modules")
        result = subprocess.run([sys.executable, "-B", "-c", script],
                                input="shuffle\nquit\n", text=True, capture_output=True,
                                timeout=30, cwd=Path(__file__).resolve().parents[1])
        self.assertEqual(result.returncode, 0, result.stderr)
        records = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertTrue(next(r["success"] for r in records if r["type"] == "result"))
