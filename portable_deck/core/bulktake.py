"""Atomic transfer from the shared table to the current hand."""
from .actionavailability import action_availability
from .actionerrors import ActionValidationError
from .cardselection import batch_indices


def take_table_cards(game, indices):
    available = action_availability(game, "take_table_cards")
    if not available.allowed:
        raise ActionValidationError(available.code, available.reason)
    indices = batch_indices(indices, len(game.table_cards), "table")
    cards = []
    for offset, index in enumerate(indices):
        card = game.take_from_table(index - offset)
        if card is None:
            raise ActionValidationError("action_rejected", "The selected table cards could not be taken.")
        cards.append(card)
    return tuple(cards)
