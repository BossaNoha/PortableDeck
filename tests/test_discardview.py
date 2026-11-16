import json
import unittest
from dataclasses import FrozenInstanceError, asdict
from pathlib import Path
from unittest.mock import Mock

from portable_deck.core.game import Game
from portable_deck.core.playerview import build_player_discard_view
from portable_deck.ui.cardactions import draw_from_discard


class DiscardViewTests(unittest.TestCase):
    def game(self, mode="top"):
        g = Game(2, str(Path(__file__).resolve().parents[1] / "decks/demodeck.json"),
                 shared_discard_pile_count=2, personal_discard_pile_count=1,
                 allow_draw_from_discard=True, draw_from_discard_mode=mode, enable_undo=True)
        g.discard_piles[1] = ["DEEP", "TOP"]
        g.personal_discard_piles[1][0] = ["PERSONAL"]
        g.deck.flat_deck = ["DRAW SECRET"]
        return g

    def test_top_mode_redacts_deeper_cards_without_mutation(self):
        g = self.game()
        before = g.capture_undo_state()
        view = build_player_discard_view(g, 0)
        self.assertEqual([p.source_index for p in view.piles], [0, 1, 2, 3])
        self.assertEqual(view.piles[0].cards, ())
        self.assertEqual(view.piles[1].card_count, 2)
        self.assertEqual([(c.index, c.card) for c in view.piles[1].cards], [(1, "TOP")])
        text = json.dumps(asdict(view))
        self.assertNotIn("DEEP", text)
        self.assertNotIn("DRAW SECRET", text)
        self.assertEqual(g.capture_undo_state(), before)

    def test_any_mode_preserves_source_indices_for_session_draw_and_undo(self):
        for source, card_index, expected in ((1, 0, "DEEP"), (3, 0, "PERSONAL")):
            with self.subTest(source=source):
                g = self.game("any")
                before = g.capture_undo_state()
                view = build_player_discard_view(g, 0)
                self.assertEqual([c.card for c in view.piles[1].cards], ["TOP", "DEEP"])
                card = next(c for c in view.piles[source].cards if c.index == card_index)
                result = g.session.execute("draw_from_discard", source_index=source, card_index=card.index)
                self.assertTrue(result.success)
                self.assertEqual(result.value, expected)
                self.assertTrue(g.session.undo())
                self.assertEqual(g.capture_undo_state(), before)

    def test_view_is_immutable_disabled_and_validated(self):
        g = self.game("any")
        view = build_player_discard_view(g, 1)
        before = asdict(view)
        g.discard_piles[1].clear()
        self.assertEqual(asdict(view), before)
        with self.assertRaises(FrozenInstanceError):
            view.piles[1].cards[0].card = "changed"
        g.enable_discard_pile = False
        self.assertEqual(build_player_discard_view(g, 0).piles, ())
        for viewer in (True, -1, 2, None):
            with self.assertRaises(ValueError):
                build_player_discard_view(g, viewer)

    def test_single_nonempty_pile_gui_draw_uses_unfiltered_source_index(self):
        g = self.game()
        g.discard_piles[1].clear()
        hand, log, status = Mock(), Mock(), Mock()
        draw_from_discard(g, hand, log, status, None)
        self.assertEqual(g.players[0].hand, ["PERSONAL"])
        self.assertEqual(g.personal_discard_piles[1][0], [])
        hand.update_hand.assert_called_once()
