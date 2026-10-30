"""Turn flow, confirmations, undo, and session exit controls for GameGUI."""
from tkinter import messagebox
from .cardactions import request_point

class GameGUIActions:

    def update_chip_action_buttons(self):
        self.chip_bank_ui.update_action_buttons()

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
        needs_point_confirmation = self.game.current_player_must_confirm_point()
        needs_pot_confirmation = self.game.current_player_must_confirm_pot_withdrawal()
        if not needs_point_confirmation and not needs_pot_confirmation:
            self.update_chip_action_buttons()
            return

        for button in self._turn_action_buttons():
            button.config(state="disabled")
        if needs_point_confirmation:
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

        if self.game.current_player_must_confirm_pot_withdrawal():
            request = self.game.pending_pot_withdrawal
            requester_name = self.game.players[request["requester"]].name
            recipient_name = self.game.players[request["recipient"]].name
            voter_name = self.current_player_name()
            approved = messagebox.askyesno(
                "Confirm pot withdrawal",
                f"{requester_name} requested to give the {self.game.chip_pot}-chip pot "
                f"to {recipient_name}.\n\nAs {voter_name}, do you approve?",
                parent=self.root,
            )
            _, result = self.game.confirm_pot_withdrawal(approved)
            self.log(result)
            self.status_panel.update_status()

        for button in self._turn_action_buttons():
            button.config(state="normal")
        self.update_point_button()
        self.update_chip_action_buttons()

    def _turn_action_buttons(self):
        buttons = [self.draw_button, self.discard_button, self.play_button, self.next_button]
        if self.discard_draw_button is not None:
            buttons.append(self.discard_draw_button)
        buttons.extend(self.chip_bank_ui.buttons)
        buttons.extend(self.positioned_play_buttons)
        buttons.extend(self.table_action_buttons)
        if hasattr(self, "play_face_down_button"):
            buttons.append(self.play_face_down_button)
        if getattr(self, "recycle_discard_button", None) is not None:
            buttons.append(self.recycle_discard_button)
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


