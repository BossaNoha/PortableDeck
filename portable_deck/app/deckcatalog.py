"""Read-only deck metadata for graphical and headless library clients."""
from dataclasses import dataclass
from pathlib import Path

from ..core.deck import Deck


@dataclass(frozen=True)
class DeckEntry:
    filename: str
    path: str
    name: str
    card_count: int | None
    symbols: tuple[str, ...]
    error: str | None


def read_deck_metadata(path):
    target = Path(path)
    try:
        deck = Deck(str(target))
        return DeckEntry(target.name, str(target), target.stem,
                         len(deck.flat_deck), tuple(deck.types), None)
    except (OSError, ValueError, KeyError, TypeError) as error:
        return DeckEntry(target.name, str(target), target.stem, None, (), str(error))


def list_decks(directory):
    """Return sorted entries; retain invalid files and propagate listing errors.

    Missing directories are empty catalogs and are not created by this query.
    """
    folder = Path(directory)
    if not folder.exists():
        return ()
    paths = sorted((path for path in folder.iterdir() if path.name.lower().endswith(".json")),
                   key=lambda path: path.name.casefold())
    return tuple(read_deck_metadata(path) for path in paths)
