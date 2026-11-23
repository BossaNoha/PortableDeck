"""Compatibility facade combining a card definition with one draw pile."""
import json
from .deckdefinition import DeckDefinition, validate_definition
from .drawpile import DrawPile


class Deck:
    @classmethod
    def from_definition(cls, data, *, path=None):
        """Create an independent draw pile from a definition without file access."""
        definition = data if isinstance(data, DeckDefinition) else DeckDefinition.from_data(data)
        deck = cls.__new__(cls)
        deck.path = path
        deck.definition = definition
        deck.draw_pile = DrawPile(definition.expanded_cards())
        return deck

    def __init__(self, path):
        self.path = path
        self.draw_pile = DrawPile()
        self.load()

    @property
    def types(self):
        return list(self.definition.types)

    @property
    def cards(self):
        return [list(group) for group in self.definition.cards]

    @property
    def flat_deck(self):
        """Legacy live-list access to the authoritative draw-pile contents."""
        return self.draw_pile.cards

    @flat_deck.setter
    def flat_deck(self, cards):
        self.draw_pile.cards = list(cards)

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
        self.definition = DeckDefinition.from_data(data)
        self.flatten()

    validate_data = staticmethod(validate_definition)

    def flatten(self):
        self.draw_pile.cards = list(self.definition.expanded_cards())

    def shuffle(self):
        self.draw_pile.shuffle()

    def draw_card(self):
        return self.draw_pile.draw_card()
