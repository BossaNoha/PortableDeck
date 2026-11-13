# player.py
class Player:
    def __init__(self, name):
        self.name = name
        self.hand = []
        self.revealed_indices = set()

    def draw_card(self, card):
        if card:
            self.hand.append(card)

    def play_card(self, index):
        if 1 <= index <= len(self.hand):
            self.revealed_indices = {i - 1 if i > index - 1 else i for i in self.revealed_indices if i != index - 1}
            return self.hand.pop(index - 1)
        return None

    def show_hand(self):
        for i, card in enumerate(self.hand, start=1):
            print(f"{i}. {card}")

    def __str__(self):
        return f"{self.name}: {self.hand}"