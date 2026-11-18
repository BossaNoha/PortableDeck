"""Client-owned table presentation state and save compatibility."""
import json
from dataclasses import asdict, dataclass
from .sessionstorage import save_session


@dataclass
class TableViewState:
    zoom: int = 100
    x: float = 0.0
    y: float = 0.0

    @classmethod
    def from_saved(cls, values):
        view = cls()
        if isinstance(values, dict):
            for key, low, high in (("zoom", 50, 200), ("x", 0, 1), ("y", 0, 1)):
                value = values.get(key)
                if isinstance(value, (int, float)) and not isinstance(value, bool) and low <= value <= high:
                    setattr(view, key, value)
        return view


def load_table_view(path):
    with open(path, encoding="utf-8") as source:
        state = json.load(source)
    client = state.get("client_state")
    values = client.get("table_view") if isinstance(client, dict) else state.get("table_view_state")
    return TableViewState.from_saved(values)


def save_with_view(game, path, view):
    save_session(game, path, client_state={"table_view": asdict(view)})
