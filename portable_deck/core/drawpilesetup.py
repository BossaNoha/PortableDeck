"""Validated initial distribution from one shuffled card set."""


def normalize_draw_pile_setup(setup, player_count):
    if not isinstance(setup, list):
        raise ValueError("Draw pile setup must be a list.")
    result, seen = [], {"main"}
    for entry in setup:
        if not isinstance(entry, dict) or set(entry) != {"id", "name", "owner", "count"}:
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
        seen.add(pile_id)
        result.append(dict(entry))
    return result


def populate_draw_piles(game):
    for entry in game.draw_pile_setup if game.enable_draw_pile_setup else ():
        count = entry["count"]
        cards = game.deck.flat_deck[:count]
        game.draw_piles.add(entry["id"], entry["name"], cards, owner=entry["owner"])
        del game.deck.flat_deck[:count]
