"""Read-only session metadata catalog without widgets or live game objects."""
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SessionEntry:
    filename: str
    path: str
    player_names: tuple[str, ...]
    next_player: str | None
    configuration: str | None
    modified: bool | None
    saved_at: float | None
    error: str | None


def read_session_metadata(path):
    target = Path(path)
    saved_at = None
    try:
        saved_at = target.stat().st_mtime
        with target.open(encoding="utf-8") as source:
            state = json.load(source)
        if not isinstance(state, dict):
            raise ValueError("Session must contain a JSON object.")
        players = state.get("players", [])
        if not isinstance(players, list) or any(not isinstance(p, dict) for p in players):
            raise ValueError("Invalid player metadata.")
        names = tuple(p.get("name", "Player") for p in players)
        if any(not isinstance(name, str) for name in names):
            raise ValueError("Invalid player name.")
        current = state.get("current_player_index", 0)
        if not isinstance(current, int) or isinstance(current, bool):
            raise ValueError("Invalid current player metadata.")
        next_player = names[current] if 0 <= current < len(names) else None
        info = state.get("configuration_info", {})
        if not isinstance(info, dict):
            raise ValueError("Invalid configuration metadata.")
        configuration = info.get("name")
        if configuration is not None and not isinstance(configuration, str):
            raise ValueError("Invalid configuration name.")
        modified = info.get("modified")
        modified = modified if isinstance(modified, bool) else None
        return SessionEntry(target.name, str(target), names, next_player,
                            configuration, modified, saved_at, None)
    except (OSError, ValueError, TypeError) as error:
        return SessionEntry(target.name, str(target), (), None, None, None, saved_at, str(error))


def list_sessions(saves_dir, source="saves"):
    """List named saves or latest+archived autosaves without creating folders.

    Per-file read failures remain catalog entries. Directory enumeration errors
    propagate so the client can distinguish inaccessible storage from no saves.
    """
    if source not in {"saves", "autosaves"}:
        raise ValueError("Choose saves or autosaves as the source.")
    base = Path(saves_dir)
    folder = base / "autosaves" if source == "autosaves" else base
    paths = (sorted((p for p in folder.iterdir() if p.is_file() and p.suffix.lower() == ".json"
                     and p.name.lower() != "last_session.json"), key=lambda p: p.name.casefold())
             if folder.exists() else [])
    latest = base / "last_session.json"
    if source == "autosaves" and latest.is_file():
        paths.insert(0, latest)
    return tuple(read_session_metadata(path) for path in paths)
