import tkinter as tk
from tkinter import messagebox, simpledialog

class SpecialActionsUI:
    def __init__(self, gui):
        self.gui = gui
        self.buttons = []
        for destination, label, enabled in (
            ("draw", "Place in Draw Deck…", gui.game.allow_insert_draw_deck),
            ("discard", "Place in Discard Pile…", gui.game.allow_insert_discard_pile and gui.game.enable_discard_pile)):
            if enabled:
                button = tk.Button(gui.card_actions_frame, text=label, command=lambda d=destination: self.choose(d))
                button.pack(side="left", padx=5)
                self.buttons.append(button)

    def choose(self, destination):
        gui, game = self.gui, self.gui.game
        selected = gui.hand_frame.selected_index
        if selected is None:
            messagebox.showwarning("No selection", "Select a card in your hand first.", parent=gui.root)
            return
        pile_index = 0
        if destination == "discard" and len(game.discard_piles) > 1:
            chosen = simpledialog.askinteger("Choose discard pile", f"Discard pile (1–{len(game.discard_piles)}):",
                                            minvalue=1, maxvalue=len(game.discard_piles), parent=gui.root)
            if chosen is None:
                return
            pile_index = chosen - 1
        pile = game.deck.flat_deck if destination == "draw" else game.discard_piles[pile_index]
        position = simpledialog.askstring("Choose card position",
            f"1–10: from the top (1 = top)\n-1–-10: from the bottom (-1 = bottom)\nX: random middle position, outside the first/last 10\nAvailable positions from either end: {min(10, len(pile) + 1)}",
            parent=gui.root)
        if position is None:
            return
        position = position.strip().upper()
        def action():
            try:
                card = game.insert_hand_card(selected + 1, destination, position, pile_index)
            except ValueError as error:
                messagebox.showwarning("Cannot place card", str(error), parent=gui.root)
                return
            name = "draw deck" if destination == "draw" else f"discard pile {pile_index + 1}"
            gui.log(f"{gui.current_player_name()} placed {card} at position {position} in the {name}.")
            gui.hand_frame.selected_index = None
            gui.hand_frame.update_hand()
            gui.status_panel.update_status()
        gui.run_action(action)
