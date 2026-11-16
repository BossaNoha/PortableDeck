import json
import unittest
from dataclasses import FrozenInstanceError, asdict
from pathlib import Path
from unittest.mock import Mock

from portable_deck.core.game import Game
from portable_deck.core.interactions import INTERACTIONS, build_interaction_options


class InteractionOptionsTests(unittest.TestCase):
    def game(self, **options):
        g = Game(3, str(Path(__file__).resolve().parents[1] / "decks/demodeck.json"),
                 enable_interactions=True, interaction_options=dict.fromkeys(INTERACTIONS, True),
                 enable_chip_accounts=True, enable_undo=True, **options)
        g.players[0].hand = ["PRIVATE ACTOR"]
        g.players[1].hand = ["PRIVATE TARGET"]
        return g

    def test_options_are_read_only_private_and_action_specific(self):
        g = self.game()
        before = g.capture_undo_state()
        take = build_interaction_options(g, "take_random_card")
        self.assertEqual([t.index for t in take.targets], [1, 2])
        self.assertTrue(take.targets[0].allowed)
        self.assertFalse(take.targets[1].allowed)
        self.assertTrue(take.targets[1].reason)
        self.assertNotIn("PRIVATE", json.dumps(asdict(take)))
        self.assertTrue(build_interaction_options(g, "give_card", 0).targets[1].allowed)
        self.assertFalse(build_interaction_options(g, "give_card").allowed)
        chips = build_interaction_options(g, "steal_chips")
        self.assertEqual(chips.targets[0].max_amount, 100)
        self.assertEqual(g.capture_undo_state(), before)
        g.chip_balances[1] = 0
        self.assertEqual(chips.targets[0].max_amount, 100)
        with self.assertRaises(FrozenInstanceError):
            chips.targets[0].name = "changed"

    def test_departed_shared_accounts_and_confirmation_reasons(self):
        g = self.game(enable_roles_teams=True, enable_teams=True, team_count=1,
                      player_teams=["team_1", "team_1", None], share_team_chips=True)
        options = build_interaction_options(g, "steal_chips")
        self.assertIn("share", options.targets[0].reason)
        g.left_players = [2]
        self.assertFalse(build_interaction_options(g, "steal_chips").allowed)
        g.current_player_must_confirm_point = lambda: True
        options = build_interaction_options(g, "give_card", 0)
        self.assertIn("confirmation", options.reason)
        self.assertTrue(all(not target.allowed for target in options.targets))

    def test_stale_targets_and_chip_limits_are_revalidated_on_execution(self):
        for case in ("departed", "empty_hand", "chips_reduced"):
            with self.subTest(case=case):
                g = self.game()
                action = "steal_chips" if case == "chips_reduced" else "take_random_card"
                options = build_interaction_options(g, action)
                target = options.targets[0]
                self.assertTrue(target.allowed)
                if case == "departed":
                    g.left_players = [target.index]
                elif case == "empty_hand":
                    g.players[target.index].hand.clear()
                else:
                    g.chip_balances[target.index] = 1
                before = g.capture_undo_state()
                saved = Mock(return_value=None)
                g.session.checkpoint_callback = saved
                result = g.session.execute(action, target=target.index, amount=50)
                self.assertFalse(result.success)
                self.assertEqual(g.capture_undo_state(), before)
                self.assertEqual(g.undo_stack, [])
                saved.assert_not_called()

    def test_random_target_options_and_disabled_actions(self):
        g = self.game()
        options = build_interaction_options(g, "discard_random_card")
        self.assertTrue(options.random_target)
        self.assertTrue(options.allowed)
        g.players[1].hand.clear()
        self.assertFalse(build_interaction_options(g, "discard_random_card").allowed)
        g.enable_interactions = False
        self.assertFalse(build_interaction_options(g, "give_card", 0).allowed)
        with self.assertRaises(ValueError):
            build_interaction_options(g, "invalid")
