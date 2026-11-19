import json
import unittest
from dataclasses import FrozenInstanceError, asdict
from pathlib import Path
from unittest.mock import Mock

from portable_deck.core.game import Game
from portable_deck.core.playerview import build_player_discard_view
from portable_deck.ui.cardactions import draw_from_discard


class DiscardViewTests(unittest.TestCase):
    def test_invalid_draw_indices_preserve_all_sources_undo_and_checkpoint(self):
        for mode in ("top", "any"):
            g = self.game(mode)
            g.players[0].hand = ["HAND"]
            g.players[0].revealed_indices = {0}
            g.session.checkpoint_callback = saved = Mock(return_value=None)
            before = g.capture_undo_state()
            cases = []
            for key, limit in (("source_index", 4), ("pile_index", 2)):
                cases += [{key: value} for value in (True, False, 0.0, -1, limit, "1", None, [], {})]
                cases += [{key: 1, "card_index": value} for value in
                          (True, False, 0.0, -1, 2, "0", None, [], {})]
                cases.append({key: 0})  # Empty shared source.
                if mode == "top":
                    cases.append({key: 1, "card_index": 0})
            for parameters in cases:
                with self.subTest(mode=mode, parameters=parameters):
                    with self.assertRaises(ValueError):
                        g.session.draw_from_discard(parameters)
                    self.assertEqual(g.capture_undo_state(), before)
                    result = g.session.execute("draw_from_discard", **parameters)
                    self.assertFalse(result.success)
                    self.assertEqual(result.code, "invalid_parameters")
                    self.assertEqual(result.events, ())
                    self.assertEqual(g.capture_undo_state(), before)
                    self.assertEqual(g.undo_stack, [])
                    saved.assert_not_called()

    def test_top_draw_from_shared_or_personal_source_remains_undoable(self):
        for parameters, expected in (({"pile_index": 1}, "TOP"),
                                     ({"source_index": 1}, "TOP"),
                                     ({"source_index": 3}, "PERSONAL")):
            with self.subTest(parameters=parameters):
                g = self.game()
                g.session.checkpoint_callback = saved = Mock(return_value=None)
                before = g.capture_undo_state()
                result = g.session.execute("draw_from_discard", **parameters)
                self.assertTrue(result.success)
                self.assertEqual(result.value, expected)
                self.assertEqual(g.players[0].hand, [expected])
                saved.assert_called_once_with(g)
                self.assertTrue(g.session.undo())
                self.assertEqual(g.capture_undo_state(), before)

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
        result = draw_from_discard(g, hand, log, status, None)
        self.assertTrue(result.success)
        self.assertEqual(result.value, "PERSONAL")
        self.assertEqual(g.players[0].hand, ["PERSONAL"])
        self.assertEqual(g.personal_discard_piles[1][0], [])
        hand.update_hand.assert_not_called()
        status.update_status.assert_not_called()
