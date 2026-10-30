# player.py
class Player:
    def __init__(self, name):
        self.name = name
        self.hand = []

    def draw_card(self, card):
        if card:
            self.hand.append(card)

    def play_card(self, index):
        if 1 <= index <= len(self.hand):
            return self.hand.pop(index - 1)
        return None

    def show_hand(self):
        for i, card in enumerate(self.hand, start=1):
            print(f"{i}. {card}")

    def __str__(self):
        return f"{self.name}: {self.hand}"