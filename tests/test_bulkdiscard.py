import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import Mock, patch

from portable_deck.app.settingspresets import load_preset, save_preset
from portable_deck.cli import CLIClient
from portable_deck.core.game import Game
from portable_deck.core.gamesession import export_session, restore_session
from tests.test_turnhandoff import HandoffGUI


class BulkDiscardTests(unittest.TestCase):
    def game(self, **kwargs):
        game = Game(3, str(Path(__file__).resolve().parents[1] / "decks/demodeck.json"),
                    allow_discard_multiple_cards=True, shared_discard_pile_count=2,
                    personal_discard_pile_count=2, enable_undo=True, **kwargs)
        game.start(0)
        game.players[0].hand = ["A", "B", "C", "D", "E"]
        game.players[0].revealed_indices = {0, 1, 4}
        game.session.checkpoint_callback = Mock(return_value=None)
        return game

    def test_shared_and_personal_batches_preserve_order_and_have_one_undo(self):
        for personal in (False, True):
            with self.subTest(personal=personal):
                game = self.game()
                pile = game.personal_discard_piles[0][1] if personal else game.discard_piles[1]
                pile.append("OLD")
                before = game.capture_undo_state()
                result = game.session.execute("discard_cards", card_indices=[3, 0, 2], pile_index=1, personal=personal)
                self.assertTrue(result.success)
                self.assertEqual(result.value, ("A", "C", "D"))
                self.assertEqual(pile, ["OLD", "A", "C", "D"])
                self.assertEqual(game.players[0].hand, ["B", "E"])
                self.assertEqual(game.players[0].revealed_indices, {0, 1})
                self.assertEqual(game.personal_discard_piles[1], [[], []])
                self.assertEqual(len(result.events), 3)
                self.assertEqual(len(game.undo_stack), 1)
                game.session.checkpoint_callback.assert_called_once_with(game)
                self.assertTrue(game.session.undo())
                self.assertEqual(game.capture_undo_state(), before)

    def test_invalid_indices_or_destination_fail_before_first_removal(self):
        cases = [{"card_indices": value} for value in (None, [], [0], [0, 0], [True, 1], [0, 5], [0, "1"])]
        cases += [{"card_indices": [0, 1], "pile_index": value} for value in (-1, 2, True, "0")]
        cases += [{"card_indices": [0, 1], "personal": 1}]
        for parameters in cases:
            with self.subTest(parameters=parameters):
                game = self.game()
                before = game.capture_undo_state()
                with patch.object(game, "discard_from_current", wraps=game.discard_from_current) as discard:
                    result = game.session.execute("discard_cards", **parameters)
                self.assertFalse(result.success)
                discard.assert_not_called()
                self.assertEqual(game.capture_undo_state(), before)
                self.assertFalse(game.undo_stack)
                game.session.checkpoint_callback.assert_not_called()

    def test_unavailable_batch_preserves_state(self):
        for reason in ("disabled", "no_discard", "departed", "confirmation", "one_card"):
            game = self.game()
            if reason == "disabled":
                game.allow_discard_multiple_cards = False
            elif reason == "no_discard":
                game.enable_discard_pile = False
            elif reason == "departed":
                game.left_players = [0]
            elif reason == "confirmation":
                game.current_player_must_confirm_point = lambda: True
            else:
                game.players[0].hand = ["A"]
            before = game.capture_undo_state()
            self.assertFalse(game.session.execute("discard_cards", card_indices=[0, 1]).success)
            self.assertEqual(game.capture_undo_state(), before)
            game.session.checkpoint_callback.assert_not_called()

    def test_failure_after_first_card_rolls_back_batch(self):
        game = self.game()
        before = game.capture_undo_state()
        discard = game.discard_from_current
        calls = []
        def fail_second(*args):
            calls.append(args)
            return discard(*args) if len(calls) == 1 else None
        with patch.object(game, "discard_from_current", side_effect=fail_second):
            result = game.session.execute("discard_cards", card_indices=[0, 1])
        self.assertFalse(result.success)
        self.assertFalse(result.events)
        self.assertEqual(game.capture_undo_state(), before)
        self.assertFalse(game.undo_stack)
        game.session.checkpoint_callback.assert_not_called()

    def test_rule_preset_save_restart_and_legacy_defaults(self):
        game = self.game()
        game.session.execute("discard_cards", card_indices=[0, 2], personal=True, pile_index=1)
        state = export_session(game)
        loaded = restore_session(Game, state)
        self.assertTrue(loaded.allow_discard_multiple_cards)
        self.assertEqual(loaded.capture_undo_state(), game.capture_undo_state())
        self.assertTrue(loaded.session.undo())
        self.assertEqual(loaded.players[0].hand, ["A", "B", "C", "D", "E"])
        self.assertTrue(game.restart().allow_discard_multiple_cards)
        del state["allow_discard_multiple_cards"]
        self.assertFalse(restore_session(Game, state).allow_discard_multiple_cards)
        with self.assertRaises(ValueError):
            restore_session(Game, dict(state, allow_discard_multiple_cards=1))
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "batch.json"
            saved = save_preset(path, {"allow_discard_multiple_cards": True})
            self.assertTrue(load_preset(path, saved).settings["allow_discard_multiple_cards"])

    def test_cli_shared_personal_invalid_input_and_handoff(self):
        game = self.game()
        output = io.StringIO()
        client = CLIClient(game, output, structured=True, confirm_next_turn=True)
        for command in ("discard-many other 1 1 2", "discard-many shared 1 1", "discard-many shared 0 1 2"):
            client.command(command)
            self.assertEqual(len(game.players[0].hand), 5)
        client.command("end")
        client.command("discard-many shared 1 1 3")
        self.assertFalse(game.discard_piles[0])
        client.command("cancel")
        client.command("discard-many shared 2 1 3")
        self.assertEqual(game.discard_piles[1], ["A", "C"])
        client.command("discard-many personal 2 1 3")
        self.assertEqual(game.personal_discard_piles[0][1], ["B", "E"])
        self.assertEqual(len(game.undo_stack), 2)

    def test_cli_flag_works_without_tkinter(self):
        script = ("import sys; from portable_deck.cli import main; "
                  "main(['--discard-multiple-cards','--hand','3','--json']); "
                  "assert 'tkinter' not in sys.modules")
        result = subprocess.run([sys.executable, "-B", "-c", script],
                                input="discard-many shared 1 1 3\nshow\nquit\n", text=True, capture_output=True,
                                timeout=30, cwd=Path(__file__).resolve().parents[1])
        self.assertEqual(result.returncode, 0, result.stderr)
        records = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertTrue(next(r["success"] for r in records if r["type"] == "result"))
        view = next(r["view"] for r in records if r["type"] == "view")
        self.assertEqual(view["status"]["discard_piles"][0]["card_count"], 2)

    def test_gui_selects_current_players_destination_from_core_options(self):
        game = self.game()
        gui = HandoffGUI(game, enabled=False)
        cards, piles = Mock(), Mock()
        cards.curselection.return_value = (0, 2)
        piles.curselection.return_value = (3,)
        commands = {}
        def button(*args, **kwargs):
            commands[kwargs["text"]] = kwargs["command"]
            return Mock()
        with ExitStack() as stack:
            for widget in ("Toplevel", "Label"):
                stack.enter_context(patch("portable_deck.ui.gameguiactions.tk." + widget))
            stack.enter_context(patch("portable_deck.ui.gameguiactions.tk.Listbox", side_effect=[cards, piles]))
            stack.enter_context(patch("portable_deck.ui.gameguiactions.tk.Button", side_effect=button))
            warning = stack.enter_context(patch("portable_deck.ui.gameguiactions.messagebox.showwarning"))
            gui.discard_multiple_cards()
            self.assertEqual(piles.insert.call_count, 4)
            piles.curselection.return_value = ()
            commands["Discard selected cards"]()
            warning.assert_called_once()
            self.assertFalse(game.undo_stack)
            piles.curselection.return_value = (3,)
            self.assertTrue(commands["Discard selected cards"]().success)
        self.assertEqual(game.personal_discard_piles[0][1], ["A", "C"])
        self.assertEqual(game.personal_discard_piles[1], [[], []])
