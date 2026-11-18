"""Choose another player and perform an enabled interaction."""
import tkinter as tk
from tkinter import messagebox, simpledialog
from ..core.interactions import INTERACTIONS, build_interaction_options

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
        targets = []
        players = tk.Listbox(dialog, height=6, exportselection=False)
        players.pack(fill="both", expand=True, padx=10, pady=8)

        def current_action():
            return next(key for key in actions if INTERACTIONS[key] == selected_action.get())

        def refresh_targets(*_):
            options = build_interaction_options(game, current_action(), gui.selection.hand_index)
            targets[:] = options.targets
            players.delete(0, "end")
            for target in targets:
                players.insert("end", target.name + (f" — {target.reason}" if not target.allowed else ""))
            if targets:
                players.selection_set(next((i for i, target in enumerate(targets) if target.allowed), 0))

        selected_action.trace_add("write", refresh_targets)
        refresh_targets()

        def perform():
            action = current_action()
            selection = players.curselection()
            target = targets[selection[0]].index if selection else None
            options = build_interaction_options(game, action, gui.selection.hand_index)
            target_option = next((item for item in options.targets if item.index == target), None)
            reason = options.reason
            if not options.random_target:
                reason = reason or (target_option.reason if target_option else "Choose another player.")
            if reason:
                messagebox.showwarning("Cannot interact", reason, parent=dialog)
                refresh_targets()
                return
            amount = None
            if action == "steal_chips" and target is not None:
                amount = simpledialog.askinteger("Steal chips", "How many chips?", minvalue=1,
                                                maxvalue=target_option.max_amount, parent=dialog)
                if amount is None:
                    return
            selected = gui.selection.hand_index
            def execute():
                outcome = game.session.execute(action, target=target, card_index=selected, amount=amount)
                if not outcome.success:
                    messagebox.showwarning("Cannot interact", outcome.message, parent=dialog)
                    return
                result = outcome.value
                name = next(item.name for item in options.targets if item.index == result["target"])
                if action.startswith("peek_"):
                    messagebox.showinfo(f"{name}'s cards — private view", "\n".join(result["cards"]), parent=dialog)
                gui.selection.hand_index = None
                dialog.destroy()
            gui.run_action(execute)
        tk.Button(dialog, text="Perform", command=perform).pack(side="right", padx=10, pady=8)
        tk.Button(dialog, text="Cancel", command=dialog.destroy).pack(side="right", pady=8)
