import unittest
import tempfile
from unittest.mock import Mock, patch
from pathlib import Path
from portable_deck.core.game import Game
from portable_deck.app.sessionstorage import save_session, load_session

class SpecialActionTests(unittest.TestCase):
    def test_invalid_direct_inputs_preserve_reveals_and_do_not_choose_random_position(self):
        for destination in ("draw", "discard"):
            game = self.game()
            game.players[0].hand = ["A of Test", "B of Test"]
            game.players[0].revealed_indices = {0, 1}
            game.deck.flat_deck[:] = [str(i) for i in range(30)]
            game.discard_piles[0][:] = [str(i) for i in range(30)]
            before = game.capture_undo_state()
            cases = [(value, destination, "X", 0) for value in
                     (True, False, 1.0, 2.0, 0, -1, 3, "1", None, [], {})]
            cases += [(1, destination, value, 0) for value in
                      (True, False, 1.0, -1.0, None, [], {}, "", "1.0", 0, 11, -11)]
            cases += [(1, value, "X", 0) for value in (None, True, [], {}, "unknown")]
            if destination == "discard":
                cases += [(1, destination, "X", value) for value in
                          (True, False, 0.0, 1.0, -1, 2, "0", None, [], {})]
            with patch("portable_deck.core.specialactions.random.randrange") as random_position:
                for hand, target, position, pile in cases:
                    with self.subTest(hand=hand, target=target, position=position, pile=pile):
                        with self.assertRaises(ValueError):
                            game.insert_hand_card(hand, target, position, pile)
                        self.assertEqual(game.capture_undo_state(), before)
                        self.assertEqual(game.undo_stack, [])
                        random_position.assert_not_called()

    def test_malformed_controller_inputs_preserve_state_undo_and_checkpoint(self):
        for action in ("insert_draw_deck", "insert_discard_pile"):
            game = self.game()
            game.players[0].hand = ["A of Test"]
            game.players[0].revealed_indices = {0}
            game.deck.flat_deck[:] = [str(i) for i in range(30)]
            game.discard_piles[0][:] = [str(i) for i in range(30)]
            game.session.checkpoint_callback = saved = Mock(return_value=None)
            before = game.capture_undo_state()
            cases = [({"card_index": value, "position": "X"}, "invalid_selection")
                     for value in (True, False, 0.0, -1, 1, "0", [], {})]
            cases += [({"card_index": 0, "position": value}, "invalid_parameters")
                      for value in (True, False, 1.0, None, [], {}, 0, 11)]
            cases.append(({"card_index": 0}, "invalid_parameters"))
            if action == "insert_discard_pile":
                cases += [({"card_index": 0, "position": "X", "pile_index": value}, "invalid_parameters")
                          for value in (True, False, 0.0, -1, 2, "0", None, [], {})]
            with patch("portable_deck.core.specialactions.random.randrange") as random_position:
                for parameters, code in cases:
                    with self.subTest(action=action, parameters=parameters):
                        result = game.session.execute(action, **parameters)
                        self.assertFalse(result.success)
                        self.assertFalse(result.changed)
                        self.assertEqual(result.code, code)
                        self.assertEqual(result.events, ())
                        self.assertEqual(game.capture_undo_state(), before)
                        self.assertEqual(game.undo_stack, [])
                        saved.assert_not_called()
                        random_position.assert_not_called()

    def test_session_placement_has_one_undo_step_and_checkpoint(self):
        for destination in ("draw", "discard"):
            with self.subTest(destination=destination):
                game = self.game()
                game.players[0].hand = ["A of Test"]
                saved = Mock(return_value=None)
                game.session.checkpoint_callback = saved
                before = game.capture_undo_state()
                # Match the GUI's outer transaction and zero-based selection.
                result = game.session.run(lambda: game.session.execute(
                    f"insert_{destination}_" + ("deck" if destination == "draw" else "pile"),
                    card_index=0, position="1", pile_index=1))
                self.assertTrue(result.success)
                self.assertTrue(result.changed)
                self.assertEqual(result.value, "A of Test")
                pile = game.deck.flat_deck if destination == "draw" else game.discard_piles[1]
                self.assertEqual(pile[0 if destination == "draw" else -1], "A of Test")
                self.assertEqual(game.players[0].hand, [])
                self.assertEqual(len(game.undo_stack), 1)
                saved.assert_called_once_with(game)
                self.assertTrue(game.session.undo())
                self.assertEqual(game.capture_undo_state(), before)
                self.assertEqual(saved.call_count, 2)

    def test_rejected_session_placement_preserves_state_and_does_not_save(self):
        for action, parameters in (
            ("insert_draw_deck", {"position": "0"}),
            ("insert_draw_deck", {"position": "X"}),
            ("insert_draw_deck", {"position": "1", "card_index": 99}),
            ("insert_discard_pile", {"position": "1", "pile_index": 99}),
        ):
            with self.subTest(action=action, parameters=parameters):
                game = self.game()
                game.players[0].hand = ["A of Test"]
                game.deck.flat_deck[:] = ["B of Test"]
                saved = Mock(return_value=None)
                game.session.checkpoint_callback = saved
                before = game.capture_undo_state()
                result = game.session.run(lambda: game.session.execute(
                    action, **{"card_index": 0, **parameters}))
                self.assertFalse(result.success)
                self.assertFalse(result.changed)
                self.assertTrue(result.message)
                self.assertEqual(game.capture_undo_state(), before)
                self.assertEqual(game.undo_stack, [])
                saved.assert_not_called()

    def game(self):
        return Game(2, str(Path(__file__).resolve().parents[1] / "decks/demodeck.json"),
                    enable_special_actions=True, allow_insert_draw_deck=True,
                    allow_insert_discard_pile=True, shared_discard_pile_count=2, enable_undo=True)

    def test_positions_are_top_based_and_undoable(self):
        for destination in ("draw", "discard"):
            for position in (1, 2, 3):
                with self.subTest(destination=destination, position=position):
                    game = self.game()
                    game.players[0].hand = ["A of Test"]
                    pile = game.deck.flat_deck if destination == "draw" else game.discard_piles[1]
                    pile[:] = ["2 of Test", "3 of Test"]
                    original = game.capture_undo_state()
                    game.undo_stack.append(original)
                    game.insert_hand_card(1, destination, position, 1)
                    self.assertEqual((pile if destination == "draw" else list(reversed(pile)))[position - 1], "A of Test")
                    self.assertEqual(game.players[0].hand, [])
                    self.assertTrue(game.undo_last_action())
                    self.assertEqual(game.capture_undo_state(), original)

    def test_signed_positions_and_random_input(self):
        from unittest.mock import patch
        for destination in ("draw", "discard"):
            for position, expected in ((1, 0), (10, 9), (-1, 20), (-10, 11)):
                game = self.game()
                game.players[0].hand = ["A of Test"]
                pile = game.deck.flat_deck if destination == "draw" else game.discard_piles[0]
                pile[:] = [str(i) for i in range(20)]
                game.insert_hand_card(1, destination, str(position))
                self.assertEqual((pile if destination == "draw" else list(reversed(pile))).index("A of Test"), expected)
        for value in ("x", "X", " x "):
            game = self.game()
            game.players[0].hand = ["A of Test"]
            game.deck.flat_deck[:] = [str(i) for i in range(30)]
            with patch("portable_deck.core.specialactions.random.randrange", return_value=15):
                game.insert_hand_card(1, "draw", value)
            self.assertEqual(game.deck.flat_deck[15], "A of Test")
        for value in (0, 11, -11, "11", "-11", "1.5", True):
            game = self.game()
            game.players[0].hand = ["A of Test"]
            before = game.capture_undo_state()
            with self.assertRaises(ValueError):
                game.insert_hand_card(1, "draw", value)
            self.assertEqual(game.capture_undo_state(), before)

    def test_x_excludes_both_end_ranges(self):
        for destination in ("draw", "discard"):
            for size in (0, 19, 20, 21, 50):
                game = self.game()
                game.players[0].hand = ["A of Test"]
                pile = game.deck.flat_deck if destination == "draw" else game.discard_piles[0]
                pile[:] = [str(i) for i in range(size)]
                original = game.capture_undo_state()
                if size < 20:
                    with self.assertRaises(ValueError):
                        game.insert_hand_card(1, destination, "x")
                    self.assertEqual(game.capture_undo_state(), original)
                else:
                    game.insert_hand_card(1, destination, "x")
                    top_index = (pile if destination == "draw" else list(reversed(pile))).index("A of Test")
                    self.assertGreaterEqual(top_index, 10)
                    self.assertLessEqual(top_index, size - 10)

    def test_permissions_and_persistence(self):
        game = self.game()
        game.players[0].hand = ["A of Test"]
        state = game.capture_undo_state()
        with self.assertRaises(ValueError):
            game.insert_hand_card(1, "discard", 0)
        self.assertEqual(game.capture_undo_state(), state)
        game.enable_discard_pile = False
        with self.assertRaises(ValueError):
            game.insert_hand_card(1, "discard", 1)
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as folder:
            path = str(Path(folder) / "save.json")
            save_session(game, path)
            loaded = load_session(Game, path)
            self.assertTrue(loaded.allow_insert_draw_deck)
            self.assertTrue(loaded.restart().enable_special_actions)
