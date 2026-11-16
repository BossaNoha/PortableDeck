"""Opaque, transient collection markers for client selection synchronization."""
import copy
from dataclasses import dataclass
from uuid import uuid4


@dataclass(frozen=True)
class SelectionSnapshot:
    session: str
    owner: int
    hand_revision: str
    table_revision: str
    hand_count: int
    table_count: int


class _CollectionMarkers:
    """Private core cache; never serialized or sent to a client."""
    def __init__(self):
        self.session = uuid4().hex
        self.hands = {}
        self.table = None

    @staticmethod
    def updated(previous, values):
        if previous is not None and previous[0] == values:
            return previous
        return copy.deepcopy(values), uuid4().hex


def build_selection_snapshot(game):
    """Expose counts and random change markers, never card values or hashes.

    Compare authoritative collections inside the core, including direct model
    changes and Undo. This cache is independent of gameplay state and saves.
    """
    markers = getattr(game, "_selection_markers", None)
    if markers is None:
        markers = game._selection_markers = _CollectionMarkers()
    owner = game.current_player_index
    hand = game.players[owner].hand
    markers.hands[owner] = markers.updated(markers.hands.get(owner), hand)
    markers.table = markers.updated(markers.table, game.table_cards)
    return SelectionSnapshot(markers.session, owner, markers.hands[owner][1],
                             markers.table[1], len(hand), len(game.table_cards))
