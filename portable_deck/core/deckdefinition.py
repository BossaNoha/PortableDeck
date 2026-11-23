"""Immutable card-set definitions, independent of draw order and file access."""
from dataclasses import dataclass


def validate_definition(data):
    """Validate the supported deck JSON shape and return its card count."""
    if not isinstance(data, dict):
        raise ValueError("Deck JSON must contain an object with 'types' and 'cards' lists.")
    types = data.get("types")
    groups = data.get("cards")
    if not isinstance(types, list) or not types:
        raise ValueError("Deck must define at least one card type in the 'types' list.")
    if any(not isinstance(name, str) or not name.strip() for name in types):
        raise ValueError("Every entry in 'types' must be a non-empty name.")
    if not isinstance(groups, list) or len(groups) != len(types):
        raise ValueError("The 'cards' list must contain one card list for every type.")
    count = 0
    for index, group in enumerate(groups):
        if not isinstance(group, list):
            raise ValueError(f"Cards for type '{types[index]}' must be a list.")
        if any(
            isinstance(value, bool)
            or not isinstance(value, (str, int, float))
            or not str(value).strip()
            for value in group
        ):
            raise ValueError(f"Cards for type '{types[index]}' must be non-empty text or numbers.")
        count += len(group)
    if count == 0:
        raise ValueError("Deck contains no cards.")
    return count


@dataclass(frozen=True)
class DeckDefinition:
    types: tuple[str, ...]
    cards: tuple[tuple[str | int | float, ...], ...]

    def __post_init__(self):
        if (not isinstance(self.types, tuple) or not isinstance(self.cards, tuple)
                or any(not isinstance(group, tuple) for group in self.cards)):
            raise ValueError("Definition types and card groups must be immutable tuples.")
        validate_definition(self.to_data())

    @classmethod
    def from_data(cls, data):
        validate_definition(data)
        return cls(tuple(data["types"]), tuple(tuple(group) for group in data["cards"]))

    def to_data(self):
        """Return an independent representation in the existing deck JSON format."""
        return {"types": list(self.types), "cards": [list(group) for group in self.cards]}

    def expanded_cards(self):
        return tuple(f"{value} of {name}" for name, group in zip(self.types, self.cards) for value in group)
