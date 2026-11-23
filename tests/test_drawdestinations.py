import io
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from portable_deck.cli import CLIClient
from portable_deck.core.game import Game
from portable_deck.core.pileoptions import insertion_options
from portable_deck.ui.specialactionsui import SpecialActionsUI
from tests.test_turnhandoff import HandoffGUI


class DrawDestinationTests(unittest.TestCase):
    def game(self, fallback=False):
        game = Game(2, str(Path(__file__).resolve().parents[1] / "decks/demodeck.json"), enable_undo=True,
                    enable_special_actions=True, allow_insert_draw_deck=True,
                    enable_table=not fallback, enable_discard_pile=not fallback)
        game.start(0)
        game.players[0].hand = ["CARD", "OTHER"]
        game.players[0].revealed_indices = {0, 1}
        game.draw_piles.add("reserve", "Reserve", ["A", "B", "C"], owner=0)
        game.draw_piles.add("theirs", "Other deck", ["PRIVATE"], owner=1)
        game.session.checkpoint_callback = Mock(return_value=None)
        return game

    def test_positioned_insertion_targets_selected_pile_with_one_undo(self):
        for position, expected in ((1, ["CARD", "A", "B", "C"]), (-1, ["A", "B", "C", "CARD"]),
                                   (2, ["A", "CARD", "B", "C"])):
            game = self.game()
            before = game.capture_undo_state()
            result = game.session.execute("insert_draw_deck", card_index=0, position=position, draw_pile_id="reserve")
            self.assertTrue(result.success)
            self.assertEqual(game.draw_piles.get("reserve").cards, expected)
            self.assertEqual(game.deck.flat_deck, before["remaining_deck"])
            self.assertEqual(game.players[0].hand, ["OTHER"])
            self.assertEqual(game.players[0].revealed_indices, {0})
            self.assertIn("reserve", result.messages[0])
            self.assertEqual(len(game.undo_stack), 1)
            game.session.checkpoint_callback.assert_called_once_with(game)
            self.assertTrue(game.session.undo())
            self.assertEqual(game.capture_undo_state(), before)

    def test_empty_pile_and_middle_position_options_follow_selected_size(self):
        game = self.game()
        game.draw_piles.get("reserve").cards.clear()
        option = insertion_options(game, "draw", "reserve")[0]
        self.assertEqual(option.positions_from_end, 1)
        self.assertEqual(option.draw_pile_id, "reserve")
        self.assertFalse(option.random_middle_available)
        self.assertTrue(game.session.execute("insert_draw_deck", card_index=0, position=1, draw_pile_id="reserve").success)
        game = self.game()
        before = game.capture_undo_state()
        self.assertFalse(game.session.execute("insert_draw_deck", card_index=0, position="X", draw_pile_id="reserve").success)
        self.assertEqual(game.capture_undo_state(), before)
        game.draw_piles.get("reserve").cards[:] = [f"C{i}" for i in range(22)]
        with patch("portable_deck.core.specialactions.random.randrange", return_value=10):
            self.assertTrue(game.session.execute("insert_draw_deck", card_index=0, position="X", draw_pile_id="reserve").success)
        self.assertEqual(game.draw_piles.get("reserve").cards[10], "CARD")

    def test_invalid_source_access_and_positions_do_not_remove_hand_cards(self):
        for action in ("insert_draw_deck", "play_card"):
            for source in ("missing", "theirs", None, True):
                game = self.game(fallback=action == "play_card")
                before = game.capture_undo_state()
                self.assertFalse(game.session.execute(action, card_index=0, position=1, draw_pile_id=source).success)
                self.assertEqual(game.capture_undo_state(), before)
                game.session.checkpoint_callback.assert_not_called()
        game = self.game()
        for position in (0, 11, -11, 9, -5):
            before = game.capture_undo_state()
            self.assertFalse(game.session.execute("insert_draw_deck", card_index=0, position=position, draw_pile_id="reserve").success)
            self.assertEqual(game.capture_undo_state(), before)

    def test_fallback_return_shuffles_selected_pile_and_undo_restores_all(self):
        game = self.game(fallback=True)
        before = game.capture_undo_state()
        with patch("portable_deck.core.drawpile.random.shuffle", side_effect=lambda cards: cards.reverse()):
            result = game.session.execute("play_card", card_index=0, draw_pile_id="reserve")
        self.assertTrue(result.success)
        self.assertEqual(game.draw_piles.get("reserve").cards, ["CARD", "C", "B", "A"])
        self.assertEqual(game.deck.flat_deck, before["remaining_deck"])
        self.assertTrue(game.session.undo())
        self.assertEqual(game.capture_undo_state(), before)
        game = self.game()
        self.assertTrue(game.session.execute("play_card", card_index=0, draw_pile_id="theirs").success)
        self.assertEqual(game.table_cards[0]["card"], "CARD")

    def test_later_failure_rolls_back_insert_or_shuffle(self):
        game = self.game()
        before = game.capture_undo_state()
        with patch.object(game, "record_event", side_effect=ValueError("failed")):
            self.assertFalse(game.session.execute("insert_draw_deck", card_index=0, position=1, draw_pile_id="reserve").success)
        self.assertEqual(game.capture_undo_state(), before)
        game = self.game(fallback=True)
        before = game.capture_undo_state()
        with patch.object(game.draw_piles.get("reserve"), "shuffle", side_effect=ValueError("failed")):
            self.assertFalse(game.session.execute("play_card", card_index=0, draw_pile_id="reserve").success)
        self.assertEqual(game.capture_undo_state(), before)

    def test_gui_insertion_prompt_and_execution_capture_selected_destination(self):
        game = self.game()
        gui = HandoffGUI(game, enabled=False)
        gui.draw_pile_id = "reserve"
        gui.selection.hand_index = 0
        ui = object.__new__(SpecialActionsUI)
        ui.gui = gui
        with patch("portable_deck.ui.specialactionsui.simpledialog.askstring", return_value="1") as prompt:
            ui.choose("draw")
        self.assertIn("Available positions from either end: 4", prompt.call_args.args[1])
        self.assertEqual(game.draw_piles.get("reserve").cards[0], "CARD")

    def test_cli_insertion_and_return_use_selected_source(self):
        game = self.game()
        output = io.StringIO()
        client = CLIClient(game, output, structured=True)
        client.command("source reserve")
        client.command("insert-draw 1 -1")
        self.assertEqual(game.draw_piles.get("reserve").cards, ["A", "B", "C", "CARD"])
        game = self.game(fallback=True)
        client = CLIClient(game, io.StringIO(), structured=True)
        client.command("source reserve")
        client.command("play 1")
        self.assertIn("CARD", game.draw_piles.get("reserve").cards)
        script = ("import sys; from portable_deck.cli import main; "
                  "main(['--players','2','--hand','1','--insert-draw-deck','--draw-pile','r','Reserve','shared','0','--json']); "
                  "assert 'tkinter' not in sys.modules")
        result = subprocess.run([sys.executable, "-B", "-c", script], input="source r\ninsert-draw 1 1\nquit\n",
                                text=True, capture_output=True, timeout=30, cwd=Path(__file__).resolve().parents[1])
        self.assertEqual(result.returncode, 0, result.stderr)
        records = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertTrue(next(r["success"] for r in records if r["type"] == "result"))
