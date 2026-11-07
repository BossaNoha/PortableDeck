"""Read-only hand viewer respecting current-player permissions."""
import tkinter as tk
from .contentscrollarea import ContentScrollArea

def show_visible_hands(gui):
    game = gui.game
    viewer = game.current_player_index
    dialog = tk.Toplevel(gui.root)
    dialog.title(f"Visible hands — {game.players[viewer].name}")
    dialog.transient(gui.root)
    dialog.grab_set()
    area = ContentScrollArea(dialog, width=500)
    area.pack(fill="both", expand=True)
    for owner, player in enumerate(game.players):
        cards = game.visible_hand(viewer, owner)
        if cards is None:
            continue
        frame = tk.LabelFrame(area.contents, text=player.name, padx=10, pady=6)
        frame.pack(fill="x", padx=8, pady=4)
        tk.Label(frame, text="\n".join(cards) if cards else "No cards", justify="left").pack(anchor="w")
    tk.Button(dialog, text="Close", command=dialog.destroy).pack(anchor="e", padx=10, pady=8)
    dialog.geometry(f"520x{min(500, dialog.winfo_screenheight() - 100)}")
