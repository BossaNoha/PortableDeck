import unittest
import tempfile
from pathlib import Path
from portable_deck.core.game import Game

class SpecialActionTests(unittest.TestCase):
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
            game.save_session(path)
            loaded = Game.load_session(path)
            self.assertTrue(loaded.allow_insert_draw_deck)
            self.assertTrue(loaded.restart().enable_special_actions)
