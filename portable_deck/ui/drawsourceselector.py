"""Local draw-source selection from core-owned public options."""
import tkinter as tk
from tkinter import ttk
from ..core.drawpiles import draw_pile_options


class DrawSourceSelector:
    def __init__(self, gui):
        self.gui = gui
        self.frame = tk.Frame(gui.options_bar)
        tk.Label(self.frame, text="Draw source:").pack(side="left")
        self.choice = ttk.Combobox(self.frame, state="readonly", width=28)
        self.choice.pack(side="left", padx=5)
        self.choice.bind("<<ComboboxSelected>>", self.select)
        self.refresh()

    def refresh(self):
        self.options = draw_pile_options(self.gui.game)
        ids = [pile.id for pile in self.options]
        if self.gui.draw_pile_id not in ids:
            self.gui.draw_pile_id = "main"
        self.choice.configure(values=[f"{pile.name} [{pile.id}] ({pile.card_count})" for pile in self.options])
        if self.gui.draw_pile_id in ids:
            self.choice.current(ids.index(self.gui.draw_pile_id))
        else:
            self.choice.set("")
        if len(self.options) > 1:
            self.frame.pack(side="left", padx=8)
        else:
            self.frame.pack_forget()

    def select(self, _event=None):
        index = self.choice.current()
        if 0 <= index < len(self.options):
            self.gui.draw_pile_id = self.options[index].id
            self.gui.refresh_action_availability()
