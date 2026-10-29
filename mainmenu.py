import os
import re
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog

from game import Game
from guibase import GameGUI
from settings import BASE_DIR, load_default_settings, load_settings, resolve_deck_path, save_settings

SAVES_DIR = os.path.join(BASE_DIR, "saves")
AUTOSAVE_PATH = os.path.join(SAVES_DIR, "last_session.json")


class MainMenu:
    def __init__(self, root):
        self.root = root
        self.settings = load_settings()
        os.makedirs(SAVES_DIR, exist_ok=True)
        self.root.title("Virtual Deck")
        self.root.protocol("WM_DELETE_WINDOW", self.root.destroy)
        self.show_main_menu()

    def clear_window(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def show_main_menu(self):
        self.clear_window()
        self.root.minsize(1, 1)
        self.root.protocol("WM_DELETE_WINDOW", self.root.destroy)
        frame = tk.Frame(self.root, padx=32, pady=28)
        # Let the menu determine the window size instead of stretching the
        # frame to the dimensions used by the game session.
        frame.pack()
        tk.Label(frame, text="Virtual Deck", font=("TkDefaultFont", 20, "bold")).pack(pady=(0, 20))
        tk.Button(frame, text="Play", width=24, command=self.play).pack(pady=5)
        resume_state = "normal" if os.path.isfile(AUTOSAVE_PATH) else "disabled"
        tk.Button(frame, text="Resume", width=24, state=resume_state, command=self.resume_game).pack(pady=5)
        tk.Button(frame, text="Load", width=24, command=self.load_game).pack(pady=5)
        tk.Button(frame, text="Settings", width=24, command=self.show_settings).pack(pady=5)
        tk.Button(frame, text="Quit", width=24, command=self.root.destroy).pack(pady=5)
        self.root.update_idletasks()
        width = frame.winfo_reqwidth()
        height = frame.winfo_reqheight()
        self.root.minsize(width, height)
        self.root.geometry(f"{width}x{height}")

    def show_settings(self):
        self.clear_window()
        self.root.minsize(1, 1)
        self.root.resizable(True, True)
        frame = tk.Frame(self.root, padx=20, pady=18)
        frame.pack(fill="both", expand=True)
        tk.Label(frame, text="Settings", font=("TkDefaultFont", 16, "bold")).grid(
            row=0, column=0, columnspan=3, pady=(0, 14)
        )

        players_var = tk.StringVar(value=str(self.settings["num_players"]))
        cards_var = tk.StringVar(value=str(self.settings["cards_per_player"]))
        deck_var = tk.StringVar(value=str(self.settings["deck_path"]))
        save_var = tk.BooleanVar(value=bool(self.settings["save_discard_on_exit"]))
        custom_names_var = tk.BooleanVar(value=bool(self.settings["use_custom_player_names"]))
        score_var = tk.BooleanVar(value=bool(self.settings.get("enable_score_counter", False)))
        confirmation_var = tk.BooleanVar(
            value=bool(self.settings.get("require_point_confirmation", False))
        )
        take_table_var = tk.BooleanVar(value=bool(self.settings.get("allow_take_from_table", False)))
        table_to_discard_var = tk.BooleanVar(
            value=bool(self.settings.get("allow_move_table_card_to_discard", False))
        )
        manual_cleanup_var = tk.BooleanVar(
            value=bool(self.settings.get("allow_manual_table_cleanup", False))
        )
        round_cleanup_var = tk.BooleanVar(
            value=bool(self.settings.get("clear_table_on_round_end", False))
        )
        positioned_play_var = tk.BooleanVar(
            value=bool(self.settings.get("allow_positioned_play", False))
        )
        occupied_slot_action_var = tk.StringVar(
            value=self.settings.get("occupied_slot_action", "invalid")
        )
        undo_var = tk.BooleanVar(value=bool(self.settings.get("enable_undo", False)))
        advanced_expanded = tk.BooleanVar(value=False)

        tk.Label(frame, text="Number of players:").grid(row=1, column=0, sticky="w", pady=5)
        tk.Spinbox(frame, from_=1, to=20, textvariable=players_var, width=8).grid(row=1, column=1, sticky="w")
        tk.Label(frame, text="Cards per player:").grid(row=2, column=0, sticky="w", pady=5)
        tk.Spinbox(frame, from_=0, to=1000, textvariable=cards_var, width=8).grid(row=2, column=1, sticky="w")
        tk.Label(frame, text="Deck file (JSON):").grid(row=3, column=0, sticky="w", pady=5)
        tk.Entry(frame, textvariable=deck_var, width=38).grid(row=3, column=1, sticky="ew")
        tk.Button(frame, text="Browse…", command=lambda: self.browse_deck(deck_var)).grid(row=3, column=2, padx=(6, 0))
        tk.Checkbutton(
            frame,
            text="Save discard pile when the game window closes",
            variable=save_var,
        ).grid(row=4, column=0, columnspan=3, sticky="w", pady=10)

        tk.Checkbutton(
            frame,
            text="Use custom player names",
            variable=custom_names_var,
        ).grid(row=5, column=0, columnspan=3, sticky="w", pady=5)

        names_frame = tk.LabelFrame(frame, text="Player names", padx=8, pady=5)
        names_frame.grid(row=6, column=0, columnspan=3, sticky="ew", pady=5)
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
                tk.Label(names_frame, text=f"Player {index + 1}:").grid(
                    row=index, column=0, sticky="w", padx=(0, 8), pady=2
                )
                tk.Entry(names_frame, textvariable=var, width=28).grid(
                    row=index, column=1, sticky="ew", pady=2
                )
            names_frame.columnconfigure(1, weight=1)
            self.root.after_idle(lambda: self._fit_window_to_frame(frame))

        players_var.trace_add("write", refresh_name_inputs)
        custom_names_var.trace_add("write", refresh_name_inputs)
        refresh_name_inputs()

        advanced_button = tk.Button(frame, text="Advanced Settings ▸")
        advanced_button.grid(row=7, column=0, columnspan=3, sticky="w", pady=(8, 2))
        advanced_frame = tk.LabelFrame(frame, text="Advanced Settings", padx=8, pady=5)
        advanced_frame.grid(row=8, column=0, columnspan=3, sticky="ew", pady=4)
        advanced_frame.grid_remove()
        tk.Checkbutton(
            advanced_frame,
            text="Enable score counters and point requests",
            variable=score_var,
        ).pack(anchor="w")
        tk.Checkbutton(
            advanced_frame,
            text="Enable Undo",
            variable=undo_var,
        ).pack(anchor="w")
        confirmation_check = tk.Checkbutton(
            advanced_frame,
            text="Require approval from the other players for a point",
            variable=confirmation_var,
        )
        confirmation_check.pack(anchor="w")
        tk.Label(advanced_frame, text="Table actions").pack(anchor="w", pady=(8, 0))
        tk.Checkbutton(
            advanced_frame,
            text="Allow taking a selected card from the table into the current hand",
            variable=take_table_var,
        ).pack(anchor="w")
        tk.Checkbutton(
            advanced_frame,
            text="Allow moving a selected table card to the discard pile",
            variable=table_to_discard_var,
        ).pack(anchor="w")
        tk.Checkbutton(
            advanced_frame,
            text="Allow the current player to clear the table",
            variable=manual_cleanup_var,
        ).pack(anchor="w")
        tk.Checkbutton(
            advanced_frame,
            text="Automatically clear the table when the last player ends the round",
            variable=round_cleanup_var,
        ).pack(anchor="w")
        tk.Checkbutton(
            advanced_frame,
            text="Allow playing cards to specific table positions",
            variable=positioned_play_var,
        ).pack(anchor="w")
        occupied_action_row = tk.Frame(advanced_frame)
        occupied_action_row.pack(anchor="w", pady=(3, 0))
        tk.Label(occupied_action_row, text="When playing on an occupied spot:").pack(side="left")
        tk.OptionMenu(occupied_action_row, occupied_slot_action_var, "invalid", "swap").pack(side="left")

        def update_confirmation_control(*_):
            confirmation_check.config(state="normal" if score_var.get() else "disabled")

        def toggle_advanced():
            expanded = not advanced_expanded.get()
            advanced_expanded.set(expanded)
            if expanded:
                advanced_frame.grid()
                advanced_button.config(text="Advanced Settings ▾")
            else:
                advanced_frame.grid_remove()
                advanced_button.config(text="Advanced Settings ▸")
            self.root.after_idle(lambda: self._fit_window_to_frame(frame))

        advanced_button.config(command=toggle_advanced)
        score_var.trace_add("write", update_confirmation_control)
        update_confirmation_control()

        buttons = tk.Frame(frame)
        buttons.grid(row=9, column=0, columnspan=3, sticky="e", pady=(12, 0))
        tk.Button(buttons, text="Back", command=self.show_main_menu).pack(side="left", padx=5)
        tk.Button(buttons, text="Restore Defaults", command=self.restore_defaults).pack(side="left", padx=5)
        tk.Button(
            buttons,
            text="Save settings",
            command=lambda: self.save_form(
                players_var, cards_var, deck_var, save_var, custom_names_var, name_vars,
                score_var, confirmation_var, take_table_var, table_to_discard_var,
                manual_cleanup_var, round_cleanup_var, positioned_play_var,
                occupied_slot_action_var, undo_var,
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

    def save_form(
        self, players_var, cards_var, deck_var, save_var, custom_names_var, name_vars,
        score_var, confirmation_var, take_table_var, table_to_discard_var,
        manual_cleanup_var, round_cleanup_var, positioned_play_var, occupied_slot_action_var,
        undo_var,
    ):
        try:
            num_players = int(players_var.get())
            cards_per_player = int(cards_var.get())
            deck_path = deck_var.get().strip()
            if num_players < 1 or cards_per_player < 0:
                raise ValueError
            if not deck_path or not os.path.isfile(resolve_deck_path(deck_path)):
                messagebox.showerror("Invalid deck", "Choose an existing deck JSON file.", parent=self.root)
                return
            player_names = [var.get().strip() for var in name_vars] if custom_names_var.get() else []
            if custom_names_var.get() and (len(player_names) != num_players or any(not name for name in player_names)):
                messagebox.showerror("Invalid names", "Enter a name for every player.", parent=self.root)
                return
        except ValueError:
            messagebox.showerror(
                "Invalid settings",
                "Players must be at least 1 and cards per player must be 0 or more.",
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
            "enable_score_counter": score_var.get(),
            "require_point_confirmation": score_var.get() and confirmation_var.get(),
            "allow_take_from_table": take_table_var.get(),
            "allow_move_table_card_to_discard": table_to_discard_var.get(),
            "allow_manual_table_cleanup": manual_cleanup_var.get(),
            "clear_table_on_round_end": round_cleanup_var.get(),
            "allow_positioned_play": positioned_play_var.get(),
            "occupied_slot_action": occupied_slot_action_var.get(),
            "enable_undo": undo_var.get(),
        }
        try:
            save_settings(self.settings)
        except OSError as error:
            messagebox.showerror("Could not save", str(error), parent=self.root)
            return
        self.show_main_menu()

    def play(self):
        deck_path = resolve_deck_path(self.settings["deck_path"])
        try:
            names = self.settings.get("player_names", []) if self.settings.get("use_custom_player_names") else None
            game = Game(
                self.settings["num_players"],
                deck_path,
                player_names=names,
                score_enabled=self.settings.get("enable_score_counter", False),
                require_point_confirmation=self.settings.get("require_point_confirmation", False),
                allow_take_from_table=self.settings.get("allow_take_from_table", False),
                allow_move_table_card_to_discard=self.settings.get(
                    "allow_move_table_card_to_discard", False
                ),
                allow_manual_table_cleanup=self.settings.get("allow_manual_table_cleanup", False),
                clear_table_on_round_end=self.settings.get("clear_table_on_round_end", False),
                allow_positioned_play=self.settings.get("allow_positioned_play", False),
                occupied_slot_action=self.settings.get("occupied_slot_action", "invalid"),
                enable_undo=self.settings.get("enable_undo", False),
            )
            game.start(self.settings["cards_per_player"])
        except (OSError, ValueError, KeyError, TypeError) as error:
            messagebox.showerror("Could not start game", str(error), parent=self.root)
            return

        self.clear_window()
        self.show_game(game)

    def load_game(self):
        path = filedialog.askopenfilename(
            title="Load saved game",
            initialdir=SAVES_DIR,
            filetypes=(("Saved games", "*.json"), ("All files", "*.*")),
            parent=self.root,
        )
        if not path:
            return
        try:
            game = Game.load_session(path)
        except (OSError, ValueError, KeyError, TypeError) as error:
            messagebox.showerror("Could not load game", str(error), parent=self.root)
            return
        self.clear_window()
        self.show_game(game)

    def resume_game(self):
        try:
            game = Game.load_session(AUTOSAVE_PATH)
        except (OSError, ValueError, KeyError, TypeError) as error:
            messagebox.showerror("Could not resume game", str(error), parent=self.root)
            return
        self.clear_window()
        self.show_game(game)

    def show_game(self, game):
        GameGUI(
            self.root,
            game,
            on_save=self.save_session,
            on_exit_menu=self.exit_to_menu,
            on_exit_desktop=self.exit_to_desktop,
            on_restart=self.restart_game,
            on_checkpoint=self.checkpoint_game,
        )

    def checkpoint_game(self, game):
        try:
            game.save_session(AUTOSAVE_PATH)
            return None
        except (OSError, TypeError, ValueError) as error:
            return str(error)

    def restart_game(self, game, keep_scores):
        try:
            restarted = game.restart(keep_scores=keep_scores)
        except (OSError, ValueError, KeyError, TypeError) as error:
            messagebox.showerror("Could not restart game", str(error), parent=self.root)
            return
        self.clear_window()
        self.show_game(restarted)

    def save_session(self, game):
        session_number = self.next_session_number()
        name = simpledialog.askstring(
            "Save game",
            "Save name:",
            initialvalue=f"session{session_number}",
            parent=self.root,
        )
        if name is None:
            return False
        name = name.strip()
        if not name or name in {".", ".."} or os.path.basename(name) != name or re.search(r'[<>:"/\\|?*]', name):
            messagebox.showerror("Invalid name", "Enter a file name without a folder path or special characters.", parent=self.root)
            return False
        if not name.lower().endswith(".json"):
            name += ".json"
        path = os.path.join(SAVES_DIR, name)
        if os.path.exists(path) and not messagebox.askyesno(
            "Replace save?", f"A save named '{name}' already exists. Replace it?", parent=self.root
        ):
            return False
        try:
            game.save_session(path)
            messagebox.showinfo("Game saved", f"Saved as {name}.", parent=self.root)
            return True
        except (OSError, TypeError, ValueError) as error:
            messagebox.showerror("Could not save game", str(error), parent=self.root)
            return False

    def next_session_number(self):
        numbers = []
        for filename in os.listdir(SAVES_DIR):
            match = re.fullmatch(r"session(\d+)\.json", filename, re.IGNORECASE)
            if match:
                numbers.append(int(match.group(1)))
        return max(numbers, default=0) + 1

    def exit_to_menu(self, game, should_save):
        if should_save and not self._save_before_exit(game):
            return
        self.show_main_menu()

    def exit_to_desktop(self, game, should_save):
        if should_save and not self._save_before_exit(game):
            return
        if self.settings["save_discard_on_exit"]:
            discard_path = os.path.join(BASE_DIR, "decks", "discard.json")
            try:
                game.save_discard_pile(discard_path)
            except OSError as error:
                messagebox.showerror("Could not save", str(error), parent=self.root)
        self.root.destroy()

    def _save_before_exit(self, game):
        return self.save_session(game)


def start_menu():
    root = tk.Tk()
    MainMenu(root)
    root.mainloop()
