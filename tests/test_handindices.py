import copy
import unittest
from pathlib import Path
from unittest.mock import Mock

from portable_deck.core.game import Game
from portable_deck.core.player import Player


INVALID_INDICES = (True, False, 1.0, 2.0, 0, -1, 3, "1", None, [], {})


class HandIndexTests(unittest.TestCase):
    def test_player_rejects_invalid_indices_without_changing_revealed_cards(self):
        player = Player("Alice")
        player.hand = ["A", "B"]
        player.revealed_indices = {0, 1}
        for index in INVALID_INDICES:
            with self.subTest(index=index):
                self.assertIsNone(player.play_card(index))
                self.assertEqual(player.hand, ["A", "B"])
                self.assertEqual(player.revealed_indices, {0, 1})
        self.assertEqual(player.play_card(1), "A")
        self.assertEqual(player.hand, ["B"])
        self.assertEqual(player.revealed_indices, {0})

    def game(self, positioned):
        game = Game(2, str(Path(__file__).resolve().parents[1] / "decks/demodeck.json"),
                    enable_undo=True, allow_positioned_play=positioned,
                    enable_flipping=True, allow_flip_table=True,
                    allow_face_down_table_cards=positioned)
        game.players[0].hand = ["A", "B"]
        game.players[0].revealed_indices = {0, 1}
        game.session.checkpoint_callback = Mock(return_value=None)
        return game

    def test_direct_table_play_rejects_invalid_indices_before_mutation(self):
        for positioned, face_up in ((False, True), (True, True), (True, False)):
            game = self.game(positioned)
            before = game.capture_undo_state()
            for index in INVALID_INDICES:
                with self.subTest(positioned=positioned, face_up=face_up, index=index):
                    self.assertIsNone(game.play_to_table(index, (0, 0), face_up=face_up))
                    self.assertEqual(game.capture_undo_state(), before)
                    self.assertEqual(game.undo_stack, [])
                    game.session.checkpoint_callback.assert_not_called()

    def test_controller_play_validation_and_valid_undo_remain_unchanged(self):
        for action, positioned in (("play_card", False), ("play_at_position", True), ("play_face_down", True)):
            game = self.game(positioned)
            before = game.capture_undo_state()
            undo = copy.deepcopy(game.undo_stack)
            for index in (True, False, 0.0, 1.0, -1, 2, "0", [], {}):
                with self.subTest(action=action, index=index):
                    result = game.session.execute(action, card_index=index, target_position=(0, 0))
                    self.assertFalse(result.success)
                    self.assertEqual(result.code, "invalid_selection")
                    self.assertEqual(game.capture_undo_state(), before)
                    self.assertEqual(game.undo_stack, undo)
                    game.session.checkpoint_callback.assert_not_called()
            result = game.session.execute(action, card_index=0, target_position=(0, 0))
            self.assertTrue(result.success, result.message)
            self.assertEqual(game.players[0].hand, ["B"])
            self.assertEqual(game.players[0].revealed_indices, {0})
            self.assertEqual(game.table_cards[0]["card"], "A")
            self.assertEqual(game.table_cards[0]["face_up"], action != "play_face_down")
            game.session.checkpoint_callback.assert_called_once_with(game)
            self.assertTrue(game.session.undo())
            self.assertEqual(game.capture_undo_state(), before)
