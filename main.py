# main.py
import os
from game import Game
from guibase import start_gui

def main():
    base_dir = os.path.dirname(__file__)
    deck_path = os.path.join(base_dir, "decks", "demodeck.json")
    discard_path = os.path.join(base_dir, "decks", "discard.json")

    game = Game(num_players=3, deck_path=deck_path)
    game.start(cards_per_player=5)

    start_gui(game)  # launch GUI instead of CLI

    # Save discard pile after closing GUI
    game.save_discard_pile(discard_path)

if __name__ == "__main__":
    main()