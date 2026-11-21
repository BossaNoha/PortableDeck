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
from portable_deck.core.selection import SelectionState
from portable_deck.core.selectionsnapshot import build_selection_snapshot
from tests.test_turnhandoff import HandoffGUI


class BulkPlayTests(unittest.TestCase):
    def game(self, **kwargs):
        game = Game(3, str(Path(__file__).resolve().parents[1] / "decks/demodeck.json"),
                    allow_play_multiple_cards=True, enable_undo=True, **kwargs)
        game.start(0)
        game.players[0].hand = ["A", "B", "C", "D", "E"]
        game.players[0].revealed_indices = {0, 1, 4}
        game.session.checkpoint_callback = Mock(return_value=None)
        return game

    def test_noncontiguous_cards_play_in_hand_order_with_one_undo_and_checkpoint(self):
        game = self.game()
        before = game.capture_undo_state()
        result = game.session.execute("play_cards", card_indices=[3, 0, 2])
        self.assertTrue(result.success)
        self.assertTrue(result.changed)
        self.assertEqual(result.value, ("A", "C", "D"))
        self.assertEqual(game.players[0].hand, ["B", "E"])
        self.assertEqual(game.players[0].revealed_indices, {0, 1})
        self.assertEqual([entry["card"] for entry in game.table_cards], ["A", "C", "D"])
        self.assertEqual([entry["position"] for entry in game.table_cards], [[0, 0], [0, 1], [0, 2]])
        self.assertTrue(all(entry["face_up"] for entry in game.table_cards))
        self.assertEqual(len(result.events), 3)
        self.assertEqual(len(game.undo_stack), 1)
        game.session.checkpoint_callback.assert_called_once_with(game)
        self.assertTrue(game.session.undo())
        self.assertEqual(game.capture_undo_state(), before)

    def test_malformed_or_stale_indices_leave_all_state_unchanged(self):
        for indices in (None, [], [0], [0, 0], [True, 1], [0, -1], [0, 5], [0, "1"], {0, 1}):
            with self.subTest(indices=indices):
                game = self.game()
                before = game.capture_undo_state()
                result = game.session.execute("play_cards", card_indices=indices)
                self.assertEqual(result.code, "invalid_selection")
                self.assertEqual(game.capture_undo_state(), before)
                self.assertFalse(result.events)
                self.assertFalse(game.undo_stack)
                game.session.checkpoint_callback.assert_not_called()

    def test_insufficient_capacity_is_rejected_before_any_card_is_played(self):
        for front in (False, True):
            game = self.game(enable_table_limits=True, max_table_rows=3, max_table_columns=2,
                             allow_play_in_front_of_players=front)
            # Only the player's own row is used when playing in front of players.
            if not front:
                game.max_table_rows = 1
            before = game.capture_undo_state()
            with patch.object(game, "play_to_table", wraps=game.play_to_table) as play:
                result = game.session.execute("play_cards", card_indices=[0, 1, 2])
            self.assertEqual(result.code, "table_full")
            play.assert_not_called()
            self.assertEqual(game.capture_undo_state(), before)
            game.session.checkpoint_callback.assert_not_called()

    def test_placement_modes_match_repeated_single_card_play(self):
        for rules in ({}, {"allow_positioned_play": True}, {"allow_move_cards_on_table": True},
                      {"allow_play_in_front_of_players": True},
                      {"allow_positioned_play": True, "enable_table_limits": True,
                       "max_table_rows": 2, "max_table_columns": 2}):
            with self.subTest(rules=rules):
                batch, singles = self.game(**rules), self.game(**rules)
                self.assertTrue(batch.session.execute("play_cards", card_indices=[0, 1, 4]).success)
                for index in (0, 0, 2):
                    self.assertTrue(singles.session.execute("play_card", card_index=index).success)
                self.assertEqual(batch.table_cards, singles.table_cards)
                self.assertEqual(batch.players[0].hand, singles.players[0].hand)

    def test_unavailable_batch_does_not_mutate(self):
        for case in ("disabled", "no_table", "departed", "confirmation", "short_hand"):
            with self.subTest(case=case):
                game = self.game()
                if case == "disabled":
                    game.allow_play_multiple_cards = False
                elif case == "no_table":
                    game.enable_table = False
                elif case == "departed":
                    game.left_players = [0]
                elif case == "confirmation":
                    game.current_player_must_confirm_point = lambda: True
                else:
                    game.players[0].hand = ["A"]
                before = game.capture_undo_state()
                self.assertFalse(game.session.execute("play_cards", card_indices=[0, 1]).success)
                self.assertEqual(game.capture_undo_state(), before)
                game.session.checkpoint_callback.assert_not_called()

    def test_unexpected_later_failure_rolls_back_entire_batch(self):
        game = self.game()
        before = game.capture_undo_state()
        play = game.play_to_table
        calls = []
        def fail_second(*args):
            calls.append(args)
            return play(*args) if len(calls) == 1 else None
        with patch.object(game, "play_to_table", side_effect=fail_second):
            result = game.session.execute("play_cards", card_indices=[0, 1])
        self.assertFalse(result.success)
        self.assertFalse(result.events)
        self.assertEqual(game.capture_undo_state(), before)
        self.assertFalse(game.undo_stack)
        game.session.checkpoint_callback.assert_not_called()

    def test_rule_save_preset_restart_legacy_and_selection_invalidation(self):
        game = self.game()
        selection = SelectionState()
        selection.synchronize(build_selection_snapshot(game))
        selection.select_hand(1)
        game.session.execute("play_cards", card_indices=[0, 2])
        selection.synchronize(build_selection_snapshot(game))
        self.assertIsNone(selection.hand_index)
        state = export_session(game)
        loaded = restore_session(Game, state)
        self.assertTrue(loaded.allow_play_multiple_cards)
        self.assertEqual(loaded.capture_undo_state(), game.capture_undo_state())
        self.assertTrue(game.restart().allow_play_multiple_cards)
        del state["allow_play_multiple_cards"]
        self.assertFalse(restore_session(Game, state).allow_play_multiple_cards)
        with self.assertRaises(ValueError):
            restore_session(Game, dict(state, allow_play_multiple_cards=1))
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "bulk.json"
            saved = save_preset(path, {"allow_play_multiple_cards": True})
            self.assertTrue(load_preset(path, saved).settings["allow_play_multiple_cards"])

    def test_cli_batch_and_hotseat_blocking(self):
        game = self.game()
        output = io.StringIO()
        client = CLIClient(game, output, structured=True, confirm_next_turn=True)
        client.command("end")
        client.command("play-many 1 3")
        self.assertFalse(game.table_cards)
        client.command("cancel")
        client.command("play-many 1 3")
        self.assertEqual([entry["card"] for entry in game.table_cards], ["A", "C"])
        self.assertEqual(len(game.undo_stack), 1)

    def test_cli_flag_enables_batch_without_gui_dependencies(self):
        script = ("import sys; from portable_deck.cli import main; "
                  "main(['--play-multiple-cards','--players','2','--hand','3','--json']); "
                  "assert 'tkinter' not in sys.modules")
        result = subprocess.run([sys.executable, "-B", "-c", script],
                                input="play-many 1 3\nshow\nquit\n", text=True, capture_output=True,
                                timeout=30, cwd=Path(__file__).resolve().parents[1])
        self.assertEqual(result.returncode, 0, result.stderr)
        records = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertTrue(next(r["success"] for r in records if r["type"] == "result"))
        view = next(r["view"] for r in records if r["type"] == "view")
        self.assertEqual(view["status"]["table_count"], 2)

    def test_gui_dialog_uses_hand_projection_and_rejects_stale_selection(self):
        game = self.game()
        gui = HandoffGUI(game, enabled=False)
        commands = {}
        with ExitStack() as stack:
            for widget in ("Toplevel", "Label", "Listbox", "Button"):
                factory = stack.enter_context(patch("portable_deck.ui.gameguiactions.tk." + widget))
                if widget == "Listbox":
                    choices = factory.return_value
                    choices.curselection.return_value = (0, 2)
                if widget == "Button":
                    factory.side_effect = lambda *args, **kw: commands.setdefault(kw["text"], kw["command"]) and Mock()
            warning = stack.enter_context(patch("portable_deck.ui.gameguiactions.messagebox.showwarning"))
            gui.play_multiple_cards()
            self.assertEqual(choices.insert.call_count, 5)
            self.assertTrue(commands["Play selected cards"]().success)
            self.assertEqual([e["card"] for e in game.table_cards], ["A", "C"])
            commands.clear()
            gui.play_multiple_cards()
            game.players[0].hand.reverse()
            before = game.capture_undo_state()
            commands["Play selected cards"]()
            warning.assert_called_once()
            self.assertEqual(game.capture_undo_state(), before)
