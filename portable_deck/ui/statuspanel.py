#statuspanel.py
import tkinter as tk
from ..core.sessionstatus import build_session_status

class StatusPanel(tk.LabelFrame):
    """
    Displays counts of cards in players' hands and the decks.
    - Hands: shows number or "many" if 8+
    - Decks: shows number or "many" if 12+
    """
    def __init__(self, master, game, **kwargs):
        super().__init__(master, text="Game Status", padx=5, pady=5, **kwargs)
        self.game = game
        status = build_session_status(game)

        # Create frames for players and decks
        self.player_labels = []
        self.turn_direction_label = None
        if status.turn_direction is not None:
            self.turn_direction_label = tk.Label(self, text="")
            self.turn_direction_label.pack(anchor="w")
        for player in status.players:
            lbl = tk.Label(self, text="")
            lbl.pack(anchor="w")
            self.player_labels.append(lbl)

        self.chip_rules_label = None
        self.chip_pot_label = None
        if status.minimum_bet is not None:
            self.chip_rules_label = tk.Label(self, text=f"Minimum bet: {status.minimum_bet} chips")
            self.chip_rules_label.pack(anchor="w")
            self.chip_pot_label = tk.Label(self, text="Pot: 0 chips")
            self.chip_pot_label.pack(anchor="w")

        self.deck_label = tk.Label(self, text="")
        self.deck_label.pack(anchor="w")

        self.discard_label = tk.Label(self, text="", justify="left", anchor="w", wraplength=620)
        if status.discard_piles is not None:
            self.discard_label.pack(anchor="w")

        self.table_label = tk.Label(self, text="")
        if status.table_count is not None:
            self.table_label.pack(anchor="w")

        # Initial update
        self.update_status(status)

    def update_status(self, status=None):
        if status is None:
            status = build_session_status(self.game)
        if self.turn_direction_label is not None:
            direction = "forward" if status.turn_direction == 1 else "reverse"
            self.turn_direction_label.config(text=f"Turn direction: {direction}")
        for player in status.players:
            count = player.card_count
            display = f"{count} card{'s' if count != 1 else ''}" if count < 8 else "many"
            if player.score is not None:
                display += f"  |  Score: {player.score}"
            if player.chips is not None:
                display += f"  |  Chips: {player.chips}"
            if player.team_name:
                display += f"  |  Team: {player.team_name}"
            if player.team_score is not None:
                display += f"  |  Team score: {player.team_score}"
            if player.dealer:
                display += "  |  Role: Dealer"
            if not player.active:
                display += "  |  Left session"
            self.player_labels[player.index].config(text=f"{player.name}: {display}")

        draw_display = str(status.draw_count) if status.draw_count < 12 else "many"
        self.deck_label.config(text=f"Draw Deck: {draw_display}")
        if status.discard_piles is not None:
            discard_lines = [f"{pile.name}: {pile.card_count}" for pile in status.discard_piles]
            self.discard_label.config(text="Discard piles:\n" + "\n".join(discard_lines))
        if status.table_count is not None:
            self.table_label.config(text=f"Cards on Table: {status.table_count}")
        if self.chip_pot_label is not None:
            self.chip_pot_label.config(text=f"Pot: {status.chip_pot} chips")
