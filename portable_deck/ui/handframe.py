"""Responsive player hand with at most four visible rows."""
import math
import tkinter as tk


class HandFrame(tk.LabelFrame):
    def __init__(self, master, game_gui, **kwargs):
        super().__init__(master, text="Your Hand", padx=5, pady=5, **kwargs)
        self.game_gui = game_gui
        self.selected_index = None
        self.card_buttons = []
        self.pending_layout = False
        self.hand_owner = None
        self.canvas = tk.Canvas(self, width=1, height=1, highlightthickness=0)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.cards_frame = tk.Frame(self.canvas)
        self.window_item = self.canvas.create_window((0, 0), window=self.cards_frame, anchor="nw")
        self.canvas.bind("<Configure>", self.schedule_layout)
        self.canvas.bind("<MouseWheel>", self.scroll)
        self.cards_frame.bind("<MouseWheel>", self.scroll)

    def update_hand(self):
        for widget in self.cards_frame.winfo_children():
            widget.destroy()
        self.card_buttons = []
        game = self.game_gui.game
        owner = game.current_player_index
        if owner != self.hand_owner:
            self.canvas.yview_moveto(0)
            self.hand_owner = owner
        player = self.game_gui.current_player()
        if self.selected_index is not None and self.selected_index >= len(player.hand):
            self.selected_index = None
        visible = game.can_view_hand(owner, owner)
        for i, card in enumerate(player.hand):
            button = tk.Button(self.cards_frame, text=(card + " (revealed)") if i in player.revealed_indices else card if visible else f"Hidden card {i + 1}",
                               width=18, wraplength=120, command=lambda index=i: self.select_card(index))
            button.bind("<MouseWheel>", self.scroll)
            button.bind("<Button-3>", lambda event, index=i: self.open_card_menu(event, index))
            if i == self.selected_index:
                button.configure(bg="lightblue")
            self.card_buttons.append(button)
        self.schedule_layout()
        if hasattr(self.game_gui, "context_actions"):
            self.game_gui.context_actions.refresh()

    def schedule_layout(self, _event=None):
        if not self.pending_layout:
            self.pending_layout = True
            self.after_idle(self.arrange_cards)

    def arrange_cards(self):
        self.pending_layout = False
        if not self.winfo_exists():
            return
        width = max(1, self.canvas.winfo_width())
        cell_width = max((button.winfo_reqwidth() + 10 for button in self.card_buttons), default=150)
        cell_height = max((button.winfo_reqheight() + 10 for button in self.card_buttons), default=36)
        columns = max(1, width // cell_width)
        rows = math.ceil(len(self.card_buttons) / columns)
        content_height = max(1, rows * cell_height)
        self.canvas.itemconfigure(self.window_item, width=width, height=content_height)
        actual_width = width // columns
        for i, button in enumerate(self.card_buttons):
            button.place(x=(i % columns) * actual_width + 5, y=(i // columns) * cell_height + 5,
                         width=max(1, actual_width - 10), height=cell_height - 10)
        requested_height = max(1, min(4, rows) * cell_height)
        if self.canvas.winfo_reqheight() != requested_height:
            self.canvas.configure(height=requested_height)
        self.canvas.configure(scrollregion=(0, 0, width, content_height))
        if rows > 4 and not self.scrollbar.winfo_manager():
            self.scrollbar.pack(side="right", fill="y", before=self.canvas)
        elif rows <= 4 and self.scrollbar.winfo_manager():
            self.scrollbar.pack_forget()
            self.canvas.yview_moveto(0)

    def scroll(self, event):
        if self.scrollbar.winfo_manager() and event.delta:
            steps = -int(event.delta / 120) or (-1 if event.delta > 0 else 1)
            self.canvas.yview_scroll(steps, "units")
            return "break"

    def open_card_menu(self, event, index):
        from .cardcontextmenu import show_card_menu
        return show_card_menu(self.game_gui, event, "hand", index)

    def select_card(self, index):
        self.selected_index = None if self.selected_index == index else index
        if hasattr(self.game_gui, "context_actions"):
            self.game_gui.table_frame.selected_index = None
            self.game_gui.table_frame.update_table()
            self.game_gui.context_actions.refresh()
        for i, button in enumerate(self.card_buttons):
            button.configure(bg="lightblue" if i == self.selected_index else "SystemButtonFace")
