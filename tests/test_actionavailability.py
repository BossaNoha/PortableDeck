import unittest
from pathlib import Path
from types import SimpleNamespace
from portable_deck.core.game import Game
from portable_deck.ui.actionavailability import action_reason

class AvailabilityTests(unittest.TestCase):
    def test_selection_chips_score_and_leaving_reasons(self):
        g = Game(2, str(Path(__file__).resolve().parents[1] / "decks/demodeck.json"),
                 enable_chip_accounts=True, minimum_bet=5, starting_balance=3,
                 enable_player_leaving=True, leave_conditions={"own_score": True},
                 score_enabled=True, enable_target_score=True, target_score=20)
        gui = SimpleNamespace(game=g, play_button=object(), leave_session_button=object(),
                              reduce_score_button=object(), hand_frame=SimpleNamespace(selected_index=None),
                              table_frame=SimpleNamespace(selected_index=None, selected_position=None),
                              chip_bank_ui=SimpleNamespace(play_button=object(), take_button=object()))
        self.assertIn("Select a card", action_reason(gui, gui.play_button))
        self.assertIn("Available: 3", action_reason(gui, gui.chip_bank_ui.play_button))
        self.assertEqual(action_reason(gui, gui.chip_bank_ui.take_button), "The pot is empty.")
        self.assertIn("20", action_reason(gui, gui.leave_session_button))
        gui.hand_frame.selected_index = 0
        self.assertEqual(action_reason(gui, gui.play_button), "")
        g.pending_point_request = {"requester": 0, "confirmed_by": []}
        self.assertIn("confirm", action_reason(gui, gui.reduce_score_button))
