import json
import tempfile
import unittest
from pathlib import Path

from portable_deck.core.game import Game
from portable_deck.app.sessionstorage import save_session, load_session
from portable_deck.core.actionavailability import action_availability
from portable_deck.core.playerview import build_player_discard_view
from portable_deck.core.sessionstatus import build_session_status


class DiscardNormalizationTests(unittest.TestCase):
    def game(self, **options):
        return Game(2, str(Path(__file__).resolve().parents[1] / "decks/demodeck.json"),
                    enable_undo=True, allow_draw_from_discard=True, **options)

    def test_queries_and_save_preserve_state_and_collection_identity(self):
        g = self.game(personal_discard_pile_count=1)
        g.personal_discard_piles[1][0] = ["A"]
        before = g.capture_undo_state()
        fields = set(g.__dict__)
        personal = g.personal_discard_piles
        groups = tuple(personal)
        shared = g.discard_piles
        for _ in range(2):
            piles = g.all_discard_piles()
            build_player_discard_view(g, 0)
            build_session_status(g)
            action_availability(g, "draw_from_discard")
        self.assertIs(piles[-1][1], personal[1][0])
        with tempfile.TemporaryDirectory() as folder:
            save_session(g, str(Path(folder) / "session.json"))
        self.assertEqual(g.capture_undo_state(), before)
        self.assertEqual(set(g.__dict__), fields)
        self.assertIs(g.personal_discard_piles, personal)
        self.assertIs(g.discard_piles, shared)
        for actual, original in zip(g.personal_discard_piles, groups):
            self.assertIs(actual, original)

    def test_load_normalizes_legacy_single_discard_before_queries_and_draw(self):
        g = self.game()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "legacy.json"
            save_session(g, str(path))
            data = json.loads(path.read_text(encoding="utf-8"))
            for key in ("discard_piles", "shared_discard_pile_count", "personal_discard_piles",
                        "personal_discard_pile_count"):
                data.pop(key)
            data["discard_pile"] = ["LEGACY"]
            path.write_text(json.dumps(data), encoding="utf-8")
            loaded = load_session(Game, str(path))
        self.assertEqual(loaded.discard_piles, [["LEGACY"]])
        self.assertEqual(loaded.personal_discard_piles, [[], []])
        self.assertEqual(loaded.shared_discard_pile_count, 1)
        self.assertEqual(loaded.all_discard_piles(), [("Shared discard 1", ["LEGACY"])])
        before = loaded.capture_undo_state()
        self.assertTrue(loaded.session.execute("draw_from_discard").success)
        self.assertTrue(loaded.session.undo())
        self.assertEqual(loaded.capture_undo_state(), before)

    def test_undo_normalizes_missing_and_incomplete_legacy_fields(self):
        for personal in (None, [[[]]]):
            with self.subTest(personal=personal):
                g = self.game(personal_discard_pile_count=2)
                snapshot = g.capture_undo_state()
                snapshot.pop("discard_piles")
                snapshot["discard_pile"] = ["A"]
                if personal is None:
                    snapshot.pop("personal_discard_piles")
                else:
                    snapshot["personal_discard_piles"] = personal
                g.undo_stack = [snapshot]
                self.assertTrue(g.session.undo())
                self.assertEqual(g.discard_piles, [["A"]])
                self.assertEqual(g.personal_discard_piles, [[[], []], [[], []]])
                self.assertEqual(len(g.all_discard_piles()), 5)

    def test_personal_only_discard_configuration_survives_save_load_and_undo(self):
        g = self.game(shared_discard_pile_count=0, personal_discard_pile_count=1)
        g.personal_discard_piles[1][0] = ["A"]
        with tempfile.TemporaryDirectory() as folder:
            path = str(Path(folder) / "session.json")
            save_session(g, path)
            g = load_session(Game, path)
        self.assertEqual(g.discard_piles, [])
        self.assertEqual(g.shared_discard_pile_count, 0)
        self.assertEqual(len(g.all_discard_piles()), 2)
        before = g.capture_undo_state()
        self.assertTrue(g.session.execute("draw_from_discard", source_index=1).success)
        self.assertTrue(g.session.undo())
        self.assertEqual(g.capture_undo_state(), before)
