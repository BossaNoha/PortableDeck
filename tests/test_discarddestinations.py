import copy
import unittest
from pathlib import Path
from unittest.mock import Mock

from portable_deck.core.game import Game


class DiscardDestinationTests(unittest.TestCase):
    def game(self):
        game = Game(2, str(Path(__file__).resolve().parents[1] / "decks/demodeck.json"),
                    enable_undo=True, allow_move_table_card_to_discard=True,
                    shared_discard_pile_count=2, personal_discard_pile_count=2)
        game.players[0].hand = ["HAND"]
        game.players[0].revealed_indices = {0}
        game.table_cards = [{"player": "Player1", "card": "TABLE", "position": [0, 0], "face_up": True}]
        game.session.checkpoint_callback = Mock(return_value=None)
        return game

    def test_invalid_destinations_do_not_remove_source_or_create_undo(self):
        invalid = [(index, personal) for personal in (False, True)
                   for index in (True, False, 0.0, 1.0, -1, 2, "0", None, [], {})]
        invalid += [(0, personal) for personal in (0, 1, "false", None, [], {})]
        for action in ("discard_card", "discard_table_card"):
            game = self.game()
            before = game.capture_undo_state()
            undo = copy.deepcopy(game.undo_stack)
            direct = game.discard_from_current if action == "discard_card" else game.move_table_card_to_discard
            source_index = 1 if action == "discard_card" else 0
            for pile_index, personal in invalid:
                with self.subTest(action=action, pile_index=pile_index, personal=personal):
                    self.assertIsNone(direct(source_index, pile_index, personal))
                    self.assertEqual(game.capture_undo_state(), before)
                    result = game.session.execute(action, card_index=0, pile_index=pile_index, personal=personal)
                    self.assertFalse(result.success)
                    self.assertEqual(result.code, "invalid_pile")
                    self.assertEqual(game.capture_undo_state(), before)
                    self.assertEqual(game.undo_stack, undo)
                    game.session.checkpoint_callback.assert_not_called()

    def test_missing_or_disabled_destination_keeps_source(self):
        for action in ("discard_card", "discard_table_card"):
            for disabled in (False, True):
                with self.subTest(action=action, disabled=disabled):
                    game = self.game()
                    if disabled:
                        game.enable_discard_pile = False
                    else:
                        game.personal_discard_piles[0].clear()
                    before = game.capture_undo_state()
                    direct = game.discard_from_current if action == "discard_card" else game.move_table_card_to_discard
                    self.assertIsNone(direct(1 if action == "discard_card" else 0, 0, True))
                    self.assertEqual(game.capture_undo_state(), before)

    def test_valid_shared_and_personal_destinations_receive_card_and_undo(self):
        for action in ("discard_card", "discard_table_card"):
            for personal in (False, True):
                for index in (0, 1):
                    with self.subTest(action=action, personal=personal, index=index):
                        game = self.game()
                        before = game.capture_undo_state()
                        result = game.session.execute(action, card_index=0, pile_index=index, personal=personal)
                        self.assertTrue(result.success, result.message)
                        expected = copy.deepcopy(before)
                        piles = game.personal_discard_piles[0] if personal else game.discard_piles
                        self.assertEqual(piles[index], ["HAND" if action == "discard_card" else "TABLE"])
                        self.assertEqual(sum(len(pile) for _, pile in game.all_discard_piles()), 1)
                        if action == "discard_card":
                            self.assertEqual(game.players[0].hand, [])
                            self.assertEqual(game.players[0].revealed_indices, set())
                        else:
                            self.assertEqual(game.table_cards, [])
                        game.session.checkpoint_callback.assert_called_once_with(game)
                        self.assertTrue(game.session.undo())
                        self.assertEqual(game.capture_undo_state(), expected)
