import json
import tempfile
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest.mock import Mock

from portable_deck.app.sessionstorage import load_session, save_session
from portable_deck.core.game import Game
from portable_deck.core.gamesession import export_session, restore_session
from portable_deck.core.sessionstatus import build_session_status


class DrawPilesTests(unittest.TestCase):
    def game(self):
        game = Game(2, str(Path(__file__).resolve().parents[1] / "decks/demodeck.json"), enable_undo=True)
        game.start(0)
        game.session.checkpoint_callback = Mock(return_value=None)
        return game

    def test_default_is_the_existing_deck_pile_through_draw_and_undo(self):
        game = self.game()
        self.assertIs(game.draw_piles.get("main"), game.deck.draw_pile)
        before = game.capture_undo_state()
        self.assertTrue(game.session.execute("draw_card").success)
        self.assertIs(game.draw_piles.get().cards, game.deck.flat_deck)
        self.assertTrue(game.session.undo())
        self.assertEqual(game.capture_undo_state(), before)
        self.assertIs(game.draw_piles.get(), game.deck.draw_pile)

    def test_named_piles_are_independent_and_public_metadata_is_private(self):
        game = self.game()
        cards = ["PRIVATE_A", "PRIVATE_B"]
        main = game.deck.flat_deck.copy()
        game.draw_piles.add("player-1", "Player deck", cards, owner=0)
        cards.clear()
        self.assertEqual(game.draw_piles.get("player-1").draw_card(), "PRIVATE_A")
        self.assertEqual(game.deck.flat_deck, main)
        view = build_session_status(game)
        self.assertEqual(view.draw_piles[-1].card_count, 1)
        self.assertEqual(view.draw_piles[-1].owner, 0)
        self.assertNotIn("PRIVATE", repr(view))
        with self.assertRaises(FrozenInstanceError): view.draw_piles[-1].name = "changed"
        self.assertEqual(view.draw_count, len(main))

    def test_pile_registration_and_mutations_are_undoable_transactions(self):
        game = self.game()
        before = game.capture_undo_state()
        def operation():
            cards = [game.deck.draw_card(), game.deck.draw_card()]
            game.draw_piles.add("reserve", "Reserve", cards)
        game.session.run(operation)
        self.assertEqual(len(game.undo_stack), 1)
        game.session.checkpoint_callback.assert_called_once_with(game)
        saved = game.capture_undo_state()
        game.session.run(lambda: game.draw_piles.get("reserve").cards.reverse())
        self.assertTrue(game.session.undo())
        self.assertEqual(game.capture_undo_state(), saved)
        self.assertTrue(game.session.undo())
        self.assertEqual(game.capture_undo_state(), before)

    def test_failed_transaction_restores_registry_and_default_alias(self):
        game = self.game()
        before = game.capture_undo_state()
        def operation():
            game.draw_piles.add("reserve", "Reserve", [game.deck.draw_card()])
            raise ValueError("failed")
        with self.assertRaises(ValueError): game.session.run(operation)
        self.assertEqual(game.capture_undo_state(), before)
        self.assertIs(game.draw_piles.get(), game.deck.draw_pile)
        game.session.checkpoint_callback.assert_not_called()

    def test_disk_roundtrip_keeps_all_orders_and_existing_remaining_deck(self):
        game = self.game()
        game.session.run(lambda: game.draw_piles.add("reserve", "Reserve", [game.deck.draw_card()], owner=1))
        before = game.capture_undo_state()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "game.json"
            save_session(game, path)
            state = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(state["remaining_deck"], game.deck.flat_deck)
            self.assertNotIn("cards", state["draw_piles"][0])
            loaded = load_session(Game, path)
        self.assertEqual(loaded.capture_undo_state(), before)
        self.assertIs(loaded.draw_piles.get(), loaded.deck.draw_pile)
        self.assertTrue(loaded.session.undo())
        self.assertEqual(len(loaded.draw_piles.view()), 1)

    def test_legacy_saves_and_undo_snapshots_create_only_default(self):
        game = self.game()
        game.session.execute("draw_card")
        state = export_session(game)
        del state["draw_piles"]
        for snapshot in state["undo_stack"]: snapshot.pop("draw_piles", None)
        loaded = restore_session(Game, state)
        self.assertEqual([pile.id for pile in loaded.draw_piles.view()], ["main"])
        self.assertTrue(loaded.session.undo())
        self.assertIs(loaded.draw_piles.get(), loaded.deck.draw_pile)

    def test_invalid_metadata_or_saved_state_never_replaces_valid_registry(self):
        game = self.game()
        before = game.draw_piles.snapshot()
        for pile_id, name, owner in (("main", "Duplicate", None), ("", "Empty", None),
                                      ("x", "", None), ("x", "Bad owner", True), ("x", "Bad owner", 2)):
            with self.assertRaises(ValueError): game.draw_piles.add(pile_id, name, owner=owner)
        for state in (None, [], [{}], before + before, [{"id": "extra", "name": "No main", "owner": None, "cards": []}],
                      before + [{"id": "extra", "name": "Invalid cards", "owner": None, "cards": [False]}],
                      [dict(before[0], cards=["DUPLICATE MAIN CONTENTS"])], [dict(before[0], owner=0)]):
            with self.assertRaises(ValueError): game.draw_piles.restore(state)
            with self.assertRaises(ValueError): restore_session(Game, dict(export_session(game), draw_piles=state))
        self.assertEqual(game.draw_piles.snapshot(), before)

    def test_restart_keeps_metadata_and_resets_extra_piles_to_empty(self):
        game = self.game()
        game.draw_piles.add("reserve", "Reserve", [game.deck.draw_card()], owner=1)
        before = game.capture_undo_state()
        restarted = game.restart()
        self.assertEqual([(p.id, p.name, p.owner) for p in restarted.draw_piles.view()],
                         [(p.id, p.name, p.owner) for p in game.draw_piles.view()])
        self.assertFalse(restarted.draw_piles.get("reserve").cards)
        self.assertEqual(len(restarted.deck.flat_deck), len(game.deck.definition.expanded_cards()))
        self.assertIs(restarted.draw_piles.get(), restarted.deck.draw_pile)
        self.assertEqual(game.capture_undo_state(), before)
