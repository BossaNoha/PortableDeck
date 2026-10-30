#handframe.py
import tkinter as tk

class HandFrame(tk.LabelFrame):
    """
    Displays the current player's hand as buttons.
    Clicking a card selects it and highlights the button.
    """
    def __init__(self, master, game_gui, **kwargs):
        super().__init__(master, text="Your Hand", padx=5, pady=5, **kwargs)
        self.game_gui = game_gui
        self.selected_index = None
        self.card_buttons = []  # keep references to buttons

    def update_hand(self):
        # Remove old buttons
        for widget in self.winfo_children():
            widget.destroy()

        self.card_buttons = []
        player = self.game_gui.current_player()

        for i, card in enumerate(player.hand):
            btn = tk.Button(
                self,
                text=card,
                width=18,
                command=lambda idx=i: self.select_card(idx)
            )
            btn.pack(side="left", padx=5, pady=5)
            self.card_buttons.append(btn)

            # Highlight if currently selected
            if i == self.selected_index:
                btn.config(bg="lightblue")

    def select_card(self, index):
        # Toggle selection: deselect if already selected
        if self.selected_index == index:
            self.card_buttons[index].config(bg="SystemButtonFace")
            self.selected_index = None
        else:
            # Reset all buttons
            for btn in self.card_buttons:
                btn.config(bg="SystemButtonFace")
            # Highlight new selection
            self.card_buttons[index].config(bg="lightblue")
            self.selected_index = index