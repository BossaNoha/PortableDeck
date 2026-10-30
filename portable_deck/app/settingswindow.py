"""Window and form for configuring a new game."""
import os
import tkinter as tk
from tkinter import filedialog, messagebox

from .settings import BASE_DIR, load_default_settings, load_settings, resolve_deck_path, save_settings
from .advancedsettings import AdvancedSettingsPanel
from .deckbuilder import DeckBuilder
from .decklibrary import DeckLibrary
from .deckpreview import show_deck_preview
from ..ui.tooltip import add_tooltip
from ..core.deck import Deck


class SettingsWindow:
    def __init__(self, menu):
        self.menu = menu
        self.root = menu.root

    @property
    def settings(self):
        return self.menu.settings

    @settings.setter
    def settings(self, value):
        self.menu.settings = value

    def show_settings(self):
        self.menu.clear_window()
        self.root.minsize(1, 1)
        self.root.resizable(True, True)
        frame = tk.Frame(self.root, padx=20, pady=18)
        frame.pack(fill="both", expand=True)
        tk.Label(frame, text="Settings", font=("TkDefaultFont", 16, "bold")).grid(
            row=0, column=0, columnspan=3, pady=(0, 14)
        )

        basic = tk.LabelFrame(frame, text="New game", padx=10, pady=8)
        basic.grid(row=1, column=0, columnspan=3, sticky="ew")
        players_var = tk.StringVar(value=str(self.settings["num_players"]))
        cards_var = tk.StringVar(value=str(self.settings["cards_per_player"]))
        deck_var = tk.StringVar(value=str(self.settings["deck_path"]))
        save_var = tk.BooleanVar(value=bool(self.settings["save_discard_on_exit"]))
        custom_names_var = tk.BooleanVar(value=bool(self.settings["use_custom_player_names"]))
        add_tooltip(tk.Label(basic, text="Players:"), "Number of players in each new game.").grid(row=0, column=0, sticky="w", pady=4)
        add_tooltip(tk.Spinbox(basic, from_=1, to=20, textvariable=players_var, width=8), "Choose between 1 and 20 players.").grid(row=0, column=1, sticky="w")
        add_tooltip(tk.Label(basic, text="Starting hand:"), "Cards dealt to each player when a new game starts.").grid(row=1, column=0, sticky="w", pady=4)
        add_tooltip(tk.Spinbox(basic, from_=0, to=1000, textvariable=cards_var, width=8), "Number of cards dealt to each player at the start.").grid(row=1, column=1, sticky="w")
        add_tooltip(tk.Label(basic, text="Deck file (JSON):"), "The deck definition used for new games.").grid(row=2, column=0, sticky="w", pady=4)
        add_tooltip(tk.Entry(basic, textvariable=deck_var, width=38), "Path to a JSON deck file. Relative paths start from the project folder.").grid(row=2, column=1, sticky="ew")
        add_tooltip(tk.Button(basic, text="Browse…", command=lambda: self.browse_deck(deck_var)), "Browse for a deck JSON file.").grid(row=2, column=2, padx=(6, 0))
        add_tooltip(
            tk.Button(
                basic,
                text="Check deck",
                command=lambda: self.check_deck(deck_var, players_var, cards_var),
            ),
            "Validate the deck format and check whether it has enough cards for this setup.",
        ).grid(row=3, column=1, sticky="w", pady=(4, 0))
        add_tooltip(
            tk.Button(
                basic,
                text="Preview deck",
                command=lambda: self.preview_deck(deck_var),
            ),
            "View the cards and symbols in the selected deck.",
        ).grid(row=3, column=0, sticky="w", pady=(4, 0))
        add_tooltip(
            tk.Button(
                basic,
                text="Create deck…",
                command=lambda: self.create_deck(deck_var),
            ),
            "Build a custom deck, duplicate card groups, and select it for this game.",
        ).grid(row=3, column=2, sticky="e", pady=(4, 0))
        add_tooltip(
            tk.Button(
                basic,
                text="Manage decks…",
                command=lambda: self.manage_decks(deck_var),
            ),
            "View available decks and quickly select, edit, or duplicate one.",
        ).grid(row=4, column=1, sticky="w", pady=(5, 0))
        add_tooltip(tk.Checkbutton(
            basic,
            text="Save discard pile when the game window closes",
            variable=save_var,
        ), "Save the discard pile to the app's internal data when exiting the app.").grid(row=5, column=0, columnspan=3, sticky="w", pady=(8, 2))

        add_tooltip(tk.Checkbutton(
            basic,
            text="Use custom player names",
            variable=custom_names_var,
        ), "Show a separate name field for every player.").grid(row=6, column=0, columnspan=3, sticky="w", pady=3)

        names_frame = tk.LabelFrame(frame, text="Player names", padx=8, pady=5)
        names_frame.grid(row=5, column=0, columnspan=3, sticky="ew", pady=5)
        name_vars = []

        def refresh_name_inputs(*_):
            old_values = [var.get() for var in name_vars]
            for widget in names_frame.winfo_children():
                widget.destroy()
            name_vars.clear()
            if not custom_names_var.get():
                names_frame.grid_remove()
                self.root.after_idle(lambda: self._fit_window_to_frame(frame))
                return
            names_frame.grid()
            try:
                count = max(1, min(20, int(players_var.get())))
            except ValueError:
                count = 0
            saved_names = self.settings.get("player_names", [])
            for index in range(count):
                default_name = (
                    old_values[index] if index < len(old_values)
                    else saved_names[index] if index < len(saved_names)
                    else f"Player{index + 1}"
                )
                var = tk.StringVar(value=default_name)
                name_vars.append(var)
                add_tooltip(tk.Label(names_frame, text=f"Player {index + 1}:"), "Name shown for this player during the game.").grid(
                    row=index, column=0, sticky="w", padx=(0, 8), pady=2
                )
                add_tooltip(tk.Entry(names_frame, textvariable=var, width=28), "Enter a non-empty display name for this player.").grid(
                    row=index, column=1, sticky="ew", pady=2
                )
            names_frame.columnconfigure(1, weight=1)
            self.root.after_idle(lambda: self._fit_window_to_frame(frame))

        players_var.trace_add("write", refresh_name_inputs)
        custom_names_var.trace_add("write", refresh_name_inputs)
        refresh_name_inputs()

        advanced = AdvancedSettingsPanel(
            frame, self.root, self.settings,
            lambda: self._fit_window_to_frame(frame),
        )

        buttons = tk.Frame(frame)
        buttons.grid(row=9, column=0, columnspan=3, sticky="e", pady=(12, 0))
        tk.Button(buttons, text="Back", command=self.menu.show_main_menu).pack(side="left", padx=5)
        tk.Button(buttons, text="Restore Defaults", command=self.restore_defaults).pack(side="left", padx=5)
        tk.Button(
            buttons,
            text="Save settings",
            command=lambda: self.save_form(
                players_var, cards_var, deck_var, save_var, custom_names_var, name_vars,
                advanced,
            ),
        ).pack(side="left", padx=5)
        frame.columnconfigure(1, weight=1)
        self.root.after_idle(lambda: self._fit_window_to_frame(frame))

    def _fit_window_to_frame(self, frame):
        if not frame.winfo_exists():
            return
        self.root.update_idletasks()
        width = frame.winfo_reqwidth()
        height = frame.winfo_reqheight()
        self.root.minsize(width, height)
        self.root.geometry(f"{width}x{height}")

    def restore_defaults(self):
        if not messagebox.askyesno(
            "Restore defaults?",
            "Replace the current settings with the saved default settings?",
            parent=self.root,
        ):
            return
        self.settings = load_default_settings()
        try:
            save_settings(self.settings)
        except OSError as error:
            messagebox.showerror("Could not restore defaults", str(error), parent=self.root)
            self.settings = load_settings()
            return
        self.show_settings()

    def browse_deck(self, deck_var):
        path = filedialog.askopenfilename(
            title="Choose a deck file",
            initialdir=os.path.join(BASE_DIR, "decks"),
            filetypes=(("JSON files", "*.json"), ("All files", "*.*")),
        )
        if path:
            try:
                deck_var.set(os.path.relpath(path, BASE_DIR))
            except ValueError:
                deck_var.set(path)

    def create_deck(self, deck_var):
        def use_created_deck(path):
            try:
                deck_var.set(os.path.relpath(path, BASE_DIR))
            except ValueError:
                deck_var.set(path)

        DeckBuilder(
            self.root,
            resolve_deck_path(deck_var.get().strip()) if deck_var.get().strip() else "",
            os.path.join(BASE_DIR, "decks"),
            use_created_deck,
        )

    def manage_decks(self, deck_var):
        def use_deck(path):
            try:
                deck_var.set(os.path.relpath(path, BASE_DIR))
            except ValueError:
                deck_var.set(path)

        DeckLibrary(self.root, os.path.join(BASE_DIR, "decks"), use_deck).show()

    def preview_deck(self, deck_var):
        path = deck_var.get().strip()
        resolved = resolve_deck_path(path) if path else ""
        show_deck_preview(self.root, resolved)

    def check_deck(self, deck_var, players_var, cards_var):
        deck_path = deck_var.get().strip()
        if not deck_path:
            messagebox.showerror("Deck check failed", "Choose a deck file first.", parent=self.root)
            return
        try:
            deck = Deck(resolve_deck_path(deck_path))
            players = int(players_var.get())
            cards_per_player = int(cards_var.get())
            if players < 1 or cards_per_player < 0:
                raise ValueError("Enter at least one player and a non-negative hand size.")
        except (OSError, ValueError, TypeError) as error:
            messagebox.showerror("Deck check failed", str(error), parent=self.root)
            return
        required = players * cards_per_player
        available = len(deck.flat_deck)
        if required > available:
            messagebox.showwarning(
                "Deck is too small",
                f"This setup needs {required} cards ({players} players × {cards_per_player}), "
                f"but the deck contains {available}.",
                parent=self.root,
            )
            return
        messagebox.showinfo(
            "Deck is valid",
            f"Deck format is valid and contains {available} cards. "
            f"This setup needs {required}.",
            parent=self.root,
        )

    def save_form(
        self, players_var, cards_var, deck_var, save_var, custom_names_var, name_vars,
        advanced_panel,
    ):
        try:
            num_players = int(players_var.get())
            cards_per_player = int(cards_var.get())
            advanced_values = advanced_panel.values()
            deck_path = deck_var.get().strip()
            if num_players < 1 or cards_per_player < 0:
                raise ValueError
            if not deck_path or not os.path.isfile(resolve_deck_path(deck_path)):
                messagebox.showerror("Invalid deck", "Choose an existing deck JSON file.", parent=self.root)
                return
            try:
                deck = Deck(resolve_deck_path(deck_path))
            except (OSError, ValueError) as error:
                messagebox.showerror("Invalid deck", str(error), parent=self.root)
                return
            if len(deck.flat_deck) < num_players * cards_per_player:
                messagebox.showerror(
                    "Deck is too small",
                    f"This setup needs {num_players * cards_per_player} cards, "
                    f"but the deck contains {len(deck.flat_deck)}.",
                    parent=self.root,
                )
                return
            player_names = [var.get().strip() for var in name_vars] if custom_names_var.get() else []
            if custom_names_var.get() and (len(player_names) != num_players or any(not name for name in player_names)):
                messagebox.showerror("Invalid names", "Enter a name for every player.", parent=self.root)
                return
        except ValueError:
            messagebox.showerror(
                "Invalid settings",
                "Players must be at least 1 and cards per player 0 or more. Advanced numeric settings must also be valid.",
                parent=self.root,
            )
            return

        self.settings = {
            "num_players": num_players,
            "cards_per_player": cards_per_player,
            "deck_path": deck_path,
            "save_discard_on_exit": save_var.get(),
            "use_custom_player_names": custom_names_var.get(),
            "player_names": player_names,
            **advanced_values,
        }
        try:
            save_settings(self.settings)
        except OSError as error:
            messagebox.showerror("Could not save", str(error), parent=self.root)
            return
        self.menu.show_main_menu()

