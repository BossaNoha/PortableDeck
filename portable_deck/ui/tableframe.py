import tkinter as tk
import tkinter.font as tkfont


class TableFrame(tk.LabelFrame):
    """Shows the shared cards that players have played onto the table."""

    def __init__(self, master, game, **kwargs):
        super().__init__(master, text="Table", padx=8, pady=5, **kwargs)
        self.game = game
        self.selected_index = None
        self.selected_position = None
        self.restoring_view = True
        self.saved_view = dict(game.table_view_state)
        self.zoom_percent = 100
        self.base_font_size = abs(tkfont.nametofont("TkDefaultFont").actual("size"))
        self.card_font = tkfont.Font(self, font="TkDefaultFont")
        toolbar = tk.Frame(self)
        toolbar.pack(fill="x", pady=(0, 4))
        self.zoom_out_button = tk.Button(toolbar, text="Zoom out", command=lambda: self.change_zoom(-25))
        self.zoom_out_button.pack(side="left")
        self.zoom_label = tk.Label(toolbar, text="100%", width=6)
        self.zoom_label.pack(side="left")
        self.zoom_in_button = tk.Button(toolbar, text="Zoom in", command=lambda: self.change_zoom(25))
        self.zoom_in_button.pack(side="left")
        tk.Button(toolbar, text="Reset", command=lambda: self.change_zoom(100 - self.zoom_percent)).pack(side="left", padx=4)
        area = tk.Frame(self)
        area.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(area, width=420, height=300, highlightthickness=0)
        vertical = tk.Scrollbar(area, orient="vertical", command=self.canvas.yview)
        horizontal = tk.Scrollbar(area, orient="horizontal", command=self.canvas.xview)
        def track_x(first, last):
            horizontal.set(first, last)
            self.capture_view()
        def track_y(first, last):
            vertical.set(first, last)
            self.capture_view()
        self.canvas.configure(yscrollcommand=track_y, xscrollcommand=track_x)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")
        area.rowconfigure(0, weight=1)
        area.columnconfigure(0, weight=1)
        self.contents = tk.Frame(self.canvas)
        self.canvas.create_window((0, 0), window=self.contents, anchor="nw")
        self.contents.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<MouseWheel>", self.scroll_table)
        self.update_table()
        self.change_zoom(self.saved_view.get("zoom", 100) - 100)
        self.after(60, self.restore_view)

    def capture_view(self):
        if self.restoring_view or not self.game.enable_table:
            return
        self.game.table_view_state = {"zoom": self.zoom_percent, "x": self.canvas.xview()[0], "y": self.canvas.yview()[0]}

    def restore_view(self):
        if not self.winfo_exists():
            return
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self.canvas.xview_moveto(self.saved_view.get("x", 0))
        self.canvas.yview_moveto(self.saved_view.get("y", 0))
        self.restoring_view = False
        self.capture_view()

    def change_zoom(self, delta):
        self.zoom_percent = max(50, min(200, self.zoom_percent + delta))
        self.card_font.configure(size=max(1, round(self.base_font_size * self.zoom_percent / 100)))
        self.zoom_label.configure(text=f"{self.zoom_percent}%")
        self.zoom_out_button.configure(state="disabled" if self.zoom_percent == 50 else "normal")
        self.zoom_in_button.configure(state="disabled" if self.zoom_percent == 200 else "normal")
        self.capture_view()

    def scroll_table(self, event):
        if event.state & 4:
            self.change_zoom(25 if event.delta > 0 else -25)
        elif event.delta:
            steps = -int(event.delta / 120) or (-1 if event.delta > 0 else 1)
            if event.state & 1:
                self.canvas.xview_scroll(steps, "units")
            else:
                self.canvas.yview_scroll(steps, "units")
        return "break"

    def update_table(self):
        for widget in self.contents.winfo_children():
            widget.destroy()
        self.card_buttons = []
        if not self.game.enable_table:
            return
        if self.game.allow_play_in_front_of_players:
            self._draw_player_lanes()
            self.after_idle(self._expand_window_for_table)
            return
        # Legacy saves may contain table cards without explicit positions.
        for index, entry in enumerate(self.game.table_cards):
            if not isinstance(entry.get("position"), (tuple, list)):
                entry["position"] = [0, index]
        self._draw_spatial_table()
        self.after_idle(self._expand_window_for_table)

    def _draw_player_lanes(self):
        occupied = {}
        for index, entry in enumerate(self.game.table_cards):
            occupied.setdefault(tuple(entry["position"]), []).append((index, entry))
        available = self.game.available_table_positions()
        for player_index, player in enumerate(self.game.players):
            lane = tk.Frame(self.contents)
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
                        text=self._card_text(entry),
                        width=18,
                        command=lambda card_index=index: self.select_card(card_index),
                    )
                    self.card_buttons.append(button)
                    button._table_card_index = index
                    button.bind("<Button-3>", lambda event, card_index=index: self.open_card_menu(event, card_index))
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
                if button.cget("text") == "Empty":
                    button._table_drop_position = position
                button.pack(side="left", padx=3, pady=3)

    def _expand_window_for_table(self):
        """Update table controls without changing the session window size."""
        if not self.winfo_exists():
            return
        def configure(widget):
            if isinstance(widget, (tk.Button, tk.Label)):
                widget.configure(font=self.card_font)
            widget.bind("<MouseWheel>", self.scroll_table)
            if hasattr(widget, "_table_card_index") and hasattr(self, "on_drag_bind"):
                self.on_drag_bind(widget, widget._table_card_index)
            for child in widget.winfo_children():
                configure(child)
        configure(self.contents)
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

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
                    self.contents,
                    text=self._card_text(entry),
                    width=18,
                    command=lambda card_index=index: self.select_card(card_index),
                )
                self.card_buttons.append(button)
                button._table_card_index = index
                button.bind("<Button-3>", lambda event, card_index=index: self.open_card_menu(event, card_index))
                if index == self.selected_index:
                    button.config(bg="lightblue")
            else:
                button = tk.Button(
                    self.contents,
                    text="Empty",
                    width=18,
                    height=2,
                    command=lambda spot=position: self.select_slot(spot),
                )
                if position == self.selected_position:
                    button.config(bg="lightgreen")
            if button.cget("text") == "Empty":
                button._table_drop_position = position
            button.grid(
                row=row - min_row,
                column=column - min_column,
                padx=3,
                pady=3,
                sticky="ew",
            )
            self.contents.grid_columnconfigure(column - min_column, weight=1)

    def _draw_card(self, index):
        entry = self.game.table_cards[index]
        button = tk.Button(
            self.contents,
            text=self._card_text(entry),
            width=18,
            command=lambda card_index=index: self.select_card(card_index),
        )
        button.pack(side="left", padx=4, pady=3)
        self.card_buttons.append(button)
        button._table_card_index = index
        button.bind("<Button-3>", lambda event, card_index=index: self.open_card_menu(event, card_index))
        if index == self.selected_index:
            button.config(bg="lightblue")

    @staticmethod
    def _card_text(entry):
        if not entry.get("face_up", True):
            return "Face down"
        return f"{entry['card']}\n{entry['player']}"

    def open_card_menu(self, event, index):
        if hasattr(self, "on_card_context"):
            return self.on_card_context(event, index)
        return "break"

    def select_card(self, index):
        self.selected_index = None if self.selected_index == index else index
        if not self.game.allow_move_cards_on_table:
            self.selected_position = None
        self.update_table()
        if hasattr(self, "on_selection_changed"):
            self.on_selection_changed()
        if hasattr(self, "on_availability_changed"):
            self.on_availability_changed()

    def select_slot(self, position):
        if not self.game.allow_move_cards_on_table:
            self.selected_index = None
        self.selected_position = position
        self.update_table()
        if hasattr(self, "on_selection_changed"):
            self.on_selection_changed()
        if hasattr(self, "on_availability_changed"):
            self.on_availability_changed()

    def clear_selection(self):
        self.selected_index = None
        self.selected_position = None
        self.update_table()
        if hasattr(self, "on_selection_changed"):
            self.on_selection_changed()
        if hasattr(self, "on_availability_changed"):
            self.on_availability_changed()
