"""Turn flow, confirmations, undo, and session exit controls for GameGUI."""
import tkinter as tk
from tkinter import messagebox
from .cardactions import request_point, end_turn
from ..core.selectionsnapshot import build_selection_snapshot
from ..core.playersessionview import build_player_session_view
from ..core.turnstart import build_turn_start_view

class GameGUIActions:
    def start_shared_offer(self):
        result = self.run_action(lambda: self.session.execute("start_shared_offer", **self.draw_source_parameters()))
        if not result.success:
            messagebox.showwarning("Cannot open shared offer", result.message, parent=self.root)
        return result

    def take_whole_personal_pile(self):
        return self._choose_whole_personal_pile("take_whole_personal_pile", "Take")

    def discard_whole_personal_pile(self):
        return self._choose_whole_personal_pile("discard_whole_personal_pile", "Discard")

    def _choose_whole_personal_pile(self, action, verb):
        from ..core.actionavailability import action_availability
        from ..core.piletransfer import accessible_pile_options
        from ..core.pileoptions import discard_destinations
        available = action_availability(self.game, action)
        if not available.allowed:
            messagebox.showwarning(f"Cannot {verb.lower()} pile", available.reason, parent=self.root)
            return
        options = tuple(pile for pile in accessible_pile_options(self.game) if pile.card_count)
        snapshot = build_selection_snapshot(self.game)
        dialog = tk.Toplevel(self.root)
        dialog.title(f"{verb} whole personal pile")
        dialog.transient(self.root)
        instruction = ("Cards are appended to your hand in pile order." if action == "take_whole_personal_pile"
                       else "Cards are discarded in pile order; the original top card remains on top.")
        tk.Label(dialog, text=instruction).pack(padx=12, pady=8)
        choices = tk.Listbox(dialog, exportselection=False, width=50, height=min(10, len(options)))
        choices.pack(fill="both", expand=True, padx=12)
        for pile in options:
            choices.insert("end", f"{pile.name} ({pile.card_count} cards)")
        choices.selection_set(0)
        destinations = discard_destinations(self.game, snapshot.owner) if action == "discard_whole_personal_pile" else ()
        if destinations:
            tk.Label(dialog, text="Destination:").pack(anchor="w", padx=12, pady=(8, 0))
            piles = tk.Listbox(dialog, exportselection=False, width=50, height=min(6, len(destinations)))
            piles.pack(fill="x", padx=12)
            for destination in destinations:
                piles.insert("end", destination.name)
            piles.selection_set(0)

        def take():
            current = build_selection_snapshot(self.game)
            if (current.session, current.owner) != (snapshot.session, snapshot.owner):
                messagebox.showwarning("Turn changed", "Reopen the pile selector before moving cards.", parent=dialog)
                return
            selected = choices.curselection()
            if not selected:
                messagebox.showwarning("Choose a pile", "Select a personal pile.", parent=dialog)
                return
            pile = options[selected[0]]
            parameters = {"owner": pile.owner, "pile_index": pile.pile_index}
            if destinations:
                selected_destination = piles.curselection()
                if not selected_destination:
                    messagebox.showwarning("Choose a pile", "Select a discard destination.", parent=dialog)
                    return
                destination = destinations[selected_destination[0]]
                parameters.update(discard_pile_index=destination.pile_index, personal=destination.personal)
            result = self.run_action(lambda: self.session.execute(action, **parameters))
            if result.success:
                dialog.destroy()
            else:
                messagebox.showwarning(f"Cannot {verb.lower()} pile", result.message, parent=dialog)
            return result

        tk.Button(dialog, text=f"{verb} whole pile", command=take).pack(pady=6)
        tk.Button(dialog, text="Cancel", command=dialog.destroy).pack(pady=(0, 8))
        dialog.grab_set()

    def transfer_personal_pile(self):
        from ..core.actionavailability import action_availability
        from ..core.piletransfer import transfer_pile_options
        available = action_availability(self.game, "transfer_personal_pile")
        if not available.allowed:
            messagebox.showwarning("Cannot transfer pile", available.reason, parent=self.root)
            return
        sources, targets = transfer_pile_options(self.game)
        snapshot = build_selection_snapshot(self.game)
        dialog = tk.Toplevel(self.root)
        dialog.title("Transfer personal pile")
        dialog.transient(self.root)
        lists = []
        for title, options in (("Source", sources), ("Destination", targets)):
            tk.Label(dialog, text=title).pack(anchor="w", padx=12, pady=(8, 0))
            choices = tk.Listbox(dialog, exportselection=False, width=50, height=min(8, len(options)))
            choices.pack(fill="both", expand=True, padx=12)
            for pile in options:
                choices.insert("end", f"{pile.name} ({pile.card_count} cards)")
            lists.append(choices)
        lists[0].selection_set(0)
        source = sources[0]
        lists[1].selection_set(next(i for i, p in enumerate(targets)
                                    if (p.owner, p.pile_index) != (source.owner, source.pile_index)))

        def transfer():
            current = build_selection_snapshot(self.game)
            if (current.session, current.owner) != (snapshot.session, snapshot.owner):
                messagebox.showwarning("Turn changed", "Reopen the pile selector before transferring.", parent=dialog)
                return
            selected = [choices.curselection() for choices in lists]
            if not all(selected):
                messagebox.showwarning("Choose piles", "Select a source and a destination.", parent=dialog)
                return
            source, target = sources[selected[0][0]], targets[selected[1][0]]
            result = self.run_action(lambda: self.session.execute("transfer_personal_pile",
                source_owner=source.owner, source_pile=source.pile_index,
                target_owner=target.owner, target_pile=target.pile_index))
            if result.success:
                dialog.destroy()
            else:
                messagebox.showwarning("Cannot transfer pile", result.message, parent=dialog)
            return result

        tk.Button(dialog, text="Transfer pile", command=transfer).pack(pady=6)
        tk.Button(dialog, text="Cancel", command=dialog.destroy).pack(pady=(0, 8))
        dialog.grab_set()

    def draw_multiple_cards(self):
        return self._choose_draw_count("draw_cards")

    def deal_cards(self):
        return self._choose_draw_count("deal_cards")

    def _choose_draw_count(self, action):
        from tkinter import simpledialog
        from ..core.actionavailability import ActionContext, action_availability
        from ..core.drawpiles import draw_pile_options
        from ..core.sessionstatus import build_session_status
        dealing = action == "deal_cards"
        failure_title = "Cannot deal cards" if dealing else "Cannot draw cards"
        parameters = self.draw_source_parameters()
        source_id = parameters.get("draw_pile_id", "main")
        available = action_availability(self.game, action, ActionContext(draw_pile_id=source_id))
        if not available.allowed:
            messagebox.showwarning(failure_title, available.reason, parent=self.root)
            return
        status = build_session_status(self.game)
        from ..core.drawrecycling import draw_capacity
        count_available = (next(pile.card_count for pile in draw_pile_options(self.game) if pile.id == source_id)
                           if dealing else draw_capacity(self.game, source_id))
        maximum = count_available // sum(player.active for player in status.players) if dealing else count_available
        count = simpledialog.askinteger("Deal to active players" if dealing else "Draw multiple cards",
                                        "How many cards per active player?" if dealing else "How many cards?",
                                        parent=self.root, minvalue=1, maxvalue=maximum)
        if count is None:
            return
        result = self.run_action(lambda: self.session.execute(action, count=count, **parameters))
        if not result.success:
            messagebox.showwarning(failure_title, result.message, parent=self.root)
        return result

    def shuffle_draw_deck(self):
        result = self.run_action(lambda: self.session.execute("shuffle_draw_deck", **self.draw_source_parameters()))
        if not result.success:
            messagebox.showwarning("Cannot shuffle draw deck", result.message, parent=self.root)
        return result

    def draw_source_parameters(self):
        pile_id = getattr(self, "draw_pile_id", "main")
        return {} if pile_id == "main" else {"draw_pile_id": pile_id}

    def play_multiple_cards(self):
        return self._choose_multiple_cards("play_cards", "Play")

    def discard_multiple_cards(self):
        return self._choose_multiple_cards("discard_cards", "Discard")

    def give_multiple_cards(self, target):
        return self._choose_multiple_cards("give_cards", "Give", target=target)

    def take_multiple_cards(self):
        return self._choose_multiple_cards("take_table_cards", "Take")

    def discard_multiple_table_cards(self):
        return self._choose_multiple_cards("discard_table_cards", "Discard")

    def _choose_multiple_cards(self, action, verb, target=None):
        from ..core.actionavailability import action_availability
        from ..core.pileoptions import discard_destinations
        available = action_availability(self.game, action)
        if not available.allowed:
            messagebox.showwarning(f"Cannot {verb.lower()} cards", available.reason, parent=self.root)
            return
        snapshot = build_selection_snapshot(self.game)
        view = build_player_session_view(self.game, snapshot.owner)
        from_table = action in {"take_table_cards", "discard_table_cards"}
        dialog = tk.Toplevel(self.root)
        dialog.title(f"{verb} multiple cards")
        dialog.transient(self.root)
        instruction = {"play_cards": "Cards play face up in hand order.",
                       "discard_cards": "Cards are discarded in hand order; the last selected card becomes the top card.",
                       "give_cards": "Cards are appended to the recipient's hand in hand order.",
                       "take_table_cards": "Cards are appended to your hand in table order.",
                       "discard_table_cards": "Cards are discarded in table order and become visible in the discard pile."}[action]
        if action == "give_cards":
            from ..core.interactions import build_interaction_options
            options = build_interaction_options(self.game, action)
            recipient = next((item for item in options.targets if item.index == target), None)
            if recipient is None or not recipient.allowed:
                dialog.destroy()
                messagebox.showwarning("Cannot give cards", recipient.reason if recipient else "Choose another player.", parent=self.root)
                return
            instruction = f"To {recipient.name}. " + instruction
        tk.Label(dialog, text="Select at least two cards (Ctrl/Shift). " + instruction,
                 wraplength=420).pack(padx=12, pady=8)
        choices = tk.Listbox(dialog, selectmode="extended", exportselection=False, width=48, height=12)
        choices.pack(padx=12, pady=5, fill="both", expand=True)
        slots = view.table.cards if from_table else view.hands.hands[snapshot.owner].cards
        for slot in slots:
            position = f" at {slot.position}" if from_table else ""
            choices.insert("end", f"{slot.index + 1}. {slot.card if slot.card is not None else 'Hidden card'}{position}")
        destinations = discard_destinations(self.game, snapshot.owner) if action in {"discard_cards", "discard_table_cards"} else ()
        if destinations:
            tk.Label(dialog, text="Destination:").pack(padx=12, anchor="w")
            pile_choices = tk.Listbox(dialog, exportselection=False, width=48, height=min(5, len(destinations)))
            pile_choices.pack(padx=12, pady=5, fill="x")
            for destination in destinations:
                pile_choices.insert("end", destination.name)
            pile_choices.selection_set(0)

        def play():
            current = build_selection_snapshot(self.game)
            revision = "table_revision" if from_table else "hand_revision"
            if (current.session, current.owner, getattr(current, revision)) != (
                    snapshot.session, snapshot.owner, getattr(snapshot, revision)):
                messagebox.showwarning("Cards changed", "Reopen the card selector before moving cards.", parent=dialog)
                return
            indices = list(choices.curselection())
            parameters = {"card_indices": indices}
            if action == "give_cards":
                parameters["target"] = target
            if destinations:
                selected = pile_choices.curselection()
                if not selected:
                    messagebox.showwarning("Choose a pile", "Select a discard destination.", parent=dialog)
                    return
                destination = destinations[selected[0]]
                parameters.update(pile_index=destination.pile_index, personal=destination.personal)
            result = self.run_action(lambda: self.session.execute(action, **parameters))
            if result.success:
                dialog.destroy()
            else:
                messagebox.showwarning(f"Cannot {verb.lower()} cards", result.message, parent=dialog)
            return result

        tk.Button(dialog, text=f"{verb} selected cards", command=play).pack(pady=5)
        tk.Button(dialog, text="Cancel", command=dialog.destroy).pack(pady=(0, 10))
        dialog.grab_set()
        choices.focus_set()

    def next_turn(self, next_player=None, skip_next=False):
        from ..app.turnhandoff import TurnHandoffController
        def advance():
            return self.run_action(end_turn, self.game, self.hand_frame, self.render_log,
                                   self.status_panel, self.handle_turn_start, next_player, skip_next)
        if not self.session.end_turn_availability(next_player, skip_next=skip_next).allowed:
            return advance()
        if not hasattr(self, "turn_flow"):
            self.turn_flow = TurnHandoffController(self.session, enabled=getattr(self, "confirm_next_turn", False),
                                                 confirm_skip=getattr(self, "confirm_skip", False))
        result = self.turn_flow.request(advance, next_player=next_player, skip_next=skip_next)
        if result.code == "skip_confirmation_required":
            if not messagebox.askyesno("Skip next player", "End your turn and skip the next active player?", parent=self.root):
                return self.turn_flow.cancel()
            result = self.turn_flow.confirm_skip()
            if not result.success:
                messagebox.showwarning("Cannot skip player", result.message, parent=self.root)
                self.turn_flow.cancel()
        if result.code == "handoff_required":
            self.turn_handoff.show()
            return None
        return result

    def reverse_turn_order(self):
        result = self.run_action(lambda: self.session.execute("reverse_turn_order"))
        if not result.success:
            messagebox.showwarning("Cannot reverse turn direction", result.message, parent=self.root)
        return result

    def choose_next_player(self):
        options = self.session.next_player_options()
        if not options.allowed:
            messagebox.showinfo("Choose next player", options.reason, parent=self.root)
            return
        dialog = tk.Toplevel(self.root)
        dialog.title("Choose next player")
        dialog.transient(self.root)
        dialog.grab_set()
        choices = tk.Listbox(dialog, height=min(10, len(options.players)), width=36, exportselection=False)
        choices.pack(fill="both", expand=True, padx=10, pady=10)
        for player in options.players:
            choices.insert("end", player.name)
        choices.selection_set(0)
        def hand_over():
            selected = choices.curselection()
            if not selected:
                return
            player = options.players[selected[0]].index
            dialog.destroy()
            return self.next_turn(player)
        tk.Button(dialog, text="Pass turn", command=hand_over).pack(side="right", padx=10, pady=(0, 10))
        tk.Button(dialog, text="Cancel", command=dialog.destroy).pack(side="right", pady=(0, 10))


    def refresh_session_panels(self):
        self.selection.synchronize(build_selection_snapshot(self.game))
        view = build_player_session_view(self.game, self.game.current_player_index,
                                         hand_index=self.selection.hand_index)
        self.status_panel.update_status(view.status)
        if hasattr(self, "personal_piles_ui"):
            self.personal_piles_ui.update(view.personal_piles)
        self.hand_frame.update_hand(view.hands)
        self.table_frame.update_table(view.table)

    def update_chip_action_buttons(self):
        self.chip_bank_ui.update_action_buttons()

    def run_action(self, action, *args):
        self.selection.synchronize(build_selection_snapshot(self.game))
        depth = getattr(self, "_action_depth", 0)
        self._action_depth = depth + 1
        try:
            result = self.session.run(action, *args)
        finally:
            self._action_depth = depth
        if depth:
            return result
        self.render_log()
        self.refresh_session_panels()
        self.update_undo_button()
        self.update_leave_button()
        if hasattr(self, "context_actions"):
            self.context_actions.refresh()
        self.refresh_action_availability()
        if hasattr(self, "offer_ui"):
            self.offer_ui.refresh()
        return result

    def undo(self):
        result = self.session.undo_result()
        if not result.success:
            messagebox.showwarning("Cannot undo", result.message, parent=self.root)
            return result
        self.selection.clear()
        if self.game.active_player_indices():
            for button in self._turn_action_buttons():
                button.configure(state="normal")
        self.handle_turn_start()
        self.render_log()
        self.update_point_button()
        self.update_undo_button()
        self.refresh_action_availability()
        if hasattr(self, "offer_ui"):
            self.offer_ui.refresh()
        return result

    def update_undo_button(self):
        if hasattr(self, "undo_button"):
            state = "normal" if self.session.undo_availability().allowed else "disabled"
            self.undo_button.config(state=state)

    def checkpoint(self):
        self.table_frame.capture_view()
        self.refresh_action_availability()
        result = self.session.checkpoint_result()
        self.render_log()
        return result

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
            result = self.session.execute("flip_hand_card", card_index=selected)
            if not result.success:
                messagebox.showwarning("Cannot flip card", result.message, parent=self.root)
            return result
        return self.run_action(action)

    def reduce_current_score(self):
        def action():
            result = self.session.execute("reduce_score")
            if not result.success:
                messagebox.showwarning("Cannot change score", result.message, parent=self.root)
            return result
        result = self.run_action(action)
        self.update_point_button()
        return result

    def update_point_button(self):
        from .actionavailability import refresh_action_availability
        refresh_action_availability(self, {"request_point", "reduce_score"})

    def update_leave_button(self):
        from .actionavailability import refresh_action_availability
        refresh_action_availability(self, {"leave_session", "end_turn", "return_player", "choose_next_player"})
        if not self.game.active_player_indices():
            for button in self._turn_action_buttons():
                button.configure(state="disabled")

    def choose_returning_player(self):
        options = self.session.return_player_options()
        if not options.allowed:
            messagebox.showinfo("Return player", options.reason, parent=self.root)
            return
        dialog = tk.Toplevel(self.root)
        dialog.title("Return player back to game")
        dialog.transient(self.root)
        dialog.grab_set()
        players = options.players
        choices = tk.Listbox(dialog, height=min(10, len(players)), width=36, exportselection=False)
        choices.pack(fill="both", expand=True, padx=10, pady=10)
        for player in players:
            choices.insert("end", player.name)
        choices.selection_set(0)
        def restore():
            selected = choices.curselection()
            if not selected:
                return
            player = players[selected[0]].index
            def action():
                result = self.session.execute("return_player", player_index=player)
                if result.success:
                    dialog.destroy()
                    for button in self._turn_action_buttons():
                        button.configure(state="normal")
                    self.selection.hand_index = None
                    self.handle_turn_start()
                    self.update_point_button()
                else:
                    messagebox.showwarning("Cannot return player", result.message, parent=dialog)
                return result
            return self.run_action(action)
        tk.Button(dialog, text="Return player", command=restore).pack(side="right", padx=10, pady=(0, 10))
        tk.Button(dialog, text="Cancel", command=dialog.destroy).pack(side="right", pady=(0, 10))

    def leave_current_player(self):
        def action():
            result = self.session.execute("leave_session")
            if not result.success:
                messagebox.showwarning("Cannot leave session", result.message, parent=self.root)
                return result
            self.selection.hand_index = None
            if self.game.active_player_indices():
                self.handle_turn_start()
            return result
        return self.run_action(action)

    def handle_turn_start(self):
        self.update_leave_button()
        self.selection.table_index = None
        self.selection.target_position = None
        work = build_turn_start_view(self.game)
        if not work.active:
            if not getattr(self, "_action_depth", 0):
                self.refresh_session_panels()
            return
        if work.notifications or work.confirmations or not getattr(self, "_action_depth", 0):
            self.refresh_session_panels()
        if work.notifications:
            messagebox.showinfo(work.notifications[0].title,
                "\n\n".join(notice.message for notice in work.notifications), parent=self.root)
        self.session.acknowledge_score_notifications(work.notifications)
        work = build_turn_start_view(self.game)
        if not work.confirmations:
            self.update_chip_action_buttons()
            return

        for button in self._turn_action_buttons():
            button.config(state="disabled")
        while work.next_confirmation is not None:
            prompt = work.next_confirmation
            approved = messagebox.askyesno(prompt.notice.title, prompt.notice.message, parent=self.root)
            result = self.session.execute(prompt.action, approved=approved)
            if not result.success:
                messagebox.showwarning("Cannot confirm", result.message, parent=self.root)
                break
            work = build_turn_start_view(self.game)
            if not getattr(self, "_action_depth", 0) or work.next_confirmation is not None:
                self.render_log()
                self.refresh_session_panels()

        for button in self._turn_action_buttons():
            button.config(state="normal")
        self.update_point_button()
        self.update_chip_action_buttons()
        self.update_leave_button()

    def _turn_action_buttons(self):
        buttons = [self.draw_button, self.discard_button, self.play_button, self.next_button]
        if hasattr(self, "shared_offer_button"):
            buttons.append(self.shared_offer_button)
        if hasattr(self, "deal_cards_button"):
            buttons.append(self.deal_cards_button)
        if hasattr(self, "draw_multiple_button"):
            buttons.append(self.draw_multiple_button)
        if hasattr(self, "shuffle_draw_button"):
            buttons.append(self.shuffle_draw_button)
        if hasattr(self, "discard_multiple_button"):
            buttons.append(self.discard_multiple_button)
        if hasattr(self, "play_multiple_button"):
            buttons.append(self.play_multiple_button)
        if hasattr(self, "skip_next_button"):
            buttons.append(self.skip_next_button)
        if hasattr(self, "reverse_turn_button"):
            buttons.append(self.reverse_turn_button)
        if hasattr(self, "choose_next_button"):
            buttons.append(self.choose_next_button)
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


