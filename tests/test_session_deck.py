import json
import tempfile
import unittest
from pathlib import Path

from portable_deck.core.game import Game
from portable_deck.app.sessionstorage import save_session, load_session


class SessionDeckTests(unittest.TestCase):
    def test_load_and_restart_use_embedded_definition(self):
        for source_state in ("changed", "deleted", "invalid"):
            with self.subTest(source_state=source_state), tempfile.TemporaryDirectory() as folder:
                deck_path = Path(folder) / "deck.json"
                definition = {"types": ["Original"], "cards": [[1, 2, 3, 4, 5, 6]]}
                deck_path.write_text(json.dumps(definition), encoding="utf-8")
                game = Game(2, str(deck_path), enable_undo=True)
                game.start(1)
                game.session.execute("draw_card")
                saved = str(Path(folder) / "session.json")
                save_session(game, saved)
                if source_state == "deleted":
                    deck_path.unlink()
                elif source_state == "invalid":
                    deck_path.write_text("broken", encoding="utf-8")
                else:
                    deck_path.write_text(json.dumps({"types": ["New"], "cards": [[99]]}), encoding="utf-8")
                loaded = load_session(Game, saved)
                self.assertEqual(loaded.deck.cards, definition["cards"])
                self.assertEqual(loaded.capture_undo_state(), game.capture_undo_state())
                for source in (game, loaded):
                    restarted = source.restart()
                    cards = restarted.deck.flat_deck + [card for player in restarted.players for card in player.hand]
                    self.assertCountEqual(cards, [f"{n} of Original" for n in range(1, 7)])
                    restarted.deck.flat_deck.append("restart only")
                    self.assertNotIn("restart only", source.deck.flat_deck)
                    self.assertEqual(source.deck.cards, definition["cards"])
                self.assertTrue(loaded.session.undo())
                self.assertEqual(loaded.capture_undo_state(), game.undo_stack[-1])

    def test_legacy_save_falls_back_only_when_definition_is_absent(self):
        with tempfile.TemporaryDirectory() as folder:
            deck_path = Path(folder) / "deck.json"
            deck_path.write_text(json.dumps({"types": ["Legacy"], "cards": [[1, 2]]}), encoding="utf-8")
            game = Game(1, str(deck_path))
            game.start(1)
            saved = Path(folder) / "session.json"
            save_session(game, str(saved))
            state = json.loads(saved.read_text(encoding="utf-8"))
            del state["deck_types"]
            del state["deck_cards"]
            saved.write_text(json.dumps(state), encoding="utf-8")
            self.assertEqual(load_session(Game, str(saved)).deck.types, ["Legacy"])
            state["deck_types"] = ["Incomplete"]
            saved.write_text(json.dumps(state), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_session(Game, str(saved))
            del state["deck_types"]
            saved.write_text(json.dumps(state), encoding="utf-8")
            deck_path.unlink()
            with self.assertRaises(FileNotFoundError):
                load_session(Game, str(saved))
