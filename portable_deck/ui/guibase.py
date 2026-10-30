# guibase.py
import tkinter as tk
from .gameguiactions import GameGUIActions
from .gameguibuilder import GameGUIBuilder

class GameGUI(GameGUIBuilder, GameGUIActions):
    def __init__(
        self, root, game, on_save=None, on_exit_menu=None, on_exit_desktop=None,
        on_restart=None, on_checkpoint=None,
    ):
        self.root = root
        self.game = game
        self.on_save = on_save
        self.on_exit_menu = on_exit_menu
        self.on_exit_desktop = on_exit_desktop
        self.on_restart = on_restart
        self.on_checkpoint = on_checkpoint
        self.root.title("Portable Deck - Game")
        self.root.minsize(900, 560)
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        self.build_game_interface()

    # ----- Helper methods -----
    def current_player(self):
        return self.game.players[self.game.current_player_index]

    def current_player_name(self):
        return self.current_player().name

    def log(self, message):
        """Append a message to the log text box."""
        self.game.gui_log.append(message)
        self.log_text.config(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    def _restore_log(self):
        """Render log messages restored from a saved game without duplicating them."""
        self.log_text.config(state="normal")
        self.log_text.insert("end", "\n".join(self.game.gui_log) + "\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    def save(self):
        if self.on_save:
            self.on_save(self.game)

# ----- GUI entry point -----
def start_gui(game):
    root = tk.Tk()
    gui = GameGUI(root, game)
    root.mainloop()
