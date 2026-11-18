import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from portable_deck.app.checkpoints import save_checkpoint
from portable_deck.core.game import Game


class CheckpointTests(unittest.TestCase):
    def game(self):
        g = Game(2, str(Path(__file__).resolve().parents[1] / "decks/demodeck.json"))
        g.deck.flat_deck = ["A", "B", "C"]
        return g

    def test_disabled_and_invalid_retention_do_not_touch_files(self):
        with tempfile.TemporaryDirectory() as folder, patch(
                "portable_deck.app.checkpoints.save_session") as save:
            latest = Path(folder) / "new" / "last_session.json"
            game = Mock()
            self.assertIsNone(save_checkpoint(game, latest, enabled=False, count="invalid"))
            for count in (0, 1001, "invalid", None):
                self.assertTrue(save_checkpoint(game, latest, count=count))
            save.assert_not_called()
            self.assertFalse(latest.parent.exists())

    def test_unchanged_checkpoint_has_no_version_and_retention_includes_latest(self):
        g = self.game()
        with tempfile.TemporaryDirectory() as folder:
            latest = Path(folder) / "last_session.json"
            archive = latest.parent / "autosaves"
            self.assertIsNone(save_checkpoint(g, latest, count=3))
            self.assertIsNone(save_checkpoint(g, latest, count=3))
            self.assertEqual(list(archive.iterdir()), [])
            versions = []
            with patch("portable_deck.app.checkpoints.time_ns", side_effect=[100, 200, 300]):
                for _ in range(3):
                    versions.append(latest.read_bytes())
                    g.session.execute("draw_card")
                    self.assertIsNone(save_checkpoint(g, latest, count=3))
            retained = sorted(archive.glob("*.json"))
            self.assertEqual([p.name for p in retained], ["autosave_200.json", "autosave_300.json"])
            self.assertEqual([p.read_bytes() for p in retained], versions[1:])
            self.assertEqual(len(Game.load_session(str(latest)).players[0].hand), 3)
            self.assertIsNone(save_checkpoint(g, latest, count=1))
            self.assertEqual(list(archive.iterdir()), [])

    def test_optional_client_metadata_roundtrips(self):
        with tempfile.TemporaryDirectory() as folder:
            latest = Path(folder) / "last_session.json"
            metadata = {"table_view": {"zoom": 150, "x": .5, "y": 0}}
            self.assertIsNone(save_checkpoint(self.game(), latest, client_state=metadata))
            self.assertEqual(json.loads(latest.read_text())["client_state"], metadata)

    def test_atomic_write_failure_preserves_previous_checkpoint(self):
        g = self.game()
        with tempfile.TemporaryDirectory() as folder:
            latest = Path(folder) / "last_session.json"
            save_checkpoint(g, latest)
            before = latest.read_bytes()
            g.session.execute("draw_card")
            with patch("portable_deck.app.sessionstorage.os.replace", side_effect=OSError("Disk full")):
                error = save_checkpoint(g, latest)
            self.assertEqual(error, "Disk full")
            self.assertEqual(latest.read_bytes(), before)
            self.assertFalse(Path(str(latest) + ".tmp").exists())
            self.assertEqual(list((latest.parent / "autosaves").iterdir()), [])

    def test_cleanup_error_is_reported_after_latest_was_saved(self):
        g = self.game()
        with tempfile.TemporaryDirectory() as folder:
            latest = Path(folder) / "last_session.json"
            save_checkpoint(g, latest)
            g.session.execute("draw_card")
            save_checkpoint(g, latest)
            g.session.execute("draw_card")
            with patch("portable_deck.app.checkpoints.Path.unlink", side_effect=OSError("Cleanup denied")):
                self.assertEqual(save_checkpoint(g, latest, count=1), "Cleanup denied")
            self.assertEqual(len(Game.load_session(str(latest)).players[0].hand), 2)

    def test_service_is_usable_in_another_client_without_tkinter(self):
        with tempfile.TemporaryDirectory() as folder:
            script = ("import sys; from portable_deck.app.checkpoints import save_checkpoint; "
                      "from portable_deck.core.game import Game; "
                      "g=Game(2,'decks/demodeck.json'); "
                      "g.session.checkpoint_callback=lambda game:save_checkpoint(game,sys.argv[1]); "
                      "assert g.session.execute('draw_card').checkpoint_error is None; "
                      "assert 'tkinter' not in sys.modules")
            latest = Path(folder) / "last_session.json"
            result = subprocess.run([sys.executable, "-B", "-c", script, str(latest)],
                                    cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(latest.exists())
