"""Validate batch hand indices before any card is removed."""
from .actionerrors import ActionValidationError


def batch_hand_indices(game, indices):
    hand = game.players[game.current_player_index].hand
    if (not isinstance(indices, (list, tuple)) or len(indices) < 2
            or any(type(index) is not int or not 0 <= index < len(hand) for index in indices)
            or len(set(indices)) != len(indices)):
        raise ActionValidationError("invalid_selection", "Choose at least two distinct available hand cards.")
    return sorted(indices)
