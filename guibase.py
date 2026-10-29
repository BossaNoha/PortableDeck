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
    play_at_selected_spot,
    play_selected,
    request_point,
    take_selected_from_table,
)

class GameGUI:
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
        self.root.title("Virtual Deck Game")
        self.root.minsize(900, 560)
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        self.layout_frame = tk.Frame(root)
        self.layout_frame.pack(fill="both", expand=True)
        self.left_frame = tk.Frame(self.layout_frame)
        self.left_frame.pack(side="left", fill="both", expand=True)
        self.right_frame = tk.Frame(self.layout_frame)
        self.right_frame.pack(side="right", fill="y", padx=(0, 10), pady=5)

        # Status, hand, actions, and log stay together on the left.
        self.status_panel = StatusPanel(self.left_frame, self.game)
        self.status_panel.pack(padx=10, pady=5, fill="x")

        self.hand_frame = HandFrame(self.left_frame, self)
        self.hand_frame.pack(padx=10, pady=5, fill="x")

        self.actions_frame = tk.LabelFrame(self.left_frame, text="Actions", padx=5, pady=5)
        self.actions_frame.pack(padx=10, pady=5, fill="x")
        self.card_actions_frame = tk.Frame(self.actions_frame)
        self.card_actions_frame.pack(fill="x")
        self.turn_actions_frame = tk.Frame(self.actions_frame)
        self.turn_actions_frame.pack(fill="x")

        self.log_frame = tk.LabelFrame(self.left_frame, text="Game Log", padx=5, pady=5)
        self.log_frame.pack(padx=10, pady=5, fill="both", expand=True)

        self.log_text = tk.Text(self.log_frame, height=10, state="disabled")
        self.log_text.pack(fill="both", expand=True)

        self.table_frame = TableFrame(self.right_frame, self.game)
        self.table_frame.pack(fill="both", expand=True)

        # ----- Action buttons -----
        self.draw_button = tk.Button(
            self.card_actions_frame,
            text="Draw Card",
            command=lambda: self.run_action(
                draw_card, self.game, self.hand_frame, self.log, self.status_panel
            ),
        )
        self.draw_button.pack(side="left", padx=5)

        self.discard_button = tk.Button(
            self.card_actions_frame,
            text="Discard Selected",
            command=lambda: self.run_action(
                discard_selected, self.game, self.hand_frame, self.log, self.status_panel
            ),
        )
        self.discard_button.pack(side="left", padx=5)

        self.play_button = tk.Button(
            self.card_actions_frame,
            text="Play Selected Card",
            command=lambda: self.run_action(
                play_selected, self.game, self.hand_frame, self.table_frame, self.log, self.status_panel
            ),
        )
        self.play_button.pack(side="left", padx=5)

        self.positioned_play_buttons = []
        if self.game.allow_positioned_play:
            self.play_at_spot_button = tk.Button(
                self.card_actions_frame,
                text="Play at Selected Spot",
                command=lambda: self.run_action(
                    play_at_selected_spot,
                    self.game, self.hand_frame, self.table_frame, self.log, self.status_panel,
                ),
            )
            self.play_at_spot_button.pack(side="left", padx=5)
            self.positioned_play_buttons.append(self.play_at_spot_button)

        self.table_action_buttons = []
        if self.game.allow_take_from_table:
            self.take_table_button = tk.Button(
                self.card_actions_frame,
                text="Take Selected from Table",
                command=lambda: self.run_action(
                    take_selected_from_table,
                    self.game, self.table_frame, self.hand_frame, self.log, self.status_panel,
                ),
            )
            self.take_table_button.pack(side="left", padx=5)
            self.table_action_buttons.append(self.take_table_button)
        if self.game.allow_move_table_card_to_discard:
            self.table_discard_button = tk.Button(
                self.card_actions_frame,
                text="Move Selected to Discard",
                command=lambda: self.run_action(
                    move_selected_table_card_to_discard,
                    self.game, self.table_frame, self.log, self.status_panel,
                ),
            )
            self.table_discard_button.pack(side="left", padx=5)
            self.table_action_buttons.append(self.table_discard_button)
        if self.game.allow_manual_table_cleanup:
            self.clear_table_button = tk.Button(
                self.card_actions_frame,
                text="Clear Table",
                command=lambda: self.run_action(
                    clear_table, self.game, self.table_frame, self.log, self.status_panel
                ),
            )
            self.clear_table_button.pack(side="left", padx=5)
            self.table_action_buttons.append(self.clear_table_button)

        self.next_button = tk.Button(
            self.turn_actions_frame,
            text="Next Turn",
            command=lambda: self.run_action(
                end_turn,
                self.game, self.hand_frame, self.log, self.status_panel, self.handle_turn_start,
            ),
        )
        self.next_button.pack(side="left", padx=5)

        if self.game.enable_undo:
            self.undo_button = tk.Button(
                self.turn_actions_frame,
                text="Undo",
                command=self.undo,
                state="disabled",
            )
            self.undo_button.pack(side="left", padx=5)

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
        if self.game.gui_log:
            self._restore_log()
        else:
            self.log(f"{self.current_player_name()}'s turn starts.")
        turn_start_state = (
            self.game.capture_undo_state() if self.game.enable_undo else None
        )
        self.handle_turn_start()
        self._record_undo_state(turn_start_state)
        self.update_point_button()
        self.update_undo_button()
        self.checkpoint()

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

    def run_action(self, action, *args):
        undo_state = self.game.capture_undo_state() if self.game.enable_undo else None
        action(*args)
        self._record_undo_state(undo_state)
        self.update_undo_button()
        self.checkpoint()

    def _record_undo_state(self, undo_state):
        if undo_state is not None and undo_state != self.game.capture_undo_state():
            self.game.undo_stack.append(undo_state)

    def undo(self):
        if not self.game.undo_last_action():
            return
        self.hand_frame.selected_index = None
        self.table_frame.selected_index = None
        self.table_frame.selected_position = None
        self.hand_frame.update_hand()
        self.table_frame.update_table()
        self.status_panel.update_status()
        self.log_text.config(state="normal")
        self.log_text.delete("1.0", "end")
        if self.game.gui_log:
            self.log_text.insert("end", "\n".join(self.game.gui_log) + "\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")
        self.handle_turn_start()
        self.update_point_button()
        self.update_undo_button()
        self.checkpoint()

    def update_undo_button(self):
        if hasattr(self, "undo_button"):
            state = "normal" if self.game.undo_stack else "disabled"
            self.undo_button.config(state=state)

    def checkpoint(self):
        if self.on_checkpoint:
            error = self.on_checkpoint(self.game)
            if error:
                self.log(f"Autosave failed: {error}")

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
        self.run_action(
            request_point, self.game, self.hand_frame, self.log, self.status_panel
        )
        self.update_point_button()

    def update_point_button(self):
        if hasattr(self, "point_button"):
            state = "disabled" if self.game.pending_point_request else "normal"
            self.point_button.config(state=state)

    def handle_turn_start(self):
        self.table_frame.selected_index = None
        self.table_frame.selected_position = None
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
        buttons.extend(self.positioned_play_buttons)
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
        self.checkpoint()
        save_choice = self._ask_to_save()
        if save_choice is None:
            return
        if self.on_exit_menu:
            self.on_exit_menu(self.game, save_choice)

    def exit_to_desktop(self):
        self.checkpoint()
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
