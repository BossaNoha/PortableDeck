import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from portable_deck.core.settingsschema import DEFAULT_SETTINGS
from portable_deck.core.settingsvalidation import validate_settings
from portable_deck.app.configurationinfo import preset_values
from portable_deck.app.settingspresets import read_preset, write_preset, preset_compatibility


class SettingsValidationTests(unittest.TestCase):
    def test_defaults_and_input_are_independent(self):
        original = copy.deepcopy(DEFAULT_SETTINGS)
        checked = validate_settings(original)
        checked['player_names'].append('Changed')
        self.assertEqual(original, DEFAULT_SETTINGS)

    def test_ranges_types_and_nested_data(self):
        for change in ({'num_players': True}, {'num_players': 21}, {'autosave_count': 0},
                       {'max_table_rows': 21}, {'shared_discard_pile_count': 0},
                       {'minimum_bet': 0}, {'starting_balance': -1},
                       {'cards_visibility': [{'players': 'wrong', 'teams': []}]},
                       {'personal_pile_settings': [[{'ordered': 'yes'}]]},
                       {'interaction_options': {'give_card': 'yes'}},
                       {'use_custom_player_names': True, 'player_names': ['Only one']},
                       {'enable_target_score': True, 'enable_score_warning': True,
                        'target_score': 10, 'score_warning': 10}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate_settings({**DEFAULT_SETTINGS, **change})

    def test_compatibility_excludes_app_settings_and_count(self):
        rules = preset_values(DEFAULT_SETTINGS)
        self.assertTrue(preset_compatibility(rules).compatible)
        rules.update(num_players=7, autosave_count=33)
        self.assertTrue(preset_compatibility(rules).compatible)
        del rules['enable_table']
        rules['future_option'] = True
        report = preset_compatibility(rules)
        self.assertEqual(report.missing, ('enable_table',))
        self.assertEqual(report.unknown, ('future_option',))

    def test_warning_and_safe_fallback_do_not_mutate_current_settings(self):
        current = copy.deepcopy(DEFAULT_SETTINGS)
        original = copy.deepcopy(current)
        rules = preset_values(DEFAULT_SETTINGS)
        del rules['enable_table']
        rules['future_option'] = True
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as folder:
            path = Path(folder) / 'Old.json'
            path.write_text(json.dumps({'settings': rules}), encoding='utf-8')
            warning = Mock()
            loaded = read_preset(path, current, on_warning=warning)
            warning.assert_called_once()
            self.assertIn('enable_table', warning.call_args.args[0])
            self.assertIn('future_option', warning.call_args.args[0])
            self.assertTrue(loaded['enable_table'])
            self.assertNotIn('future_option', loaded)
            self.assertEqual(current, original)

    def test_same_schema_is_silent_and_wrong_types_are_replaced_with_warning(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as folder:
            path = Path(folder) / 'Rules.json'
            write_preset(path, DEFAULT_SETTINGS)
            warning = Mock()
            read_preset(path, on_warning=warning)
            warning.assert_not_called()
            data = json.loads(path.read_text(encoding='utf-8'))
            data['settings']['enable_table'] = 'yes'
            path.write_text(json.dumps(data), encoding='utf-8')
            loaded = read_preset(path, on_warning=warning)
            self.assertTrue(loaded['enable_table'])
            warning.assert_called_once()
            self.assertIn('enable_table', warning.call_args.args[0])

    def test_form_and_preset_report_same_validation_error(self):
        from portable_deck.app.settingswindow import SettingsWindow
        window = SettingsWindow(SimpleNamespace(root=None, settings=copy.deepcopy(DEFAULT_SETTINGS)))
        variable = lambda value: SimpleNamespace(get=lambda: value)
        panel = SimpleNamespace(values=lambda: {'starting_balance': -1})
        basic = SimpleNamespace(values=lambda: {})
        with patch('portable_deck.app.settingswindow.messagebox.showerror') as error:
            window.save_form(variable('3'), variable('5'), variable('decks/demodeck.json'),
                             variable(False), [], panel, basic)
        with self.assertRaises(ValueError) as caught:
            validate_settings({**DEFAULT_SETTINGS, 'starting_balance': -1})
        self.assertEqual(error.call_args.args[1], str(caught.exception))

    def test_validator_imports_no_tkinter(self):
        script = "from portable_deck.core.settingsvalidation import validate_settings; import sys; validate_settings({}); assert 'tkinter' not in sys.modules"
        result = subprocess.run([sys.executable, '-B', '-c', script], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_nested_unknown_interaction_is_reported(self):
        rules = preset_values(DEFAULT_SETTINGS)
        rules['interaction_options'] = {'give_card': True, 'future_action': False}
        report = preset_compatibility(rules)
        self.assertIn('interaction_options.future_action', report.unknown)

    def test_team_validation_is_available_without_gui(self):
        for change in ({'team_count': 4}, {'team_names': ['']},
                       {'player_teams': ['missing', None, None]},
                       {'dealer_players': [True]}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate_settings({**DEFAULT_SETTINGS, **change})

    def test_invalid_values_are_skipped_without_losing_valid_settings(self):
        rules = preset_values(DEFAULT_SETTINGS)
        rules.update(starting_balance=-1, enable_table=False,
                     enable_chip_accounts=True, minimum_bet=7,
                     enable_target_score=True, target_score=10,
                     enable_score_warning=True, score_warning=30,
                     cards_visibility=[{'players': 'wrong', 'teams': []}],
                     personal_pile_settings=[[{'access': 'invalid'}]],
                     team_count=-1, team_names=[''],
                     deck_path='missing-deck.json')
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as folder:
            path = Path(folder) / 'Broken.json'
            path.write_text(json.dumps({'settings': rules}), encoding='utf-8')
            original = path.read_bytes()
            warning = Mock()
            loaded = read_preset(path, on_warning=warning)
            warning.assert_called_once()
            text = warning.call_args.args[0]
            for key in ('starting_balance', 'score_warning', 'cards_visibility',
                        'personal_pile_settings', 'team_count', 'team_names', 'deck_path'):
                self.assertIn(key, text)
            self.assertFalse(loaded['enable_table'])
            self.assertTrue(loaded['enable_chip_accounts'])
            self.assertEqual(loaded['minimum_bet'], 7)
            self.assertEqual(loaded['target_score'], 10)
            self.assertLess(loaded['score_warning'], 10)
            self.assertEqual(loaded['starting_balance'], DEFAULT_SETTINGS['starting_balance'])
            validate_settings(loaded)
            self.assertEqual(path.read_bytes(), original)

    def test_malformed_json_still_cannot_be_loaded(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as folder:
            path = Path(folder) / 'Malformed.json'
            path.write_text('{broken', encoding='utf-8')
            with self.assertRaises(ValueError):
                read_preset(path)
