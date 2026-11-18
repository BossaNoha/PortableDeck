"""Cross-client regression through pending saves, approvals and persisted Undo."""
import io
import json
import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path

from portable_deck.cli import CLIClient
from portable_deck.core.game import Game
from portable_deck.core.playersessionview import build_player_session_view
from portable_deck.core.turnstart import build_turn_start_view


class HotseatLifecycleTests(unittest.TestCase):
    def test_three_player_pending_save_cli_decisions_and_persisted_undo(self):
        g = Game(3, str(Path(__file__).resolve().parents[1] / "decks/demodeck.json"),
                 enable_undo=True, enable_flipping=True, allow_flip_table=True, allow_face_down_table_cards=True,
                 score_enabled=True, require_point_confirmation=True,
                 enable_chip_accounts=True, require_pot_withdrawal_confirmation=True)
        g.players[0].hand = ["HIDDEN TABLE", "OWNER CARD"]
        g.players[1].hand = ["PRIVATE ONE"]
        g.players[2].hand = ["PRIVATE TWO"]
        g.deck.flat_deck = ["DRAWN CARD", "DRAW ORDER SECRET"]
        for action, args in (
            ("draw_card", {}), ("play_face_down", {"card_index": 0}),
            ("request_point", {}), ("play_chips", {"amount": 5}),
            ("take_pot", {"player_index": 0}), ("end_turn", {}),
            ("confirm_point", {"approved": True}), ("confirm_pot", {"approved": True}),
            ("end_turn", {}),
        ):
            result = g.session.execute(action, **args)
            self.assertTrue(result.success, f"{action}: {result.message}")
        self.assertEqual(build_turn_start_view(g).player, 2)
        self.assertEqual([p.action for p in build_turn_start_view(g).confirmations], ["confirm_point", "confirm_pot"])
        with tempfile.TemporaryDirectory() as folder:
            path = str(Path(folder) / "pending.json")
            g.save_session(path)
            loaded = Game.load_session(path)
            self.assertEqual(loaded.capture_undo_state(), g.capture_undo_state())
            loaded.session.checkpoint_callback = lambda game: game.save_session(path)
            output = io.StringIO()
            client = CLIClient(loaded, output, structured=True)
            client.command("draw")
            self.assertEqual(json.loads(output.getvalue().splitlines()[-1])["code"], "confirmation_required")
            client.command("approve")
            self.assertEqual(loaded.scores, [1, 0, 0])
            self.assertEqual(build_turn_start_view(loaded).next_confirmation.action, "confirm_pot")
            before_pot = loaded.capture_undo_state()
            client.command("approve")
            self.assertEqual(loaded.chip_pot, 0)
            self.assertEqual(loaded.chip_balance(0), 100)
            client.command("undo")
            self.assertEqual(loaded.capture_undo_state(), before_pot)
            resumed = Game.load_session(path)
            self.assertEqual(resumed.capture_undo_state(), before_pot)
            resumed.session.checkpoint_callback = lambda game: game.save_session(path)
            resumed_client = CLIClient(resumed, output, structured=True)
            resumed_client.command("reject")
            self.assertEqual(resumed.chip_pot, 5)
            self.assertIsNone(resumed.pending_pot_withdrawal)
            resumed_client.command("end")
            view = build_player_session_view(resumed, 0)
            self.assertTrue(view.status.players[0].is_current)
            serialized = json.dumps(asdict(view))
            for secret in ("HIDDEN TABLE", "PRIVATE ONE", "PRIVATE TWO", "DRAW ORDER SECRET"):
                self.assertNotIn(secret, serialized)
            final = Game.load_session(path)
            self.assertEqual(final.capture_undo_state(), resumed.capture_undo_state())
        records = [json.loads(line) for line in output.getvalue().splitlines()]
        self.assertFalse(any("HIDDEN TABLE" in json.dumps(record) for record in records))
