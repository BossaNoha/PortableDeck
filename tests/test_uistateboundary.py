"""Keep GUI code on the session's public log and Undo query APIs."""
import ast
import unittest
from pathlib import Path


REPLACEMENTS = {
    "game_log": "session.log_snapshot()",
    "gui_log": "session.log_snapshot()",
    "undo_stack": "session.undo_availability() / session.undo_result()",
}


def private_state_accesses(source):
    violations = []
    for node in ast.walk(ast.parse(source)):
        attribute = None
        if isinstance(node, ast.Attribute):
            attribute = node.attr
        elif isinstance(node, ast.Call):
            name = node.func.id if isinstance(node.func, ast.Name) else (
                node.func.attr if isinstance(node.func, ast.Attribute) else None)
            if (name in {"getattr", "setattr", "delattr", "hasattr"} and len(node.args) >= 2
                    and isinstance(node.args[1], ast.Constant)):
                attribute = node.args[1].value
        if isinstance(attribute, str) and attribute in REPLACEMENTS:
            violations.append(f"line {node.lineno}: {attribute}; use {REPLACEMENTS[attribute]}")
    return violations


class GUIStateBoundaryTests(unittest.TestCase):
    def test_gui_modules_do_not_access_mutable_log_or_undo_history(self):
        directory = Path(__file__).resolve().parents[1] / "portable_deck" / "ui"
        paths = sorted(directory.rglob("*.py"))
        self.assertTrue(paths)
        for path in paths:
            with self.subTest(module=path.name):
                self.assertEqual(private_state_accesses(path.read_text(encoding="utf-8")), [], str(path))

    def test_guard_detects_nested_reads_writes_and_literal_reflection(self):
        examples = (
            "def render():\n    return self.game.game_log",
            "model.gui_log = []",
            "del alias.undo_stack",
            "getattr(model, 'undo_stack', [])",
            "setattr(model, 'game_log', [])",
            "delattr(model, 'gui_log')",
            "hasattr(model, 'undo_stack')",
            "builtins.getattr(model, 'game_log')",
        )
        for source in examples:
            with self.subTest(source=source):
                violations = private_state_accesses(source)
                self.assertEqual(len(violations), 1)
                self.assertIn("use session.", violations[0])

    def test_guard_allows_client_flags_public_queries_and_text(self):
        source = """
# game.game_log and game.undo_stack must stay behind the controller.
show_game_log = True
if self.show_game_log:
    lines = self.session.log_snapshot()
allowed = self.session.undo_availability().allowed
result = self.session.undo_result()
message = 'game_log / gui_log / undo_stack'
"""
        self.assertEqual(private_state_accesses(source), [])
