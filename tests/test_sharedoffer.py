import io
import json
import subprocess
import sys
import tempfile
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest.mock import Mock, patch

from portable_deck.app.settingspresets import load_preset, save_preset
from portable_deck.app.sessionstorage import load_session, save_session
from portable_deck.cli import CLIClient
from portable_deck.core.game import Game
from portable_deck.core.gamesession import export_session, restore_session
from portable_deck.core.playersessionview import build_player_session_view
from portable_deck.core.sharedoffer import shared_offer_view


class SharedOfferTests(unittest.TestCase):
    def game(self):
        game = Game(4, str(Path(__file__).resolve().parents[1] / "decks/demodeck.json"),
                    enable_special_actions=True, allow_shared_offer=True, enable_undo=True,
                    allow_reverse_turn_order=True)
        game.start(0)
        game.deck.flat_deck = ["A", "B", "C", "D", "E"]
        for index, player in enumerate(game.players):
            player.hand = [f"PRIVATE_{index}"]
        game.cards_drawn_this_turn = 2
        game.session.checkpoint_callback = Mock(return_value=None)
        return game

    def test_public_offer_chooses_in_direction_skips_departed_and_keeps_turn(self):
        for direction, order in ((1, [2, 3, 0]), (-1, [2, 0, 3])):
            game = self.game()
            game.current_player_index = 2
            game.left_players = [1]
            game.turn_direction = direction
            self.assertTrue(game.session.execute("start_shared_offer").success)
            self.assertEqual(game.deck.flat_deck, ["D", "E"])
            initial = shared_offer_view(game)
            self.assertEqual(initial.remaining_players, tuple(order))
            self.assertEqual(initial.cards, ("A", "B", "C"))
            for player, card, chosen_index in zip(order, ("B", "A", "C"), (1, 0, 0)):
                self.assertEqual(shared_offer_view(game).player, player)
                self.assertTrue(game.session.execute("choose_shared_offer", card_index=chosen_index).success)
                self.assertEqual(game.players[player].hand[-1], card)
            self.assertFalse(shared_offer_view(game).active)
            self.assertEqual(game.players[1].hand, ["PRIVATE_1"])
            self.assertEqual(game.current_player_index, 2)
            self.assertEqual(game.cards_drawn_this_turn, 2)
            self.assertEqual(len(game.undo_stack), 4)
            self.assertEqual(game.session.checkpoint_callback.call_count, 4)
            self.assertEqual(initial.cards, ("A", "B", "C"))
            with self.assertRaises(FrozenInstanceError): initial.active = False

    def test_undo_restores_last_pick_and_opening_restores_deck(self):
        game = self.game()
        before = game.capture_undo_state()
        game.session.execute("start_shared_offer")
        opened = game.capture_undo_state()
        game.session.execute("choose_shared_offer", card_index=2)
        self.assertTrue(game.session.undo())
        self.assertEqual(game.capture_undo_state(), opened)
        self.assertTrue(game.session.undo())
        self.assertEqual(game.capture_undo_state(), before)

    def test_pending_offer_blocks_gameplay_lifecycle_and_hides_private_hands(self):
        game = self.game()
        game.players[0].revealed_indices = {0}
        game.session.execute("start_shared_offer")
        before = game.capture_undo_state()
        for action in ("draw_card", "end_turn", "leave_session", "return_player", "confirm_point",
                       "confirm_pot", "start_shared_offer", "reverse_turn_order", "deal_cards"):
            self.assertEqual(game.session.execute(action).code, "shared_offer_pending")
        self.assertEqual(game.capture_undo_state(), before)
        self.assertEqual(game.session.checkpoint_callback.call_count, 1)
        self.assertEqual(game.session.end_turn_availability().code, "shared_offer_pending")
        for viewer in range(4):
            view = build_player_session_view(game, viewer)
            self.assertNotIn("PRIVATE_", repr(view))
            self.assertTrue(view.shared_offer.active)

    def test_invalid_picks_and_no_pending_offer_preserve_state(self):
        game = self.game()
        self.assertEqual(game.session.execute("choose_shared_offer", card_index=0).code, "no_shared_offer")
        game.session.execute("start_shared_offer")
        before = game.capture_undo_state()
        for index in (None, -1, True, "1", 4):
            self.assertEqual(game.session.execute("choose_shared_offer", card_index=index).code, "invalid_selection")
        self.assertEqual(game.capture_undo_state(), before)
        self.assertEqual(game.session.checkpoint_callback.call_count, 1)

    def test_unavailable_opening_and_short_deck_preserve_state(self):
        for reason in ("disabled", "option", "short", "left", "point", "pot"):
            game = self.game()
            if reason == "disabled": game.enable_special_actions = False
            elif reason == "option": game.allow_shared_offer = False
            elif reason == "short": game.deck.flat_deck = ["A", "B"]
            elif reason == "left": game.left_players = [0]
            elif reason == "point": game.pending_point_request = {"requester": 0}
            else: game.pending_pot_withdrawal = {"requester": 0}
            before = game.capture_undo_state()
            self.assertFalse(game.session.execute("start_shared_offer").success)
            self.assertEqual(game.capture_undo_state(), before)
            game.session.checkpoint_callback.assert_not_called()

    def test_failed_open_or_pick_rolls_back_all_state(self):
        game = self.game()
        before = game.capture_undo_state()
        draw = game.deck.draw_card
        calls = []
        def fail_third():
            calls.append(1)
            return draw() if len(calls) < 3 else None
        with patch.object(game.deck, "draw_card", side_effect=fail_third):
            self.assertFalse(game.session.execute("start_shared_offer").success)
        self.assertEqual(game.capture_undo_state(), before)
        game.session.execute("start_shared_offer")
        before = game.capture_undo_state()
        with patch.object(game, "log_action", side_effect=ValueError("log failed")):
            self.assertFalse(game.session.execute("choose_shared_offer", card_index=0).success)
        self.assertEqual(game.capture_undo_state(), before)

    def test_pending_save_load_preset_legacy_and_restart(self):
        game = self.game()
        game.session.execute("start_shared_offer")
        game.session.execute("choose_shared_offer", card_index=0)
        state = export_session(game)
        loaded = restore_session(Game, state)
        self.assertEqual(loaded.capture_undo_state(), game.capture_undo_state())
        self.assertEqual(shared_offer_view(loaded).player, 1)
        for _ in range(3):
            self.assertTrue(loaded.session.execute("choose_shared_offer", card_index=0).success)
        self.assertFalse(shared_offer_view(loaded).active)
        restarted = game.restart()
        self.assertTrue(restarted.allow_shared_offer)
        self.assertIsNone(restarted.pending_shared_offer)
        legacy = export_session(restarted)
        del legacy["allow_shared_offer"]
        del legacy["pending_shared_offer"]
        self.assertFalse(restore_session(Game, legacy).allow_shared_offer)
        with tempfile.TemporaryDirectory() as folder:
            saved_game = Path(folder) / "game.json"
            save_session(game, saved_game)
            disk_game = load_session(Game, saved_game)
            self.assertEqual(shared_offer_view(disk_game), shared_offer_view(game))
            self.assertTrue(disk_game.session.execute("choose_shared_offer", card_index=0).success)
            path = Path(folder) / "offer.json"
            saved = save_preset(path, {"enable_special_actions": True, "allow_shared_offer": True})
            self.assertTrue(load_preset(path, saved).settings["allow_shared_offer"])

    def test_malformed_saved_offer_is_rejected(self):
        game = self.game()
        game.session.execute("start_shared_offer")
        state = export_session(game)
        for offer in ({}, {"cards": [], "players": []}, {"cards": ["A"], "players": [True]},
                      {"cards": ["A"], "players": [4]}, {"cards": ["A", "B"], "players": [0, 0]},
                      {"cards": [None], "players": [0]}):
            with self.assertRaises(ValueError): restore_session(Game, dict(state, pending_shared_offer=offer))
        with self.assertRaises(ValueError): restore_session(Game, dict(state, allow_shared_offer=False))

    def test_one_active_player_and_duplicate_offer_cards(self):
        game = self.game()
        game.left_players = [1, 2, 3]
        game.deck.flat_deck = ["A"]
        self.assertTrue(game.session.execute("start_shared_offer").success)
        self.assertTrue(game.session.execute("choose_shared_offer", card_index=0).success)
        self.assertFalse(shared_offer_view(game).active)
        game = self.game()
        game.deck.flat_deck = ["A"] * 4
        game.session.execute("start_shared_offer")
        for _ in range(4): self.assertTrue(game.session.execute("choose_shared_offer", card_index=0).success)
        self.assertTrue(all(player.hand[-1] == "A" for player in game.players))

    def test_cli_offer_resumes_public_phase_and_blocks_handoff(self):
        game = self.game()
        output = io.StringIO()
        client = CLIClient(game, output, structured=True, confirm_next_turn=True)
        client.command("offer")
        client.command("show")
        client.command("end")
        self.assertFalse(client.turn_flow.pending)
        self.assertNotIn("PRIVATE_", output.getvalue())
        for _ in range(4): client.command("choose-offer 1")
        self.assertIsNone(game.pending_shared_offer)
        self.assertEqual(game.current_player_index, 0)
        script = ("import sys; from portable_deck.cli import main; "
                  "main(['--shared-offer','--players','2','--hand','1','--json']); "
                  "assert 'tkinter' not in sys.modules")
        result = subprocess.run([sys.executable, "-B", "-c", script],
                                input="offer\nshow\nchoose-offer 1\nchoose-offer 1\nquit\n",
                                text=True, capture_output=True, timeout=30, cwd=Path(__file__).resolve().parents[1])
        self.assertEqual(result.returncode, 0, result.stderr)
        records = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertTrue(any(r["type"] == "shared_offer" for r in records))
