"""Session library rename/delete operations, independent of widgets."""
from pathlib import Path


def rename_session(path, new_name):
    """Rename within the source directory without replacing an existing entry."""
    source = Path(path)
    if source.name.lower() == "last_session.json":
        raise ValueError("The latest autosave is used by Resume and cannot be renamed.")
    if not isinstance(new_name, str):
        raise ValueError("Enter a file name without a folder path or special characters.")
    name = new_name.strip()
    if (not name or name in {".", ".."} or any(char in name for char in '<>:"/\\|?*')
            or any(ord(char) < 32 for char in name)):
        raise ValueError("Enter a file name without a folder path or special characters.")
    if not name.lower().endswith(".json"):
        name += ".json"
    if name.lower() == "last_session.json":
        raise ValueError("This name is reserved for the latest automatic checkpoint.")
    destination = source.with_name(name)
    if destination.exists():
        raise FileExistsError(f"A session named '{name}' already exists.")
    if not source.is_file():
        raise FileNotFoundError(f"Saved session does not exist: {source}")
    source.rename(destination)
    return destination


def delete_session(path, *, confirmed=False):
    """Delete one session only with explicit confirmation; never recurse.

    The library permits deleting latest/archived autosaves after confirmation,
    matching the existing browser behavior. Only renaming latest is forbidden.
    """
    if confirmed is not True:
        return False
    Path(path).unlink()
    return True
