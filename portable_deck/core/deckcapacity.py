"""Shared starting-hand limits and deck-capacity calculation."""
from dataclasses import dataclass


class DealInputError(ValueError):
    def __init__(self, message, field):
        super().__init__(message)
        self.field = field


def validate_deal_counts(players, cards_per_player):
    if not isinstance(players, int) or isinstance(players, bool) or not 1 <= players <= 20:
        raise DealInputError("Player count must be between 1 and 20.", "num_players")
    if (not isinstance(cards_per_player, int) or isinstance(cards_per_player, bool)
            or cards_per_player < 0):
        raise DealInputError("Starting hand size must be non-negative.", "cards_per_player")


@dataclass(frozen=True)
class DeckCapacity:
    players: int
    cards_per_player: int
    available: int
    required: int

    @property
    def sufficient(self):
        return self.required <= self.available


def deck_capacity(deck, players, cards_per_player):
    validate_deal_counts(players, cards_per_player)
    return DeckCapacity(players, cards_per_player, len(deck.flat_deck), players * cards_per_player)
