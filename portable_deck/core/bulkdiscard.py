"""Atomic batches from the current hand to one discard destination."""
from .actionavailability import action_availability
from .actionerrors import ActionValidationError
from .cardselection import batch_hand_indices, batch_indices
from .discardvalidation import discard_destination


def discard_cards(game, indices, pile_index=0, personal=False):
    available = action_availability(game, "discard_cards")
    if not available.allowed:
        raise ActionValidationError(available.code, available.reason)
    indices = batch_hand_indices(game, indices)
    if discard_destination(game, pile_index, personal) is None:
        raise ActionValidationError("invalid_pile", "Choose a valid discard destination.")
    cards = []
    for offset, index in enumerate(indices):
        card = game.discard_from_current(index - offset + 1, pile_index, personal)
        if card is None:
            raise ActionValidationError("action_rejected", "The selected cards could not be discarded.")
        cards.append(card)
    return tuple(cards)


def discard_table_cards(game, indices, pile_index=0, personal=False):
    available = action_availability(game, "discard_table_cards")
    if not available.allowed:
        raise ActionValidationError(available.code, available.reason)
    indices = batch_indices(indices, len(game.table_cards), "table")
    if discard_destination(game, pile_index, personal) is None:
        raise ActionValidationError("invalid_pile", "Choose a valid discard destination.")
    cards = []
    for offset, index in enumerate(indices):
        card = game.move_table_card_to_discard(index - offset, pile_index, personal)
        if card is None:
            raise ActionValidationError("action_rejected", "The selected table cards could not be discarded.")
        cards.append(card)
    return tuple(cards)
