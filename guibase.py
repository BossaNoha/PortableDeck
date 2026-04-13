# guibase.py
import tkinter as tk
from handframe import HandFrame
from statuspanel import StatusPanel
from cardactions import draw_card, discard_selected, end_turn

class GameGUI:
    def __init__(self, root, game):
        self.root = root
        self.game = game
        self.root.title("Virtual Deck Game")

        # ----- Frames -----
        # Status panel shows counts of cards
        self.status_panel = StatusPanel(root, self.game)
        self.status_panel.pack(padx=10, pady=5, fill="x")

        # HandFrame shows the current player's hand
        self.hand_frame = HandFrame(root, self)
        self.hand_frame.pack(padx=10, pady=5, fill="x")

        # Action buttons frame
        self.actions_frame = tk.LabelFrame(root, text="Actions", padx=5, pady=5)
        self.actions_frame.pack(padx=10, pady=5, fill="x")

        # Game log frame
        self.log_frame = tk.LabelFrame(root, text="Game Log", padx=5, pady=5)
        self.log_frame.pack(padx=10, pady=5, fill="both", expand=True)

        self.log_text = tk.Text(self.log_frame, height=10, state="disabled")
        self.log_text.pack(fill="both", expand=True)

        # ----- Action buttons -----
        self.draw_button = tk.Button(
            self.actions_frame,
            text="Draw Card",
            command=lambda: draw_card(self.game, self.hand_frame, self.log, self.status_panel)
        )
        self.draw_button.pack(side="left", padx=5)

        self.discard_button = tk.Button(
            self.actions_frame,
            text="Discard Selected",
            command=lambda: discard_selected(self.game, self.hand_frame, self.log, self.status_panel)
        )
        self.discard_button.pack(side="left", padx=5)

        self.next_button = tk.Button(
            self.actions_frame,
            text="Next Turn",
            command=lambda: end_turn(self.game, self.hand_frame, self.log, self.status_panel)
        )
        self.next_button.pack(side="left", padx=5)

        # Initialize GUI
        self.hand_frame.update_hand()
        self.status_panel.update_status()
        self.log(f"{self.current_player_name()}'s turn starts.")

    # ----- Helper methods -----
    def current_player(self):
        return self.game.players[self.game.current_player_index]

    def current_player_name(self):
        return self.current_player().name

    def log(self, message):
        """Append a message to the log text box."""
        self.log_text.config(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")


# ----- GUI entry point -----
def start_gui(game):
    root = tk.Tk()
    gui = GameGUI(root, game)
    root.mainloop()