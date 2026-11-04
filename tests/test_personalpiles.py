import json
from pathlib import Path
import tempfile
import unittest

from portable_deck.core.game import Game


class PersonalPileTests(unittest.TestCase):
    def game(self, rules=None):
        return Game(2, str(Path(__file__).resolve().parents[1] / "decks/demodeck.json"),
                    enable_personal_piles=True, personal_pile_count=2,
                    personal_pile_settings=rules, enable_undo=True)

    def test_access_applies_to_both_play_and_take(self):
        for access, allowed in (("everyone", True), ("team", False), ("owner", False)):
            with self.subTest(access=access):
                game = self.game([[{"access": access}]])
                game.personal_piles[0][0] = ["2 of Test"]
                game.current_player_index = 1
                game.players[1].hand = ["3 of Test"]
                self.assertEqual(game.can_access_personal_pile(0, 0), allowed)
                self.assertEqual(game.play_to_personal_pile(1, 0, 0) is not None, allowed)
                self.assertEqual(game.take_from_personal_pile(0, 0) is not None, allowed)
                if not allowed:
                    self.assertEqual(game.players[1].hand, ["3 of Test"])
                    self.assertEqual(game.personal_piles[0][0], ["2 of Test"])

    def test_ordering(self):
        for mode, position, expected in (
            ("time", "top", ["K of Test", "2 of Test", "A of Test"]),
            ("time", "bottom", ["A of Test", "2 of Test", "K of Test"]),
            ("size", "top", ["2 of Test", "K of Test", "A of Test"]),
        ):
            with self.subTest(mode=mode, position=position):
                game = self.game([[{"ordered": True, "order_by": mode, "new_card": position}]])
                game.players[0].hand = ["K of Test", "2 of Test", "A of Test"]
                for _ in range(3):
                    game.play_to_personal_pile(1, 0, 0)
                self.assertEqual(game.personal_piles[0][0], expected)

    def test_size_order_direction_and_persistence(self):
        for direction, expected in (("up", ["2 of Test", "K of Test", "A of Test"]),
                                    ("down", ["A of Test", "K of Test", "2 of Test"])):
            with self.subTest(direction=direction):
                game = self.game([[{"ordered": True, "order_by": "size", "size_order": direction}]])
                game.players[0].hand = ["K of Test", "A of Test", "2 of Test"]
                for _ in range(3):
                    game.play_to_personal_pile(1, 0, 0)
                self.assertEqual(game.personal_piles[0][0], expected)
                with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as directory:
                    path = str(Path(directory) / "save.json")
                    game.save_session(path)
                    loaded = Game.load_session(path)
                    self.assertEqual(loaded.personal_pile_settings[0][0]["size_order"], direction)
                    self.assertEqual(loaded.take_from_personal_pile(0, 0), expected[-1])

    def test_undo_save_and_restart(self):
        game = self.game()
        game.players[0].hand = ["2 of Test"]
        original = game.capture_undo_state()
        game.undo_stack.append(original)
        game.play_to_personal_pile(1, 0, 0)
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as directory:
            path = str(Path(directory) / "save.json")
            game.save_session(path)
            loaded = Game.load_session(path)
            self.assertEqual(loaded.personal_piles, game.personal_piles)
            self.assertTrue(loaded.undo_last_action())
            self.assertEqual(loaded.capture_undo_state(), original)
            restarted = loaded.restart()
            self.assertEqual(restarted.personal_pile_settings, game.personal_pile_settings)
            self.assertEqual(restarted.personal_piles, [[[], []], [[], []]])

    def test_legacy_personal_discard_migration_and_undo(self):
        game = self.game()
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as directory:
            path = str(Path(directory) / "legacy.json")
            game.save_session(path)
            data = json.loads(Path(path).read_text())
            for key in ("enable_personal_piles", "personal_pile_count", "personal_pile_settings", "personal_piles"):
                data.pop(key)
            data["personal_discard_pile_count"] = 1
            data["personal_discard_piles"] = [[["2 of Test"]], [[]]]
            snapshot = game.capture_undo_state()
            snapshot.pop("personal_piles")
            snapshot["personal_discard_piles"] = [[["3 of Test"]], [[]]]
            data["undo_stack"] = [snapshot]
            Path(path).write_text(json.dumps(data))
            loaded = Game.load_session(path)
            self.assertEqual(loaded.personal_piles, [[["2 of Test"]], [[]]])
            self.assertEqual(loaded.personal_discard_pile_count, 0)
            self.assertTrue(loaded.undo_last_action())
            self.assertEqual(loaded.personal_piles, [[["3 of Test"]], [[]]])
            self.assertEqual(loaded.personal_discard_piles, [[], []])

    def test_unequal_counts_roundtrip_and_restart(self):
        game = Game(2, str(Path(__file__).resolve().parents[1] / "decks/demodeck.json"),
                    enable_personal_piles=True, unequal_personal_piles=True,
                    personal_pile_counts=[0, 3])
        self.assertEqual([len(group) for group in game.personal_piles], [0, 3])
        self.assertFalse(game.can_access_personal_pile(0, 0))
        game.current_player_index = 1
        game.players[1].hand = ["2 of Test"]
        self.assertEqual(game.play_to_personal_pile(1, 1, 2), "2 of Test")
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as directory:
            path = str(Path(directory) / "save.json")
            game.save_session(path)
            loaded = Game.load_session(path)
            self.assertEqual(loaded.personal_pile_counts, [0, 3])
            self.assertEqual(loaded.personal_piles, game.personal_piles)
            self.assertEqual(loaded.restart().personal_pile_counts, [0, 3])

    def test_invalid_unequal_counts_are_rejected(self):
        for counts in ([1], [1, -1], [1, 21], [True, 2]):
            with self.subTest(counts=counts), self.assertRaises(ValueError):
                self.game().initialize_personal_piles(True, 1, unequal=True, counts=counts)

    def test_disabled_table_blocks_personal_actions(self):
        game = self.game()
        game.enable_table = False
        game.players[0].hand = ["2 of Test"]
        self.assertIsNone(game.play_to_personal_pile(1, 0, 0))
        self.assertEqual(game.players[0].hand, ["2 of Test"])


if __name__ == "__main__":
    unittest.main()
