import os
from dataclasses import asdict
import tkinter as tk
from tkinter import messagebox

from ..core.game import Game
from ..ui.guibase import GameGUI
from .settings import BASE_DIR, DISCARD_PATH, load_settings_result
from .settingswindow import SettingsWindow
from .savemanager import SaveManager
from .sessionbrowser import SessionBrowser
from .sessionview import TableViewState
from .checkpoints import save_checkpoint
from .newgame import create_game
from .sessionstorage import load_session_with_view
from .discardstorage import save_discard_pile

SAVES_DIR = os.path.join(BASE_DIR, "saves")
AUTOSAVE_PATH = os.path.join(SAVES_DIR, "last_session.json")


class MainMenu:
    def __init__(self, root):
        self.root = root
        loaded = load_settings_result()
        self.settings = loaded.settings
        self.migrate_discard_data()
        os.makedirs(SAVES_DIR, exist_ok=True)
        self.save_manager = SaveManager(self.root, SAVES_DIR)
        self.root.title("Portable Deck")
        self.root.protocol("WM_DELETE_WINDOW", self.quit_app)
        self.show_main_menu()
        if loaded.error:
            messagebox.showwarning(
                "Could not save settings",
                "The application is using the loaded or default settings in memory. "
                "Changes could not be saved to disk.\n\n" + loaded.error,
                parent=self.root,
            )

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
        self.root.protocol("WM_DELETE_WINDOW", self.quit_app)
        frame = tk.Frame(self.root, padx=32, pady=28)
        # Let the menu determine the window size instead of stretching the
        # frame to the dimensions used by the game session.
        frame.pack()
        tk.Label(frame, text="Portable Deck", font=("TkDefaultFont", 20, "bold")).pack(pady=(0, 20))
        tk.Button(frame, text="New game", width=24, command=self.play).pack(pady=5)
        resume_state = "normal" if os.path.isfile(AUTOSAVE_PATH) else "disabled"
        tk.Button(frame, text="Resume game", width=24, state=resume_state, command=self.resume_game).pack(pady=5)
        tk.Button(frame, text="Load save", width=24, command=self.load_game).pack(pady=5)
        tk.Button(frame, text="Settings", width=24, command=self.show_settings).pack(pady=5)
        tk.Button(frame, text="Quit", width=24, command=self.quit_app).pack(pady=5)
        self.root.update_idletasks()
        width = frame.winfo_reqwidth()
        height = frame.winfo_reqheight()
        self.root.minsize(width, height)
        self.root.geometry(f"{width}x{height}")

    def quit_app(self):
        if self.settings.get("require_exit_confirmation", True) and not messagebox.askyesno(
            "Quit Portable Deck?", "Close the application?", parent=self.root
        ):
            return
        self.root.destroy()

    def show_settings(self):
        SettingsWindow(self).show_settings()

    def play(self):
        try:
            game = create_game(self.settings)
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
            game, table_view = load_session_with_view(Game, path)
        except (OSError, ValueError, KeyError, TypeError) as error:
            messagebox.showerror("Could not load game", str(error), parent=self.root)
            return
        self.clear_window()
        self.show_game(game, table_view=table_view)

    def resume_game(self):
        try:
            game, table_view = load_session_with_view(Game, AUTOSAVE_PATH)
        except (OSError, ValueError, KeyError, TypeError) as error:
            messagebox.showerror("Could not resume game", str(error), parent=self.root)
            return
        self.clear_window()
        self.show_game(game, table_view=table_view)

    def show_game(self, game, table_view=None):
        self.save_manager.table_view = table_view if table_view is not None else TableViewState()
        GameGUI(
            self.root,
            game,
            table_view=self.save_manager.table_view,
            on_save=self.save_manager.save_session,
            on_save_as=self.save_manager.save_session_as,
            on_exit_menu=self.exit_to_menu,
            on_exit_desktop=self.exit_to_desktop,
            on_restart=self.restart_game,
            on_checkpoint=self.checkpoint_game,
            require_exit_confirmation=self.settings.get("require_exit_confirmation", True),
            confirm_next_turn=self.settings.get("confirm_next_turn", False),
            confirm_skip=self.settings.get("confirm_skip", False),
            contextual_session_actions=self.settings.get("contextual_session_actions", False),
            show_game_log=self.settings.get("show_game_log", True),
        )

    def checkpoint_game(self, game):
        return save_checkpoint(game, AUTOSAVE_PATH,
            enabled=self.settings.get("autosave_enabled", True),
            count=self.settings.get("autosave_count", 5),
            client_state={"table_view": asdict(self.save_manager.table_view)})

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
        if game.enable_discard_pile and self.settings["save_discard_on_exit"]:
            try:
                save_discard_pile(game, DISCARD_PATH)
            except OSError as error:
                messagebox.showerror("Could not save", str(error), parent=self.root)
        self.root.destroy()


def start_menu():
    root = tk.Tk()
    MainMenu(root)
    from .welcome import show_first_run_intro
    root.after(100, lambda: show_first_run_intro(root))
    root.mainloop()
