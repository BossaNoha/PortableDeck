"""Transient input selection shared by clients; independent of rendering and saves."""
from dataclasses import dataclass, field


@dataclass
class SelectionState:
    hand_index: int | None = None
    table_index: int | None = None
    target_position: tuple[int, int] | None = None
    _owner: int | None = field(default=None, init=False, repr=False)
    _hand: tuple = field(default=(), init=False, repr=False)
    _table: tuple = field(default=(), init=False, repr=False)

    def clear(self):
        self.hand_index = self.table_index = self.target_position = None

    def select_hand(self, index, *, toggle=True):
        self.hand_index = None if toggle and self.hand_index == index else index

    def select_table(self, index, *, toggle=True, keep_target=False):
        self.table_index = None if toggle and self.table_index == index else index
        if not keep_target:
            self.target_position = None

    def select_target(self, position, *, keep_card=False):
        self.target_position = tuple(position) if position is not None else None
        if not keep_card:
            self.table_index = None

    def synchronize(self, game):
        """Discard stale selections after a turn change or card mutation.

        Clearing on collection changes also prevents an index from silently
        selecting the next card after the selected card has been removed.
        """
        owner = game.current_player_index
        hand = tuple(game.players[owner].hand)
        table = tuple(tuple(sorted(entry.items())) for entry in game.table_cards)
        if owner != self._owner:
            self.clear()
        else:
            if hand != self._hand:
                self.hand_index = None
            if table != self._table:
                self.table_index = None
                self.target_position = None
        if self.hand_index is not None and not 0 <= self.hand_index < len(hand):
            self.hand_index = None
        if self.table_index is not None and not 0 <= self.table_index < len(table):
            self.table_index = None
        self._owner, self._hand, self._table = owner, hand, table
