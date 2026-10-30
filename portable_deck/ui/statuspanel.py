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

        self.chip_rules_label = None
        self.chip_pot_label = None
        if game.enable_chip_accounts:
            self.chip_rules_label = tk.Label(self, text=f"Minimum bet: {game.minimum_bet} chips")
            self.chip_rules_label.pack(anchor="w")
            self.chip_pot_label = tk.Label(self, text="Pot: 0 chips")
            self.chip_pot_label.pack(anchor="w")

        self.deck_label = tk.Label(self, text="")
        self.deck_label.pack(anchor="w")

        self.discard_label = tk.Label(self, text="", justify="left", anchor="w", wraplength=620)
        self.discard_label.pack(anchor="w")

        self.table_label = tk.Label(self, text="")
        self.table_label.pack(anchor="w")

        # Initial update
        self.update_status()

    def update_status(self):
        # Update player hands
        for i, player in enumerate(self.game.players):
            count = len(player.hand)
            display = f"{count} card{'s' if count != 1 else ''}" if count < 8 else "many"
            if self.game.score_enabled:
                display += f"  |  Score: {self.game.scores[i]}"
            if self.game.enable_chip_accounts:
                display += f"  |  Chips: {self.game.chip_balances[i]}"
            self.player_labels[i].config(text=f"{player.name}: {display}")

        # Update draw deck
        draw_count = len(self.game.deck.flat_deck)
        draw_display = str(draw_count) if draw_count < 12 else "many"
        self.deck_label.config(text=f"Draw Deck: {draw_display}")

        # Show each shared discard and each player's own private piles.
        discard_lines = [
            f"{name}: {len(pile)}"
            for name, pile in self.game.all_discard_piles()
        ]
        self.discard_label.config(text="Discard piles:\n" + "\n".join(discard_lines))

        self.table_label.config(text=f"Cards on Table: {len(self.game.table_cards)}")
        if self.chip_pot_label is not None:
            self.chip_pot_label.config(text=f"Pot: {self.game.chip_pot} chips")
