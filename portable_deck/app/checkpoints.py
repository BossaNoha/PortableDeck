"""GUI-independent checkpoint persistence and autosave retention."""
from pathlib import Path
from time import time_ns


def save_checkpoint(game, latest_path, *, enabled=True, count=5, client_state=None):
    """Save latest state and retain count versions including the latest file.

    Return None on success/disabled autosave, otherwise an error string suitable
    for SessionController.checkpoint_callback. The core serializer performs the
    atomic latest-file write; an archive/cleanup error does not undo that write.
    """
    if not enabled:
        return None
    try:
        count = int(count)
        if not 1 <= count <= 1000:
            raise ValueError("Autosaves to keep must be between 1 and 1000.")
        latest = Path(latest_path)
        previous = latest.read_bytes() if latest.exists() else None
        game.save_session(str(latest), client_state=client_state)
        archive = latest.parent / "autosaves"
        archive.mkdir(exist_ok=True)
        if count > 1 and previous is not None and previous != latest.read_bytes():
            (archive / f"autosave_{time_ns()}.json").write_bytes(previous)
        versions = sorted(archive.glob("autosave_*.json"), key=lambda path: path.name, reverse=True)
        for old in versions[count - 1:]:
            old.unlink()
        return None
    except (OSError, TypeError, ValueError) as error:
        return str(error)
