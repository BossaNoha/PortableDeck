import ast
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock
from portable_deck.core.game import Game


class GameLogTests(unittest.TestCase):
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

    def test_gui_does_not_append_game_log_or_history(self):
        root = Path(__file__).resolve().parents[1] / 'portable_deck/ui'
        for path in root.glob('*.py'):
            for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                    if node.func.attr == 'append' and isinstance(node.func.value, ast.Attribute):
                        self.assertNotIn(node.func.value.attr, ('game_log', 'gui_log', 'history'), path.name)

    def test_cli_uses_log_without_tkinter(self):
        script = "from portable_deck.core.game import Game; import sys; g=Game(2,'decks/demodeck.json'); r=g.session.execute('draw_card'); assert r.messages==tuple(g.game_log); assert 'tkinter' not in sys.modules"
        result = subprocess.run([sys.executable, '-B', '-c', script], cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
