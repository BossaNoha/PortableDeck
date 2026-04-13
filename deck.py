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
        with open(self.path, "r") as f:
            data = json.load(f)
            self.types = data["types"]
            self.cards = data["cards"]
            self.flatten()

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