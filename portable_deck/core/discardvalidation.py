"""Resolve a valid discard destination before removing any source card."""


def discard_destination(game, pile_index, personal):
    if (not game.enable_discard_pile or not isinstance(personal, bool)
            or not isinstance(pile_index, int) or isinstance(pile_index, bool)):
        return None
    piles = game.personal_discard_piles[game.current_player_index] if personal else game.discard_piles
    return piles[pile_index] if 0 <= pile_index < len(piles) else None
