import unittest
from pathlib import Path
from unittest.mock import Mock

from portable_deck.core.game import Game
from portable_deck.core.actionavailability import ActionContext, action_availability
from portable_deck.ui.actionavailability import action_reason


class TableSwapTests(unittest.TestCase):
    def game(self):
        game = Game(2, str(Path(__file__).resolve().parents[1] / "decks/demodeck.json"),
                    allow_positioned_play=True, occupied_slot_action="swap", enable_undo=True)
        game.players[0].hand = ["A of Test", "K of Test"]
        game.table_cards = [{"card": "2 of Test", "player": "Player2",
                             "position": (0, 0), "face_up": True}]
        return game

    def test_swap_preserves_slot_and_has_one_undo_and_checkpoint(self):
        game = self.game()
        before = game.capture_undo_state()
        saved = Mock(return_value=None)
        game.session.checkpoint_callback = saved
        result = game.session.run(lambda: game.session.execute(
            "swap_table_card", card_index=1, table_index=0))
        self.assertTrue(result.success, result.message)
        self.assertTrue(result.changed)
        self.assertEqual(result.value, ("K of Test", "2 of Test"))
        self.assertEqual(game.players[0].hand, ["A of Test", "2 of Test"])
        self.assertEqual(game.table_cards, [{"card": "K of Test", "player": game.players[0].name,
                                            "position": (0, 0), "face_up": True}])
        self.assertEqual(result.events[0]["action"], "swap_table_card")
        self.assertEqual(len(game.undo_stack), 1)
        saved.assert_called_once_with(game)
        self.assertTrue(game.session.undo())
        self.assertEqual(game.capture_undo_state(), before)
        self.assertEqual(saved.call_count, 2)

    def test_rejected_swaps_leave_state_and_checkpoint_unchanged(self):
        for case in ("disabled_table", "disabled_positioning", "disabled_swap", "confirmation",
                     "departed", "missing_hand", "missing_table", "bad_hand", "bad_table", "bool_table"):
            with self.subTest(case=case):
                game = self.game()
                parameters = dict(card_index=0, table_index=0)
                if case == "disabled_table":
                    game.enable_table = False
                elif case == "disabled_positioning":
                    game.allow_positioned_play = False
                elif case == "disabled_swap":
                    game.occupied_slot_action = "invalid"
                elif case == "confirmation":
                    game.current_player_must_confirm_point = lambda: True
                elif case == "departed":
                    game.left_players = [0]
                elif case == "missing_hand":
                    parameters.pop("card_index")
                elif case == "missing_table":
                    parameters.pop("table_index")
                elif case == "bad_hand":
                    parameters["card_index"] = -1
                elif case == "bad_table":
                    parameters["table_index"] = 99
                else:
                    parameters["table_index"] = False
                before = game.capture_undo_state()
                saved = Mock(return_value=None)
                game.session.checkpoint_callback = saved
                result = game.session.execute("swap_table_card", **parameters)
                self.assertFalse(result.success)
                self.assertTrue(result.message)
                self.assertEqual(game.capture_undo_state(), before)
                self.assertEqual(game.undo_stack, [])
                saved.assert_not_called()

    def test_gui_button_uses_swap_availability_for_occupied_selection(self):
        game = self.game()
        gui = Mock(game=game)
        gui.selection = Mock(hand_index=0, table_index=0, target_position=None)
        gui.chip_bank_ui = None
        gui.special_actions_ui = None
        self.assertEqual(action_reason(gui, gui.play_at_spot_button), "")
        game.occupied_slot_action = "invalid"
        self.assertTrue(action_reason(gui, gui.play_at_spot_button))
        self.assertFalse(action_availability(game, "swap_table_card",
                         ActionContext(hand_index=0, table_index=0)).allowed)
