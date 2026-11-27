import unittest
from unittest.mock import patch
from tests import test_linkedrecycling


class AutoRefillTests(unittest.TestCase):
    def game(self):
        game = test_linkedrecycling.LinkedRecyclingTests().game()
        game.allow_draw_multiple_cards = True
        game.enable_special_actions = True
        game.draw_pile_recycling["mine"]["automatic"] = True
        return game

    def test_mid_draw_refills_only_after_existing_cards_and_undo_restores_everything(self):
        game = self.game()
        game.draw_piles.get("mine").cards = ["FIRST", "SECOND"]
        before = game.capture_undo_state()
        with patch("portable_deck.core.gametable.random.shuffle"):
            result = game.session.execute("draw_cards", count=3, draw_pile_id="mine")
        self.assertTrue(result.success)
        self.assertEqual(game.players[0].hand, ["FIRST", "SECOND", "OWN_A"])
        self.assertEqual(game.draw_piles.get("mine").cards, ["OWN_B"])
        self.assertEqual(len(game.undo_stack), 1)
        game.session.checkpoint_callback.assert_called_once_with(game)
        self.assertTrue(game.session.undo())
        self.assertEqual(game.capture_undo_state(), before)

    def test_insufficient_total_rejects_without_mutation(self):
        game = self.game()
        game.draw_piles.get("mine").cards = ["FIRST"]
        before = game.capture_undo_state()
        self.assertFalse(game.session.execute("draw_cards", count=4, draw_pile_id="mine").success)
        self.assertEqual(game.capture_undo_state(), before)
        game.session.checkpoint_callback.assert_not_called()

    def test_single_draw_refills_but_disabled_option_does_not(self):
        game = self.game()
        self.assertTrue(game.session.execute("draw_card", draw_pile_id="mine").success)
        game = self.game()
        game.draw_pile_recycling["mine"]["automatic"] = False
        self.assertFalse(game.session.execute("draw_card", draw_pile_id="mine").success)
