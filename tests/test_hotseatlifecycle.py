"""Cross-client regression through pending saves, approvals and persisted Undo."""
import io
import json
import tempfile
import unittest
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

from portable_deck.cli import CLIClient
from portable_deck.app.checkpoints import save_checkpoint
from portable_deck.app.newgame import create_game
from portable_deck.app.namedsaves import save_named_session
from portable_deck.app.sessionstorage import load_session, load_session_with_view
from portable_deck.app.sessionview import TableViewState
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
            save_named_session(g, path)
            loaded = load_session(Game, path)
            self.assertEqual(loaded.capture_undo_state(), g.capture_undo_state())
            loaded.session.checkpoint_callback = lambda game: save_checkpoint(game, path)
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
            resumed = load_session(Game, path)
            self.assertEqual(resumed.capture_undo_state(), before_pot)
            resumed.session.checkpoint_callback = lambda game: save_checkpoint(game, path)
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
            final = load_session(Game, path)
            self.assertEqual(final.capture_undo_state(), resumed.capture_undo_state())
        records = [json.loads(line) for line in output.getvalue().splitlines()]
        self.assertFalse(any("HIDDEN TABLE" in json.dumps(record) for record in records))

    def test_new_game_save_clients_undo_and_restart_without_source_deck(self):
        with tempfile.TemporaryDirectory() as folder:
            deck_path = Path(folder) / "deck.json"
            definition = {"types": ["Portable"], "cards": [list(range(1, 13))]}
            deck_path.write_text(json.dumps(definition), encoding="utf-8")
            game = create_game({"num_players": 2, "cards_per_player": 2,
                                "deck_path": str(deck_path), "enable_undo": True})
            checkpoint = Path(folder) / "last_session.json"
            game.session.checkpoint_callback = lambda current: save_checkpoint(current, checkpoint)
            for action, arguments in (("draw_card", {}), ("play_card", {"card_index": 0}),
                                      ("end_turn", {})):
                result = game.session.execute(action, **arguments)
                self.assertTrue(result.success, result.message)
                self.assertIsNone(result.checkpoint_error)
            view = TableViewState(150, .25, .5)
            path = Path(folder) / "named.json"
            save_named_session(game, path, client_state={"table_view": asdict(view)})
            saved_bytes = path.read_bytes()
            deck_path.unlink()
            loaded, loaded_view = load_session_with_view(Game, path)
            self.assertEqual(loaded_view, view)
            self.assertEqual(loaded.capture_undo_state(), game.capture_undo_state())
            self.assertEqual(load_session(Game, checkpoint).capture_undo_state(), game.capture_undo_state())
            self.assertTrue(loaded.session.undo())
            self.assertEqual(loaded.capture_undo_state(), game.undo_stack[-1])
            expected_view = json.loads(json.dumps(asdict(build_player_session_view(
                loaded, loaded.current_player_index))))
            script = ("import sys; from portable_deck.cli import main; "
                      "assert main(['--json','--load',sys.argv[1]]) == 0; "
                      "assert 'tkinter' not in sys.modules")
            result = subprocess.run([sys.executable, "-B", "-c", script, str(path)],
                                    input="undo\nshow\nquit\n", text=True, capture_output=True,
                                    cwd=Path(__file__).resolve().parents[1], timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            records = [json.loads(line) for line in result.stdout.splitlines()]
            self.assertEqual([record for record in records if record["type"] == "view"][-1]["view"], expected_view)
            self.assertEqual(path.read_bytes(), saved_bytes)
            restarted = loaded.restart()
            cards = restarted.deck.flat_deck + [card for player in restarted.players for card in player.hand]
            self.assertCountEqual(cards, [f"{n} of Portable" for n in range(1, 13)])
            self.assertEqual([len(player.hand) for player in restarted.players], [2, 2])
            self.assertEqual(restarted.table_cards, [])
            self.assertEqual(restarted.undo_stack, [])
            self.assertIsNone(restarted.session.checkpoint_callback)
