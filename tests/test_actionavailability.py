import subprocess
import sys
import unittest
from pathlib import Path
from portable_deck.core.game import Game
from portable_deck.core.actionavailability import ActionContext, action_availability

class AvailabilityTests(unittest.TestCase):
    def game(self):
        g = Game(2, str(Path(__file__).resolve().parents[1] / "decks/demodeck.json"),
                 enable_chip_accounts=True, minimum_bet=5, starting_balance=3,
                 enable_player_leaving=True, leave_conditions={"own_score": True},
                 score_enabled=True, allow_reduce_score=True, enable_target_score=True,
                 target_score=20, allow_move_cards_on_table=True, allow_positioned_play=True)
        g.players[0].hand = ["A"]
        return g

    def test_cli_selection_chips_score_and_leaving_reasons(self):
        g = self.game()
        self.assertIn("Select a card", action_availability(g, "play_card").reason)
        self.assertIn("Available: 3", action_availability(g, "play_chips").reason)
        self.assertEqual(action_availability(g, "take_pot").reason, "The pot is empty.")
        self.assertIn("20", action_availability(g, "leave_session").reason)
        self.assertTrue(action_availability(g, "play_card", ActionContext(hand_index=0)).allowed)
        g.pending_point_request = {"requester": 0, "confirmed_by": []}
        self.assertIn("confirm", action_availability(g, "reduce_score").reason)

    def test_feature_flags_invalid_selection_and_state_preservation(self):
        g = self.game()
        before = g.capture_undo_state()
        self.assertFalse(action_availability(g, "insert_draw_deck", ActionContext(hand_index=0)).allowed)
        self.assertFalse(action_availability(g, "play_card", ActionContext(hand_index=99)).allowed)
        self.assertEqual(before, g.capture_undo_state())
        with self.assertRaises(ValueError):
            action_availability(g, "not_an_action")
        g.play_to_table(1)
        self.assertIn("target position", action_availability(g, "move_table_card", ActionContext(table_index=0)).reason)
        self.assertTrue(action_availability(g, "move_table_card", ActionContext(table_index=0,target_position=(0,1))).allowed)
        self.assertFalse(action_availability(g, "move_table_card", ActionContext(table_index=0,target_position=(0,0))).allowed)

    def test_import_and_query_without_tkinter(self):
        script = "from portable_deck.core.game import Game; from portable_deck.core.actionavailability import action_availability; import sys; g=Game(2,'decks/demodeck.json'); print(action_availability(g,'draw_card').allowed); assert 'tkinter' not in sys.modules"
        result = subprocess.run([sys.executable, "-B", "-c", script], cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "True")
