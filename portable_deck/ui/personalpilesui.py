"""Personal table piles and the actions available to the current player."""
import tkinter as tk
from tkinter import messagebox
from .contentscrollarea import ContentScrollArea
from ..core.playerview import build_player_personal_piles_view


class PersonalPilesUI:
    def __init__(self, gui):
        self.gui = gui
        self.frame = tk.LabelFrame(gui.right_frame, text="Personal piles", padx=6, pady=5)
        if gui.game.enable_table and gui.game.enable_personal_piles:
            self.frame.pack(fill="x", pady=5)
        self.scroll_area = ContentScrollArea(self.frame, width=420)
        self.scroll_area.pack(fill="both", expand=True)
        self.contents = self.scroll_area.contents
        self.update()

    def update(self, view=None):
        for child in self.contents.winfo_children():
            child.destroy()
        if view is None:
            game = self.gui.game
            view = build_player_personal_piles_view(game, game.current_player_index)
        if not view.enabled:
            return
        for entry in view.piles:
            owner, pile, cards = entry.owner, entry.pile_index, entry.cards
            frame = tk.LabelFrame(self.contents, text=f"{entry.owner_name} — Pile {pile + 1} ({entry.access})")
            frame.pack(fill="x", pady=3)
            if cards:
                listing = tk.Listbox(frame, height=min(4, len(cards)), exportselection=False)
                listing.pack(side="left", fill="both", expand=True)
                for index, card in enumerate(reversed(cards)):
                    listing.insert("end", f"{card}{' (top)' if index == 0 else ''}")
                bar = tk.Scrollbar(frame, command=listing.yview)
                bar.pack(side="left", fill="y")
                listing.configure(yscrollcommand=bar.set)
            else:
                tk.Label(frame, text="Empty").pack(side="left")
            tk.Button(frame, text="Take top card", state="normal" if entry.take.allowed else "disabled",
                      command=lambda o=owner, p=pile: self.gui.run_action(self.take, o, p)).pack(side="right")
        self.scroll_area.schedule_resize()

    def refresh_hand(self):
        self.gui.selection.hand_index = None
        self.gui.hand_frame.update_hand()
        self.gui.status_panel.update_status()
        self.gui.render_log()

    def take(self, owner, pile):
        result = self.gui.game.session.execute("take_personal_pile", owner=owner, pile_index=pile)
        if result.success:
            self.refresh_hand()
        else:
            messagebox.showwarning("Cannot take card", result.message, parent=self.gui.root)

    def choose_destination(self):
        if self.gui.selection.hand_index is None:
            messagebox.showwarning("No selection", "Select a card first.", parent=self.gui.root)
            return
        game = self.gui.game
        dialog = tk.Toplevel(self.gui.root)
        dialog.title("Play to personal pile")
        dialog.transient(self.gui.root)
        dialog.grab_set()
        choices = tk.Listbox(dialog, width=50, height=12, exportselection=False)
        choices.pack(fill="both", expand=True, padx=10, pady=10)
        destinations = []
        view = build_player_personal_piles_view(game, game.current_player_index, self.gui.selection.hand_index)
        for entry in view.piles:
            if entry.play.allowed:
                destinations.append((entry.owner, entry.pile_index))
                choices.insert("end", f"{entry.owner_name} — Pile {entry.pile_index + 1}")
        if not destinations:
            dialog.destroy()
            messagebox.showinfo("No accessible piles", "There are no personal piles available to this player.", parent=self.gui.root)
            return
        choices.selection_set(0)

        def play():
            selection = choices.curselection()
            if not selection:
                return
            owner, pile = destinations[selection[0]]
            index = self.gui.selection.hand_index
            def action():
                result = game.session.execute("play_personal_pile", card_index=index, owner=owner, pile_index=pile)
                if result.success:
                    self.refresh_hand()
                    dialog.destroy()
                else:
                    messagebox.showwarning("Cannot play card", result.message, parent=dialog)
            self.gui.run_action(action)
        tk.Button(dialog, text="Play", command=play).pack(side="right", padx=10, pady=(0, 10))
        tk.Button(dialog, text="Cancel", command=dialog.destroy).pack(side="right", pady=(0, 10))
