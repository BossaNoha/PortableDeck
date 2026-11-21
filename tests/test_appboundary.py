"""Prevent extracted application services from depending on desktop widgets."""
import ast
import importlib.util
import json
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


# Explicit scope: the app package also contains Tk clients, which are permitted
# to depend on services. New extracted services should be added here.
SERVICES = frozenset((
    "checkpoints", "configurationinfo", "deckcatalog", "deckcheck", "deckfiles",
    "deckstorage", "discardstorage", "namedsaves", "newgame", "sessioncatalog",
    "sessionfiles", "sessionstorage", "sessionview", "settings",
    "settingsapplication", "settingspresets",
    "turnhandoff",
))
ROOT = Path(__file__).resolve().parents[1]


def forbidden_dependency(name):
    if name == "tkinter" or name.startswith("tkinter."):
        return True
    if name == "portable_deck.ui" or name.startswith("portable_deck.ui."):
        return True
    if name.startswith("portable_deck.app."):
        return name.split(".")[2] not in SERVICES
    return False


def import_violations(source, module):
    violations = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            dependencies = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                base = importlib.util.resolve_name("." * node.level + base, module.rpartition(".")[0])
            dependencies = [base] + [f"{base}.{alias.name}" for alias in node.names]
        else:
            continue
        violations.extend((node.lineno, name) for name in dependencies if forbidden_dependency(name))
    return violations


class ApplicationBoundaryTests(unittest.TestCase):
    def test_service_imports_exclude_tkinter_and_gui_even_inside_functions(self):
        for service in sorted(SERVICES):
            with self.subTest(service=service):
                path = ROOT / "portable_deck" / "app" / f"{service}.py"
                self.assertEqual(import_violations(path.read_text(encoding="utf-8"),
                                                  f"portable_deck.app.{service}"), [], str(path))

    def test_guard_recognizes_relative_absolute_and_deferred_gui_imports(self):
        source = """
from .settings import DEFAULT_SETTINGS
from ..core.game import Game
def deferred():
    import tkinter as tk
    from .settingswindow import SettingsWindow
    from .. import ui
    from portable_deck.app import decklibrary as library
"""
        violations = import_violations(source, "portable_deck.app.newgame")
        self.assertEqual({name for _, name in violations}, {
            "tkinter", "portable_deck.app.settingswindow", "portable_deck.app.settingswindow.SettingsWindow",
            "portable_deck.ui", "portable_deck.app.decklibrary",
        })

    def test_all_services_import_with_gui_dependencies_blocked_in_clean_process(self):
        script = textwrap.dedent("""
            import importlib
            import importlib.abc
            import json
            import sys
            sys.path.insert(0, sys.argv[1])
            services = set(json.loads(sys.argv[2]))
            attempted = []
            def forbidden(name):
                return (name == 'tkinter' or name.startswith('tkinter.')
                        or name == 'portable_deck.ui' or name.startswith('portable_deck.ui.')
                        or (name.startswith('portable_deck.app.') and name.split('.')[2] not in services))
            class BlockGUI(importlib.abc.MetaPathFinder):
                def find_spec(self, fullname, path=None, target=None):
                    if forbidden(fullname):
                        attempted.append(fullname)
                        raise ImportError('Application service requested GUI: ' + fullname)
            sys.meta_path.insert(0, BlockGUI())
            for name in sorted(services):
                importlib.import_module('portable_deck.app.' + name)
            assert not attempted, attempted
            assert not [name for name in sys.modules if forbidden(name)]
        """)
        with tempfile.TemporaryDirectory() as folder:
            result = subprocess.run([sys.executable, "-B", "-c", script, str(ROOT), json.dumps(sorted(SERVICES))],
                                    cwd=folder, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(list(Path(folder).iterdir()), [])
