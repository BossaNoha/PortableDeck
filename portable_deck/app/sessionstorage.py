"""JSON session files, atomic writes and legacy external-deck resolution."""
import json
import os

from ..core.deck import Deck
from ..core.gamesession import export_session, restore_session


def save_session(game, path, *, client_state=None):
    state = export_session(game)
    if client_state is not None:
        state["client_state"] = client_state
    path = os.fspath(path)
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    temporary_path = path + ".tmp"
    try:
        with open(temporary_path, "w", encoding="utf-8") as session_file:
            json.dump(state, session_file, indent=2)
        os.replace(temporary_path, path)
    except Exception:
        if os.path.exists(temporary_path):
            os.remove(temporary_path)
        raise


def load_session(game_class, path):
    with open(path, "r", encoding="utf-8") as session_file:
        state = json.load(session_file)
    if "deck_types" not in state and "deck_cards" not in state:
        deck = Deck(state["deck_path"])
        state["deck_types"] = deck.types
        state["deck_cards"] = deck.cards
    game = restore_session(game_class, state)
    if os.path.basename(path).lower() != "last_session.json" and os.path.basename(os.path.dirname(os.path.abspath(path))).lower() != "autosaves":
        game.named_save_path = os.path.abspath(path)
    return game
