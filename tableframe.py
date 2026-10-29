import tkinter as tk


class TableFrame(tk.LabelFrame):
    """Shows the shared cards that players have played onto the table."""

    def __init__(self, master, game, **kwargs):
        super().__init__(master, text="Table", padx=8, pady=5, **kwargs)
        self.game = game
        self.selected_index = None
        self.selected_position = None
        self.update_table()

    def update_table(self):
        for widget in self.winfo_children():
            widget.destroy()
        self.card_buttons = []
        if self.game.allow_play_in_front_of_players:
            self._draw_player_lanes()
            self.after_idle(self._expand_window_for_table)
            return
        if self.game.allow_positioned_play or self.game.allow_move_cards_on_table:
            self._draw_spatial_table()
            self.after_idle(self._expand_window_for_table)
            return
        if not self.game.table_cards:
            tk.Label(self, text="No cards on the table.").pack(anchor="w")
            self.after_idle(self._expand_window_for_table)
            return
        for index, entry in enumerate(self.game.table_cards):
            self._draw_card(index)
        self.after_idle(self._expand_window_for_table)

    def _draw_player_lanes(self):
        occupied = {}
        for index, entry in enumerate(self.game.table_cards):
            occupied.setdefault(tuple(entry["position"]), []).append((index, entry))
        available = self.game.available_table_positions()
        for player_index, player in enumerate(self.game.players):
            lane = tk.Frame(self)
            lane.pack(anchor="w", fill="x", pady=2)
            tk.Label(lane, text=f"{player.name}:", width=14, anchor="w").pack(side="left")
            columns = sorted(
                column for row, column in set(occupied) | available
                if row == player_index
            )
            for column in columns:
                position = (player_index, column)
                if position in occupied:
                    index, entry = occupied[position][-1]
                    button = tk.Button(
                        lane,
                        text=f"{entry['card']}\n{entry['player']}",
                        width=18,
                        command=lambda card_index=index: self.select_card(card_index),
                    )
                    self.card_buttons.append(button)
                    if index == self.selected_index:
                        button.config(bg="lightblue")
                else:
                    button = tk.Button(
                        lane,
                        text="Empty",
                        width=18,
                        height=2,
                        command=lambda spot=position: self.select_slot(spot),
                    )
                    if position == self.selected_position:
                        button.config(bg="lightgreen")
                button.pack(side="left", padx=3, pady=3)

    def _expand_window_for_table(self):
        """Grow the game window when the table needs more room for its cards."""
        root = self.winfo_toplevel()
        root.update_idletasks()
        width = max(root.winfo_width(), root.winfo_reqwidth())
        height = max(root.winfo_height(), root.winfo_reqheight())
        if width > root.winfo_width() or height > root.winfo_height():
            root.geometry(f"{width}x{height}")

    def _draw_spatial_table(self):
        occupied = {}
        for index, entry in enumerate(self.game.table_cards):
            occupied.setdefault(tuple(entry["position"]), []).append((index, entry))
        available = self.game.available_table_positions()
        positions = set(occupied) | available
        min_row = min(row for row, _ in positions)
        min_column = min(column for _, column in positions)

        for position in sorted(positions):
            row, column = position
            if position in occupied:
                index, entry = occupied[position][-1]
                button = tk.Button(
                    self,
                    text=f"{entry['card']}\n{entry['player']}",
                    width=18,
                    command=lambda card_index=index: self.select_card(card_index),
                )
                self.card_buttons.append(button)
                if index == self.selected_index:
                    button.config(bg="lightblue")
            else:
                button = tk.Button(
                    self,
                    text="Empty",
                    width=18,
                    height=2,
                    command=lambda spot=position: self.select_slot(spot),
                )
                if position == self.selected_position:
                    button.config(bg="lightgreen")
            button.grid(
                row=row - min_row,
                column=column - min_column,
                padx=3,
                pady=3,
                sticky="ew",
            )
            self.grid_columnconfigure(column - min_column, weight=1)

    def _draw_card(self, index):
        entry = self.game.table_cards[index]
        button = tk.Button(
            self,
            text=f"{entry['card']}\n{entry['player']}",
            width=18,
            command=lambda card_index=index: self.select_card(card_index),
        )
        button.pack(side="left", padx=4, pady=3)
        self.card_buttons.append(button)
        if index == self.selected_index:
            button.config(bg="lightblue")

    def select_card(self, index):
        self.selected_index = index
        if not self.game.allow_move_cards_on_table:
            self.selected_position = None
        self.update_table()

    def select_slot(self, position):
        if not self.game.allow_move_cards_on_table:
            self.selected_index = None
        self.selected_position = position
        self.update_table()

    def clear_selection(self):
        self.selected_index = None
        self.selected_position = None
        self.update_table()
