"""Read-only hand viewer respecting current-player permissions."""
import tkinter as tk
from .contentscrollarea import ContentScrollArea
from ..core.playerview import build_player_hands_view

def show_visible_hands(gui):
    game = gui.game
    view = build_player_hands_view(game, game.current_player_index)
    dialog = tk.Toplevel(gui.root)
    dialog.title(f"Visible hands — {view.viewer_name}")
    dialog.transient(gui.root)
    dialog.grab_set()
    area = ContentScrollArea(dialog, width=500)
    area.pack(fill="both", expand=True)
    for hand in view.hands:
        if not hand.visible:
            continue
        cards = [slot.card if slot.card is not None else "Hidden card" for slot in hand.cards]
        frame = tk.LabelFrame(area.contents, text=hand.name, padx=10, pady=6)
        frame.pack(fill="x", padx=8, pady=4)
        tk.Label(frame, text="\n".join(cards) if cards else "No cards", justify="left").pack(anchor="w")
    tk.Button(dialog, text="Close", command=dialog.destroy).pack(anchor="e", padx=10, pady=8)
    dialog.geometry(f"520x{min(500, dialog.winfo_screenheight() - 100)}")
