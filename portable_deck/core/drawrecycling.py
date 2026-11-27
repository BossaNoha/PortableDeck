"""Explicit discard-to-draw associations and execution-time resolution."""
from .actionerrors import ActionValidationError
from .drawpiles import resolve_draw_pile


def normalize_recycling(links, setup, shared_count, personal_count):
    if not isinstance(links, dict):
        raise ValueError("Draw pile recycling links must be an object.")
    owners = {"main": None, **{entry["id"]: entry["owner"] for entry in setup}}
    result = {}
    for pile_id, link in links.items():
        if not isinstance(pile_id, str) or pile_id not in owners:
            raise ValueError("Recycling links must refer to main or a configured draw pile.")
        if (not isinstance(link, dict) or set(link) not in ({"personal", "pile_index"}, {"personal", "pile_index", "automatic"})
                or type(link["personal"]) is not bool or type(link["pile_index"]) is not int):
            raise ValueError("Each recycling link needs personal and pile_index.")
        if type(link.get("automatic", False)) is not bool:
            raise ValueError("Automatic recycling must be true or false.")
        count = personal_count if link["personal"] else shared_count
        if not 0 <= link["pile_index"] < count:
            raise ValueError("Recycling link refers to an unavailable discard pile.")
        if link["personal"] and owners[pile_id] is None:
            raise ValueError("Personal discards require a draw pile owned by that player.")
        result[pile_id] = dict(link)
    return result


def recycling_sources(game, pile_id="main"):
    resolve_draw_pile(game, pile_id)
    if not game.enable_linked_recycling:
        if pile_id != "main":
            raise ActionValidationError("linked_recycling_disabled", "Enable linked recycling for named draw piles.")
        return tuple(game.all_discard_piles())
    link = game.draw_pile_recycling.get(pile_id)
    if link is None:
        raise ActionValidationError("no_discard_link", "This draw pile has no assigned discard pile.")
    owner = next(pile.owner for pile in game.draw_piles.view() if pile.id == pile_id)
    if link["personal"]:
        if owner is None or owner != game.current_player_index:
            raise ActionValidationError("access_denied", "Only the owner may recycle this personal discard.")
        piles = game.personal_discard_piles[owner]
        name = f"{game.players[owner].name}'s discard"
    else:
        piles, name = game.discard_piles, "Shared discard"
    index = link["pile_index"]
    if not 0 <= index < len(piles):
        raise ActionValidationError("invalid_pile", "The assigned discard pile is unavailable.")
    return ((f"{name} {index + 1}", piles[index]),)


def draw_capacity(game, pile_id="main"):
    pile = resolve_draw_pile(game, pile_id)
    total = len(pile.cards)
    link = game.draw_pile_recycling.get(pile_id, {})
    if (game.enable_linked_recycling and game.enable_discard_pile
            and game.allow_recycle_discard_to_deck and link.get("automatic", False)):
        total += sum(len(cards) for _, cards in recycling_sources(game, pile_id))
    return total
