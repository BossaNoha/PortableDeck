from pathlib import Path
import tempfile
import unittest
from portable_deck.core.game import Game
from portable_deck.core.interactions import INTERACTIONS

class InteractionTests(unittest.TestCase):
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
            game.save_session(path)
            loaded = Game.load_session(path)
            self.assertEqual(loaded.interaction_options, game.interaction_options)
            self.assertTrue(loaded.restart().enable_interactions)
