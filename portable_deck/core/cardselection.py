"""Validate batch indices before any card is removed."""
from .actionerrors import ActionValidationError


def batch_hand_indices(game, indices):
    hand = game.players[game.current_player_index].hand
    return batch_indices(indices, len(hand), "hand")


def batch_indices(indices, count, source):
    if (not isinstance(indices, (list, tuple)) or len(indices) < 2
            or any(type(index) is not int or not 0 <= index < count for index in indices)
            or len(set(indices)) != len(indices)):
        raise ActionValidationError("invalid_selection", f"Choose at least two distinct available {source} cards.")
    return sorted(indices)
