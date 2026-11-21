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


class BulkTableDiscardTests(unittest.TestCase):
    def game(self):
        game = Game(3, str(Path(__file__).resolve().parents[1] / "decks/demodeck.json"),
                    allow_move_table_card_to_discard=True, allow_discard_multiple_table_cards=True,
                    shared_discard_pile_count=2, personal_discard_pile_count=2, enable_undo=True)
        game.start(0)
        game.table_cards = [dict(player="Player2", card=card, position=[0, i * 2], face_up=i != 2)
                            for i, card in enumerate(["A", "B", "HIDDEN_SECRET", "D"])]
        game.session.checkpoint_callback = Mock(return_value=None)
        return game

    def test_shared_personal_order_positions_and_one_undo_checkpoint(self):
        for personal in (False, True):
            game = self.game()
            pile = game.personal_discard_piles[0][1] if personal else game.discard_piles[1]
            pile.append("OLD")
            before = game.capture_undo_state()
            result = game.session.execute("discard_table_cards", card_indices=[3, 0, 2], pile_index=1, personal=personal)
            self.assertTrue(result.success)
            self.assertEqual(pile, ["OLD", "A", "HIDDEN_SECRET", "D"])
            self.assertEqual(game.table_cards, [before["table_cards"][1]])
            self.assertEqual(game.personal_discard_piles[1], [[], []])
            self.assertEqual(len(game.undo_stack), 1)
            game.session.checkpoint_callback.assert_called_once_with(game)
            self.assertTrue(game.session.undo())
            self.assertEqual(game.capture_undo_state(), before)

    def test_invalid_selection_or_destination_rejected_before_first_removal(self):
        cases = [{"card_indices": value} for value in (None, [], [0], [0, 0], [True, 1], [0, 4], [0, "1"])]
        cases += [{"pile_index": value} for value in (-1, 2, True, "0")]
        cases += [{"personal": 1}, {"personal": True, "pile_index": 2}]
        for overrides in cases:
            game = self.game()
            before = game.capture_undo_state()
            parameters = dict(card_indices=[0, 1])
            parameters.update(overrides)
            with patch.object(game, "move_table_card_to_discard", wraps=game.move_table_card_to_discard) as move:
                result = game.session.execute("discard_table_cards", **parameters)
            self.assertFalse(result.success)
            move.assert_not_called()
            self.assertEqual(game.capture_undo_state(), before)
            game.session.checkpoint_callback.assert_not_called()

    def test_unavailable_batch_preserves_state(self):
        for reason in ("disabled", "single_disabled", "no_table", "no_discard", "departed", "confirmation", "one_card"):
            game = self.game()
            if reason == "disabled":
                game.allow_discard_multiple_table_cards = False
            elif reason == "single_disabled":
                game.allow_move_table_card_to_discard = False
            elif reason == "no_table":
                game.enable_table = False
            elif reason == "no_discard":
                game.enable_discard_pile = False
            elif reason == "departed":
                game.left_players = [0]
            elif reason == "confirmation":
                game.current_player_must_confirm_point = lambda: True
            else:
                game.table_cards = game.table_cards[:1]
            before = game.capture_undo_state()
            self.assertFalse(game.session.execute("discard_table_cards", card_indices=[0, 1]).success)
            self.assertEqual(game.capture_undo_state(), before)
            game.session.checkpoint_callback.assert_not_called()

    def test_later_failure_rolls_back_entire_batch(self):
        game = self.game()
        before = game.capture_undo_state()
        move = game.move_table_card_to_discard
        calls = []
        def fail_second(*args):
            calls.append(args)
            return move(*args) if len(calls) == 1 else None
        with patch.object(game, "move_table_card_to_discard", side_effect=fail_second):
            result = game.session.execute("discard_table_cards", card_indices=[0, 2])
        self.assertFalse(result.success)
        self.assertFalse(result.events)
        self.assertEqual(game.capture_undo_state(), before)
        self.assertFalse(game.undo_stack)
        game.session.checkpoint_callback.assert_not_called()

    def test_save_preset_restart_and_legacy_default(self):
        game = self.game()
        game.session.execute("discard_table_cards", card_indices=[0, 2], personal=True)
        state = export_session(game)
        loaded = restore_session(Game, state)
        self.assertTrue(loaded.allow_discard_multiple_table_cards)
        self.assertEqual(loaded.capture_undo_state(), game.capture_undo_state())
        self.assertTrue(loaded.session.undo())
        self.assertEqual(len(loaded.table_cards), 4)
        self.assertTrue(game.restart().allow_discard_multiple_table_cards)
        del state["allow_discard_multiple_table_cards"]
        self.assertFalse(restore_session(Game, state).allow_discard_multiple_table_cards)
        with self.assertRaises(ValueError):
            restore_session(Game, dict(state, allow_discard_multiple_table_cards=1))
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "discard.json"
            saved = save_preset(path, {"allow_discard_multiple_table_cards": True})
            self.assertTrue(load_preset(path, saved).settings["allow_discard_multiple_table_cards"])

    def test_gui_projects_hidden_cards_and_checks_table_revision(self):
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
            stack.enter_context(patch("portable_deck.ui.gameguiactions.tk.Listbox", side_effect=[cards, piles, cards, piles]))
            stack.enter_context(patch("portable_deck.ui.gameguiactions.tk.Button", side_effect=button))
            warning = stack.enter_context(patch("portable_deck.ui.gameguiactions.messagebox.showwarning"))
            gui.discard_multiple_table_cards()
            self.assertNotIn("HIDDEN_SECRET", repr(cards.insert.call_args_list))
            self.assertTrue(commands["Discard selected cards"]().success)
            self.assertEqual(game.personal_discard_piles[0][1], ["A", "HIDDEN_SECRET"])
            gui.discard_multiple_table_cards()
            game.table_cards.reverse()
            before = game.capture_undo_state()
            commands["Discard selected cards"]()
            warning.assert_called_once()
            self.assertEqual(game.capture_undo_state(), before)

    def test_cli_personal_shared_and_handoff_blocking(self):
        game = self.game()
        output = io.StringIO()
        client = CLIClient(game, output, structured=True, confirm_next_turn=True)
        client.command("end")
        client.command("discard-table-many shared 2 1 3")
        self.assertEqual(len(game.table_cards), 4)
        client.command("cancel")
        client.command("discard-table-many shared 2 1 3")
        self.assertEqual(game.discard_piles[1], ["A", "HIDDEN_SECRET"])
        client.command("discard-table-many personal 2 1 2")
        self.assertEqual(game.personal_discard_piles[0][1], ["B", "D"])
        self.assertEqual(len(game.undo_stack), 2)

    def test_cli_flag_works_without_tkinter(self):
        script = ("import sys; from portable_deck.cli import main; "
                  "main(['--discard-multiple-table-cards','--play-multiple-cards','--hand','3','--json']); "
                  "assert 'tkinter' not in sys.modules")
        result = subprocess.run([sys.executable, "-B", "-c", script],
                                input="play-many 1 3\ndiscard-table-many shared 1 1 2\nshow\nquit\n", text=True, capture_output=True,
                                timeout=30, cwd=Path(__file__).resolve().parents[1])
        self.assertEqual(result.returncode, 0, result.stderr)
        records = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertTrue(all(r["success"] for r in records if r["type"] == "result"))
        view = next(r["view"] for r in records if r["type"] == "view")
        self.assertEqual(view["status"]["table_count"], 0)
        self.assertEqual(view["status"]["discard_piles"][0]["card_count"], 2)
