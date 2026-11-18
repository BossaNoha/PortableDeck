import json
import unittest
from dataclasses import FrozenInstanceError, asdict
from pathlib import Path

from portable_deck.core.game import Game
from portable_deck.core.playersessionview import build_player_session_view
from portable_deck.core.playerview import (
    build_player_hands_view, build_player_table_view,
    build_player_personal_piles_view, build_player_discard_view,
)
from portable_deck.core.sessionstatus import build_session_status


class PlayerSessionViewTests(unittest.TestCase):
    def game(self, **options):
        g = Game(2, str(Path(__file__).resolve().parents[1] / "decks/demodeck.json"),
                 enable_personal_piles=True, **options)
        g.players[0].hand = ["PRIVATE ZERO"]
        g.players[1].hand = ["PRIVATE ONE", "REVEALED ONE"]
        g.players[1].revealed_indices = {1}
        g.table_cards = [{"card": "HIDDEN TABLE", "player": "Player1", "position": [0, 0], "face_up": False}]
        g.deck.flat_deck = ["HIDDEN DRAW ORDER"]
        g.discard_piles[0] = ["DEEP DISCARD", "PUBLIC DISCARD"]
        g.personal_piles[1][0] = ["PUBLIC PERSONAL"]
        g.history.append({"action": "private", "card": "HIDDEN HISTORY"})
        return g

    def test_combined_view_matches_existing_projections_without_mutation(self):
        g = self.game()
        before = g.capture_undo_state()
        view = build_player_session_view(g, 0, hand_index=0)
        self.assertEqual(view.status, build_session_status(g))
        self.assertEqual(view.hands, build_player_hands_view(g, 0))
        self.assertEqual(view.table, build_player_table_view(g, 0))
        self.assertEqual(view.personal_piles, build_player_personal_piles_view(g, 0, 0))
        self.assertEqual(view.discard, build_player_discard_view(g, 0))
        self.assertEqual(g.capture_undo_state(), before)

    def test_serialization_contains_only_viewer_visible_identities(self):
        g = self.game()
        for viewer, own, other in ((0, "PRIVATE ZERO", "PRIVATE ONE"), (1, "PRIVATE ONE", "PRIVATE ZERO")):
            with self.subTest(viewer=viewer):
                text = json.dumps(asdict(build_player_session_view(g, viewer)))
                self.assertIn(own, text)
                self.assertNotIn(other, text)
                for hidden in ("HIDDEN TABLE", "HIDDEN DRAW ORDER", "HIDDEN HISTORY", "DEEP DISCARD"):
                    self.assertNotIn(hidden, text)
                for public in ("REVEALED ONE", "PUBLIC DISCARD", "PUBLIC PERSONAL"):
                    self.assertIn(public, text)

    def test_permissions_are_reused_and_snapshot_is_independent(self):
        g = self.game(enable_cards_visibility=True, cards_visibility=[
            {"players": [0], "teams": []}, {"players": [0, 1], "teams": []}])
        view = build_player_session_view(g, 0)
        self.assertEqual(view.hands.hands[1].cards[0].card, "PRIVATE ONE")
        before = asdict(view)
        g.players[1].hand.clear()
        g.personal_piles[1][0].clear()
        g.table_cards[0]["position"][0] = 5
        g.cards_visibility[1]["players"] = []
        self.assertEqual(asdict(view), before)
        with self.assertRaises(FrozenInstanceError):
            view.viewer = 1
        with self.assertRaises(FrozenInstanceError):
            view.hands.hands[0].cards[0].card = "changed"

    def test_disabled_areas_and_invalid_viewers(self):
        g = self.game(enable_table=False, enable_discard_pile=False)
        view = build_player_session_view(g, 0)
        self.assertFalse(view.table.enabled)
        self.assertFalse(view.personal_piles.enabled)
        self.assertEqual(view.table.cards, ())
        self.assertEqual(view.personal_piles.piles, ())
        self.assertEqual(view.discard.piles, ())
        for viewer in (True, -1, 2, None, "0"):
            with self.subTest(viewer=viewer), self.assertRaises(ValueError):
                build_player_session_view(g, viewer)
