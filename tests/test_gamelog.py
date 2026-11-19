import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from portable_deck.core.game import Game


class GameLogTests(unittest.TestCase):
    def test_session_log_snapshot_is_independent_ordered_and_tracks_undo_and_checkpoint(self):
        g = self.game(enable_undo=True)
        before = g.capture_undo_state()
        empty = g.session.log_snapshot()
        self.assertEqual(empty, ())
        self.assertEqual(g.capture_undo_state(), before)
        g.session.execute("draw_card")
        drawn = g.session.log_snapshot()
        self.assertEqual(drawn, ("Player1 drew a card.",))
        with self.assertRaises(TypeError):
            drawn[0] = "changed"
        g.session.execute("end_turn")
        self.assertEqual(g.session.log_snapshot()[:1], drawn)
        self.assertEqual(g.session.log_snapshot()[-1], "Player2's turn starts.")
        self.assertEqual(drawn, ("Player1 drew a card.",))
        self.assertTrue(g.session.undo_result().success)
        self.assertEqual(g.session.log_snapshot(), drawn)
        g.session.checkpoint_callback = lambda game: "Disk full"
        self.assertFalse(g.session.checkpoint_result().success)
        failed = g.session.log_snapshot()
        self.assertEqual(failed[:-1], drawn)
        self.assertIn("Disk full", failed[-1])
        self.assertEqual(drawn, ("Player1 drew a card.",))
        self.assertEqual(empty, ())

    def test_gui_renders_one_session_snapshot_without_model_access(self):
        from portable_deck.ui.guibase import GameGUI
        for lines in ((), ("First", "Second")):
            with self.subTest(lines=lines):
                session = Mock()
                session.log_snapshot.return_value = lines
                gui = SimpleNamespace(session=session, log_text=Mock())
                GameGUI.render_log(gui)
                session.log_snapshot.assert_called_once_with()
                gui.log_text.delete.assert_called_once_with("1.0", "end")
                if lines:
                    gui.log_text.insert.assert_called_once_with("end", "First\nSecond\n")
                else:
                    gui.log_text.insert.assert_not_called()
                gui.log_text.see.assert_called_once_with("end")
                self.assertEqual(gui.log_text.config.call_args_list[-1].kwargs, {"state": "disabled"})

    def test_start_and_restart_initialize_log_without_gui(self):
        g = self.game(enable_undo=True)
        g.start(cards_per_player=0)
        self.assertEqual(g.game_log, ["Player1's turn starts."])
        g.ensure_initial_log()
        self.assertEqual(len(g.history), 1)
        restarted = g.restart()
        self.assertEqual(restarted.game_log, ["Player1's turn starts."])
        before = restarted.capture_undo_state()
        self.assertTrue(restarted.session.execute("draw_card").success)
        self.assertTrue(restarted.session.undo())
        self.assertEqual(restarted.capture_undo_state(), before)

    def test_load_initializes_empty_log_once_and_preserves_existing_text(self):
        for log in ([], ["Existing saved message"]):
            for legacy in (False, True):
                with self.subTest(log=log, legacy=legacy), tempfile.TemporaryDirectory() as folder:
                    g = self.game()
                    g.current_player_index = 1
                    g.game_log = list(log)
                    path = Path(folder) / "session.json"
                    g.save_session(str(path))
                    if legacy:
                        state = json.loads(path.read_text(encoding="utf-8"))
                        state["gui_log"] = state.pop("game_log")
                        path.write_text(json.dumps(state), encoding="utf-8")
                    loaded = Game.load_session(str(path))
                    self.assertEqual(loaded.game_log, log or ["Player2's turn starts."])
                    self.assertEqual(len(loaded.history), 0 if log else 1)
                    loaded.save_session(str(path))
                    reloaded = Game.load_session(str(path))
                    self.assertEqual(reloaded.game_log, loaded.game_log)
                    self.assertEqual(reloaded.history, loaded.history)

    def test_load_does_not_start_turn_when_everyone_has_left(self):
        g = self.game(enable_player_leaving=True)
        g.left_players = [0, 1]
        with tempfile.TemporaryDirectory() as folder:
            path = str(Path(folder) / "session.json")
            g.save_session(path)
            loaded = Game.load_session(path)
            self.assertEqual(loaded.game_log, [])
            self.assertEqual(loaded.history, [])

    def game(self, **options):
        return Game(2, str(Path(__file__).resolve().parents[1] / 'decks/demodeck.json'), **options)

    def test_direct_core_actions_log_without_session_or_gui(self):
        g = self.game()
        g.deal_card_to_current()
        self.assertEqual(g.game_log, ["Player1 drew a card."])
        g.play_to_table(1)
        self.assertIn('onto the table', g.game_log[-1])
        g.finish_turn()
        self.assertEqual(g.game_log[-1], "Player2's turn starts.")
        self.assertEqual(sum('drew a card' in text for text in g.game_log), 1)

    def test_session_returns_core_events_and_public_messages(self):
        g = self.game(enable_undo=True)
        result = g.session.execute('draw_card')
        self.assertEqual(result.messages, ('Player1 drew a card.',))
        self.assertEqual(result.events[0]['action'], 'draw_card')
        self.assertNotIn('card', result.events[0])
        result.events[0]['action'] = 'modified'
        self.assertEqual(g.history[0]['action'], 'draw_card')
        self.assertTrue(g.session.undo())
        self.assertEqual(g.game_log, [])
        self.assertEqual(g.history, [])

    def test_failed_action_and_transaction_do_not_leave_logs(self):
        g = self.game(enable_undo=True)
        self.assertFalse(g.session.execute('play_card', card_index=99).success)
        self.assertEqual(g.game_log, [])
        def broken():
            g.deal_card_to_current()
            raise RuntimeError('Failed')
        with self.assertRaises(RuntimeError):
            g.session.run(broken)
        self.assertEqual(g.game_log, [])
        self.assertEqual(g.history, [])

    def test_face_down_and_private_peeks_do_not_expose_cards(self):
        g = self.game(enable_flipping=True, allow_flip_table=True,
                      allow_face_down_table_cards=True, enable_interactions=True,
                      interaction_options={'peek_all_cards': True, 'take_random_card': True})
        g.players[0].hand = ['SECRET FACE DOWN']
        g.play_to_table(1, face_up=False)
        g.players[1].hand = ['SECRET PEEK']
        result = g.interact('peek_all_cards', 1)
        self.assertEqual(result['cards'], ['SECRET PEEK'])
        g.interact('take_random_card', 1)
        text = '\n'.join(g.game_log)
        self.assertNotIn('SECRET', text)
        self.assertIn('looked at all cards', text)
        g.flip_table_card(0)
        self.assertIn('SECRET FACE DOWN', g.game_log[-1])

    def test_chip_score_and_special_actions_have_core_messages(self):
        g = self.game(enable_chip_accounts=True, score_enabled=True,
                      enable_special_actions=True, allow_insert_draw_deck=True)
        g.buy_chips(0, 5)
        self.assertIn('bought 5 chips', g.game_log[-1])
        g.play_chips(3)
        self.assertIn('put 3 chips', g.game_log[-1])
        g.request_point()
        self.assertIn('+1', g.game_log[-1])
        g.players[0].hand = ['A']
        g.insert_hand_card(1, 'draw', '1')
        self.assertIn('position 1 in the draw deck', g.game_log[-1])

    def test_personal_piles_and_leaving_have_core_messages(self):
        g = self.game(enable_personal_piles=True, enable_player_leaving=True,
                      enable_player_return=True)
        g.players[0].hand = ['A']
        g.play_to_personal_pile(1, 0, 0)
        self.assertIn("Player1's pile 1", g.game_log[-1])
        g.take_from_personal_pile(0, 0)
        self.assertIn('personal pile', g.game_log[-1])
        g.leave_session()
        self.assertIn('left the session', g.game_log[-2])
        g.return_player(0)
        self.assertIn('returned to the session', g.game_log[-1])

    def test_save_round_trip_and_legacy_log_key(self):
        g = self.game()
        g.deal_card_to_current()
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as folder:
            path = Path(folder) / 'session.json'
            g.save_session(str(path))
            saved = json.loads(path.read_text(encoding='utf-8'))
            self.assertIn('game_log', saved)
            self.assertEqual(Game.load_session(str(path)).game_log, g.game_log)
            saved['gui_log'] = saved.pop('game_log')
            path.write_text(json.dumps(saved), encoding='utf-8')
            self.assertEqual(Game.load_session(str(path)).game_log, g.game_log)

    def test_checkpoint_receives_core_log_and_reports_failures(self):
        g = self.game()
        seen = []
        def save(game):
            seen.append(tuple(game.game_log))
            return 'Disk full'
        g.session.checkpoint_callback = save
        result = g.session.execute('draw_card')
        self.assertEqual(seen[0], ('Player1 drew a card.',))
        self.assertEqual(g.game_log[-1], 'Autosave failed: Disk full')
        self.assertEqual(result.messages[-1], 'Autosave failed: Disk full')
