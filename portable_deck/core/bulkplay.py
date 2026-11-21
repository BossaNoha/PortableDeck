"""Atomic hand-to-table batch placement, independent of clients."""
import copy

from .actionavailability import action_availability
from .actionerrors import ActionValidationError
from .cardselection import batch_hand_indices


def play_cards(game, indices):
    available = action_availability(game, "play_cards")
    if not available.allowed:
        raise ActionValidationError(available.code, available.reason)
    indices = batch_hand_indices(game, indices)
    # Position queries only need a private table list. Plan every destination
    # before touching the real hand, table, log or revealed-card indices.
    planner = copy.copy(game)
    planner.table_cards = copy.deepcopy(game.table_cards)
    positions = []
    for _ in indices:
        position = planner.default_table_position()
        if position is None or position not in planner.available_table_positions():
            raise ActionValidationError("table_full", "The table has insufficient space for all selected cards.")
        positions.append(position)
        planner.table_cards.append({"position": list(position)})
    cards = []
    for offset, (index, position) in enumerate(zip(indices, positions)):
        card = game.play_to_table(index - offset + 1, position)
        if card is None:
            raise ActionValidationError("action_rejected", "The selected cards could not be played.")
        cards.append(card)
    return tuple(cards)
