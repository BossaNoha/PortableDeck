"""Check a new-game deck and starting-hand capacity without widgets."""
import os

from ..core.deck import Deck
from ..core.deckcapacity import deck_capacity, validate_deal_counts
from .settings import resolve_deck_path


def check_deck(path, players, cards_per_player):
    validate_deal_counts(players, cards_per_player)
    path = os.fspath(path).strip()
    if not path:
        raise ValueError("Choose a deck file first.")
    return deck_capacity(Deck(resolve_deck_path(path)), players, cards_per_player)
