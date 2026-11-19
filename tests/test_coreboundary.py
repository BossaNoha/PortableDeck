"""One architectural check for all core modules, including lazy query paths."""
import subprocess
import sys
import unittest
from pathlib import Path
from textwrap import dedent


class CoreBoundaryTests(unittest.TestCase):
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
            assert restarted.pending_point_request is None
            assert restarted.pending_pot_withdrawal is None
            assert not any(name == 'tkinter' or name.startswith('tkinter.') for name in sys.modules)
        ''')
        result = subprocess.run([sys.executable, '-B', '-c', script],
                                cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
