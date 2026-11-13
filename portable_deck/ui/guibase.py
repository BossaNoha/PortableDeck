# guibase.py
import tkinter as tk
from .gameguiactions import GameGUIActions
from .gameguibuilder import GameGUIBuilder

class GameGUI(GameGUIBuilder, GameGUIActions):
    def __init__(
        self, root, game, on_save=None, on_exit_menu=None, on_exit_desktop=None,
        on_restart=None, on_checkpoint=None, require_exit_confirmation=True, on_save_as=None, show_game_log=True, contextual_session_actions=False,
    ):
        self.contextual_session_actions = bool(contextual_session_actions)
        self.show_game_log = bool(show_game_log)
        self.root = root
        self.game = game
        self.on_save = on_save
        self.on_save_as = on_save_as
        self.on_exit_menu = on_exit_menu
        self.on_exit_desktop = on_exit_desktop
        self.on_restart = on_restart
        self.on_checkpoint = on_checkpoint
        self.require_exit_confirmation = require_exit_confirmation
        self.root.title("Portable Deck - Game")
        self.root.minsize(900, 560)
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        self.build_game_interface()
        self.refresh_action_availability()
        self.selection_bindings = {
            "<Escape>": self.root.bind("<Escape>", self.cancel_selection, add="+"),
            "<Button-1>": self.root.bind("<Button-1>", self.cancel_selection_on_background, add="+"),
        }
        self.layout_frame.bind("<Destroy>", self.remove_selection_bindings, add="+")

    def refresh_action_availability(self):
        from .actionavailability import refresh_action_availability
        refresh_action_availability(self)

    def remove_selection_bindings(self, event):
        if event.widget == self.layout_frame:
            for sequence, binding in self.selection_bindings.items():
                self.root.unbind(sequence, binding)
            self.selection_bindings.clear()

    def cancel_selection_on_background(self, event):
        if not isinstance(event.widget, (tk.Frame, tk.LabelFrame, tk.Canvas)):
            return
        if event.widget.winfo_toplevel() != self.root:
            return
        return self.cancel_selection(event)

    def cancel_selection(self, event=None):
        if event is not None and (isinstance(event.widget, tk.Menu) or event.widget.winfo_toplevel() != self.root):
            return
        if (self.hand_frame.selected_index is None and self.table_frame.selected_index is None
                and self.table_frame.selected_position is None):
            return
        self.hand_frame.selected_index = None
        self.table_frame.selected_index = None
        self.table_frame.selected_position = None
        self.hand_frame.update_hand()
        self.table_frame.update_table()
        if hasattr(self, "context_actions"):
            self.context_actions.refresh()
        return "break"

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

    def save_as(self):
        self.table_frame.capture_view()
        callback = self.on_save_as or self.on_save
        if callback:
            callback(self.game)

    def save(self):
        self.table_frame.capture_view()
        if self.on_save:
            self.on_save(self.game)

# ----- GUI entry point -----
def start_gui(game):
    root = tk.Tk()
    gui = GameGUI(root, game)
    root.mainloop()
