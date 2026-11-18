import tempfile
import unittest
from pathlib import Path

from portable_deck.app.deckcatalog import list_decks
from portable_deck.app.deckfiles import export_deck, import_deck
from portable_deck.app.deckstorage import prepare_deck_definition, save_deck_definition
from portable_deck.app.newgame import create_game
from portable_deck.app.sessionstorage import load_session, save_session
from portable_deck.core.deck import Deck
from portable_deck.core.game import Game


class DeckLifecycleTests(unittest.TestCase):
    def test_library_edit_transfer_and_new_game_preserve_running_session(self):
        with tempfile.TemporaryDirectory() as folder:
            library = Path(folder) / "library"
            original = library / "original.json"
            definition = prepare_deck_definition(["Žaludy"], [["1", "2", "2", "3", "4", "5"]])
            save_deck_definition(original, definition)
            game = create_game({"num_players": 2, "cards_per_player": 1,
                                "deck_path": str(original), "enable_undo": True})
            self.assertTrue(game.session.execute("draw_card").success)
            before = game.capture_undo_state()
            saved = Path(folder) / "session.json"
            save_session(game, saved)
            edited = prepare_deck_definition(["New"], [["A", "B", "C", "D"]])
            save_deck_definition(original, edited, overwrite=True)
            duplicate = library / "duplicate.json"
            save_deck_definition(duplicate, edited)
            exported = export_deck(duplicate, Path(folder) / "exported")
            second_library = Path(folder) / "imported"
            second_library.mkdir()
            imported = import_deck(exported, second_library)
            self.assertEqual(Path(imported).read_bytes(), duplicate.read_bytes())
            entries = list_decks(library)
            self.assertEqual([entry.name for entry in entries], ["duplicate", "original"])
            self.assertTrue(all(entry.card_count == 4 and entry.error is None for entry in entries))
            new_game = create_game({"num_players": 2, "cards_per_player": 1, "deck_path": imported})
            self.assertEqual(new_game.deck.types, ["New"])
            self.assertEqual(len(new_game.deck.flat_deck), 2)
            self.assertEqual(game.capture_undo_state(), before)
            self.assertEqual(game.deck.types, ["Žaludy"])
            original.unlink()
            restored = load_session(Game, saved)
            self.assertEqual(restored.capture_undo_state(), before)
            restarted = game.restart()
            self.assertEqual(restarted.deck.types, ["Žaludy"])
            self.assertEqual(len(restarted.deck.flat_deck), 4)
            self.assertTrue(restored.session.undo())
            self.assertEqual(restored.capture_undo_state(), game.undo_stack[-1])
            self.assertEqual(Deck(imported).cards, edited["cards"])
