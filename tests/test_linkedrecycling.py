import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from portable_deck.app.settingspresets import load_preset, save_preset
from portable_deck.app.sessionstorage import load_session, save_session
from portable_deck.cli import CLIClient
from portable_deck.core.game import Game
from portable_deck.core.settingsvalidation import SettingsValidationError, validate_settings


class LinkedRecyclingTests(unittest.TestCase):
    def setup_data(self):
        return [{"id": "mine", "name": "My deck", "owner": 0, "count": 0},
                {"id": "theirs", "name": "Other deck", "owner": 1, "count": 0}]

    def game(self, links=None):
        game = Game(2, str(Path(__file__).resolve().parents[1] / "decks/demodeck.json"), enable_undo=True,
                    allow_recycle_discard_to_deck=True, enable_draw_pile_setup=True,
                    draw_pile_setup=self.setup_data(), enable_linked_recycling=True,
                    draw_pile_recycling={"mine": {"personal": True, "pile_index": 1}} if links is None else links,
                    shared_discard_pile_count=2, personal_discard_pile_count=2)
        game.start(0)
        game.discard_piles[:] = [["SHARED_A"], ["SHARED_B", "SHARED_C"]]
        game.personal_discard_piles[:] = [[["OWN_0"], ["OWN_A", "OWN_B"]], [["OTHER_0"], ["OTHER_1"]]]
        game.session.checkpoint_callback = Mock(return_value=None)
        return game

    def test_personal_recycle_moves_only_assigned_discard_and_one_undo(self):
        game = self.game()
        before = game.capture_undo_state()
        with patch("portable_deck.core.gametable.random.shuffle", side_effect=lambda cards: cards.reverse()):
            result = game.session.execute("recycle_discard", draw_pile_id="mine")
        self.assertTrue(result.success)
        self.assertEqual(result.value, 2)
        self.assertEqual(game.draw_piles.get("mine").cards, ["OWN_B", "OWN_A"])
        self.assertEqual(game.personal_discard_piles[0], [["OWN_0"], []])
        self.assertEqual(game.personal_discard_piles[1], [["OTHER_0"], ["OTHER_1"]])
        self.assertEqual(game.discard_piles, before["discard_piles"])
        self.assertEqual(game.deck.flat_deck, before["remaining_deck"])
        self.assertNotIn("OWN_A", repr(result.messages) + repr(result.events))
        self.assertEqual(len(game.undo_stack), 1)
        game.session.checkpoint_callback.assert_called_once_with(game)
        self.assertTrue(game.session.undo())
        self.assertEqual(game.capture_undo_state(), before)

    def test_shared_discard_can_feed_named_or_main_pile(self):
        for target in ("mine", "main"):
            game = self.game({target: {"personal": False, "pile_index": 1}})
            game.draw_piles.get(target).cards.clear()
            before = game.capture_undo_state()
            self.assertTrue(game.session.execute("recycle_discard", draw_pile_id=target).success)
            self.assertCountEqual(game.draw_piles.get(target).cards, ["SHARED_B", "SHARED_C"])
            self.assertEqual(game.discard_piles[0], ["SHARED_A"])
            self.assertEqual(game.personal_discard_piles, before["personal_discard_piles"])

    def test_unmapped_nonempty_empty_disabled_and_other_owner_are_rejected(self):
        for reason in ("unmapped", "nonempty", "empty", "disabled", "other", "pending"):
            game = self.game()
            target = "mine"
            if reason == "unmapped": game.draw_pile_recycling = {}
            elif reason == "nonempty": game.draw_piles.get(target).cards.append("X")
            elif reason == "empty": game.personal_discard_piles[0][1].clear()
            elif reason == "disabled": game.allow_recycle_discard_to_deck = False
            elif reason == "other": target = "theirs"
            else: game.current_player_must_confirm_point = lambda: True
            before = game.capture_undo_state()
            self.assertFalse(game.session.execute("recycle_discard", draw_pile_id=target).success)
            self.assertEqual(game.capture_undo_state(), before)
            game.session.checkpoint_callback.assert_not_called()
        game = self.game()
        game.deck.flat_deck.clear()
        self.assertEqual(game.session.execute("recycle_discard").code, "no_discard_link")

    def test_legacy_mode_keeps_old_main_behavior_and_rejects_named_targets(self):
        game = self.game()
        game.enable_linked_recycling = False
        self.assertEqual(game.session.execute("recycle_discard", draw_pile_id="mine").code, "linked_recycling_disabled")
        game.deck.flat_deck.clear()
        total = sum(len(pile) for _, pile in game.all_discard_piles())
        self.assertTrue(game.session.execute("recycle_discard").success)
        self.assertEqual(len(game.deck.flat_deck), total)
        self.assertFalse(any(pile for _, pile in game.all_discard_piles()))

    def test_invalid_links_are_rejected_by_settings_validation(self):
        for links in ({"missing": {"personal": False, "pile_index": 0}},
                      {"main": {"personal": True, "pile_index": 0}},
                      {"mine": {"personal": False, "pile_index": 2}},
                      {"mine": {"personal": True, "pile_index": True}},
                      {"mine": {"personal": 1, "pile_index": 0}}):
            with self.assertRaises(SettingsValidationError) as error:
                validate_settings({"num_players": 2, "draw_pile_setup": self.setup_data(),
                                   "shared_discard_pile_count": 2, "personal_discard_pile_count": 2,
                                   "draw_pile_recycling": links})
            self.assertIn("draw_pile_recycling", error.exception.fields)

    def test_failed_shuffle_restores_all_piles(self):
        game = self.game()
        before = game.capture_undo_state()
        with patch("portable_deck.core.gametable.random.shuffle", side_effect=ValueError("failed")):
            self.assertFalse(game.session.execute("recycle_discard", draw_pile_id="mine").success)
        self.assertEqual(game.capture_undo_state(), before)
        self.assertFalse(game.undo_stack)
        game.session.checkpoint_callback.assert_not_called()

    def test_preset_save_load_undo_restart_and_legacy_defaults(self):
        game = self.game()
        game.session.execute("recycle_discard", draw_pile_id="mine")
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "game.json"
            save_session(game, path)
            loaded = load_session(Game, path)
            self.assertEqual(loaded.draw_pile_recycling, game.draw_pile_recycling)
            self.assertTrue(loaded.session.undo())
            self.assertEqual(loaded.personal_discard_piles[0][1], ["OWN_A", "OWN_B"])
            self.assertTrue(loaded.restart().enable_linked_recycling)
            state = json.loads(path.read_text(encoding="utf-8"))
            del state["enable_linked_recycling"]; del state["draw_pile_recycling"]
            path.write_text(json.dumps(state), encoding="utf-8")
            legacy = load_session(Game, path)
            self.assertFalse(legacy.enable_linked_recycling)
            self.assertEqual(legacy.draw_pile_recycling, {})
            preset = Path(folder) / "preset.json"
            values = {"num_players": 2, "draw_pile_setup": self.setup_data(), "personal_discard_pile_count": 2,
                      "enable_linked_recycling": True, "draw_pile_recycling": game.draw_pile_recycling}
            saved = save_preset(preset, values)
            self.assertEqual(load_preset(preset, saved).settings["draw_pile_recycling"], game.draw_pile_recycling)

    def test_cli_selected_target_and_flags_without_tk(self):
        game = self.game()
        client = CLIClient(game, io.StringIO(), structured=True)
        client.command("source mine"); client.command("recycle")
        self.assertCountEqual(game.draw_piles.get("mine").cards, ["OWN_A", "OWN_B"])
        script = ("import sys; from portable_deck.cli import main; main(['--players','2','--hand','2',"
                  "'--draw-pile','mine','My deck','1','0','--personal-discards','1',"
                  "'--recycle-from','mine','personal','1','--discard-multiple-cards','--json']); "
                  "assert 'tkinter' not in sys.modules")
        result = subprocess.run([sys.executable, "-B", "-c", script],
                                input="discard-many personal 1 1 2\nsource mine\nrecycle\nshow\nquit\n",
                                text=True, capture_output=True, timeout=30, cwd=Path(__file__).resolve().parents[1])
        self.assertEqual(result.returncode, 0, result.stderr)
        records = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertTrue(all(r["success"] for r in records if r["type"] == "result"))
