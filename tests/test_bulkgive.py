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
from portable_deck.core.interactions import build_interaction_options
from tests.test_turnhandoff import HandoffGUI


class BulkGiveTests(unittest.TestCase):
    def game(self):
        game = Game(3, str(Path(__file__).resolve().parents[1] / "decks/demodeck.json"),
                    enable_interactions=True, interaction_options={"give_cards": True}, enable_undo=True)
        game.start(0)
        game.players[0].hand = ["SECRET_A", "SECRET_B", "SECRET_C", "SECRET_D"]
        game.players[0].revealed_indices = {0, 1, 3}
        game.players[1].hand = ["OLD"]
        game.players[1].revealed_indices = {0}
        game.session.checkpoint_callback = Mock(return_value=None)
        return game

    def test_batch_order_visibility_privacy_and_one_undo_checkpoint(self):
        game = self.game()
        before = game.capture_undo_state()
        result = game.session.execute("give_cards", target=1, card_indices=[3, 0, 2])
        self.assertTrue(result.success)
        self.assertEqual(game.players[0].hand, ["SECRET_B"])
        self.assertEqual(game.players[0].revealed_indices, {0})
        self.assertEqual(game.players[1].hand, ["OLD", "SECRET_A", "SECRET_C", "SECRET_D"])
        self.assertEqual(game.players[1].revealed_indices, {0})
        self.assertNotIn("SECRET", repr(result.events) + repr(result.messages))
        self.assertEqual(result.events[0]["count"], 3)
        self.assertEqual(len(game.undo_stack), 1)
        game.session.checkpoint_callback.assert_called_once_with(game)
        self.assertTrue(game.session.undo())
        self.assertEqual(game.capture_undo_state(), before)

    def test_invalid_selection_target_or_disabled_interaction_preserves_state(self):
        cases = [{"card_indices": value} for value in (None, [], [0], [0, 0], [True, 1], [0, 4])]
        cases += [{"target": value} for value in (0, 3, -1, True, None)]
        for overrides in cases:
            game = self.game()
            before = game.capture_undo_state()
            parameters = dict(target=1, card_indices=[0, 1])
            parameters.update(overrides)
            self.assertFalse(game.session.execute("give_cards", **parameters).success)
            self.assertEqual(game.capture_undo_state(), before)
            game.session.checkpoint_callback.assert_not_called()
        for reason in ("disabled", "option_disabled", "left_actor", "left_target", "confirmation"):
            game = self.game()
            if reason == "disabled":
                game.enable_interactions = False
            elif reason == "option_disabled":
                game.interaction_options["give_cards"] = False
            elif reason == "left_actor":
                game.left_players = [0]
            elif reason == "left_target":
                game.left_players = [1]
            else:
                game.current_player_must_confirm_point = lambda: True
            before = game.capture_undo_state()
            self.assertFalse(game.session.execute("give_cards", target=1, card_indices=[0, 1]).success)
            self.assertEqual(game.capture_undo_state(), before)
            game.session.checkpoint_callback.assert_not_called()

    def test_options_allow_empty_recipient_and_exclude_departed_players(self):
        game = self.game()
        game.players[1].hand.clear()
        game.left_players = [2]
        options = build_interaction_options(game, "give_cards")
        self.assertTrue(options.allowed)
        self.assertTrue(options.targets[0].allowed)
        self.assertFalse(options.targets[1].allowed)
        self.assertNotIn("SECRET", repr(options))
        self.assertTrue(game.session.execute("give_cards", target=1, card_indices=[0, 1]).success)

    def test_later_failure_rolls_back_both_hands(self):
        game = self.game()
        before = game.capture_undo_state()
        draw = game.players[1].draw_card
        calls = []
        def fail_second(card):
            calls.append(card)
            if len(calls) == 2:
                raise ValueError("Failed delivery")
            draw(card)
        with patch.object(game.players[1], "draw_card", side_effect=fail_second):
            self.assertFalse(game.session.execute("give_cards", target=1, card_indices=[0, 1]).success)
        self.assertEqual(game.capture_undo_state(), before)
        self.assertFalse(game.undo_stack)
        game.session.checkpoint_callback.assert_not_called()

    def test_preset_save_restart_and_legacy_option_default(self):
        game = self.game()
        game.session.execute("give_cards", target=1, card_indices=[0, 2])
        state = export_session(game)
        loaded = restore_session(Game, state)
        self.assertTrue(loaded.interaction_allowed("give_cards"))
        self.assertEqual(loaded.capture_undo_state(), game.capture_undo_state())
        self.assertTrue(loaded.session.undo())
        self.assertTrue(game.restart().interaction_allowed("give_cards"))
        del state["interaction_options"]["give_cards"]
        self.assertFalse(restore_session(Game, state).interaction_allowed("give_cards"))
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "give.json"
            saved = save_preset(path, {"enable_interactions": True, "interaction_options": {"give_cards": True}})
            self.assertTrue(load_preset(path, saved).settings["interaction_options"]["give_cards"])

    def test_gui_selector_validates_recipient_again_on_execution(self):
        game = self.game()
        gui = HandoffGUI(game, enabled=False)
        commands = {}
        def button(*args, **kwargs):
            commands[kwargs["text"]] = kwargs["command"]
            return Mock()
        with ExitStack() as stack:
            for widget in ("Toplevel", "Label"):
                stack.enter_context(patch("portable_deck.ui.gameguiactions.tk." + widget))
            choices = stack.enter_context(patch("portable_deck.ui.gameguiactions.tk.Listbox")).return_value
            choices.curselection.return_value = (0, 2)
            stack.enter_context(patch("portable_deck.ui.gameguiactions.tk.Button", side_effect=button))
            warning = stack.enter_context(patch("portable_deck.ui.gameguiactions.messagebox.showwarning"))
            gui.give_multiple_cards(1)
            game.left_players = [1]
            self.assertFalse(commands["Give selected cards"]().success)
            warning.assert_called_once()
            self.assertFalse(game.undo_stack)
            game.left_players = []
            self.assertTrue(commands["Give selected cards"]().success)
        self.assertEqual(game.players[1].hand, ["OLD", "SECRET_A", "SECRET_C"])

    def test_cli_privacy_and_handoff_blocking(self):
        game = self.game()
        output = io.StringIO()
        client = CLIClient(game, output, structured=True, confirm_next_turn=True)
        client.command("end")
        client.command("give-many 2 1 3")
        self.assertEqual(len(game.players[0].hand), 4)
        client.command("cancel")
        client.command("give-many 2 1 3")
        self.assertEqual(game.players[1].hand, ["OLD", "SECRET_A", "SECRET_C"])
        self.assertNotIn("SECRET", output.getvalue())

    def test_cli_flag_enables_batch_without_tkinter(self):
        script = ("import sys; from portable_deck.cli import main; "
                  "main(['--give-multiple-cards','--hand','3','--json']); "
                  "assert 'tkinter' not in sys.modules")
        result = subprocess.run([sys.executable, "-B", "-c", script],
                                input="give-many 2 1 3\nshow\nquit\n", text=True, capture_output=True,
                                timeout=30, cwd=Path(__file__).resolve().parents[1])
        self.assertEqual(result.returncode, 0, result.stderr)
        records = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertTrue(next(r["success"] for r in records if r["type"] == "result"))
        view = next(r["view"] for r in records if r["type"] == "view")
        self.assertEqual(view["status"]["players"][1]["card_count"], 5)
