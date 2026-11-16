import json
import unittest
from dataclasses import FrozenInstanceError, asdict
from pathlib import Path
from unittest.mock import Mock, patch

from portable_deck.core.game import Game
from portable_deck.core.pileoptions import discard_destinations, insertion_options
from portable_deck.ui.specialactionsui import SpecialActionsUI


class PileOptionsTests(unittest.TestCase):
    def game(self):
        return Game(2, str(Path(__file__).resolve().parents[1] / "decks/demodeck.json"),
                    shared_discard_pile_count=2, personal_discard_pile_count=1,
                    enable_special_actions=True, allow_insert_draw_deck=True, allow_insert_discard_pile=True)

    def test_destinations_preserve_shared_and_own_personal_indices(self):
        g = self.game()
        targets = discard_destinations(g, 1)
        self.assertEqual([(t.pile_index, t.personal) for t in targets], [(0, False), (1, False), (0, True)])
        g.current_player_index = 1
        g.players[1].hand = ["A"]
        target = targets[-1]
        result = g.session.execute("discard_card", card_index=0, pile_index=target.pile_index, personal=target.personal)
        self.assertTrue(result.success)
        self.assertEqual(g.personal_discard_piles[1][0], ["A"])
        self.assertEqual(g.personal_discard_piles[0][0], [])
        with self.assertRaises(FrozenInstanceError):
            targets[0].pile_index = 9
        for viewer in (True, -1, 2, None):
            with self.assertRaises(ValueError):
                discard_destinations(g, viewer)
        g.enable_discard_pile = False
        self.assertEqual(discard_destinations(g, 1), ())

    def test_insertion_ranges_and_no_card_identities(self):
        for count in (0, 1, 9, 10, 19, 20, 21):
            with self.subTest(count=count):
                g = self.game()
                g.deck.flat_deck = ["SECRET"] * count
                g.discard_piles[1] = ["SECRET"] * count
                before = g.capture_undo_state()
                for option in (insertion_options(g, "draw")[0], insertion_options(g, "discard")[1]):
                    self.assertEqual(option.card_count, count)
                    self.assertEqual(option.positions_from_end, min(10, count + 1))
                    self.assertEqual(option.random_middle_available, count >= 20)
                    self.assertNotIn("SECRET", json.dumps(asdict(option)))
                self.assertEqual(g.capture_undo_state(), before)

    def test_disabled_options_and_independent_snapshots(self):
        g = self.game()
        options = insertion_options(g, "draw")
        original = options[0].card_count
        g.deck.flat_deck.clear()
        self.assertEqual(options[0].card_count, original)
        with self.assertRaises(FrozenInstanceError):
            options[0].card_count = 0
        g.allow_insert_draw_deck = False
        self.assertEqual(insertion_options(g, "draw"), ())
        g.enable_discard_pile = False
        self.assertEqual(insertion_options(g, "discard"), ())
        g.enable_special_actions = False
        self.assertEqual(insertion_options(g, "draw"), ())
        with self.assertRaises(ValueError):
            insertion_options(g, "invalid")

    def test_insertion_dialog_uses_counts_and_selected_pile(self):
        g = self.game()
        g.players[0].hand = ["A"]
        g.discard_piles[1] = ["B", "C"]
        gui = Mock(game=g)
        gui.selection.hand_index = 0
        gui.run_action.side_effect = lambda operation: g.session.run(operation)
        ui = object.__new__(SpecialActionsUI)
        ui.gui = gui
        with patch("portable_deck.ui.specialactionsui.simpledialog.askinteger", return_value=2), patch(
                "portable_deck.ui.specialactionsui.simpledialog.askstring", return_value="1") as prompt:
            ui.choose("discard")
        self.assertIn("Available positions from either end: 3", prompt.call_args.args[1])
        self.assertEqual(g.discard_piles[1], ["B", "C", "A"])
        self.assertEqual(g.discard_piles[0], [])
