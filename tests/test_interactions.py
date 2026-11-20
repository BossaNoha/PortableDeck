from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock
from portable_deck.core.game import Game
from portable_deck.app.sessionstorage import save_session, load_session
from portable_deck.core.interactions import INTERACTIONS

class InteractionTests(unittest.TestCase):
    def test_session_interactions_have_one_undo_and_checkpoint(self):
        for action in INTERACTIONS:
            with self.subTest(action=action):
                game = self.game()
                before = game.capture_undo_state()
                saved = Mock(return_value=None)
                game.session.checkpoint_callback = saved
                result = game.session.run(lambda: game.session.execute(
                    action, target=1, card_index=0, amount=5))
                self.assertTrue(result.success, result.message)
                self.assertTrue(result.changed)
                self.assertTrue(result.events)
                self.assertEqual(len(game.undo_stack), 1)
                saved.assert_called_once_with(game)
                if action == "give_card":
                    self.assertIn("A of Test", game.players[1].hand)
                elif action == "steal_chips":
                    self.assertEqual(game.chip_balance(0), 105)
                    self.assertEqual(game.chip_balance(1), 95)
                elif action == "take_random_card":
                    self.assertIn(result.value["card"], game.players[0].hand)
                elif action == "discard_random_card":
                    self.assertIn(result.value["card"], game.discard_pile)
                else:
                    self.assertTrue(result.value["cards"])
                    self.assertEqual([p.hand for p in game.players],
                                     [["A of Test"], ["2 of Test", "3 of Test"], ["4 of Test"]])
                    for event in result.events:
                        self.assertNotIn("card", event)
                        self.assertNotIn("cards", event)
                    for card in game.players[1].hand:
                        self.assertNotIn(card, repr(result.messages))
                self.assertTrue(game.session.undo())
                self.assertEqual(game.capture_undo_state(), before)
                self.assertEqual(saved.call_count, 2)

    def test_session_rejections_do_not_change_state_or_save(self):
        for case in ("disabled", "confirmation", "departed_actor", "departed_target",
                     "invalid_target", "missing_card", "invalid_amount", "empty_target", "shared_account"):
            with self.subTest(case=case):
                options = {}
                if case == "shared_account":
                    options = dict(enable_roles_teams=True, enable_teams=True, team_count=1,
                                   player_teams=["team_1", "team_1", None], share_team_chips=True)
                game = self.game(**options)
                action, parameters = "take_random_card", {"target": 1}
                if case == "disabled":
                    game.enable_interactions = False
                elif case == "confirmation":
                    game.current_player_must_confirm_point = lambda: True
                elif case == "departed_actor":
                    game.left_players = [0]
                elif case == "departed_target":
                    game.left_players = [1]
                elif case == "invalid_target":
                    parameters["target"] = True
                elif case == "missing_card":
                    action = "give_card"
                elif case in {"invalid_amount", "shared_account"}:
                    action = "steal_chips"
                    parameters["amount"] = -1 if case == "invalid_amount" else 5
                elif case == "empty_target":
                    game.players[1].hand.clear()
                before = game.capture_undo_state()
                saved = Mock(return_value=None)
                game.session.checkpoint_callback = saved
                result = game.session.execute(action, **parameters)
                self.assertFalse(result.success)
                self.assertTrue(result.message)
                self.assertEqual(game.capture_undo_state(), before)
                self.assertEqual(game.undo_stack, [])
                saved.assert_not_called()

    def game(self, **options):
        game = Game(3, str(Path(__file__).resolve().parents[1] / "decks/demodeck.json"),
                    enable_interactions=True, interaction_options=dict.fromkeys(INTERACTIONS, True),
                    enable_chip_accounts=True, enable_undo=True, **options)
        game.players[0].hand = ["A of Test"]
        game.players[1].hand = ["2 of Test", "3 of Test"]
        game.players[2].hand = ["4 of Test"]
        return game

    def test_card_transfers_and_random_discard_conserve_cards(self):
        game = self.game()
        card = game.interact("take_random_card", 1)["card"]
        self.assertIn(card, game.players[0].hand)
        self.assertNotIn(card, game.players[1].hand)
        game.interact("give_card", 2, hand_index=1)
        self.assertIn("A of Test", game.players[2].hand)
        result = game.interact("discard_random_card")
        self.assertNotEqual(result["target"], 0)
        self.assertIn(result["card"], game.discard_pile)
        self.assertEqual(sum(len(p.hand) for p in game.players) + len(game.discard_pile), 4)

    def test_peeks_are_private_and_do_not_change_hands(self):
        game = self.game()
        hands = [p.hand.copy() for p in game.players]
        self.assertIn(game.interact("peek_random_card", 1)["cards"][0], hands[1])
        self.assertEqual(game.interact("peek_all_cards", 1)["cards"], hands[1])
        self.assertEqual([p.hand for p in game.players], hands)
        self.assertTrue(all("card" not in entry and "cards" not in entry for entry in game.history))

    def test_shared_chip_accounts_and_undo(self):
        game = self.game(enable_roles_teams=True, enable_teams=True, team_count=2,
                         player_teams=["team_1", "team_1", "team_2"], share_team_chips=True)
        with self.assertRaises(ValueError):
            game.interact("steal_chips", 1, amount=5)
        state = game.capture_undo_state()
        game.undo_stack.append(state)
        game.interact("steal_chips", 2, amount=30)
        self.assertEqual(game.chip_balance(1), 230)
        self.assertEqual(game.chip_balance(2), 70)
        self.assertTrue(game.undo_last_action())
        self.assertEqual(game.capture_undo_state(), state)

    def test_permissions_invalid_targets_and_persistence(self):
        game = self.game(enable_discard_pile=False)
        for action, target in (("discard_random_card", None), ("give_card", 0), ("steal_chips", 99)):
            state = game.capture_undo_state()
            with self.assertRaises(ValueError):
                game.interact(action, target)
            self.assertEqual(game.capture_undo_state(), state)
        game.enable_interactions = False
        with self.assertRaises(ValueError):
            game.interact("take_random_card", 1)
        game.enable_interactions = True
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as directory:
            path = str(Path(directory) / "save.json")
            save_session(game, path)
            loaded = load_session(Game, path)
            self.assertEqual(loaded.interaction_options, game.interaction_options)
            self.assertTrue(loaded.restart().enable_interactions)
