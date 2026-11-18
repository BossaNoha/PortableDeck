"""Named-save path rules and persistence without dialog dependencies."""
import os
import re
from pathlib import Path


def validate_named_save_path(path):
    """Reject reserved checkpoint destinations without touching the filesystem."""
    if not os.fspath(path):
        raise ValueError("Choose a named save file.")
    target = Path(path)
    if target.name.lower() == "last_session.json" or target.absolute().parent.name.lower() == "autosaves":
        raise ValueError("Choose a named session outside the automatic checkpoint files.")
    return target


def next_session_number(directory):
    folder = Path(directory)
    if not folder.exists():
        return 1
    numbers = []
    for entry in folder.iterdir():
        match = re.fullmatch(r"session(\d+)\.json", entry.name, re.IGNORECASE)
        if match:
            numbers.append(int(match.group(1)))
    return max(numbers, default=0) + 1


def save_named_session(game, path, *, client_state=None, overwrite=False):
    """Validate and save; update the associated path only after successful IO.

    Clients choose a path and obtain overwrite consent before calling with
    overwrite=True. Exceptions propagate for the client to present appropriately.
    """
    target = validate_named_save_path(path)
    if target.exists() and not overwrite:
        raise FileExistsError(f"A save named '{target.name}' already exists.")
    game.save_session(str(target), client_state=client_state)
    game.named_save_path = str(target)
