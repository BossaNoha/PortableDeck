#game.py
from deck import Deck
from player import Player
import json

class Game:
    def __init__(self, num_players, deck_path):
        self.players = [Player(f"Player{i+1}") for i in range(num_players)]
        self.deck = Deck(deck_path)
        self.discard_pile = []
        self.current_player_index = 0
        self.history = []
        self.cards_drawn_this_turn = 0

    def start(self, cards_per_player=5):
        self.deck.shuffle()
        print("Deck shuffled. Starting the game...")
        for _ in range(cards_per_player):
            for player in self.players:
                player.draw_card(self.deck.draw_card())

    def log_draws_for_turn(self):
        if self.cards_drawn_this_turn > 0:
            player_name = self.players[self.current_player_index].name
            entry = {"player": player_name, "action": "draw_multiple", "count": self.cards_drawn_this_turn}
            self.history.append(entry)
            self.cards_drawn_this_turn = 0

    def deal_card_to_current(self):
        card = self.deck.draw_card()
        player = self.players[self.current_player_index]
        if card:
            player.draw_card(card)
            print(f"Drew card: {card}")
            self.cards_drawn_this_turn += 1
        else:
            print("No more cards to draw.")

    def discard_from_current(self, index):
        player = self.players[self.current_player_index]
        card = player.play_card(index)

        if card:
            self.discard_pile.append(card)
            self.log_action(player.name, "discard", card)
            return card   # ✅ success
        else:
            return None   # ❌ failure

    def log_action(self, player_name, action, card=None):
        entry = {"player": player_name, "action": action}
        if card:
            entry["card"] = card
        self.history.append(entry)

    def next_turn(self):
        confirm = input("End turn? (y/n): ").strip().lower()
        if confirm == "y":
            self.log_draws_for_turn()
            self.current_player_index = (self.current_player_index + 1) % len(self.players)
            print("Turn ended.")
        else:
            print("Continuing current turn.")

    def show_discard_pile(self):
        print("\nDiscard Pile:")
        if self.discard_pile:
            for card in self.discard_pile:
                print(f"- {card}")
        else:
            print("Discard pile is empty.")

    def show_log_to_player(self, player_index):
        player_name = self.players[player_index].name
        print(f"\n--- Game Log for {player_name} ---")
        if not self.history:
            print("No actions recorded yet.")
            return
        for entry in self.history:
            actor = entry["player"]
            action = entry["action"]
            if action == "draw_multiple":
                count = entry["count"]
                if actor == player_name:
                    print(f"{actor} drew {count} card{'s' if count > 1 else ''}")
                else:
                    print(f"{actor} drew some cards")
            elif action == "discard":
                card = entry.get("card")
                if actor == player_name:
                    print(f"You discarded: {card}")
                else:
                    print(f"{actor} discarded a card: {card}")
            else:
                print(f"{actor} performed action: {action}")

    def save_discard_pile(self, path):
        with open(path, "w") as f:
            json.dump(self.discard_pile, f, indent=2)