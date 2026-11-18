"""Small modal dialogs used by the chip account controls."""
import tkinter as tk
from tkinter import messagebox


def ask_chip_purchase(parent, view):
    """Return (player_index, amount), or None when the dialog is cancelled."""
    result = {}
    dialog = tk.Toplevel(parent)
    dialog.title("Buy Chips")
    dialog.transient(parent)
    dialog.resizable(False, False)
    frame = tk.Frame(dialog, padx=14, pady=12)
    frame.pack(fill="both", expand=True)

    options = [f"{player.index + 1}. {player.name}" for player in view.players]
    current = next(i for i, player in enumerate(view.players) if player.index == view.current_player)
    selected_player = tk.StringVar(value=options[current])
    amount = tk.StringVar(value=str(view.default_purchase_amount))
    tk.Label(frame, text="Player:").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=4)
    tk.OptionMenu(frame, selected_player, *options).grid(
        row=0, column=1, sticky="ew", pady=4
    )
    tk.Label(frame, text="Chips to add:").grid(
        row=1, column=0, sticky="w", padx=(0, 8), pady=4
    )
    amount_entry = tk.Entry(frame, textvariable=amount, width=12)
    amount_entry.grid(row=1, column=1, sticky="w", pady=4)

    def confirm():
        try:
            chip_count = int(amount.get())
            player_index = view.players[options.index(selected_player.get())].index
        except (ValueError, IndexError):
            messagebox.showerror(
                "Invalid purchase", "Enter a positive whole number of chips.", parent=dialog
            )
            return
        if chip_count < 1:
            messagebox.showerror("Invalid purchase", "Enter at least one chip.", parent=dialog)
            return
        result["purchase"] = (player_index, chip_count)
        dialog.destroy()

    buttons = tk.Frame(frame)
    buttons.grid(row=2, column=0, columnspan=2, sticky="e", pady=(8, 0))
    tk.Button(buttons, text="Cancel", command=dialog.destroy).pack(side="left", padx=4)
    tk.Button(buttons, text="Buy", command=confirm).pack(side="left", padx=4)
    dialog.bind("<Return>", lambda _event: confirm())
    dialog.grab_set()
    amount_entry.focus_set()
    parent.wait_window(dialog)
    return result.get("purchase")


def ask_pot_recipient(parent, view):
    """Return the selected recipient index, or None when cancelled."""
    result = {}
    dialog = tk.Toplevel(parent)
    dialog.title("Take Pot")
    dialog.transient(parent)
    dialog.resizable(False, False)
    frame = tk.Frame(dialog, padx=14, pady=12)
    frame.pack(fill="both", expand=True)

    options = [f"{player.index + 1}. {player.name}" for player in view.players]
    current = next(i for i, player in enumerate(view.players) if player.index == view.current_player)
    recipient = tk.StringVar(value=options[current])
    tk.Label(frame, text=f"Pot: {view.pot} chips").grid(
        row=0, column=0, columnspan=2, sticky="w", pady=(0, 8)
    )
    tk.Label(frame, text="Give the pot to:").grid(
        row=1, column=0, sticky="w", padx=(0, 8)
    )
    tk.OptionMenu(frame, recipient, *options).grid(row=1, column=1, sticky="ew")

    def confirm():
        try:
            result["recipient"] = view.players[options.index(recipient.get())].index
        except ValueError:
            messagebox.showerror("Invalid player", "Choose a valid player.", parent=dialog)
            return
        dialog.destroy()

    buttons = tk.Frame(frame)
    buttons.grid(row=2, column=0, columnspan=2, sticky="e", pady=(8, 0))
    tk.Button(buttons, text="Cancel", command=dialog.destroy).pack(side="left", padx=4)
    tk.Button(buttons, text="Request", command=confirm).pack(side="left", padx=4)
    dialog.bind("<Return>", lambda _event: confirm())
    dialog.grab_set()
    parent.wait_window(dialog)
    return result.get("recipient")
