"""Named session draw piles, with one canonical default draw order."""
from dataclasses import dataclass
from .drawpile import DrawPile
from .actionerrors import ActionValidationError


DRAW_SOURCE_ACTIONS = frozenset({"draw_card", "draw_cards", "shuffle_draw_deck", "deal_cards", "start_shared_offer", "insert_draw_deck"})


def uses_draw_source(game, action):
    return action in DRAW_SOURCE_ACTIONS or (action == "play_card" and not game.enable_table)


def draw_pile_options(game):
    if game.current_player_index not in game.active_player_indices():
        return ()
    return tuple(pile for pile in game.draw_piles.view() if pile.owner in (None, game.current_player_index))


def resolve_draw_pile(game, pile_id="main"):
    if not isinstance(pile_id, str) or not any(pile.id == pile_id for pile in game.draw_piles.view()):
        raise ActionValidationError("invalid_draw_pile", "Choose an existing draw pile.")
    if not any(pile.id == pile_id for pile in draw_pile_options(game)):
        raise ActionValidationError("access_denied", "This draw pile belongs to another player.")
    return game.draw_piles.get(pile_id)


@dataclass(frozen=True)
class DrawPileInfo:
    id: str
    name: str
    owner: int | None
    card_count: int


class DrawPiles:
    DEFAULT_ID = "main"

    def __init__(self, default_pile, player_count):
        self.player_count = player_count
        self._piles = {self.DEFAULT_ID: default_pile}
        self._metadata = {self.DEFAULT_ID: ("Draw deck", None)}

    def _validate_metadata(self, pile_id, name, owner):
        if not isinstance(pile_id, str) or not pile_id.strip() or pile_id != pile_id.strip():
            raise ValueError("Draw pile ID must be nonempty text without surrounding whitespace.")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Draw pile name must be nonempty text.")
        if owner is not None and (type(owner) is not int or not 0 <= owner < self.player_count):
            raise ValueError("Draw pile owner must be an existing player or null.")

    def add(self, pile_id, name, cards=(), *, owner=None):
        """Register an independent pile; this does not create or move game cards."""
        self._validate_metadata(pile_id, name, owner)
        if pile_id in self._piles:
            raise ValueError("Draw pile ID already exists.")
        if not isinstance(cards, (list, tuple)) or any(not isinstance(card, str) or not card for card in cards):
            raise ValueError("Draw pile cards must be a list of nonempty card names.")
        pile = DrawPile(cards)
        self._piles[pile_id] = pile
        self._metadata[pile_id] = (name, owner)
        return pile

    def get(self, pile_id=DEFAULT_ID):
        return self._piles[pile_id]

    def view(self):
        """Public metadata only: never expose identities or draw order."""
        return tuple(DrawPileInfo(pile_id, *self._metadata[pile_id], len(pile.cards))
                     for pile_id, pile in self._piles.items())

    def snapshot(self):
        """Default contents remain solely in the legacy remaining_deck field."""
        result = []
        for pile_id, pile in self._piles.items():
            name, owner = self._metadata[pile_id]
            entry = {"id": pile_id, "name": name, "owner": owner}
            if pile_id != self.DEFAULT_ID:
                entry["cards"] = list(pile.cards)
            result.append(entry)
        return result

    def restore(self, state):
        """Validate all metadata/content before replacing the registry."""
        if not isinstance(state, list) or not state:
            raise ValueError("Saved draw piles must be a nonempty list.")
        restored = DrawPiles(self.get(), self.player_count)
        seen = set()
        for entry in state:
            if not isinstance(entry, dict):
                raise ValueError("Each saved draw pile must be an object.")
            pile_id = entry.get("id")
            restored._validate_metadata(pile_id, entry.get("name"), entry.get("owner"))
            if pile_id in seen:
                raise ValueError("Duplicate saved draw pile ID.")
            seen.add(pile_id)
            expected = {"id", "name", "owner"} | ({"cards"} if pile_id != self.DEFAULT_ID else set())
            if set(entry) != expected:
                raise ValueError("Invalid saved draw pile fields.")
            if pile_id == self.DEFAULT_ID:
                if entry["owner"] is not None:
                    raise ValueError("The default draw pile must remain shared.")
                restored._metadata[pile_id] = (entry["name"], None)
            else:
                restored.add(pile_id, entry["name"], entry["cards"], owner=entry["owner"])
        if self.DEFAULT_ID not in seen:
            raise ValueError("Saved draw piles must include the default pile.")
        self._piles, self._metadata = restored._piles, restored._metadata
