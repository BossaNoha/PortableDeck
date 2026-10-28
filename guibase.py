# guibase.py
import tkinter as tk
from tkinter import messagebox
from handframe import HandFrame
from statuspanel import StatusPanel
from tableframe import TableFrame
from cardactions import (
    clear_table,
    draw_card,
    discard_selected,
    end_turn,
    move_selected_table_card_to_discard,
    play_selected,
    request_point,
    take_selected_from_table,
)

class GameGUI:
    def __init__(
        self, root, game, on_save=None, on_exit_menu=None, on_exit_desktop=None, on_restart=None
    ):
        self.root = root
        self.game = game
        self.on_save = on_save
        self.on_exit_menu = on_exit_menu
        self.on_exit_desktop = on_exit_desktop
        self.on_restart = on_restart
        self.root.title("Virtual Deck Game")
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        # ----- Frames -----
        # Status panel shows counts of cards
        self.status_panel = StatusPanel(root, self.game)
        self.status_panel.pack(padx=10, pady=5, fill="x")

        self.table_frame = TableFrame(root, self.game)
        self.table_frame.pack(padx=10, pady=5, fill="x")

        # HandFrame shows the current player's hand
        self.hand_frame = HandFrame(root, self)
        self.hand_frame.pack(padx=10, pady=5, fill="x")

        # Action buttons frame
        self.actions_frame = tk.LabelFrame(root, text="Actions", padx=5, pady=5)
        self.actions_frame.pack(padx=10, pady=5, fill="x")
        self.card_actions_frame = tk.Frame(self.actions_frame)
        self.card_actions_frame.pack(fill="x")
        self.turn_actions_frame = tk.Frame(self.actions_frame)
        self.turn_actions_frame.pack(fill="x")

        # Game log frame
        self.log_frame = tk.LabelFrame(root, text="Game Log", padx=5, pady=5)
        self.log_frame.pack(padx=10, pady=5, fill="both", expand=True)

        self.log_text = tk.Text(self.log_frame, height=10, state="disabled")
        self.log_text.pack(fill="both", expand=True)

        # ----- Action buttons -----
        self.draw_button = tk.Button(
            self.card_actions_frame,
            text="Draw Card",
            command=lambda: draw_card(self.game, self.hand_frame, self.log, self.status_panel)
        )
        self.draw_button.pack(side="left", padx=5)

        self.discard_button = tk.Button(
            self.card_actions_frame,
            text="Discard Selected",
            command=lambda: discard_selected(self.game, self.hand_frame, self.log, self.status_panel)
        )
        self.discard_button.pack(side="left", padx=5)

        self.play_button = tk.Button(
            self.card_actions_frame,
            text="Play Selected",
            command=lambda: play_selected(
                self.game, self.hand_frame, self.table_frame, self.log, self.status_panel
            ),
        )
        self.play_button.pack(side="left", padx=5)

        self.table_action_buttons = []
        if self.game.allow_take_from_table:
            self.take_table_button = tk.Button(
                self.card_actions_frame,
                text="Take Selected from Table",
                command=lambda: take_selected_from_table(
                    self.game, self.table_frame, self.hand_frame, self.log, self.status_panel
                ),
            )
            self.take_table_button.pack(side="left", padx=5)
            self.table_action_buttons.append(self.take_table_button)
        if self.game.allow_move_table_card_to_discard:
            self.table_discard_button = tk.Button(
                self.card_actions_frame,
                text="Move Selected to Discard",
                command=lambda: move_selected_table_card_to_discard(
                    self.game, self.table_frame, self.log, self.status_panel
                ),
            )
            self.table_discard_button.pack(side="left", padx=5)
            self.table_action_buttons.append(self.table_discard_button)
        if self.game.allow_manual_table_cleanup:
            self.clear_table_button = tk.Button(
                self.card_actions_frame,
                text="Clear Table",
                command=lambda: clear_table(
                    self.game, self.table_frame, self.log, self.status_panel
                ),
            )
            self.clear_table_button.pack(side="left", padx=5)
            self.table_action_buttons.append(self.clear_table_button)

        self.next_button = tk.Button(
            self.turn_actions_frame,
            text="Next Turn",
            command=lambda: end_turn(
                self.game, self.hand_frame, self.log, self.status_panel, self.handle_turn_start
            ),
        )
        self.next_button.pack(side="left", padx=5)

        self.save_button = tk.Button(self.turn_actions_frame, text="Save", command=self.save)
        self.save_button.pack(side="left", padx=5)

        self.menu_button = tk.Button(
            self.turn_actions_frame, text="Exit to Main Menu", command=self.exit_to_menu
        )
        self.menu_button.pack(side="left", padx=5)

        self.desktop_button = tk.Button(
            self.turn_actions_frame, text="Exit to Desktop", command=self.exit_to_desktop
        )
        self.desktop_button.pack(side="left", padx=5)

        self.restart_button = tk.Button(
            self.turn_actions_frame, text="Restart Game", command=self.restart
        )
        self.restart_button.pack(side="left", padx=5)

        if self.game.score_enabled:
            self.point_button = tk.Button(
                self.turn_actions_frame,
                text="Request Point",
                command=self.request_current_point,
            )
            self.point_button.pack(side="left", padx=5)

        # Initialize GUI
        self.hand_frame.update_hand()
        self.status_panel.update_status()
        self.log(f"{self.current_player_name()}'s turn starts.")
        self.handle_turn_start()
        self.update_point_button()

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

    def save(self):
        if self.on_save:
            self.on_save(self.game)

    def restart(self):
        if self.game.score_enabled:
            keep_scores = messagebox.askyesnocancel(
                "Restart game?",
                "Start a new game? Choose Yes to keep the current scores, or No to reset them.",
                parent=self.root,
            )
            if keep_scores is None:
                return
        else:
            confirmed = messagebox.askyesno(
                "Restart game?",
                "Start a new game? Current hands, table cards, and discard pile will be cleared.",
                parent=self.root,
            )
            if not confirmed:
                return
            keep_scores = False

        if self.on_restart:
            self.on_restart(self.game, keep_scores)

    def request_current_point(self):
        request_point(self.game, self.hand_frame, self.log, self.status_panel)
        self.update_point_button()

    def update_point_button(self):
        if hasattr(self, "point_button"):
            state = "disabled" if self.game.pending_point_request else "normal"
            self.point_button.config(state=state)

    def handle_turn_start(self):
        self.table_frame.selected_index = None
        self.table_frame.update_table()
        if not self.game.current_player_must_confirm_point():
            return

        for button in self._turn_action_buttons():
            button.config(state="disabled")
        requester_name = self.game.players[
            self.game.pending_point_request["requester"]
        ].name
        voter_name = self.current_player_name()
        approved = messagebox.askyesno(
            "Confirm point request",
            f"{requester_name} requested a point.\n\n"
            f"As {voter_name}, should {requester_name} receive it?",
            parent=self.root,
        )
        _, result = self.game.confirm_point_request(approved)
        self.log(result)
        self.status_panel.update_status()
        for button in self._turn_action_buttons():
            button.config(state="normal")
        self.update_point_button()

    def _turn_action_buttons(self):
        buttons = [self.draw_button, self.discard_button, self.play_button, self.next_button]
        buttons.extend(self.table_action_buttons)
        if hasattr(self, "point_button"):
            buttons.append(self.point_button)
        return buttons

    def _ask_to_save(self):
        return messagebox.askyesnocancel(
            "Save game?",
            "Save the current game before leaving?",
            parent=self.root,
        )

    def exit_to_menu(self):
        save_choice = self._ask_to_save()
        if save_choice is None:
            return
        if self.on_exit_menu:
            self.on_exit_menu(self.game, save_choice)

    def exit_to_desktop(self):
        save_choice = self._ask_to_save()
        if save_choice is None:
            return
        if self.on_exit_desktop:
            self.on_exit_desktop(self.game, save_choice)
        else:
            self.root.destroy()

    def close(self):
        self.exit_to_desktop()


# ----- GUI entry point -----
def start_gui(game):
    root = tk.Tk()
    gui = GameGUI(root, game)
    root.mainloop()
