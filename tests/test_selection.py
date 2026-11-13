import subprocess
import sys
import unittest
from pathlib import Path
from portable_deck.core.game import Game
from portable_deck.core.selection import SelectionState


class SelectionTests(unittest.TestCase):
    def setUp(self):
        self.game = Game(2, str(Path(__file__).resolve().parents[1] / 'decks/demodeck.json'))
        self.game.players[0].hand = ['A', 'B']
        self.state = SelectionState()
        self.state.synchronize(self.game)

    def test_toggle_and_explicit_selection(self):
        self.state.select_hand(0)
        self.state.select_hand(0)
        self.assertIsNone(self.state.hand_index)
        self.state.select_hand(0, toggle=False)
        self.state.select_hand(0, toggle=False)
        self.assertEqual(self.state.hand_index, 0)

    def test_source_and_target_can_coexist_for_move_or_swap(self):
        self.state.select_hand(0)
        self.state.select_table(1)
        self.state.select_target((0, 2), keep_card=True)
        self.assertEqual(self.state.hand_index, 0)
        self.assertEqual(self.state.table_index, 1)
        self.assertEqual(self.state.target_position, (0, 2))
        self.state.select_target((0, 3))
        self.assertIsNone(self.state.table_index)

    def test_mutation_does_not_select_next_card(self):
        self.state.select_hand(0)
        self.game.players[0].hand.pop(0)
        self.state.synchronize(self.game)
        self.assertIsNone(self.state.hand_index)

    def test_table_mutation_clears_stale_card_and_destination(self):
        self.game.play_to_table(1)
        self.state.synchronize(self.game)
        self.state.select_table(0)
        self.state.select_target((0, 1), keep_card=True)
        self.game.table_cards.clear()
        self.state.synchronize(self.game)
        self.assertIsNone(self.state.table_index)
        self.assertIsNone(self.state.target_position)

    def test_turn_change_clears_all_selection(self):
        self.state.select_hand(0)
        self.state.select_target((0, 1))
        self.game.current_player_index = 1
        self.state.synchronize(self.game)
        self.assertEqual((self.state.hand_index, self.state.table_index, self.state.target_position), (None, None, None))

    def test_refresh_preserves_valid_selection(self):
        self.state.select_hand(1)
        self.state.select_target((0, 1))
        self.state.synchronize(self.game)
        self.assertEqual(self.state.hand_index, 1)
        self.assertEqual(self.state.target_position, (0, 1))
        self.state.clear()
        self.assertIsNone(self.state.hand_index)
        self.assertIsNone(self.state.target_position)

    def test_no_gui_dependency(self):
        result = subprocess.run([sys.executable, '-B', '-c',
            "from portable_deck.core.selection import SelectionState; import sys; s=SelectionState(); s.select_hand(0); assert s.hand_index == 0; assert 'tkinter' not in sys.modules"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
