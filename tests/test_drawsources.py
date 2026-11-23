import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from portable_deck.app.sessionstorage import load_session, save_session
from portable_deck.cli import CLIClient
from portable_deck.core.actionavailability import ActionContext, action_availability
from portable_deck.core.drawpiles import DRAW_SOURCE_ACTIONS, draw_pile_options
from portable_deck.core.game import Game
from tests.test_turnhandoff import HandoffGUI


class DrawSourceTests(unittest.TestCase):
    def game(self):
        game = Game(2, str(Path(__file__).resolve().parents[1] / "decks/demodeck.json"), enable_undo=True,
                    enable_special_actions=True, allow_draw_multiple_cards=True,
                    allow_shuffle_draw_deck=True, allow_deal_cards=True, allow_shared_offer=True)
        game.start(0)
        game.draw_piles.add("reserve", "Reserve", [f"SECRET_{i}" for i in range(6)])
        game.draw_piles.add("mine", "My deck", ["OWN_A", "OWN_B"], owner=0)
        game.draw_piles.add("theirs", "Other deck", ["OTHER_A", "OTHER_B"], owner=1)
        game.session.checkpoint_callback = Mock(return_value=None)
        return game

    def test_draw_and_batch_use_only_selected_pile_with_one_undo(self):
        for action, count in (("draw_card", 1), ("draw_cards", 3)):
            game = self.game()
            before = game.capture_undo_state()
            result = game.session.execute(action, count=count, draw_pile_id="reserve")
            self.assertTrue(result.success)
            self.assertEqual(game.players[0].hand, [f"SECRET_{i}" for i in range(count)])
            self.assertEqual(game.deck.flat_deck, before["remaining_deck"])
            self.assertEqual(len(game.draw_piles.get("reserve").cards), 6 - count)
            self.assertEqual(len(game.undo_stack), 1)
            game.session.checkpoint_callback.assert_called_once_with(game)
            self.assertNotIn("SECRET", repr(result.messages))
            self.assertTrue(game.session.undo())
            self.assertEqual(game.capture_undo_state(), before)

    def test_shuffle_deal_and_offer_honor_selected_source(self):
        for action in ("shuffle_draw_deck", "deal_cards", "start_shared_offer"):
            game = self.game()
            before = game.capture_undo_state()
            with patch("portable_deck.core.specialactions.random.shuffle", side_effect=lambda cards: cards.reverse()):
                result = game.session.execute(action, count=2, draw_pile_id="reserve")
            self.assertTrue(result.success)
            self.assertEqual(game.deck.flat_deck, before["remaining_deck"])
            if action == "shuffle_draw_deck":
                self.assertEqual(game.draw_piles.get("reserve").cards[0], "SECRET_5")
            elif action == "deal_cards":
                self.assertEqual(game.players[1].hand, ["SECRET_1", "SECRET_3"])
            else:
                self.assertEqual(game.pending_shared_offer["cards"], ["SECRET_0", "SECRET_1"])
            self.assertTrue(game.session.undo())
            self.assertEqual(game.capture_undo_state(), before)

    def test_unknown_or_inaccessible_piles_are_rejected_for_all_source_actions(self):
        for action in DRAW_SOURCE_ACTIONS:
            for source in ("missing", "theirs", True, None, []):
                game = self.game()
                before = game.capture_undo_state()
                result = game.session.execute(action, count=1, draw_pile_id=source)
                self.assertFalse(result.success, (action, source))
                self.assertEqual(result.code, "access_denied" if source == "theirs" else "invalid_draw_pile")
                self.assertEqual(game.capture_undo_state(), before)
                game.session.checkpoint_callback.assert_not_called()

    def test_availability_and_capacity_use_selected_contents_not_default(self):
        game = self.game()
        game.deck.flat_deck.clear()
        context = ActionContext(draw_pile_id="reserve")
        self.assertTrue(action_availability(game, "draw_card", context).allowed)
        self.assertFalse(action_availability(game, "draw_card").allowed)
        self.assertTrue(game.session.execute("draw_cards", count=6, draw_pile_id="reserve").success)
        self.assertFalse(action_availability(game, "draw_card", context).allowed)
        game = self.game()
        before = game.capture_undo_state()
        self.assertEqual(game.session.execute("draw_cards", count=7, draw_pile_id="reserve").code, "insufficient_cards")
        self.assertEqual(game.capture_undo_state(), before)

    def test_personal_access_tracks_current_player_and_options_are_public(self):
        game = self.game()
        self.assertEqual([p.id for p in draw_pile_options(game)], ["main", "reserve", "mine"])
        self.assertNotIn("SECRET", repr(draw_pile_options(game)))
        self.assertTrue(game.session.execute("draw_card", draw_pile_id="mine").success)
        game.session.execute("end_turn")
        self.assertEqual([p.id for p in draw_pile_options(game)], ["main", "reserve", "theirs"])
        self.assertEqual(game.session.execute("draw_card", draw_pile_id="mine").code, "access_denied")

    def test_named_source_failures_restore_all_piles_and_hand(self):
        game = self.game()
        before = game.capture_undo_state()
        pile = game.draw_piles.get("reserve")
        draw = pile.draw_card
        calls = []
        def fail_second():
            calls.append(1)
            return draw() if len(calls) == 1 else None
        with patch.object(pile, "draw_card", side_effect=fail_second):
            self.assertFalse(game.session.execute("draw_cards", count=2, draw_pile_id="reserve").success)
        self.assertEqual(game.capture_undo_state(), before)
        game.session.checkpoint_callback.assert_not_called()

    def test_gui_count_prompt_uses_selected_source(self):
        game = self.game()
        gui = HandoffGUI(game, enabled=False)
        gui.draw_pile_id = "reserve"
        with patch("tkinter.simpledialog.askinteger", return_value=3) as prompt:
            self.assertTrue(gui.draw_multiple_cards().success)
        self.assertEqual(prompt.call_args.kwargs["maxvalue"], 6)
        self.assertEqual(game.players[0].hand, ["SECRET_0", "SECRET_1", "SECRET_2"])
        with patch("tkinter.simpledialog.askinteger", return_value=1) as prompt:
            self.assertTrue(gui.deal_cards().success)
        self.assertEqual(prompt.call_args.kwargs["maxvalue"], 1)

    def test_cli_sources_selection_privacy_turn_fallback_and_disk_load(self):
        game = self.game()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "game.json"
            save_session(game, path)
            game = load_session(Game, path)
        output = io.StringIO()
        client = CLIClient(game, output, structured=True)
        client.command("sources")
        options = json.loads(output.getvalue().splitlines()[-1])
        self.assertNotIn("theirs", [p["id"] for p in options["piles"]])
        client.command("source reserve")
        client.command("draw-many 2")
        self.assertEqual(game.players[0].hand, ["SECRET_0", "SECRET_1"])
        self.assertNotIn("SECRET", output.getvalue())
        client.command("source mine")
        client.command("end")
        self.assertEqual(client.draw_pile_id, "main")
        client.command("source theirs")
        client.command("draw")
        self.assertEqual(game.players[1].hand[-1], "OTHER_A")
