"""Mutable draw order, independent of a card-set definition or file."""
import random


class DrawPile:
    def __init__(self, cards=()):
        self.cards = list(cards)

    def shuffle(self):
        random.shuffle(self.cards)

    def draw_card(self):
        return self.cards.pop(0) if self.cards else None
