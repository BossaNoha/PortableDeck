import tkinter as tk
from tkinter import messagebox, simpledialog
from ..core.pileoptions import insertion_options

class SpecialActionsUI:
    def __init__(self, gui):
        self.gui = gui
        self.buttons = []
        for destination, label, enabled in (
            ("draw", "Place in Draw Deck…", gui.game.allow_insert_draw_deck),
            ("discard", "Place in Discard Pile…", gui.game.allow_insert_discard_pile and gui.game.enable_discard_pile)):
            if enabled:
                button = tk.Button(gui.card_actions_frame, text=label, command=lambda d=destination: self.choose(d))
                button.action_id = "insert_draw_deck" if destination == "draw" else "insert_discard_pile"
                button.pack(side="left", padx=5)
                self.buttons.append(button)

    def choose(self, destination):
        gui, game = self.gui, self.gui.game
        selected = gui.selection.hand_index
        if selected is None:
            messagebox.showwarning("No selection", "Select a card in your hand first.", parent=gui.root)
            return
        pile_index = 0
        parameters = gui.draw_source_parameters() if destination == "draw" else {}
        options = insertion_options(game, destination, **parameters)
        if not options:
            messagebox.showwarning("Cannot place card", "This placement is disabled.", parent=gui.root)
            return
        if destination == "discard" and len(options) > 1:
            chosen = simpledialog.askinteger("Choose discard pile", f"Discard pile (1–{len(options)}):",
                                            minvalue=1, maxvalue=len(options), parent=gui.root)
            if chosen is None:
                return
            pile_index = chosen - 1
        option = options[pile_index]
        position = simpledialog.askstring("Choose card position",
            f"1–10: from the top (1 = top)\n-1–-10: from the bottom (-1 = bottom)\nX: random middle position, outside the first/last 10\nAvailable positions from either end: {option.positions_from_end}",
            parent=gui.root)
        if position is None:
            return
        position = position.strip().upper()
        def action():
            action_id = "insert_draw_deck" if destination == "draw" else "insert_discard_pile"
            result = game.session.execute(
                action_id, card_index=selected, position=position, pile_index=pile_index, **parameters)
            if not result.success:
                messagebox.showwarning("Cannot place card", result.message, parent=gui.root)
                return
            gui.selection.hand_index = None
        gui.run_action(action)
