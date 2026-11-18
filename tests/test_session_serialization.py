import json
import unittest
from pathlib import Path
from unittest.mock import patch

from portable_deck.core.game import Game
from portable_deck.core.gamesession import export_session, restore_session


class SessionSerializationTests(unittest.TestCase):
    def game(self):
        game = Game(2, str(Path(__file__).resolve().parents[1] / "decks/demodeck.json"),
                    enable_undo=True, score_enabled=True, require_point_confirmation=True,
                    enable_chip_accounts=True, starting_balance=10,
                    require_pot_withdrawal_confirmation=True)
        game.start(2)
        for action, arguments in (("play_card", {"card_index": 0}),
                                  ("draw_card", {}), ("request_point", {}),
                                  ("play_chips", {"amount": 3}),
                                  ("take_pot", {"player_index": 1})):
            self.assertTrue(game.session.execute(action, **arguments).success)
        return game

    def test_round_trip_without_file_access_preserves_state_and_undo(self):
        original = self.game()
        original.named_save_path = "client-only.json"
        with patch("builtins.open", side_effect=AssertionError("Unexpected file access")):
            state = export_session(original)
            restored = restore_session(Game, json.loads(json.dumps(state)))
            self.assertEqual(json.loads(json.dumps(export_session(restored))),
                             json.loads(json.dumps(state)))
            self.assertIsNotNone(restored.pending_point_request)
            self.assertIsNotNone(restored.pending_pot_withdrawal)
            self.assertFalse(hasattr(restored, "named_save_path"))
            self.assertIsNone(restored.session.checkpoint_callback)
            self.assertTrue(restored.session.undo())
            self.assertTrue(original.session.undo())
            self.assertEqual(restored.capture_undo_state(), original.capture_undo_state())

    def test_export_and_restore_do_not_share_mutable_state(self):
        original = self.game()
        state = export_session(original)
        before = export_session(original)
        restored = restore_session(Game, state)
        self.assertEqual(state, before)
        restored.players[0].hand.append("restored only")
        restored.deck.cards[0].append("restored only")
        restored.undo_stack.clear()
        self.assertEqual(state, before)
        state["players"][0]["hand"].append("export only")
        state["deck_cards"][0].append("export only")
        state["undo_stack"].clear()
        self.assertEqual(export_session(original), before)
        self.assertNotIn("export only", restored.players[0].hand)
