"""Persist the shared discard pile independently of desktop widgets."""
import json
import os


def save_discard_pile(game, path):
    """Write the existing discard-list format; propagate filesystem errors."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as destination:
        json.dump(game.discard_pile, destination, indent=2)
