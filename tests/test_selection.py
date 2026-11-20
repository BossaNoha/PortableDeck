import unittest
import json
import tempfile
from dataclasses import asdict
from pathlib import Path
from portable_deck.core.game import Game
from portable_deck.app.sessionstorage import save_session, load_session
from portable_deck.core.selection import SelectionState
from portable_deck.core.selectionsnapshot import SelectionSnapshot, build_selection_snapshot
from portable_deck.core.playerview import build_player_hands_view, build_player_table_view


class SelectionTests(unittest.TestCase):
    def test_snapshot_alone_synchronizes_without_secret_values(self):
        self.game.players[0].hand = ["PRIVATE HAND"]
        snapshot = build_selection_snapshot(self.game)
        # A client can receive the DTO as JSON without access to Game.
        snapshot = SelectionSnapshot(**json.loads(json.dumps(asdict(snapshot))))
        state = SelectionState()
        state.synchronize(snapshot)
        state.select_hand(0)
        state.synchronize(snapshot)
        self.assertEqual(state.hand_index, 0)
        self.assertNotIn("PRIVATE HAND", json.dumps(asdict(snapshot)))
        self.assertNotIn("PRIVATE HAND", repr(vars(state)))

    def test_hidden_hand_replacement_invalidates_identical_redacted_view(self):
        self.game.enable_cards_visibility = True
        self.game.cards_visibility[0] = {"players": [], "teams": []}
        before = build_player_hands_view(self.game, 0)
        self.state.synchronize(build_selection_snapshot(self.game))
        self.state.select_hand(0)
        self.game.players[0].hand[0] = "ANOTHER SECRET"
        self.assertEqual(build_player_hands_view(self.game, 0), before)
        self.state.synchronize(build_selection_snapshot(self.game))
        self.assertIsNone(self.state.hand_index)

    def test_face_down_replacement_and_in_place_position_change_invalidate(self):
        self.game.table_cards = [{"card": "SECRET", "player": "Player1", "position": [0, 0], "face_up": False}]
        before = build_player_table_view(self.game, 0)
        self.state.synchronize(build_selection_snapshot(self.game))
        self.state.select_table(0)
        self.state.select_target((0, 1), keep_card=True)
        self.game.table_cards[0]["card"] = "OTHER SECRET"
        self.assertEqual(build_player_table_view(self.game, 0), before)
        self.state.synchronize(build_selection_snapshot(self.game))
        self.assertIsNone(self.state.table_index)
        self.assertIsNone(self.state.target_position)
        self.state.select_table(0)
        self.game.table_cards[0]["position"][0] = 2
        self.state.synchronize(build_selection_snapshot(self.game))
        self.assertIsNone(self.state.table_index)

    def test_markers_are_stable_scoped_and_not_part_of_saves(self):
        before = self.game.capture_undo_state()
        first = build_selection_snapshot(self.game)
        self.assertEqual(build_selection_snapshot(self.game), first)
        self.assertEqual(self.game.capture_undo_state(), before)
        self.state.select_hand(0)
        other = Game(2, str(Path(__file__).resolve().parents[1] / 'decks/demodeck.json'))
        other.players[0].hand = ['A', 'B']
        self.state.synchronize(build_selection_snapshot(other))
        self.assertIsNone(self.state.hand_index)
        with tempfile.TemporaryDirectory() as folder:
            path = str(Path(folder) / 'session.json')
            save_session(self.game, path)
            data = Path(path).read_text(encoding='utf-8')
            self.assertNotIn(first.session, data)
            self.assertNotIn(first.hand_revision, data)
            loaded = load_session(Game, path)
            self.assertNotEqual(build_selection_snapshot(loaded).session, first.session)

    def test_undo_invalidates_only_changed_collections(self):
        self.game.enable_undo = True
        self.game.table_cards = [{"card": "B", "player": "Player1", "position": [0, 0]}]
        self.state.synchronize(build_selection_snapshot(self.game))
        self.state.select_table(0)
        self.state.select_target((0, 1), keep_card=True)
        self.game.session.execute('draw_card')
        self.state.synchronize(build_selection_snapshot(self.game))
        self.assertEqual(self.state.table_index, 0)
        self.state.select_hand(0)
        self.assertTrue(self.game.session.undo())
        self.state.synchronize(build_selection_snapshot(self.game))
        self.assertIsNone(self.state.hand_index)
        self.assertEqual(self.state.table_index, 0)
        self.assertEqual(self.state.target_position, (0, 1))

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
