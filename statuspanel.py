#statuspanel.py
import tkinter as tk

class StatusPanel(tk.LabelFrame):
    """
    Displays counts of cards in players' hands and the decks.
    - Hands: shows number or "many" if 8+
    - Decks: shows number or "many" if 12+
    """
    def __init__(self, master, game, **kwargs):
        super().__init__(master, text="Game Status", padx=5, pady=5, **kwargs)
        self.game = game

        # Create frames for players and decks
        self.player_labels = []
        for player in game.players:
            lbl = tk.Label(self, text="")
            lbl.pack(anchor="w")
            self.player_labels.append(lbl)

        self.deck_label = tk.Label(self, text="")
        self.deck_label.pack(anchor="w")

        self.discard_label = tk.Label(self, text="")
        self.discard_label.pack(anchor="w")

        # Initial update
        self.update_status()

    def update_status(self):
        # Update player hands
        for i, player in enumerate(self.game.players):
            count = len(player.hand)
            display = f"{count} card{'s' if count != 1 else ''}" if count < 8 else "many"
            self.player_labels[i].config(text=f"{player.name}: {display}")

        # Update draw deck
        draw_count = len(self.game.deck.flat_deck)
        draw_display = str(draw_count) if draw_count < 12 else "many"
        self.deck_label.config(text=f"Draw Deck: {draw_display}")

        # Update discard pile
        discard_count = len(self.game.discard_pile)
        discard_display = str(discard_count) if discard_count < 12 else "many"
        self.discard_label.config(text=f"Discard Pile: {discard_display}")