import subprocess
import sys
import unittest
from dataclasses import FrozenInstanceError, asdict
from pathlib import Path

from portable_deck.core.game import Game
from portable_deck.core.rulesoverview import (
    build_rules_overview, configuration_summary, format_rules_overview,
    session_rule_sections,
)


class RulesOverviewTests(unittest.TestCase):
    def game(self, **options):
        return Game(3, str(Path(__file__).resolve().parents[1] / 'decks/demodeck.json'), **options)

    def test_disabled_sections_and_typed_values(self):
        game = self.game(enable_table=False, enable_discard_pile=False)
        overview = build_rules_overview(game)
        self.assertEqual([section.key for section in overview.sections], ['game'])
        players = overview.sections[0].entries[0]
        self.assertEqual(players.key, 'players')
        self.assertIs(type(players.value), int)
        self.assertEqual(players.value, 3)
        self.assertEqual(asdict(overview)['sections'][0]['title'], 'Game')

    def test_effective_rules_and_feature_dependencies(self):
        game = self.game(score_enabled=True, enable_target_score=True, target_score=50,
                         enable_score_warning=True, score_warning=40,
                         enable_chip_accounts=False, enable_interactions=True,
                         interaction_options={'give_card': True, 'steal_chips': True},
                         enable_table_limits=True, limit_table_rows=True,
                         limit_table_columns=False, max_table_rows=4)
        sections = {section.key: section for section in build_rules_overview(game).sections}
        score = {entry.key: entry.value for entry in sections['scoring'].entries}
        self.assertEqual(score['target_score'], 50)
        self.assertEqual(score['score_warning'], 40)
        self.assertNotIn('chips', sections)
        self.assertEqual([entry.key for entry in sections['interactions'].entries], ['give_card'])
        table = {entry.key: entry.value for entry in sections['table'].entries}
        self.assertEqual(table['max_table_rows'], 4)
        self.assertNotIn('max_table_columns', table)

    def test_named_teams_personal_piles_and_visibility(self):
        game = self.game(player_names=['Alice', 'Bob', 'Carol'], enable_roles_teams=True,
            enable_teams=True, enable_dealer=True, team_count=2, team_names=['Red'],
            player_teams=['team_1', 'team_1', None], dealer_players=[False, False, True],
            enable_personal_piles=True, enable_cards_visibility=True,
            cards_visibility=[{'players': [0], 'teams': ['team_1']},
                              {'players': [1], 'teams': []}, {'players': [2], 'teams': []}])
        overview = build_rules_overview(game)
        sections = {section.key: section for section in overview.sections}
        self.assertEqual(sections['roles_teams'].entries[0].label, 'Dealer')
        self.assertEqual(sections['roles_teams'].entries[0].value, ('Carol',))
        self.assertEqual(sections['roles_teams'].entries[1].value, ('Alice', 'Bob'))
        self.assertIn('Alice / Pile 1', format_rules_overview(overview))
        self.assertEqual(sections['visibility'].entries[0].value, ('Alice', 'Red'))

    def test_snapshot_is_independent_and_read_only(self):
        game = self.game(score_enabled=True, enable_target_score=True, target_score=50)
        game.configuration_info = {'name': 'Friday', 'modified': True}
        game.players[0].hand = ['PRIVATE CARD']
        before = game.capture_undo_state()
        overview = build_rules_overview(game)
        text = format_rules_overview(overview)
        self.assertEqual(before, game.capture_undo_state())
        self.assertNotIn('PRIVATE CARD', text)
        self.assertIn('Configuration: Friday', text)
        self.assertIn('Modified preset: Yes', text)
        game.target_score = 100
        game.configuration_info['name'] = 'Changed'
        self.assertEqual(format_rules_overview(overview), text)
        with self.assertRaises(FrozenInstanceError):
            overview.configuration_name = 'Other'

    def test_unknown_preset_metadata_and_compatibility_adapter(self):
        game = self.game()
        overview = build_rules_overview(game)
        self.assertIn('Modified preset: Unknown', configuration_summary(overview))
        sections = session_rule_sections(game)
        self.assertEqual(sections[0], ('Game', ['Players: 3', 'Deck: demodeck.json',
                                              'Starting hand: 0 cards per player']))

    def test_cli_works_without_tkinter(self):
        script = "from portable_deck.core.game import Game; from portable_deck.core.rulesoverview import build_rules_overview, format_rules_overview; import sys; g=Game(2,'decks/demodeck.json'); print(format_rules_overview(build_rules_overview(g))); assert 'tkinter' not in sys.modules"
        result = subprocess.run([sys.executable, '-B', '-c', script],
            cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Players: 2', result.stdout)
