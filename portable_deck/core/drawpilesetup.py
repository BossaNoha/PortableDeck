"""Validated initial distribution and independent embedded card sets."""
from .deckdefinition import DeckDefinition
from .drawpile import DrawPile


def normalize_draw_pile_setup(setup, player_count):
    if not isinstance(setup, list):
        raise ValueError("Draw pile setup must be a list.")
    result, seen = [], {"main"}
    for entry in setup:
        if not isinstance(entry, dict) or set(entry) not in (
                {"id", "name", "owner", "count"},
                {"id", "name", "owner", "count", "mode", "definition"}):
            raise ValueError("Each draw pile needs id, name, owner and count.")
        pile_id, name, owner, count = (entry[key] for key in ("id", "name", "owner", "count"))
        if not isinstance(pile_id, str) or not pile_id.strip() or pile_id != pile_id.strip() or pile_id in seen:
            raise ValueError("Draw pile IDs must be unique, nonempty, and different from main.")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Draw pile names must be nonempty text.")
        if owner is not None and (type(owner) is not int or not 0 <= owner < player_count):
            raise ValueError("Choose an existing draw pile owner or Shared.")
        if type(count) is not int or count < 0:
            raise ValueError("Initial draw pile counts must be nonnegative whole numbers.")
        normalized = dict(entry)
        if "mode" in entry:
            if entry["mode"] != "independent":
                raise ValueError("Unknown draw pile setup mode.")
            definition = DeckDefinition.from_data(entry["definition"])
            if count != len(definition.expanded_cards()):
                raise ValueError("Independent pile count must match its complete card set.")
            normalized["definition"] = definition.to_data()
        seen.add(pile_id)
        result.append(normalized)
    return result


def populate_draw_piles(game):
    for entry in game.draw_pile_setup if game.enable_draw_pile_setup else ():
        count = entry["count"]
        if entry.get("mode") == "independent":
            pile = DrawPile(DeckDefinition.from_data(entry["definition"]).expanded_cards())
            pile.shuffle()
            cards = pile.cards
        else:
            cards = game.deck.flat_deck[:count]
            del game.deck.flat_deck[:count]
        game.draw_piles.add(entry["id"], entry["name"], cards, owner=entry["owner"])


def normalize_hand_sources(enabled, sources, player_count):
    if type(enabled) is not bool:
        raise ValueError("deal_starting_hands_from_piles must be true or false")
    if not isinstance(sources, list) or any(not isinstance(source, str) or not source for source in sources):
        raise ValueError("Initial hand sources must be a list of draw pile IDs.")
    if enabled and len(sources) != player_count:
        raise ValueError("Choose one starting hand source per player.")
    return list(sources)


def starting_card_requirement(game, hand_size):
    setup = game.draw_pile_setup if game.enable_draw_pile_setup else []
    total = sum(entry["count"] for entry in setup if entry.get("mode") != "independent")
    if not game.deal_starting_hands_from_piles:
        return total + len(game.players) * hand_size
    sources = normalize_hand_sources(True, game.initial_hand_sources, len(game.players))
    entries = {entry["id"]: entry for entry in setup}
    demand = {}
    for player, source in enumerate(sources):
        if source != "main":
            if source not in entries:
                raise ValueError(f"Unknown starting hand source: {source}")
            if entries[source]["owner"] not in (None, player):
                raise ValueError("Players may only start from shared or their own draw piles.")
        demand[source] = demand.get(source, 0) + hand_size
    for source, count in demand.items():
        if source != "main" and count > entries[source]["count"]:
            raise ValueError(f"Draw pile {source} cannot supply all requested starting hands.")
    return total + demand.get("main", 0)
