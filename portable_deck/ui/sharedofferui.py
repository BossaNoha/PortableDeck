"""Public offer screen keeps private hands hidden while players choose."""
import tkinter as tk
from tkinter import messagebox
from ..core.sharedoffer import shared_offer_view


class SharedOfferUI:
    def __init__(self, gui):
        self.gui = gui
        self.frame = None

    def refresh(self):
        view = shared_offer_view(self.gui.game)
        if not view.active and self.frame is None:
            return
        if self.frame is None:
            self.packing = self.gui.layout_frame.pack_info()
            self.gui.layout_frame.pack_forget()
            self.frame = tk.Frame(self.gui.root, padx=20, pady=20)
            self.frame.pack(fill="both", expand=True)
        for widget in self.frame.winfo_children():
            widget.destroy()
        if view.active:
            tk.Label(self.frame, text=f"Shared offer — {view.player_name} chooses", font=("TkDefaultFont", 16, "bold")).pack(pady=10)
            self.choices = tk.Listbox(self.frame, exportselection=False, width=48, height=12)
            self.choices.pack(fill="both", expand=True)
            for card in view.cards:
                self.choices.insert("end", card)
            self.choices.selection_set(0)
            tk.Button(self.frame, text="Take selected card", command=self.choose).pack(pady=8)
        else:
            tk.Label(self.frame, text="Shared offer complete. Return the device to the current player.", wraplength=500).pack(pady=20)
            tk.Button(self.frame, text="Resume turn — show cards", command=self.resume).pack(pady=8)
        if self.gui.session.undo_availability().allowed:
            tk.Button(self.frame, text="Undo", command=self.gui.undo).pack(pady=5)

    def choose(self):
        selected = self.choices.curselection()
        if not selected:
            return
        result = self.gui.run_action(lambda: self.gui.session.execute("choose_shared_offer", card_index=selected[0]))
        if not result.success:
            messagebox.showwarning("Cannot choose card", result.message, parent=self.gui.root)
        return result

    def resume(self):
        if shared_offer_view(self.gui.game).active:
            return
        self.frame.destroy()
        self.frame = None
        self.gui.layout_frame.pack(**self.packing)
