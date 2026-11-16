import json
import unittest
from dataclasses import FrozenInstanceError, asdict
from pathlib import Path

from portable_deck.core.game import Game
from portable_deck.core.playerview import build_player_personal_piles_view


class PersonalPileViewTests(unittest.TestCase):
    def game(self, **options):
        g = Game(3, str(Path(__file__).resolve().parents[1] / "decks/demodeck.json"),
                 enable_personal_piles=True, unequal_personal_piles=True,
                 personal_pile_counts=[0, 2, 1], **options)
        g.players[0].hand = ["HAND SECRET"]
        g.personal_piles[1][0] = ["BOTTOM", "TOP"]
        return g

    def test_public_cards_are_separate_from_access_and_keep_order(self):
        g = self.game()
        before = g.capture_undo_state()
        view = build_player_personal_piles_view(g, 0, 0)
        self.assertEqual([(p.owner, p.pile_index) for p in view.piles], [(1, 0), (1, 1), (2, 0)])
        pile = view.piles[0]
        self.assertEqual(pile.cards, ("BOTTOM", "TOP"))
        self.assertFalse(pile.accessible)
        self.assertFalse(pile.play.allowed)
        self.assertFalse(pile.take.allowed)
        self.assertIn("TOP", json.dumps(asdict(view)))
        self.assertNotIn("HAND SECRET", json.dumps(asdict(view)))
        self.assertEqual(g.capture_undo_state(), before)

    def test_owner_access_empty_piles_selection_and_turn(self):
        g = self.game()
        view = build_player_personal_piles_view(g, 1, 0)
        self.assertTrue(view.piles[0].accessible)
        self.assertFalse(view.piles[0].take.allowed)
        g.current_player_index = 1
        g.players[1].hand = ["A"]
        view = build_player_personal_piles_view(g, 1, 0)
        self.assertTrue(view.piles[0].play.allowed)
        self.assertTrue(view.piles[0].take.allowed)
        self.assertFalse(view.piles[1].take.allowed)
        self.assertTrue(view.piles[1].play.allowed)
        self.assertFalse(build_player_personal_piles_view(g, 1).piles[0].play.allowed)
        g.current_player_must_confirm_point = lambda: True
        view = build_player_personal_piles_view(g, 1, 0)
        self.assertTrue(view.piles[0].accessible)
        self.assertFalse(view.piles[0].play.allowed)
        self.assertFalse(view.piles[0].take.allowed)

    def test_team_and_dealer_access_for_explicit_viewer(self):
        g = self.game(enable_roles_teams=True, enable_teams=True, enable_dealer=True,
                      team_count=2, player_teams=["team_1", "team_1", None],
                      dealer_players=[False, False, True], enable_team_pile_access=True)
        g.personal_pile_settings[1][0]["access"] = "team"
        g.personal_pile_settings[1][1]["access"] = "dealer_only"
        self.assertTrue(build_player_personal_piles_view(g, 0).piles[0].accessible)
        self.assertFalse(build_player_personal_piles_view(g, 0).piles[1].accessible)
        self.assertTrue(build_player_personal_piles_view(g, 2).piles[1].accessible)
        self.assertEqual(g.current_player_index, 0)

    def test_snapshot_is_immutable_and_disabled_piles_are_absent(self):
        g = self.game()
        view = build_player_personal_piles_view(g, 0)
        data = asdict(view)
        g.personal_piles[1][0].clear()
        g.personal_pile_settings[1][0]["access"] = "everyone"
        self.assertEqual(asdict(view), data)
        with self.assertRaises(FrozenInstanceError):
            view.piles[0].access = "everyone"
        for flag in ("enable_table", "enable_personal_piles"):
            setattr(g, flag, False)
            disabled = build_player_personal_piles_view(g, 0)
            self.assertFalse(disabled.enabled)
            self.assertEqual(disabled.piles, ())
            setattr(g, flag, True)
        for viewer in (True, -1, 3, None):
            with self.assertRaises(ValueError):
                build_player_personal_piles_view(g, viewer)
