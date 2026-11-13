"""Turn flow, confirmations, undo, and session exit controls for GameGUI."""
import tkinter as tk
from tkinter import messagebox
from .cardactions import request_point
from .sessionactions import execute_value

class GameGUIActions:

    def update_chip_action_buttons(self):
        self.chip_bank_ui.update_action_buttons()

    def run_action(self, action, *args):
        self.session.run(action, *args)
        if hasattr(self, "personal_piles_ui"):
            self.personal_piles_ui.update()
        self.update_undo_button()
        self.update_leave_button()
        if hasattr(self, "context_actions"):
            self.context_actions.refresh()
        self.refresh_action_availability()

    def undo(self):
        if not self.session.undo():
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
        if self.game.active_player_indices():
            for button in self._turn_action_buttons():
                button.configure(state="normal")
        self.handle_turn_start()
        self.update_point_button()
        self.update_undo_button()
        self.refresh_action_availability()

    def update_undo_button(self):
        if hasattr(self, "undo_button"):
            state = "normal" if self.game.undo_stack else "disabled"
            self.undo_button.config(state=state)

    def checkpoint(self):
        self.table_frame.capture_view()
        self.refresh_action_availability()
        self.session.checkpoint()

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

    def flip_current_hand_card(self):
        selected = self.hand_frame.selected_index
        if selected is None:
            messagebox.showwarning("No selection", "Select a card in your hand first.", parent=self.root)
            return
        def action():
            card = execute_value(self.game, "flip_hand_card", card_index=selected)
            if card is not None:
                revealed = selected in self.current_player().revealed_indices
                self.log(f"{self.current_player_name()} revealed {card}." if revealed else f"{self.current_player_name()} hid a hand card.")
                self.hand_frame.update_hand()
        self.run_action(action)

    def reduce_current_score(self):
        def action():
            _, message = execute_value(self.game, "reduce_score")
            self.log(message)
            self.status_panel.update_status()
        self.run_action(action)
        self.update_point_button()

    def update_point_button(self):
        if hasattr(self, "point_button"):
            state = "disabled" if self.game.pending_point_request else "normal"
            self.point_button.config(state=state)
            if hasattr(self, "reduce_score_button"):
                self.reduce_score_button.config(state=state)

    def update_leave_button(self):
        if hasattr(self, "leave_session_button"):
            self.leave_session_button.configure(state="normal" if self.game.can_leave_session() else "disabled")
        if not self.game.active_player_indices():
            for button in self._turn_action_buttons():
                button.configure(state="disabled")

    def choose_returning_player(self):
        if not self.game.left_players:
            messagebox.showinfo("Return player", "No players have left the session.", parent=self.root)
            return
        if self.game.pending_point_request is not None or self.game.pending_pot_withdrawal is not None:
            messagebox.showinfo("Return player", "Complete the pending confirmation first.", parent=self.root)
            return
        dialog = tk.Toplevel(self.root)
        dialog.title("Return player back to game")
        dialog.transient(self.root)
        dialog.grab_set()
        players = list(self.game.left_players)
        choices = tk.Listbox(dialog, height=min(10, len(players)), width=36, exportselection=False)
        choices.pack(fill="both", expand=True, padx=10, pady=10)
        for player in players:
            choices.insert("end", self.game.players[player].name)
        choices.selection_set(0)
        def restore():
            selected = choices.curselection()
            if not selected:
                return
            player = players[selected[0]]
            def action():
                ok, message = execute_value(self.game, "return_player", player_index=player)
                self.log(message)
                if ok:
                    for button in self._turn_action_buttons():
                        button.configure(state="normal")
                    self.hand_frame.selected_index = None
                    self.hand_frame.update_hand()
                    self.status_panel.update_status()
                    self.handle_turn_start()
                    self.update_point_button()
            dialog.destroy()
            self.run_action(action)
        tk.Button(dialog, text="Return player", command=restore).pack(side="right", padx=10, pady=(0, 10))
        tk.Button(dialog, text="Cancel", command=dialog.destroy).pack(side="right", pady=(0, 10))

    def leave_current_player(self):
        def action():
            ok, message = execute_value(self.game, "leave_session")
            self.log(message)
            if not ok:
                return
            self.hand_frame.selected_index = None
            self.hand_frame.update_hand()
            self.status_panel.update_status()
            if self.game.active_player_indices():
                self.handle_turn_start()
                self.log(f"{self.current_player_name()}'s turn starts.")
            else:
                self.log("All players have left the session.")
        self.run_action(action)

    def handle_turn_start(self):
        self.update_leave_button()
        if not self.game.active_player_indices():
            return
        alerts = self.game.turn_score_alerts()
        if alerts:
            messagebox.showinfo("Score notice", "\n\n".join(alerts), parent=self.root)
        if hasattr(self, "personal_piles_ui"):
            self.personal_piles_ui.update()
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
                f"{requester_name} requested a score change of {self.game.pending_point_request.get('delta', 1):+d}.\n\n"
                f"As {voter_name}, do you approve this score change?",
                parent=self.root,
            )
            _, result = execute_value(self.game, "confirm_point", approved=approved)
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
            _, result = execute_value(self.game, "confirm_pot", approved=approved)
            self.log(result)
            self.status_panel.update_status()

        for button in self._turn_action_buttons():
            button.config(state="normal")
        self.update_point_button()
        self.update_chip_action_buttons()
        self.update_leave_button()

    def _turn_action_buttons(self):
        buttons = [self.draw_button, self.discard_button, self.play_button, self.next_button]
        if self.discard_draw_button is not None:
            buttons.append(self.discard_draw_button)
        buttons.extend(self.chip_bank_ui.buttons)
        buttons.extend(self.positioned_play_buttons)
        buttons.extend(self.table_action_buttons)
        if hasattr(self, "flip_hand_button"):
            buttons.append(self.flip_hand_button)
        if hasattr(self, "special_actions_ui"):
            buttons.extend(self.special_actions_ui.buttons)
        if hasattr(self, "visible_hands_button"):
            buttons.append(self.visible_hands_button)
        if hasattr(self, "interactions_ui"):
            buttons.append(self.interactions_ui.button)
        if hasattr(self, "personal_pile_button"):
            buttons.append(self.personal_pile_button)
        if hasattr(self, "play_face_down_button"):
            buttons.append(self.play_face_down_button)
        if getattr(self, "recycle_discard_button", None) is not None:
            buttons.append(self.recycle_discard_button)
        if hasattr(self, "point_button"):
            buttons.append(self.point_button)
        if hasattr(self, "reduce_score_button"):
            buttons.append(self.reduce_score_button)
        if hasattr(self, "leave_session_button"):
            buttons.append(self.leave_session_button)
        return buttons

    def _ask_to_save(self):
        if not self.require_exit_confirmation:
            return False
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


