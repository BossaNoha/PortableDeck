import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from portable_deck.core.game import Game
from portable_deck.core.actionavailability import drop_availability
from portable_deck.ui.carddrag import CardDrag


class AutomaticDropTests(unittest.TestCase):
    def game(self, **options):
        g = Game(2, str(Path(__file__).resolve().parents[1] / "decks/demodeck.json"),
                 enable_undo=True, **options)
        g.players[0].hand = ["A", "B"]
        return g

    def test_surface_drop_resolves_next_position_and_keeps_undo(self):
        g = self.game()
        for index, pointer_position in enumerate((None, (0, 0))):
            before = g.capture_undo_state()
            proposal = drop_availability(g, "hand", 0, pointer_position)
            self.assertTrue(proposal.availability.allowed)
            self.assertEqual(proposal.action, "play_card")
            self.assertEqual(proposal.target_position, (0, index))
            result = g.session.execute(proposal.action, card_index=0,
                                       target_position=proposal.target_position)
            self.assertTrue(result.success)
            self.assertEqual(g.table_cards[-1]["position"], [0, index])
        self.assertTrue(g.session.undo())
        self.assertEqual(g.capture_undo_state(), before)

    def test_automatic_drop_does_not_bypass_confirmation_or_full_table(self):
        g = self.game(enable_table_limits=True, max_table_rows=1, max_table_columns=1)
        g.session.execute("play_card", card_index=0)
        self.assertFalse(drop_availability(g, "hand", 0).availability.allowed)
        g = self.game()
        g.current_player_must_confirm_point = lambda: True
        self.assertFalse(drop_availability(g, "hand", 0).availability.allowed)

    def test_positioned_and_table_card_drops_still_require_empty_slot(self):
        for options in ({"allow_positioned_play": True}, {"allow_play_in_front_of_players": True}):
            g = self.game(**options)
            self.assertFalse(drop_availability(g, "hand", 0).availability.allowed)
            self.assertTrue(drop_availability(g, "hand", 0, (0, 0)).availability.allowed)
        g = self.game(allow_move_cards_on_table=True)
        g.session.execute("play_card", card_index=0)
        self.assertFalse(drop_availability(g, "table", 0).availability.allowed)

    def test_occupied_widget_and_blank_canvas_resolve_to_table_surface(self):
        g = self.game()
        table = SimpleNamespace(master=None)
        canvas = table.canvas = SimpleNamespace(master=table)
        occupied = SimpleNamespace(master=canvas)
        outside = SimpleNamespace(master=None)
        root = SimpleNamespace(winfo_containing=Mock())
        drag = object.__new__(CardDrag)
        drag.gui = SimpleNamespace(game=g, table_frame=table, root=root)
        drag.pending = ("hand", 0, 0, 0)
        for widget in (occupied, canvas, table):
            root.winfo_containing.return_value = widget
            self.assertIs(drag.target(10, 20), canvas)
        root.winfo_containing.return_value = outside
        self.assertIsNone(drag.target(10, 20))
        g.allow_positioned_play = True
        root.winfo_containing.return_value = occupied
        self.assertIsNone(drag.target(10, 20))

    def test_release_submits_surface_drop_but_not_outside_drop(self):
        for target in (SimpleNamespace(), None):
            drag = object.__new__(CardDrag)
            drag.suppress_release = False
            drag.pending = ("hand", 0, 0, 0)
            drag.dragging = True
            drag.target = Mock(return_value=target)
            drag.cancel = Mock()
            drag.drop = Mock()
            event = SimpleNamespace(x_root=10, y_root=20, widget=Mock())
            drag.release(event)
            if target is not None:
                drag.drop.assert_called_once_with("hand", 0, None)
            else:
                drag.drop.assert_not_called()
