"""Immutable card projections containing only identities visible to a player."""
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


def _validate_viewer(game, viewer):
    if (not isinstance(viewer, int) or isinstance(viewer, bool)
            or not 0 <= viewer < len(game.players)):
        raise ValueError("Choose a valid viewing player.")


def build_player_hands_view(game, viewer):
    """Project hands for an explicit player; hidden identities are never copied.

    This is a presentation query, not authentication of a remote caller.
    """
    _validate_viewer(game, viewer)
    hands = []
    for owner, player in enumerate(game.players):
        full = game.can_view_hand(viewer, owner)
        cards = tuple(CardView(i, card if full or i in player.revealed_indices else None,
                               i in player.revealed_indices)
                      for i, card in enumerate(player.hand))
        hands.append(HandView(owner, player.name, full, cards))
    return PlayerHandsView(viewer, game.players[viewer].name, tuple(hands))


@dataclass(frozen=True)
class TableCardView:
    index: int
    card: str | None
    player: str
    position: tuple[int, int]
    face_up: bool


@dataclass(frozen=True)
class PlayerTableView:
    viewer: int
    enabled: bool
    player_lanes: bool
    player_names: tuple[str, ...]
    cards: tuple[TableCardView, ...]
    available_positions: tuple[tuple[int, int], ...]


def build_player_table_view(game, viewer):
    """Hide face-down identities from every viewer, including their owner.

    Indices retain their model meaning even when cards share a position.
    A disabled table exposes no cards or targets.
    """
    _validate_viewer(game, viewer)
    cards = tuple(TableCardView(
        i, entry["card"] if entry.get("face_up", True) else None,
        entry["player"], tuple(entry.get("position", (0, i))), bool(entry.get("face_up", True)))
        for i, entry in enumerate(game.table_cards)) if game.enable_table else ()
    available = tuple(sorted(game.available_table_positions())) if game.enable_table else ()
    return PlayerTableView(viewer, game.enable_table, game.allow_play_in_front_of_players,
                           tuple(player.name for player in game.players), cards, available)
