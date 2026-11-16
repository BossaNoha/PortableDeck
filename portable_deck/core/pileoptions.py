"""Immutable pile destinations and insertion ranges without card identities."""
from dataclasses import dataclass
from .playerview import _validate_viewer


@dataclass(frozen=True)
class DiscardDestination:
    name: str
    pile_index: int
    personal: bool


def discard_destinations(game, viewer):
    """List shared piles and this player's personal discard destinations."""
    _validate_viewer(game, viewer)
    if not game.enable_discard_pile:
        return ()
    return tuple(
        [DiscardDestination(f"Shared discard {i + 1}", i, False)
         for i in range(len(game.discard_piles))]
        + [DiscardDestination(f"Your personal discard {i + 1}", i, True)
           for i in range(len(game.personal_discard_piles[viewer]))])


@dataclass(frozen=True)
class InsertionOption:
    destination: str
    pile_index: int
    card_count: int
    positions_from_end: int
    random_middle_available: bool


def insertion_options(game, destination):
    """Describe enabled insertion targets; actual commands revalidate input."""
    if destination not in {"draw", "discard"}:
        raise ValueError("Choose draw or discard as the destination.")
    if not game.enable_special_actions:
        return ()
    if destination == "draw":
        counts = [len(game.deck.flat_deck)] if game.allow_insert_draw_deck else []
    else:
        counts = ([len(pile) for pile in game.discard_piles]
                  if game.allow_insert_discard_pile and game.enable_discard_pile else [])
    return tuple(InsertionOption(destination, i, count, min(10, count + 1), count >= 20)
                 for i, count in enumerate(counts))
