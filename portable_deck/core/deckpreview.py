"""Immutable preview of a deck definition, independent of draw order and GUI."""
from dataclasses import dataclass
from .deck import Deck


@dataclass(frozen=True)
class DeckSymbolView:
    name: str
    values: tuple[str, ...]


@dataclass(frozen=True)
class DeckPreview:
    card_count: int
    symbols: tuple[DeckSymbolView, ...]


def card_sort_key(value):
    """Preserve preview order: numbers, common faces, then casefolded text."""
    text = str(value).strip()
    faces = {"j": 11, "jack": 11, "knight": 11, "q": 12, "queen": 12,
             "k": 13, "king": 13, "a": 14, "ace": 14}
    try:
        return 0, float(text)
    except ValueError:
        if text.casefold() in faces:
            return 1, faces[text.casefold()]
        return 2, text.casefold()


def build_deck_preview(deck):
    """Read definition groups only; never read remaining shuffled cards."""
    count = Deck.validate_data({"types": deck.types, "cards": deck.cards})
    return DeckPreview(count, tuple(
        DeckSymbolView(name, tuple(str(value) for value in sorted(values, key=card_sort_key)))
        for name, values in zip(deck.types, deck.cards)))
