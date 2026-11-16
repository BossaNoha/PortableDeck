"""Transient input selection shared by clients; independent of rendering and saves."""
from dataclasses import dataclass, field
from .selectionsnapshot import SelectionSnapshot, build_selection_snapshot


@dataclass
class SelectionState:
    hand_index: int | None = None
    table_index: int | None = None
    target_position: tuple[int, int] | None = None
    _owner: int | None = field(default=None, init=False, repr=False)
    _session: str | None = field(default=None, init=False, repr=False)
    _hand_revision: str | None = field(default=None, init=False, repr=False)
    _table_revision: str | None = field(default=None, init=False, repr=False)

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

    def synchronize(self, snapshot):
        """Discard stale selections after a turn change or card mutation.

        Clearing on collection changes also prevents an index from silently
        selecting the next card after the selected card has been removed.
        """
        # Keep the previous local API usable; clients can pass only the DTO.
        if not isinstance(snapshot, SelectionSnapshot):
            snapshot = build_selection_snapshot(snapshot)
        owner = snapshot.owner
        if snapshot.session != self._session or owner != self._owner:
            self.clear()
        else:
            if snapshot.hand_revision != self._hand_revision:
                self.hand_index = None
            if snapshot.table_revision != self._table_revision:
                self.table_index = None
                self.target_position = None
        if self.hand_index is not None and not 0 <= self.hand_index < snapshot.hand_count:
            self.hand_index = None
        if self.table_index is not None and not 0 <= self.table_index < snapshot.table_count:
            self.table_index = None
        self._owner, self._session = owner, snapshot.session
        self._hand_revision, self._table_revision = snapshot.hand_revision, snapshot.table_revision
