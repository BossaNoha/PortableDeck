"""One architectural check for all core modules, including lazy query paths."""
import subprocess
import ast
import importlib.util
import sys
import unittest
import tempfile
from pathlib import Path
from textwrap import dedent


class CoreBoundaryTests(unittest.TestCase):
    def test_standalone_session_lifecycle_with_application_and_gui_imports_blocked(self):
        script = dedent('''
            import importlib.abc
            import json
            import sys
            from unittest.mock import patch
            sys.path.insert(0, sys.argv[1])
            attempts = []
            def forbidden(name):
                return (name == 'tkinter' or name.startswith('tkinter.')
                        or name == 'portable_deck.cli'
                        or name.startswith(('portable_deck.app', 'portable_deck.ui')))
            class BlockClients(importlib.abc.MetaPathFinder):
                def find_spec(self, fullname, path=None, target=None):
                    if forbidden(fullname):
                        attempts.append(fullname)
                        raise ImportError('Core requested a client dependency: ' + fullname)
            sys.meta_path.insert(0, BlockClients())
            from portable_deck.core.deck import Deck
            from portable_deck.core.game import Game
            from portable_deck.core.gamecreation import create_configured_game, start_prepared_game
            from portable_deck.core.gamesession import export_session, restore_session
            from portable_deck.core.playersessionview import build_player_session_view
            definition = {'types': ['Standalone'], 'cards': [list(range(1, 13))]}
            deck = Deck.from_definition(definition, path='missing-original-deck.json')
            with patch('builtins.open', side_effect=AssertionError('Unexpected file IO')):
                game = create_configured_game({
                    'num_players': 2, 'deck_path': deck, 'enable_undo': True,
                    'score_enabled': True, 'require_point_confirmation': True,
                    'enable_chip_accounts': True, 'require_pot_withdrawal_confirmation': True,
                    'enable_flipping': True, 'allow_flip_table': True,
                    'allow_face_down_table_cards': True,
                })
                start_prepared_game(game, 2, {'name': 'Standalone', 'modified': False})
                checkpoints = []
                def checkpoint(current):
                    checkpoints.append(export_session(current))
                game.session.checkpoint_callback = checkpoint
                for action, parameters in (
                    ('draw_card', {}), ('play_face_down', {'card_index': 0}),
                    ('request_point', {}), ('play_chips', {'amount': 3}),
                    ('take_pot', {'player_index': 0}), ('end_turn', {}),
                ):
                    result = game.session.execute(action, **parameters)
                    assert result.success, (action, result)
                assert len(checkpoints) == 6
                state = export_session(game)
                restored = restore_session(Game, json.loads(json.dumps(state)))
                assert restored.capture_undo_state() == game.capture_undo_state()
                assert restored.session.checkpoint_callback is None
                assert not hasattr(restored, 'named_save_path')
                assert not restored.session.end_turn_availability().allowed
                before = restored.capture_undo_state()
                refused = restored.session.execute('end_turn')
                assert refused.code == 'confirmation_required'
                assert restored.capture_undo_state() == before
                assert restored.session.execute('confirm_point', approved=True).success
                before_pot = restored.capture_undo_state()
                assert restored.session.execute('confirm_pot', approved=True).success
                assert restored.chip_pot == 0 and restored.scores == [1, 0]
                assert restored.session.undo_result().success
                assert restored.capture_undo_state() == before_pot
                assert restored.session.execute('confirm_pot', approved=False).success
                assert restored.chip_pot == 3
                assert restored.session.log_snapshot()
                assert build_player_session_view(restored, 1).viewer == 1
                restarted = restored.restart(keep_scores=True)
                assert restarted.deck.types == ['Standalone']
                assert len(restarted.deck.flat_deck) == 8
                assert [len(player.hand) for player in restarted.players] == [2, 2]
                assert restarted.scores == [1, 0]
                assert not restarted.undo_stack and not restarted.pending_point_request
                assert not restarted.pending_pot_withdrawal
                assert export_session(game) == state
                assert checkpoints[0] != checkpoints[-1]
            assert not attempts, attempts
            assert not [name for name in sys.modules if forbidden(name)]
        ''')
        with tempfile.TemporaryDirectory() as folder:
            result = subprocess.run([sys.executable, '-B', '-c', script,
                                     str(Path(__file__).resolve().parents[1])],
                                    cwd=folder, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(list(Path(folder).iterdir()), [])

    def test_core_does_not_import_application_or_presentation_modules(self):
        root = Path(__file__).resolve().parents[1]
        violations = []
        for path in (root / "portable_deck" / "core").rglob("*.py"):
            module = ".".join(path.relative_to(root).with_suffix("").parts)
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    base = node.module or ""
                    if node.level:
                        base = importlib.util.resolve_name("." * node.level + base, module.rpartition(".")[0])
                    names = [base] + [base + "." + alias.name for alias in node.names]
                else:
                    continue
                for name in names:
                    if (name == "tkinter" or name.startswith("tkinter.")
                            or (name.startswith("portable_deck.") and not
                                (name == "portable_deck.core" or name.startswith("portable_deck.core.")))):
                        violations.append(f"{path.name}:{node.lineno}: {name}")
        self.assertEqual(violations, [])

    def test_all_core_modules_and_public_queries_work_without_tkinter(self):
        script = dedent('''
            import importlib
            import pkgutil
            import sys
            import portable_deck.core as core

            for module in pkgutil.walk_packages(core.__path__, core.__name__ + '.'):
                importlib.import_module(module.name)

            from portable_deck.core.game import Game
            from portable_deck.core.chipoptions import build_chip_options
            from portable_deck.core.turnstart import build_turn_start_view
            from portable_deck.core.playersessionview import build_player_session_view
            from portable_deck.core.actionavailability import action_availability
            from portable_deck.core.deckpreview import build_deck_preview
            from portable_deck.core.interactions import build_interaction_options
            from portable_deck.core.pileoptions import discard_destinations, insertion_options
            from portable_deck.core.playerleaving import build_player_return_options
            from portable_deck.core.playerview import (
                build_player_hands_view, build_player_table_view,
                build_player_personal_piles_view, build_player_discard_view)
            from portable_deck.core.rulesoverview import build_rules_overview, format_rules_overview
            from portable_deck.core.selection import SelectionState
            from portable_deck.core.selectionsnapshot import build_selection_snapshot
            from portable_deck.core.sessionstatus import build_session_status
            from portable_deck.core.settingsvalidation import validate_settings

            validate_settings({})
            g = Game(2, 'decks/demodeck.json', score_enabled=True,
                     enable_target_score=True, target_score=10,
                     enable_score_warning=True, score_warning=7,
                     enable_chip_accounts=True, require_pot_withdrawal_confirmation=True)
            action_availability(g, 'draw_card')
            g.session.execute('draw_card')
            g.session.execute('play_chips', amount=5)
            g.session.execute('take_pot', player_index=0)
            g.session.execute('end_turn')
            g.pot_confirmation_notification()
            g.scores[0] = 7
            g.session.acknowledge_score_notifications(g.score_notifications())
            g.score_confirmation_notification()
            SelectionState().synchronize(build_selection_snapshot(g))
            build_deck_preview(g.deck)
            build_session_status(g)
            build_chip_options(g)
            build_player_session_view(g, 1)
            build_turn_start_view(g)
            format_rules_overview(build_rules_overview(g))
            for query in (build_player_hands_view, build_player_table_view,
                          build_player_personal_piles_view, build_player_discard_view):
                query(g, 1)
            build_interaction_options(g, 'give_card')
            build_player_return_options(g)
            discard_destinations(g, 1)
            insertion_options(g, 'draw')
            restarted = g.restart(keep_scores=True)
            assert not restarted.session.undo_availability().allowed
            assert isinstance(restarted.session.log_snapshot(), tuple)
            assert restarted.session.end_turn_availability().allowed
            assert not restarted.session.return_player_options().allowed
            assert restarted.pending_point_request is None
            assert restarted.pending_pot_withdrawal is None
            assert not any(name == 'tkinter' or name.startswith('tkinter.') for name in sys.modules)
            assert not any(name.startswith(('portable_deck.app', 'portable_deck.ui')) for name in sys.modules)
        ''')
        result = subprocess.run([sys.executable, '-B', '-c', script],
                                cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
