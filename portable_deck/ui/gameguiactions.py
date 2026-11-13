"""Turn flow, confirmations, undo, and session exit controls for GameGUI."""
import tkinter as tk
from tkinter import messagebox
from .cardactions import request_point
from .sessionactions import execute_value

class GameGUIActions:

    def update_chip_action_buttons(self):
        self.chip_bank_ui.update_action_buttons()

    def run_action(self, action, *args):
        self.selection.synchronize(self.game)
        self.session.run(action, *args)
        self.render_log()
        self.selection.synchronize(self.game)
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
        self.selection.clear()
        self.hand_frame.update_hand()
        self.table_frame.update_table()
        self.status_panel.update_status()
        self.log_text.config(state="normal")
        self.log_text.delete("1.0", "end")
        if self.game.game_log:
            self.log_text.insert("end", "\n".join(self.game.game_log) + "\n")
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
        self.render_log()

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
            request_point, self.game, self.hand_frame, self.render_log, self.status_panel
        )
        self.update_point_button()

    def flip_current_hand_card(self):
        selected = self.selection.hand_index
        if selected is None:
            messagebox.showwarning("No selection", "Select a card in your hand first.", parent=self.root)
            return
        def action():
            card = execute_value(self.game, "flip_hand_card", card_index=selected)
            if card is not None:
                revealed = selected in self.current_player().revealed_indices
                self.render_log()
                self.hand_frame.update_hand()
        self.run_action(action)

    def reduce_current_score(self):
        def action():
            _, message = execute_value(self.game, "reduce_score")
            self.render_log()
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
                self.render_log()
                if ok:
                    for button in self._turn_action_buttons():
                        button.configure(state="normal")
                    self.selection.hand_index = None
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
            self.render_log()
            if not ok:
                return
            self.selection.hand_index = None
            self.hand_frame.update_hand()
            self.status_panel.update_status()
            if self.game.active_player_indices():
                self.handle_turn_start()
                self.render_log()
        self.run_action(action)

    def handle_turn_start(self):
        self.update_leave_button()
        if not self.game.active_player_indices():
            return
        alerts = self.game.score_notifications()
        if alerts:
            messagebox.showinfo(alerts[0].title, "\n\n".join(notice.message for notice in alerts), parent=self.root)
        self.game.acknowledge_score_notifications(alerts)
        if hasattr(self, "personal_piles_ui"):
            self.personal_piles_ui.update()
        self.selection.table_index = None
        self.selection.target_position = None
        self.table_frame.update_table()
        needs_point_confirmation = self.game.current_player_must_confirm_point()
        needs_pot_confirmation = self.game.current_player_must_confirm_pot_withdrawal()
        if not needs_point_confirmation and not needs_pot_confirmation:
            self.update_chip_action_buttons()
            return

        for button in self._turn_action_buttons():
            button.config(state="disabled")
        if needs_point_confirmation:
            notice = self.game.score_confirmation_notification()
            approved = messagebox.askyesno(notice.title, notice.message, parent=self.root)
            _, result = execute_value(self.game, "confirm_point", approved=approved)
            self.render_log()
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
            self.render_log()
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


