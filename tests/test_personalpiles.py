import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

from portable_deck.core.game import Game


class PersonalPileTests(unittest.TestCase):
    def test_direct_actions_reject_malformed_targets_before_moving_cards(self):
        game = self.game()
        game.players[0].hand = ["3 of Test"]
        game.players[0].revealed_indices = {0}
        game.personal_piles[0][0] = ["2 of Test"]
        game.personal_piles[1][0] = ["4 of Test"]
        before = game.capture_undo_state()
        cases = [(value, 0) for value in (True, False, 0.0, 1.0, -1, 2, "0", None, [], {})]
        cases += [(0, value) for value in (True, False, 0.0, 1.0, -1, 2, "0", None, [], {})]
        for owner, pile in cases:
            with self.subTest(owner=owner, pile=pile):
                self.assertFalse(game.can_access_personal_pile(owner, pile))
                self.assertIsNone(game.play_to_personal_pile(1, owner, pile))
                self.assertIsNone(game.take_from_personal_pile(owner, pile))
                self.assertEqual(game.capture_undo_state(), before)

    def test_access_query_rejects_invalid_viewer_even_for_public_piles(self):
        game = self.game([[{"access": "everyone"}]])
        before = game.capture_undo_state()
        for viewer in (True, False, 0.0, 1.0, -1, 2, "0", [], {}):
            with self.subTest(viewer=viewer):
                self.assertFalse(game.can_access_personal_pile(0, 0, viewer=viewer))
                self.assertEqual(game.capture_undo_state(), before)
        self.assertTrue(game.can_access_personal_pile(0, 0, viewer=0))
        self.assertTrue(game.can_access_personal_pile(0, 0, viewer=1))

    def test_session_actions_share_one_undo_and_checkpoint(self):
        for action in ("play_personal_pile", "take_personal_pile"):
            with self.subTest(action=action):
                game = self.game()
                game.players[0].hand = ["3 of Test"]
                game.personal_piles[0][1] = ["2 of Test"]
                before = game.capture_undo_state()
                saved = Mock(return_value=None)
                game.session.checkpoint_callback = saved
                result = game.session.run(lambda: game.session.execute(
                    action, card_index=0, owner=0, pile_index=1))
                self.assertTrue(result.success)
                self.assertTrue(result.changed)
                self.assertEqual(result.value, "3 of Test" if action == "play_personal_pile" else "2 of Test")
                self.assertEqual(game.personal_piles[0][1],
                                 ["2 of Test", "3 of Test"] if action == "play_personal_pile" else [])
                self.assertEqual(len(game.undo_stack), 1)
                saved.assert_called_once_with(game)
                self.assertTrue(game.session.undo())
                self.assertEqual(game.capture_undo_state(), before)
                self.assertEqual(saved.call_count, 2)

    def test_session_rejects_invalid_or_inaccessible_piles_without_changes(self):
        for action in ("play_personal_pile", "take_personal_pile"):
            for owner, pile in ((1, 0), (-1, 0), (0, -1), (99, 0), (0, 99),
                                (True, 0), (0, False), (0.0, 0), (0, 1.0),
                                ("0", 0), ([], 0), (0, {}), (None, None)):
                with self.subTest(action=action, owner=owner, pile=pile):
                    game = self.game()
                    game.players[0].hand = ["3 of Test"]
                    game.personal_piles[1][0] = ["2 of Test"]
                    before = game.capture_undo_state()
                    saved = Mock(return_value=None)
                    game.session.checkpoint_callback = saved
                    result = game.session.execute(action, card_index=0, owner=owner, pile_index=pile)
                    self.assertFalse(result.success)
                    self.assertTrue(result.message)
                    self.assertEqual(game.capture_undo_state(), before)
                    self.assertEqual(game.undo_stack, [])
                    saved.assert_not_called()

    def test_session_rejects_empty_disabled_and_confirmation_blocked_piles(self):
        for blocked in ("empty", "disabled", "confirmation"):
            with self.subTest(blocked=blocked):
                game = self.game()
                if blocked != "empty":
                    game.personal_piles[0][0] = ["2 of Test"]
                if blocked == "disabled":
                    game.enable_personal_piles = False
                if blocked == "confirmation":
                    game.current_player_must_confirm_point = lambda: True
                saved = Mock(return_value=None)
                game.session.checkpoint_callback = saved
                before = game.capture_undo_state()
                result = game.session.execute("take_personal_pile", owner=0, pile_index=0)
                self.assertFalse(result.success)
                self.assertEqual(game.capture_undo_state(), before)
                saved.assert_not_called()

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

    def test_team_and_dealer_access_are_opt_in(self):
        game = Game(3, str(Path(__file__).resolve().parents[1] / "decks/demodeck.json"),
                    enable_personal_piles=True, enable_roles_teams=True, enable_teams=True,
                    enable_dealer=True, team_count=2, player_teams=["team_1", "team_1", None],
                    dealer_players=[False, False, True], personal_pile_settings=[[{"access": "team"}]])
        game.current_player_index = 1
        self.assertFalse(game.can_access_personal_pile(0, 0))
        game.enable_team_pile_access = True
        self.assertTrue(game.can_access_personal_pile(0, 0))
        game.personal_pile_settings[0][0]["access"] = "owner"
        self.assertFalse(game.can_access_personal_pile(0, 0))
        game.current_player_index = 2
        self.assertFalse(game.can_access_personal_pile(0, 0))
        game.enable_dealer_pile_access = True
        self.assertTrue(game.can_access_personal_pile(0, 0))
        game.enable_roles_teams = False
        self.assertFalse(game.can_access_personal_pile(0, 0))

    def test_access_excluding_owner(self):
        game = Game(3, str(Path(__file__).resolve().parents[1] / "decks/demodeck.json"),
                    enable_personal_piles=True, enable_roles_teams=True, enable_teams=True,
                    enable_dealer=True, team_count=2, player_teams=["team_1", "team_1", None],
                    dealer_players=[True, False, False], enable_team_pile_access=True,
                    enable_dealer_pile_access=True)
        for access, expected in (("everyone_but_owner", [False, True, True]),
                                 ("team_but_member", [False, True, False])):
            game.personal_pile_settings[0][0]["access"] = access
            for viewer, allowed in enumerate(expected):
                game.current_player_index = viewer
                self.assertEqual(game.can_access_personal_pile(0, 0), allowed)
        game.enable_teams = False
        game.current_player_index = 1
        self.assertFalse(game.can_access_personal_pile(0, 0))

    def test_disabled_table_blocks_personal_actions(self):
        game = self.game()
        game.enable_table = False
        game.players[0].hand = ["2 of Test"]
        self.assertIsNone(game.play_to_personal_pile(1, 0, 0))
        self.assertEqual(game.players[0].hand, ["2 of Test"])


if __name__ == "__main__":
    unittest.main()
