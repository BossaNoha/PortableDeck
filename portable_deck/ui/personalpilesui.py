"""Personal table piles and the actions available to the current player."""
import tkinter as tk
from tkinter import messagebox
from .contentscrollarea import ContentScrollArea


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

    def update(self):
        for child in self.contents.winfo_children():
            child.destroy()
        game = self.gui.game
        if not game.enable_table or not game.enable_personal_piles:
            return
        for owner, player in enumerate(game.players):
            for pile, cards in enumerate(game.personal_piles[owner]):
                rule = game.personal_pile_settings[owner][pile]
                frame = tk.LabelFrame(self.contents, text=f"{player.name} — Pile {pile + 1} ({rule['access']})")
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
                tk.Button(frame, text="Take top card", state="normal" if cards and game.can_access_personal_pile(owner, pile) else "disabled",
                          command=lambda o=owner, p=pile: self.gui.run_action(self.take, o, p)).pack(side="right")
        self.scroll_area.schedule_resize()

    def refresh_hand(self, message):
        self.gui.hand_frame.selected_index = None
        self.gui.hand_frame.update_hand()
        self.gui.status_panel.update_status()
        self.gui.log(message)

    def take(self, owner, pile):
        card = self.gui.game.take_from_personal_pile(owner, pile)
        if card:
            self.refresh_hand(f"{self.gui.current_player_name()} took {card} from a personal pile.")

    def choose_destination(self):
        if self.gui.hand_frame.selected_index is None:
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
        for owner, player in enumerate(game.players):
            for pile in range(game.personal_pile_count):
                if game.can_access_personal_pile(owner, pile):
                    destinations.append((owner, pile))
                    choices.insert("end", f"{player.name} — Pile {pile + 1}")
        choices.selection_set(0)

        def play():
            selection = choices.curselection()
            if not selection:
                return
            owner, pile = destinations[selection[0]]
            index = self.gui.hand_frame.selected_index
            def action():
                card = game.play_to_personal_pile(index + 1, owner, pile)
                if card:
                    self.refresh_hand(f"{self.gui.current_player_name()} played {card} to {game.players[owner].name}'s pile {pile + 1}.")
            self.gui.run_action(action)
            dialog.destroy()
        tk.Button(dialog, text="Play", command=play).pack(side="right", padx=10, pady=(0, 10))
        tk.Button(dialog, text="Cancel", command=dialog.destroy).pack(side="right", pady=(0, 10))
