"""Right-click actions reuse the session's existing action buttons."""
import tkinter as tk


def card_menu_entries(gui, location):
    gui.refresh_action_availability()
    game = gui.game
    entries = []
    def include(name, allowed=True):
        button = getattr(gui, name, None)
        if allowed and button is not None:
            entries.append((button.cget("text"), button.invoke, button.cget("state")))
    if location == "hand":
        include("play_button", game.enable_table or (not game.enable_discard_pile and not game.enable_interactions))
        include("discard_button", game.enable_discard_pile)
        for name in ("play_face_down_button", "personal_pile_button", "flip_hand_button"):
            include(name)
        include("play_at_spot_button", gui.table_frame.selected_position is not None)
        if hasattr(gui, "interactions_ui") and game.interaction_allowed("give_card"):
            entries.append(("Give to player…", lambda: gui.interactions_ui.show("give_card"), "normal" if game.active_player_indices() and not game.current_player_must_confirm_point() and not game.current_player_must_confirm_pot_withdrawal() else "disabled"))
        if hasattr(gui, "special_actions_ui"):
            entries.extend((button.cget("text"), button.invoke, button.cget("state")) for button in gui.special_actions_ui.buttons)
    else:
        for name in ("take_table_button", "table_discard_button", "flip_table_card_button"):
            include(name)
        move = getattr(gui, "move_table_card_button", None)
        if move is not None:
            command = move.invoke if gui.table_frame.selected_position is not None else lambda: choose_move_destination(gui)
            entries.append(("Move to position…", command, "normal" if gui.table_frame.selected_index is not None and gui.game.active_player_indices() and not gui.game.current_player_must_confirm_point() and not gui.game.current_player_must_confirm_pot_withdrawal() else "disabled"))
    return entries


def choose_move_destination(gui):
    positions = sorted(gui.game.available_table_positions())
    if not positions:
        from tkinter import messagebox
        messagebox.showinfo("Move card", "There are no empty positions available.", parent=gui.root)
        return
    dialog = tk.Toplevel(gui.root)
    dialog.title("Choose table position")
    dialog.transient(gui.root)
    dialog.grab_set()
    choices = tk.Listbox(dialog, height=min(12, len(positions)), width=36, exportselection=False)
    choices.pack(fill="both", expand=True, padx=10, pady=10)
    scrollbar = tk.Scrollbar(dialog, command=choices.yview)
    scrollbar.pack(side="right", fill="y")
    choices.configure(yscrollcommand=scrollbar.set)
    for row, column in positions:
        choices.insert("end", f"Row {row}, column {column}")
    choices.selection_set(0)
    def move():
        selected = choices.curselection()
        if selected:
            gui.table_frame.selected_position = positions[selected[0]]
            dialog.destroy()
            gui.refresh_action_availability()
            gui.move_table_card_button.invoke()
    tk.Button(dialog, text="Move", command=move).pack(side="right", padx=10, pady=10)
    tk.Button(dialog, text="Cancel", command=dialog.destroy).pack(side="right", pady=10)


def show_card_menu(gui, event, location, index):
    if location == "hand":
        if not 0 <= index < len(gui.current_player().hand):
            return "break"
        # Selecting through a context menu must never toggle the card off.
        gui.hand_frame.selected_index = None
        gui.hand_frame.select_card(index)
        gui.table_frame.selected_index = None
        gui.table_frame.update_table()
    else:
        if not 0 <= index < len(gui.game.table_cards):
            return "break"
        gui.table_frame.selected_index = None
        gui.table_frame.select_card(index)
    if hasattr(gui, "context_actions"):
        gui.context_actions.refresh()
    previous = getattr(gui, "card_context_menu", None)
    if previous is not None:
        previous.destroy()
    menu = tk.Menu(gui.root, tearoff=False)
    gui.card_context_menu = menu
    entries = card_menu_entries(gui, location)
    from .actionavailability import action_reason
    for label, command, state in entries:
        reason = ""
        if state == "disabled":
            for button in gui.card_actions_frame.winfo_children():
                if isinstance(button, tk.Button) and button.cget("text") == label:
                    reason = action_reason(gui, button)
                    break
        menu.add_command(label=label + (" — " + reason if reason else ""), command=command, state=state)
    if not entries:
        menu.add_command(label="No available actions", state="disabled")
    try:
        menu.tk_popup(event.x_root, event.y_root)
    finally:
        menu.grab_release()
    return "break"
