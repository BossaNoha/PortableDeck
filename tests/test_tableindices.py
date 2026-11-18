import copy
import unittest
from pathlib import Path
from unittest.mock import Mock

from portable_deck.core.game import Game


class TableIndexTests(unittest.TestCase):
    def game(self, sequences=False):
        game = Game(2, str(Path(__file__).resolve().parents[1] / "decks/demodeck.json"),
                    enable_undo=True, allow_positioned_play=True, occupied_slot_action="swap",
                    allow_move_cards_on_table=True, allow_move_table_sequences=sequences,
                    allow_take_from_table=True, allow_move_table_card_to_discard=True,
                    enable_flipping=True, allow_flip_table=True, allow_face_down_table_cards=True)
        game.players[0].hand = ["HAND"]
        game.players[0].revealed_indices = {0}
        game.table_cards = [
            {"player": "Player1", "card": "A", "position": [0, 0], "face_up": True},
            {"player": "Player1", "card": "B", "position": [1, 0], "face_up": True},
        ]
        game.session.checkpoint_callback = Mock(return_value=None)
        return game

    def test_direct_actions_reject_invalid_indices_without_partial_effects(self):
        for sequences in (False, True):
            game = self.game(sequences)
            actions = (
                game.take_from_table, game.flip_table_card, game.move_table_card_to_discard,
                lambda index: game.swap_with_table(1, index),
                lambda index: game.move_table_card(index, (0, 1)),
            )
            before = game.capture_undo_state()
            for action_index, action in enumerate(actions):
                for index in (True, False, 0.0, 1.0, -1, 2, "0", None, [], {}):
                    with self.subTest(sequences=sequences, action=action_index, index=index):
                        self.assertIsNone(action(index))
                        self.assertEqual(game.capture_undo_state(), before)
                        self.assertEqual(game.undo_stack, [])
                        game.session.checkpoint_callback.assert_not_called()

    def test_controller_rejection_preserves_state_undo_and_checkpoint(self):
        for action in ("take_table_card", "flip_table_card", "discard_table_card", "swap_table_card", "move_table_card"):
            game = self.game()
            before = game.capture_undo_state()
            undo = copy.deepcopy(game.undo_stack)
            for index in (True, False, 0.0, 1.0, -1, 2, "0", [], {}):
                with self.subTest(action=action, index=index):
                    parameters = {"card_index": index, "target_position": (0, 1)}
                    if action == "swap_table_card":
                        parameters.update(card_index=0, table_index=index)
                    result = game.session.execute(action, **parameters)
                    self.assertFalse(result.success)
                    self.assertEqual(result.code, "invalid_selection")
                    self.assertEqual(game.capture_undo_state(), before)
                    self.assertEqual(game.undo_stack, undo)
                    game.session.checkpoint_callback.assert_not_called()

    def test_valid_actions_and_sequence_move_remain_undoable(self):
        for action, sequences in (("take_table_card", False), ("flip_table_card", False),
                                  ("discard_table_card", False), ("swap_table_card", False),
                                  ("move_table_card", False), ("move_table_card", True)):
            with self.subTest(action=action, sequences=sequences):
                game = self.game(sequences)
                before = game.capture_undo_state()
                parameters = {"card_index": 0, "target_position": (0, 1)}
                if action == "swap_table_card":
                    parameters["table_index"] = 0
                result = game.session.execute(action, **parameters)
                self.assertTrue(result.success, result.message)
                if action == "take_table_card":
                    self.assertEqual(game.players[0].hand, ["HAND", "A"])
                elif action == "flip_table_card":
                    self.assertFalse(game.table_cards[0]["face_up"])
                elif action == "discard_table_card":
                    self.assertEqual(game.discard_pile, ["A"])
                elif action == "swap_table_card":
                    self.assertEqual(game.players[0].hand, ["A"])
                    self.assertEqual(game.table_cards[0]["card"], "HAND")
                else:
                    self.assertEqual(game.table_cards[0]["position"], [0, 1])
                    self.assertEqual(game.table_cards[1]["position"], [1, 1] if sequences else [1, 0])
                game.session.checkpoint_callback.assert_called_once_with(game)
                self.assertTrue(game.session.undo())
                self.assertEqual(game.capture_undo_state(), before)
