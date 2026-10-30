"""GUI for creating reusable JSON card decks."""
import json
import os
import tkinter as tk
from tkinter import filedialog, messagebox

from ..core.deck import Deck


class DeckBuilder:
    def __init__(self, parent, initial_path, decks_dir, on_created, edit_path=None):
        self.parent = parent
        self.decks_dir = decks_dir
        self.on_created = on_created
        self.edit_path = edit_path
        self.groups = []
        self.window = tk.Toplevel(parent)
        self.window.title("Edit deck" if edit_path else "Create a deck")
        self.window.transient(parent)
        self.window.grab_set()
        self.window.geometry("700x560")
        self.window.minsize(560, 400)

        self.name_var = tk.StringVar(value="my_deck")
        top = tk.Frame(self.window, padx=12, pady=10)
        top.pack(fill="x")
        tk.Label(top, text="Deck name:").pack(side="left")
        tk.Entry(top, textvariable=self.name_var, width=28).pack(side="left", padx=6)
        tk.Button(top, text="New blank", command=self.start_blank).pack(side="right")
        tk.Button(top, text="Load existing deck…", command=self.load_deck).pack(side="right", padx=(0, 5))

        tk.Label(
            self.window,
            text="Create one card list per symbol. Use commas or new lines between card values. "
                 "Duplicate a group to reuse its cards with another symbol.",
            justify="left", wraplength=660, padx=12,
        ).pack(anchor="w", pady=(0, 8))

        list_frame = tk.Frame(self.window, padx=12)
        list_frame.pack(fill="both", expand=True)
        list_frame.rowconfigure(0, weight=1)
        list_frame.columnconfigure(0, weight=1)
        self.canvas = tk.Canvas(list_frame, highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar = tk.Scrollbar(list_frame, orient="vertical", command=self.canvas.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.rows_frame = tk.Frame(self.canvas)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.rows_frame, anchor="nw")
        self.rows_frame.bind("<Configure>", self._update_scroll_region)
        self.canvas.bind("<Configure>", self._resize_rows)

        actions = tk.Frame(self.window, padx=12, pady=10)
        actions.pack(fill="x")
        tk.Button(actions, text="Add symbol", command=self.add_group).pack(side="left")
        save_label = "Save changes" if edit_path else "Save deck…"
        tk.Button(actions, text=save_label, command=self.save_deck).pack(side="right", padx=(5, 0))
        tk.Button(actions, text="Cancel", command=self.window.destroy).pack(side="right")

        if initial_path:
            try:
                self.load_path(initial_path)
            except (OSError, ValueError, KeyError, TypeError):
                self.add_group()
        else:
            self.add_group()
        self.window.bind("<Escape>", lambda _event: self.window.destroy())

    def _update_scroll_region(self, _event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _resize_rows(self, event):
        self.canvas.itemconfigure(self.canvas_window, width=event.width)

    def add_group(self, symbol="", cards=""):
        row = tk.LabelFrame(self.rows_frame, text=f"Card group {len(self.groups) + 1}", padx=8, pady=6)
        row.pack(fill="x", pady=(0, 7))
        row.columnconfigure(1, weight=1)
        symbol_var = tk.StringVar(value=symbol)
        tk.Label(row, text="Symbol:").grid(row=0, column=0, sticky="w", padx=(0, 6))
        tk.Entry(row, textvariable=symbol_var, width=22).grid(row=0, column=1, sticky="ew")
        tk.Label(row, text="Cards (one per line or comma-separated):").grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(5, 0)
        )
        text = tk.Text(row, height=3, wrap="word")
        text.grid(row=2, column=0, columnspan=2, sticky="ew")
        if cards:
            text.insert("1.0", "\n".join(str(value) for value in cards))
        controls = tk.Frame(row)
        controls.grid(row=0, column=2, rowspan=3, padx=(8, 0), sticky="n")
        group = {"frame": row, "symbol": symbol_var, "cards": text}
        self.groups.append(group)
        tk.Button(controls, text="Duplicate", command=lambda: self.duplicate_group(group)).pack(fill="x")
        tk.Button(controls, text="Remove", command=lambda: self.remove_group(group)).pack(fill="x", pady=(5, 0))
        self._renumber_groups()
        self.window.after_idle(self._update_scroll_region)

    def duplicate_group(self, source):
        self.add_group(
            "", self._parse_cards(source["cards"].get("1.0", "end-1c")),
        )
        self.groups[-1]["symbol"].set(f"{source['symbol'].get().strip()} copy".strip())

    def remove_group(self, group):
        if len(self.groups) == 1:
            messagebox.showinfo("Keep one group", "A deck must have at least one card group.", parent=self.window)
            return
        self.groups.remove(group)
        group["frame"].destroy()
        self._renumber_groups()
        self.window.after_idle(self._update_scroll_region)

    def _renumber_groups(self):
        for index, group in enumerate(self.groups, start=1):
            group["frame"].configure(text=f"Card group {index}")

    @staticmethod
    def _parse_cards(raw):
        return [value.strip() for line in raw.splitlines() for value in line.split(",") if value.strip()]

    def load_deck(self):
        path = filedialog.askopenfilename(
            title="Load a deck to edit", initialdir=self.decks_dir,
            filetypes=(("JSON deck", "*.json"), ("All files", "*.*")), parent=self.window,
        )
        if path:
            try:
                self.load_path(path)
                if self.edit_path:
                    self.edit_path = path
                    self.window.title("Edit deck")
            except (OSError, ValueError, KeyError, TypeError) as error:
                messagebox.showerror("Could not load deck", str(error), parent=self.window)

    def load_path(self, path):
        deck = Deck(path)
        stem = os.path.splitext(os.path.basename(path))[0]
        self.name_var.set(stem if self.edit_path else f"custom_{stem}")
        for group in self.groups:
            group["frame"].destroy()
        self.groups.clear()
        for symbol, cards in zip(deck.types, deck.cards):
            self.add_group(symbol, cards)

    def start_blank(self):
        for group in self.groups:
            group["frame"].destroy()
        self.groups.clear()
        self.name_var.set("my_deck")
        self.add_group()

    def save_deck(self):
        name = self.name_var.get().strip()
        if not name:
            messagebox.showerror("Deck name required", "Enter a name for this deck.", parent=self.window)
            return
        types, cards = [], []
        for index, group in enumerate(self.groups, start=1):
            symbol = group["symbol"].get().strip()
            values = self._parse_cards(group["cards"].get("1.0", "end-1c"))
            if not symbol:
                messagebox.showerror("Symbol required", f"Enter a symbol for card group {index}.", parent=self.window)
                return
            if not values:
                messagebox.showerror("Cards required", f"Add at least one card to '{symbol}'.", parent=self.window)
                return
            types.append(symbol)
            cards.append(values)
        data = {"types": types, "cards": cards}
        try:
            Deck.validate_data(data)
        except ValueError as error:
            messagebox.showerror("Invalid deck", str(error), parent=self.window)
            return

        if self.edit_path:
            path = self.edit_path
            if not messagebox.askyesno(
                "Save changes?", f"Replace '{os.path.basename(path)}' with these changes?",
                parent=self.window,
            ):
                return
        else:
            filename = name if name.lower().endswith(".json") else f"{name}.json"
            path = filedialog.asksaveasfilename(
                title="Save new deck", initialdir=self.decks_dir, initialfile=filename,
                defaultextension=".json", filetypes=(("JSON deck", "*.json"),), parent=self.window,
            )
            if not path:
                return
            if not path.lower().endswith(".json"):
                path += ".json"
        temporary_path = path + ".tmp"
        try:
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            with open(temporary_path, "w", encoding="utf-8") as deck_file:
                json.dump(data, deck_file, indent=2, ensure_ascii=False)
                deck_file.write("\n")
            os.replace(temporary_path, path)
        except OSError as error:
            if os.path.exists(temporary_path):
                try:
                    os.remove(temporary_path)
                except OSError:
                    pass
            messagebox.showerror("Could not save deck", str(error), parent=self.window)
            return
        self.on_created(path)
        self.window.destroy()
