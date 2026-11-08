"""Window and form for configuring a new game."""
import os
import tkinter as tk
from tkinter import filedialog, messagebox

from .settings import BASE_DIR, load_default_settings, load_settings, resolve_deck_path, save_settings
from .gamesettings import GameSettingsPanel
from .basicsettings import BasicSettingsPanel
from .deckbuilder import DeckBuilder
from .decklibrary import DeckLibrary
from .deckpreview import show_deck_preview
from ..ui.tooltip import add_tooltip
from ..ui.collapsiblesection import CollapsibleSection
from ..ui.contentscrollarea import ContentScrollArea
from ..core.deck import Deck


class SettingsWindow:
    def __init__(self, menu):
        self.menu = menu
        self.root = menu.root

    @property
    def settings(self):
        return self.form_settings if getattr(self, "form_settings", None) is not None else self.menu.settings

    @settings.setter
    def settings(self, value):
        self.menu.settings = value
        self.form_settings = None

    def show_settings(self):
        self.menu.clear_window()
        self.root.minsize(1, 1)
        self.root.resizable(True, True)
        self.viewport = ContentScrollArea(self.root, width=700)
        self.viewport.pack(fill="both", expand=True)
        frame = tk.Frame(self.viewport.contents, padx=20, pady=18)
        frame.pack(fill="x")
        tk.Label(frame, text="Settings", font=("TkDefaultFont", 16, "bold")).grid(
            row=0, column=0, columnspan=3, pady=(0, 14)
        )

        basic = tk.LabelFrame(frame, text="New game", padx=10, pady=8)
        basic.grid(row=1, column=0, columnspan=3, sticky="ew")
        players_var = tk.StringVar(value=str(self.settings["num_players"]))
        cards_var = tk.StringVar(value=str(self.settings["cards_per_player"]))
        deck_var = tk.StringVar(value=str(self.settings["deck_path"]))
        custom_names_var = tk.BooleanVar(value=bool(self.settings["use_custom_player_names"]))
        add_tooltip(tk.Label(basic, text="Players:"), "Number of players in each new game.").grid(row=0, column=0, sticky="w", pady=4)
        add_tooltip(tk.Spinbox(basic, from_=1, to=20, textvariable=players_var, width=8), "Choose between 1 and 20 players.").grid(row=0, column=1, sticky="w")
        add_tooltip(tk.Label(basic, text="Starting hand:"), "Cards dealt to each player when a new game starts.").grid(row=1, column=0, sticky="w", pady=4)
        add_tooltip(tk.Spinbox(basic, from_=0, to=1000, textvariable=cards_var, width=8), "Number of cards dealt to each player at the start.").grid(row=1, column=1, sticky="w")
        deck_section = CollapsibleSection(
            frame, "Deck", lambda: self._fit_window_to_frame(frame)
        )
        deck_section.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(8, 0))
        deck_controls = deck_section.content
        deck_controls.columnconfigure(1, weight=1)
        add_tooltip(tk.Label(deck_controls, text="Deck file (JSON):"), "The deck definition used for new games.").grid(row=0, column=0, sticky="w", pady=4)
        add_tooltip(tk.Entry(deck_controls, textvariable=deck_var, width=38), "Path to a JSON deck file. Relative paths start from the project folder.").grid(row=0, column=1, sticky="ew")
        add_tooltip(tk.Button(deck_controls, text="Browse…", command=lambda: self.browse_deck(deck_var)), "Browse for a deck JSON file.").grid(row=0, column=2, padx=(6, 0))
        deck_buttons = tk.Frame(deck_controls)
        deck_buttons.grid(row=1, column=0, columnspan=3, sticky="w", pady=(4, 0))
        add_tooltip(
            tk.Button(
                deck_buttons,
                text="Check deck",
                command=lambda: self.check_deck(deck_var, players_var, cards_var),
            ),
            "Validate the deck format and check whether it has enough cards for this setup.",
        ).pack(side="left", padx=(0, 6))
        add_tooltip(
            tk.Button(
                deck_buttons,
                text="Preview deck",
                command=lambda: self.preview_deck(deck_var),
            ),
            "View the cards and symbols in the selected deck.",
        ).pack(side="left", padx=(0, 6))
        add_tooltip(
            tk.Button(
                deck_buttons,
                text="Create deck…",
                command=lambda: self.create_deck(deck_var),
            ),
            "Build a custom deck, duplicate card groups, and select it for this game.",
        ).pack(side="left", padx=(0, 6))
        add_tooltip(
            tk.Button(
                deck_buttons,
                text="Manage decks…",
                command=lambda: self.manage_decks(deck_var),
            ),
            "View available decks and quickly select, edit, or duplicate one.",
        ).pack(side="left", padx=(0, 6))
        add_tooltip(tk.Checkbutton(
            basic,
            text="Custom player names",
            variable=custom_names_var,
        ), "Show a separate name field for every player.").grid(row=6, column=0, columnspan=3, sticky="w", pady=3)

        names_frame = tk.LabelFrame(frame, text="Player names", padx=8, pady=5)
        names_frame.grid(row=2, column=0, columnspan=3, sticky="ew", pady=5)
        name_vars = []
        game_settings = None

        def player_name(owner):
            if custom_names_var.get() and owner < len(name_vars):
                return name_vars[owner].get().strip() or f"Player {owner + 1}"
            return f"Player {owner + 1}"

        def update_pile_names(*_):
            if game_settings is not None:
                game_settings.personal_piles.update_names()
                game_settings.roles_teams.update_names()

        def refresh_name_inputs(*_):
            old_values = [var.get() for var in name_vars]
            for widget in names_frame.winfo_children():
                widget.destroy()
            name_vars.clear()
            if not custom_names_var.get():
                names_frame.grid_remove()
                update_pile_names()
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
                var.trace_add("write", update_pile_names)
                add_tooltip(tk.Label(names_frame, text=f"Player {index + 1}:"), "Name shown for this player during the game.").grid(
                    row=index, column=0, sticky="w", padx=(0, 8), pady=2
                )
                add_tooltip(tk.Entry(names_frame, textvariable=var, width=28), "Enter a non-empty display name for this player.").grid(
                    row=index, column=1, sticky="ew", pady=2
                )
            update_pile_names()
            names_frame.columnconfigure(1, weight=1)
            self.root.after_idle(lambda: self._fit_window_to_frame(frame))

        players_var.trace_add("write", refresh_name_inputs)
        custom_names_var.trace_add("write", refresh_name_inputs)
        refresh_name_inputs()

        basic_settings = BasicSettingsPanel(
            frame, self.settings, lambda: self._fit_window_to_frame(frame)
        )
        game_settings = GameSettingsPanel(
            frame, self.root, self.settings,
            lambda: self._fit_window_to_frame(frame),
            players_var=players_var, player_name=player_name, custom_names_var=custom_names_var,
            color_categories_var=basic_settings.color_categories_var,
        )

        self.game_settings_panel = game_settings

        buttons = tk.Frame(frame)
        buttons.grid(row=9, column=0, columnspan=3, sticky="e", pady=(12, 0))
        tk.Button(buttons, text="Back", command=self.menu.show_main_menu).pack(side="left", padx=5)
        tk.Button(buttons, text="Restore Defaults", command=self.restore_defaults).pack(side="left", padx=5)
        def submit(mode="use"):
            self.save_form(players_var, cards_var, deck_var, custom_names_var, name_vars,
                           game_settings, basic_settings, mode=mode)
        tk.Button(buttons, text="Use current settings", command=submit).pack(side="left", padx=5)
        tk.Button(buttons, text="Save settings", command=lambda: submit("named")).pack(side="left", padx=5)
        self.current_app_settings = lambda: {**basic_settings.values(), "num_players": int(players_var.get())}
        tk.Button(buttons, text="Load settings", command=self.load_named_settings).pack(side="left", padx=5)
        frame.columnconfigure(1, weight=1)
        self.root.after_idle(lambda: self._fit_window_to_frame(frame))

    def save_named_settings(self, selected_settings):
        from .settingspresets import PRESETS_DIR, write_preset
        os.makedirs(PRESETS_DIR, exist_ok=True)
        path = filedialog.asksaveasfilename(title="Save settings", initialdir=PRESETS_DIR,
                                          initialfile="My settings.json", defaultextension=".json",
                                          filetypes=(("Settings", "*.json"),), parent=self.root)
        if not path:
            return
        try:
            write_preset(path, selected_settings)
        except (OSError, ValueError, TypeError) as error:
            messagebox.showerror("Could not save settings", str(error), parent=self.root)
            return
        from .configurationinfo import configuration_values
        self.form_settings = dict(selected_settings)
        self.form_settings["configuration_name"] = os.path.splitext(os.path.basename(path))[0]
        self.form_settings["configuration_baseline"] = configuration_values(selected_settings)
        messagebox.showinfo("Settings saved", f"Saved as {os.path.splitext(os.path.basename(path))[0]}.", parent=self.root)

    def load_named_settings(self):
        from .settingspresets import PRESETS_DIR, read_preset
        os.makedirs(PRESETS_DIR, exist_ok=True)
        path = filedialog.askopenfilename(title="Load settings", initialdir=PRESETS_DIR,
                                         filetypes=(("Settings", "*.json"),), parent=self.root)
        if not path:
            return
        try:
            selected_settings = read_preset(path, {**self.settings, **self.current_app_settings()})
        except (OSError, ValueError, TypeError, KeyError, AttributeError) as error:
            messagebox.showerror("Could not load settings", str(error), parent=self.root)
            return
        self.form_settings = selected_settings
        self.show_settings()

    def _fit_window_to_frame(self, frame):
        if not frame.winfo_exists() or getattr(self, "fitting_window", False):
            return
        self.fitting_window = True
        try:
            self.root.update_idletasks()
            screen_width = self.root.winfo_screenwidth() - 80
            screen_height = self.root.winfo_screenheight() - 100
            desired_width = max(720, frame.winfo_reqwidth())
            panel = getattr(self, "game_settings_panel", None)
            if panel is not None and panel.frame.winfo_manager():
                desired_width = max(desired_width, panel.preferred_width() + 60)
            width = min(desired_width, screen_width)
            self.root.minsize(min(720, screen_width), min(300, screen_height))
            self.root.geometry(f"{width}x{min(max(300, frame.winfo_reqheight()), screen_height)}")
            self.root.update_idletasks()
            # Width changes may wrap categories onto a different number of rows.
            height = min(max(300, frame.winfo_reqheight()), screen_height)
            x = max(0, min(self.root.winfo_x(), self.root.winfo_screenwidth() - width - 40))
            y = max(0, min(self.root.winfo_y(), self.root.winfo_screenheight() - height - 60))
            self.root.geometry(f"{width}x{height}+{x}+{y}")
            self.viewport.schedule_resize()
        finally:
            self.fitting_window = False

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
        self, players_var, cards_var, deck_var, custom_names_var, name_vars,
        game_settings_panel, basic_settings_panel, mode="use",
    ):
        try:
            num_players = int(players_var.get())
            cards_per_player = int(cards_var.get())
            game_settings_values = game_settings_panel.values()
            basic_settings_values = basic_settings_panel.values()
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
        except ValueError as error:
            messagebox.showerror(
                "Invalid settings",
                str(error) or "Players must be at least 1 and cards per player 0 or more. Numeric settings must also be valid.",
                parent=self.root,
            )
            return

        selected_settings = {
            "num_players": num_players,
            "cards_per_player": cards_per_player,
            "deck_path": deck_path,
            "use_custom_player_names": custom_names_var.get(),
            "player_names": player_names,
            **game_settings_values,
            **basic_settings_values,
        }
        selected_settings["configuration_name"] = self.settings.get("configuration_name", "Default")
        selected_settings["configuration_baseline"] = self.settings.get("configuration_baseline", {})
        if mode == "named":
            self.save_named_settings(selected_settings)
            return
        try:
            save_settings(selected_settings)
        except OSError as error:
            messagebox.showerror("Could not save", str(error), parent=self.root)
            return
        self.settings = selected_settings
        self.menu.show_main_menu()

