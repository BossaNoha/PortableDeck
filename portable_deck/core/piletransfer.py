"""Whole personal-pile transfers and immutable client choices."""
from dataclasses import dataclass
from .actionerrors import ActionValidationError


@dataclass(frozen=True)
class TransferPile:
    owner: int
    pile_index: int
    name: str
    card_count: int


def accessible_pile_options(game):
    return tuple(TransferPile(owner, index, f"{player.name} — Pile {index + 1}", len(cards))
                    for owner, player in enumerate(game.players)
                    for index, cards in enumerate(game.personal_piles[owner])
                    if game.can_access_personal_pile(owner, index))


def transfer_pile_options(game):
    choices = accessible_pile_options(game)
    targets = tuple(pile for pile in choices if pile.owner not in game.left_players)
    sources = tuple(pile for pile in choices if pile.card_count and any(
        (pile.owner, pile.pile_index) != (target.owner, target.pile_index) for target in targets))
    return sources, targets


def transfer_personal_pile(game, source_owner, source_pile, target_owner, target_pile):
    from .actionavailability import action_availability
    available = action_availability(game, "transfer_personal_pile")
    if not available.allowed:
        raise ActionValidationError(available.code, available.reason)
    for owner, index in ((source_owner, source_pile), (target_owner, target_pile)):
        if (type(owner) is not int or type(index) is not int or not 0 <= owner < len(game.players)
                or not 0 <= index < len(game.personal_piles[owner])):
            raise ActionValidationError("invalid_pile", "Choose valid source and destination piles.")
        if not game.can_access_personal_pile(owner, index):
            raise ActionValidationError("access_denied", "You need access to both personal piles.")
    if (source_owner, source_pile) == (target_owner, target_pile):
        raise ActionValidationError("same_pile", "Choose a different destination pile.")
    if target_owner in game.left_players:
        raise ActionValidationError("target_left", "The destination player has left the session.")
    source = game.personal_piles[source_owner][source_pile]
    target = game.personal_piles[target_owner][target_pile]
    if not source:
        raise ActionValidationError("empty_pile", "The source pile is empty.")
    rule = game.personal_pile_settings[target_owner][target_pile]
    merged = (source + target if rule["ordered"] and rule["order_by"] == "time"
              and rule["new_card"] == "bottom" else target + source)
    if rule["ordered"] and rule["order_by"] == "size":
        ordered = sorted(merged, key=game.personal_card_sort_key, reverse=rule["size_order"] == "down")
        if merged != ordered:
            raise ActionValidationError("ordering_conflict", "This transfer would break the destination's size order.")
    count = len(source)
    target[:] = merged
    source.clear()
    game.log_action(game.players[game.current_player_index].name, "transfer_personal_pile", count=count,
                    source=game.players[source_owner].name, source_pile=source_pile + 1,
                    target=game.players[target_owner].name, target_pile=target_pile + 1)
    return count
