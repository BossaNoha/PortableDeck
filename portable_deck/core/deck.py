#deck.py
import json
import random

class Deck:
    def __init__(self, path):
        self.path = path
        self.types = []
        self.cards = []
        self.flat_deck = []
        self.load()

    def load(self):
        try:
            with open(self.path, "r", encoding="utf-8") as deck_file:
                data = json.load(deck_file)
        except json.JSONDecodeError as error:
            raise ValueError(
                f"Deck file is not valid JSON (line {error.lineno}, column {error.colno})."
            ) from error
        except UnicodeDecodeError as error:
            raise ValueError("Deck file must use UTF-8 text encoding.") from error
        self.validate_data(data)
        self.types = data["types"]
        self.cards = data["cards"]
        self.flatten()

    @staticmethod
    def validate_data(data):
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

    def flatten(self):
        self.flat_deck = []
        for type_index, group in enumerate(self.cards):
            type_name = self.types[type_index]
            for value in group:
                self.flat_deck.append(f"{value} of {type_name}")

    def shuffle(self):
        random.shuffle(self.flat_deck)

    def draw_card(self):
        return self.flat_deck.pop(0) if self.flat_deck else None
