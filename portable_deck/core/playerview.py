"""Immutable hand projections containing only cards visible to a given player."""
from dataclasses import dataclass


@dataclass(frozen=True)
class CardView:
    index: int
    card: str | None
    revealed: bool


@dataclass(frozen=True)
class HandView:
    owner: int
    name: str
    fully_visible: bool
    cards: tuple[CardView, ...]

    @property
    def visible(self):
        return self.fully_visible or any(slot.card is not None for slot in self.cards)


@dataclass(frozen=True)
class PlayerHandsView:
    viewer: int
    viewer_name: str
    hands: tuple[HandView, ...]


def build_player_hands_view(game, viewer):
    """Project hands for an explicit player; hidden identities are never copied.

    This is a presentation query, not authentication of a remote caller.
    """
    if (not isinstance(viewer, int) or isinstance(viewer, bool)
            or not 0 <= viewer < len(game.players)):
        raise ValueError("Choose a valid viewing player.")
    hands = []
    for owner, player in enumerate(game.players):
        full = game.can_view_hand(viewer, owner)
        cards = tuple(CardView(i, card if full or i in player.revealed_indices else None,
                               i in player.revealed_indices)
                      for i, card in enumerate(player.hand))
        hands.append(HandView(owner, player.name, full, cards))
    return PlayerHandsView(viewer, game.players[viewer].name, tuple(hands))
