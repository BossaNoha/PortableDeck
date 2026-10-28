import tkinter as tk


class TableFrame(tk.LabelFrame):
    """Shows the shared cards that players have played onto the table."""

    def __init__(self, master, game, **kwargs):
        super().__init__(master, text="Table", padx=8, pady=5, **kwargs)
        self.game = game
        self.selected_index = None
        self.update_table()

    def update_table(self):
        for widget in self.winfo_children():
            widget.destroy()
        self.card_buttons = []
        if not self.game.table_cards:
            tk.Label(self, text="No cards on the table.").pack(anchor="w")
            return
        for index, entry in enumerate(self.game.table_cards):
            button = tk.Button(
                self,
                text=f"{entry['card']}\n{entry['player']}",
                width=16,
                command=lambda card_index=index: self.select_card(card_index),
            )
            button.pack(side="left", padx=4, pady=3)
            self.card_buttons.append(button)
            if index == self.selected_index:
                button.config(bg="lightblue")

    def select_card(self, index):
        self.selected_index = index
        self.update_table()

    def clear_selection(self):
        if self.selected_index is not None:
            self.selected_index = None
            self.update_table()
