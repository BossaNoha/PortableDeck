import os
import tkinter as tk
from tkinter import messagebox

from ..core.game import Game
from ..ui.guibase import GameGUI
from .settings import BASE_DIR, DISCARD_PATH, load_settings, resolve_deck_path
from .settingswindow import SettingsWindow
from .savemanager import SaveManager
from .sessionbrowser import SessionBrowser

SAVES_DIR = os.path.join(BASE_DIR, "saves")
AUTOSAVE_PATH = os.path.join(SAVES_DIR, "last_session.json")


class MainMenu:
    def __init__(self, root):
        self.root = root
        self.settings = load_settings()
        self.migrate_discard_data()
        os.makedirs(SAVES_DIR, exist_ok=True)
        self.save_manager = SaveManager(self.root, SAVES_DIR)
        self.root.title("Portable Deck")
        self.root.protocol("WM_DELETE_WINDOW", self.root.destroy)
        self.show_main_menu()

    def migrate_discard_data(self):
        """Move the previous user-visible discard file into internal app data."""
        legacy_path = os.path.join(BASE_DIR, "decks", "discard.json")
        if os.path.isfile(legacy_path) and not os.path.exists(DISCARD_PATH):
            os.makedirs(os.path.dirname(DISCARD_PATH), exist_ok=True)
            try:
                os.replace(legacy_path, DISCARD_PATH)
            except OSError:
                # Keep startup available if legacy data cannot be moved; exit
                # will still write the current discard pile to the new path.
                pass

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
        tk.Label(frame, text="Portable Deck", font=("TkDefaultFont", 20, "bold")).pack(pady=(0, 20))
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
        SettingsWindow(self).show_settings()

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
                allow_move_cards_on_table=self.settings.get("allow_move_cards_on_table", False),
                allow_play_in_front_of_players=self.settings.get(
                    "allow_play_in_front_of_players", False
                ),
                allow_draw_from_discard=self.settings.get("allow_draw_from_discard", False),
                draw_from_discard_mode=self.settings.get("draw_from_discard_mode", "top"),
                allow_face_down_table_cards=self.settings.get("allow_face_down_table_cards", False),
                allow_move_table_sequences=self.settings.get("allow_move_table_sequences", False),
                allow_recycle_discard_to_deck=self.settings.get("allow_recycle_discard_to_deck", False),
                shared_discard_pile_count=self.settings.get("shared_discard_pile_count", 1),
                personal_discard_pile_count=self.settings.get("personal_discard_pile_count", 0),
                enable_chip_accounts=self.settings.get("enable_chip_accounts", False),
                minimum_bet=self.settings.get("minimum_bet", 1),
                starting_balance=self.settings.get("starting_balance", 100),
                require_pot_withdrawal_confirmation=self.settings.get(
                    "require_pot_withdrawal_confirmation", False
                ),
            )
            game.start(self.settings["cards_per_player"])
        except (OSError, ValueError, KeyError, TypeError) as error:
            messagebox.showerror("Could not start game", str(error), parent=self.root)
            return

        self.clear_window()
        self.show_game(game)

    def load_game(self):
        path = SessionBrowser(self.root, SAVES_DIR).show()
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
            on_save=self.save_manager.save_session,
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

    def exit_to_menu(self, game, should_save):
        if should_save and not self.save_manager.save_session(game):
            return
        self.show_main_menu()

    def exit_to_desktop(self, game, should_save):
        if should_save and not self.save_manager.save_session(game):
            return
        if self.settings["save_discard_on_exit"] and hasattr(game, "save_discard_pile"):
            try:
                game.save_discard_pile(DISCARD_PATH)
            except OSError as error:
                messagebox.showerror("Could not save", str(error), parent=self.root)
        self.root.destroy()


def start_menu():
    root = tk.Tk()
    MainMenu(root)
    root.mainloop()
