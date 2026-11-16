import json
import subprocess
import sys
import unittest
from dataclasses import FrozenInstanceError, asdict
from pathlib import Path

from portable_deck.core.game import Game
from portable_deck.core.playerview import build_player_hands_view, build_player_table_view
from portable_deck.ui.tableframe import TableFrame


class PlayerViewTests(unittest.TestCase):
    def test_table_hides_face_down_cards_for_every_player(self):
        g = self.game()
        g.table_cards = [
            {"card": "PUBLIC", "player": "Player1", "position": [0, 0]},
            {"card": "SECRET", "player": "Player2", "position": [0, 0], "face_up": False},
        ]
        before = g.capture_undo_state()
        for viewer in range(3):
            view = build_player_table_view(g, viewer)
            self.assertEqual([card.index for card in view.cards], [0, 1])
            self.assertEqual(view.cards[0].card, "PUBLIC")
            self.assertIsNone(view.cards[1].card)
            self.assertNotIn("SECRET", json.dumps(asdict(view)))
            self.assertEqual(view.cards[1].position, (0, 0))
            self.assertEqual(TableFrame._card_text(view.cards[1]), "Face down")
            self.assertEqual(TableFrame._card_text(view.cards[0]), "PUBLIC\nPlayer1")
            self.assertNotIn((0, 0), view.available_positions)
        self.assertEqual(g.capture_undo_state(), before)

    def test_table_snapshot_is_independent_and_respects_lanes(self):
        g = self.game(allow_play_in_front_of_players=True)
        g.table_cards = [{"card": "PUBLIC", "player": "Player1", "position": [0, 0]}]
        view = build_player_table_view(g, 0)
        data = asdict(view)
        self.assertTrue(view.player_lanes)
        self.assertEqual(view.player_names, ("Player1", "Player2", "Player3"))
        self.assertIn((1, 0), view.available_positions)
        g.table_cards[0]["position"][0] = 2
        g.table_cards[0]["card"] = "CHANGED"
        self.assertEqual(asdict(view), data)
        with self.assertRaises(FrozenInstanceError):
            view.cards[0].card = "changed"

    def test_disabled_empty_table_and_invalid_viewers(self):
        g = self.game()
        self.assertEqual(build_player_table_view(g, 0).available_positions, ((0, 0),))
        g.enable_table = False
        g.table_cards = [{"card": "SECRET", "player": "Player1", "position": [0, 0]}]
        view = build_player_table_view(g, 0)
        self.assertFalse(view.enabled)
        self.assertEqual(view.cards, ())
        self.assertEqual(view.available_positions, ())
        for viewer in (-1, 3, True, None, "0"):
            with self.subTest(viewer=viewer), self.assertRaises(ValueError):
                build_player_table_view(g, viewer)

    def game(self, **options):
        g = Game(3, str(Path(__file__).resolve().parents[1] / "decks/demodeck.json"), **options)
        for i, player in enumerate(g.players):
            player.hand = [f"PRIVATE {i}", f"REVEALED {i}"]
        return g

    def test_hidden_identities_are_absent_from_serialized_view(self):
        g = self.game()
        g.players[1].revealed_indices = {1}
        before = g.capture_undo_state()
        view = build_player_hands_view(g, 0)
        data = json.dumps(asdict(view))
        self.assertIn("PRIVATE 0", data)
        self.assertIn("REVEALED 1", data)
        self.assertNotIn("PRIVATE 1", data)
        self.assertNotIn("PRIVATE 2", data)
        self.assertNotIn("REVEALED 2", data)
        self.assertIsNone(view.hands[1].cards[0].card)
        self.assertTrue(view.hands[1].visible)
        self.assertFalse(view.hands[2].visible)
        self.assertEqual(g.capture_undo_state(), before)

    def test_explicit_viewer_and_directional_team_dealer_permissions(self):
        g = self.game(enable_cards_visibility=True, enable_roles_teams=True, enable_teams=True,
                      enable_dealer=True, team_count=2, player_teams=["team_1", "team_1", None],
                      dealer_players=[False, False, True], cards_visibility=[
                          {"players": [0], "teams": ["dealer"]},
                          {"players": [], "teams": ["team_1"]},
                          {"players": [0], "teams": []}])
        for viewer, expected in ((0, [True, True, True]), (1, [False, True, False]), (2, [True, False, False])):
            with self.subTest(viewer=viewer):
                view = build_player_hands_view(g, viewer)
                self.assertEqual([hand.fully_visible for hand in view.hands], expected)
                self.assertEqual(view.viewer, viewer)
                for hand in view.hands:
                    if not hand.fully_visible:
                        self.assertTrue(all(slot.card is None for slot in hand.cards))

    def test_snapshot_is_independent_and_immutable(self):
        g = self.game()
        view = build_player_hands_view(g, 0)
        original = asdict(view)
        g.players[0].hand.clear()
        g.players[1].revealed_indices.add(0)
        self.assertEqual(asdict(view), original)
        with self.assertRaises(FrozenInstanceError):
            view.hands[0].cards[0].card = "changed"

    def test_invalid_viewers_and_empty_hands(self):
        g = self.game()
        for viewer in (-1, 3, True, None, "0"):
            with self.subTest(viewer=viewer), self.assertRaises(ValueError):
                build_player_hands_view(g, viewer)
        g.players[0].hand.clear()
        view = build_player_hands_view(g, 0)
        self.assertTrue(view.hands[0].visible)
        self.assertEqual(view.hands[0].cards, ())

    def test_projection_works_without_tkinter(self):
        script = ("from portable_deck.core.game import Game; "
                  "from portable_deck.core.playerview import build_player_hands_view, build_player_table_view, build_player_personal_piles_view, build_player_discard_view; import sys; "
                  "g=Game(2,'decks/demodeck.json'); assert build_player_hands_view(g,1).viewer==1; "
                  "assert build_player_table_view(g,1).viewer==1; "
                  "assert build_player_personal_piles_view(g,1).viewer==1; "
                  "assert build_player_discard_view(g,1).viewer==1; "
                  "assert 'tkinter' not in sys.modules")
        result = subprocess.run([sys.executable, "-B", "-c", script],
                                cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
