"""Choose another player and perform an enabled interaction."""
import tkinter as tk
from tkinter import messagebox, simpledialog
from ..core.interactions import INTERACTIONS

class InteractionsUI:
    def __init__(self, gui):
        self.gui = gui
        self.button = tk.Button(gui.card_actions_frame, text="Player interactions", command=self.show)
        self.button.pack(side="left", padx=5)

    def show(self, initial_action=None):
        gui, game = self.gui, self.gui.game
        actions = [key for key in INTERACTIONS if game.interaction_allowed(key)]
        if not actions:
            messagebox.showinfo("Player interactions", "No interactions are enabled.", parent=gui.root)
            return
        dialog = tk.Toplevel(gui.root)
        dialog.title("Player interactions")
        dialog.transient(gui.root)
        dialog.grab_set()
        selected_action = tk.StringVar(value=INTERACTIONS[initial_action if initial_action in actions else actions[0]])
        tk.OptionMenu(dialog, selected_action, *[INTERACTIONS[key] for key in actions]).pack(fill="x", padx=10, pady=8)
        tk.Label(dialog, text="Choose a player (ignored for random discard):").pack(anchor="w", padx=10)
        targets = [i for i in game.active_player_indices() if i != game.current_player_index]
        players = tk.Listbox(dialog, height=max(1, min(10, len(targets))), exportselection=False)
        players.pack(fill="both", expand=True, padx=10, pady=8)
        for target in targets:
            players.insert("end", game.players[target].name)
        if targets:
            players.selection_set(0)

        def perform():
            action = next(key for key in actions if INTERACTIONS[key] == selected_action.get())
            selection = players.curselection()
            target = targets[selection[0]] if selection else None
            amount = None
            if action == "steal_chips" and target is not None:
                balance = game.chip_balance(target)
                if balance < 1:
                    messagebox.showinfo("No chips", "This player has no chips to steal.", parent=dialog)
                    return
                amount = simpledialog.askinteger("Steal chips", "How many chips?", minvalue=1, maxvalue=balance, parent=dialog)
                if amount is None:
                    return
            selected = gui.selection.hand_index
            def execute():
                try:
                    result = game.interact(action, target, None if selected is None else selected + 1, amount)
                except ValueError as error:
                    messagebox.showwarning("Cannot interact", str(error), parent=dialog)
                    return
                name = game.players[result["target"]].name
                if action.startswith("peek_"):
                    gui.render_log()
                    messagebox.showinfo(f"{name}'s cards — private view", "\n".join(result["cards"]), parent=dialog)
                else:
                    gui.render_log()
                gui.selection.hand_index = None
                gui.hand_frame.update_hand()
                gui.status_panel.update_status()
                gui.update_chip_action_buttons()
                dialog.destroy()
            gui.run_action(execute)
        tk.Button(dialog, text="Perform", command=perform).pack(side="right", padx=10, pady=8)
        tk.Button(dialog, text="Cancel", command=dialog.destroy).pack(side="right", pady=8)
