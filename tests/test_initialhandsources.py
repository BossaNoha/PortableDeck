import json
import subprocess
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from unittest.mock import patch
from portable_deck.core.deck import Deck
from portable_deck.core.game import Game
from portable_deck.app.sessionstorage import save_session, load_session
from portable_deck.app.settingspresets import save_preset, load_preset


class InitialHandSourcesTests(unittest.TestCase):
    def game(self, sources=None, setup=None):
        return Game(2, Deck.from_definition({"types": ["T"], "cards": [list(range(10))]}),
                    enable_undo=True, enable_draw_pile_setup=True,
                    draw_pile_setup=setup or [{"id": "p1", "name": "P1", "owner": 0, "count": 4},
                                             {"id": "p2", "name": "P2", "owner": 1, "count": 4}],
                    deal_starting_hands_from_piles=True, initial_hand_sources=sources or ["p1", "p2"])

    def test_owned_hands_are_dealt_after_split_without_duplication(self):
        game = self.game()
        with patch.object(game.deck, "shuffle"): game.start(2)
        self.assertEqual([p.hand for p in game.players], [["0 of T", "1 of T"], ["4 of T", "5 of T"]])
        self.assertEqual(game.draw_piles.get("p1").cards, ["2 of T", "3 of T"])
        cards = [card for p in game.players for card in p.hand]
        for pile in game.draw_piles.view(): cards.extend(game.draw_piles.get(pile.id).cards)
        self.assertEqual(Counter(cards), Counter(game.deck.definition.expanded_cards()))

    def test_shared_source_checks_combined_demand_before_shuffle(self):
        setup = [{"id": "shared", "name": "Shared", "owner": None, "count": 3}]
        game = self.game(["shared", "shared"], setup)
        before = game.capture_undo_state()
        with patch.object(game.deck, "shuffle") as shuffle:
            with self.assertRaises(ValueError): game.start(2)
        shuffle.assert_not_called()
        self.assertEqual(game.capture_undo_state(), before)
        with patch.object(game.deck, "shuffle"): game.start(1)
        self.assertEqual([p.hand for p in game.players], [["0 of T"], ["1 of T"]])

    def test_mixed_main_and_personal_sources(self):
        game = self.game(["main", "p2"])
        with patch.object(game.deck, "shuffle"): game.start(2)
        self.assertEqual(game.players[0].hand, ["8 of T", "9 of T"])
        self.assertFalse(game.deck.flat_deck)

    def test_unknown_or_other_owned_source_is_rejected(self):
        for sources in (["missing", "p2"], ["p2", "p1"]):
            game = self.game(sources)
            before = game.capture_undo_state()
            with self.assertRaises(ValueError): game.start(1)
            self.assertEqual(game.capture_undo_state(), before)

    def test_save_restart_preset_and_undo(self):
        game = self.game(); game.start(2)
        before = game.capture_undo_state()
        game.session.execute("draw_card", draw_pile_id="p1")
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "game.json"
            save_session(game, path); loaded = load_session(Game, path)
            self.assertEqual(loaded.initial_hand_sources, ["p1", "p2"])
            self.assertTrue(loaded.session.undo())
            self.assertEqual(loaded.capture_undo_state(), before)
            restarted = loaded.restart()
            self.assertEqual([len(p.hand) for p in restarted.players], [2, 2])
            self.assertEqual(len(restarted.draw_piles.get("p1").cards), 2)
            preset = Path(folder) / "preset.json"
            values = {"num_players": 2, "cards_per_player": 2, "enable_draw_pile_setup": True,
                      "draw_pile_setup": game.draw_pile_setup, "deal_starting_hands_from_piles": True,
                      "initial_hand_sources": game.initial_hand_sources}
            saved = save_preset(preset, values)
            self.assertEqual(load_preset(preset, saved).settings["initial_hand_sources"], ["p1", "p2"])

    def test_cli_sources_and_no_tk_dependency(self):
        script = ("import sys; from portable_deck.cli import main; main(['--players','2','--hand','2',"
                  "'--draw-pile','p1','P1','1','4','--draw-pile','p2','P2','2','4',"
                  "'--initial-hand-source','p1','--initial-hand-source','p2','--json']); assert 'tkinter' not in sys.modules")
        result = subprocess.run([sys.executable, "-B", "-c", script], input="show\nquit\n",
                                capture_output=True, text=True, timeout=30, cwd=Path(__file__).resolve().parents[1])
        self.assertEqual(result.returncode, 0, result.stderr)
        view = next(json.loads(line)["view"] for line in result.stdout.splitlines() if json.loads(line)["type"] == "view")
        self.assertEqual([p["card_count"] for p in view["status"]["players"]], [2, 2])
