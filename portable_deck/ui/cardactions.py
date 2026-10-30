# cardactions.py
import tkinter as tk
from tkinter import messagebox

def draw_card(game, hand_frame, gui_log, status_panel):
    """Current player draws a card."""
    player_name = game.players[game.current_player_index].name
    card = game.deal_card_to_current()
    hand_frame.update_hand()
    status_panel.update_status()
    if card is None:
        gui_log("The draw deck is empty. No card was drawn.")
    else:
        gui_log(f"{player_name} drew a card.")


def draw_from_discard(game, hand_frame, gui_log, status_panel, root):
    """Take the configured card from any shared or personal discard pile."""
    piles = [(name, pile) for name, pile in game.all_discard_piles() if pile]
    if not piles:
        messagebox.showinfo("Discard pile is empty", "There are no cards to take.", parent=root)
        return
    if game.draw_from_discard_mode == "any":
        _choose_discard_card(game, piles, hand_frame, gui_log, status_panel, root)
    elif len(piles) == 1:
        _take_discard_card(game, piles[0][1], len(piles[0][1]) - 1, hand_frame, gui_log, status_panel, piles[0][0])
    else:
        _choose_discard_pile(game, piles, hand_frame, gui_log, status_panel, root)


def _choose_discard_pile(game, piles, hand_frame, gui_log, status_panel, root):
    dialog = tk.Toplevel(root)
    dialog.title("Choose a discard pile")
    dialog.transient(root)
    dialog.grab_set()
    tk.Label(dialog, text="Choose a pile; its top card will be taken:").pack(anchor="w", padx=10, pady=(10, 5))
    choices = tk.Listbox(dialog, exportselection=False, width=45, height=min(12, len(piles)))
    choices.pack(fill="both", expand=True, padx=10)
    for name, pile in piles:
        choices.insert("end", f"{name} ({len(pile)} cards): {pile[-1]}")
    choices.selection_set(0)

    def take_selected():
        selected = choices.curselection()
        if not selected:
            return
        name, pile = piles[selected[0]]
        _take_discard_card(game, pile, len(pile) - 1, hand_frame, gui_log, status_panel, name)
        dialog.destroy()

    buttons = tk.Frame(dialog)
    buttons.pack(fill="x", padx=10, pady=10)
    tk.Button(buttons, text="Take top card", command=take_selected).pack(side="right")
    tk.Button(buttons, text="Cancel", command=dialog.destroy).pack(side="right", padx=5)
    choices.bind("<Double-1>", lambda _event: take_selected())
    dialog.wait_window()


def _choose_discard_card(game, piles, hand_frame, gui_log, status_panel, root):
    dialog = tk.Toplevel(root)
    dialog.title("Choose a discard card")
    dialog.transient(root)
    dialog.grab_set()
    dialog.geometry("440x360")
    tk.Label(dialog, text="Select a card from any discard pile:").pack(anchor="w", padx=10, pady=(10, 5))
    list_frame = tk.Frame(dialog)
    list_frame.pack(fill="both", expand=True, padx=10)
    card_list = tk.Listbox(list_frame, exportselection=False)
    card_list.pack(side="left", fill="both", expand=True)
    scrollbar = tk.Scrollbar(list_frame, orient="vertical", command=card_list.yview)
    scrollbar.pack(side="right", fill="y")
    card_list.configure(yscrollcommand=scrollbar.set)
    card_sources = []
    for pile_name, pile in piles:
        for position in range(len(pile) - 1, -1, -1):
            marker = " (top)" if position == len(pile) - 1 else ""
            card_sources.append((pile, position, pile_name))
            card_list.insert("end", f"{pile_name}: {pile[position]}{marker}")
    card_list.selection_set(0)
    card_list.activate(0)

    buttons = tk.Frame(dialog)
    buttons.pack(fill="x", padx=10, pady=10)

    def take_selected():
        selection = card_list.curselection()
        if not selection:
            messagebox.showwarning("Select a card", "Choose a card from the list.", parent=dialog)
            return
        pile, index, pile_name = card_sources[selection[0]]
        _take_discard_card(game, pile, index, hand_frame, gui_log, status_panel, pile_name)
        dialog.destroy()

    tk.Button(buttons, text="Take selected", command=take_selected).pack(side="right")
    tk.Button(buttons, text="Cancel", command=dialog.destroy).pack(side="right", padx=5)
    card_list.bind("<Double-1>", lambda _event: take_selected())
    dialog.wait_window()


def _take_discard_card(game, pile, index, hand_frame, gui_log, status_panel, pile_name):
    card = pile.pop(index)
    player = game.players[game.current_player_index]
    player.draw_card(card)
    game.log_action(player.name, "draw_from_discard", card)
    hand_frame.selected_index = None
    hand_frame.update_hand()
    status_panel.update_status()
    gui_log(f"{player.name} took {card} from {pile_name}.")


def discard_selected(game, hand_frame, gui_log, status_panel):
    """Discard the currently selected card."""
    selected = hand_frame.selected_index
    if selected is None:
        messagebox.showwarning("No selection", "Select a card first!")
        return

    destinations = _current_player_discard_destinations(game)
    if len(destinations) == 1:
        _discard_to_destination(game, hand_frame, gui_log, status_panel, selected, destinations[0])
    else:
        _choose_discard_destination(game, hand_frame, gui_log, status_panel, selected, destinations)


def _discard_to_destination(game, hand_frame, gui_log, status_panel, selected, destination):
    name, pile_index, personal = destination
    card = game.discard_from_current(selected + 1, pile_index, personal)
    if card:
        hand_frame.selected_index = None
        hand_frame.update_hand()
        status_panel.update_status()
        gui_log(f"{game.players[game.current_player_index].name} discarded {card} to {name}.")
    else:
        messagebox.showwarning("Invalid", "Invalid card selection!")


def _choose_discard_destination(game, hand_frame, gui_log, status_panel, selected, destinations):
    dialog = tk.Toplevel(hand_frame.winfo_toplevel())
    dialog.title("Choose a discard pile")
    dialog.transient(hand_frame.winfo_toplevel())
    dialog.grab_set()
    tk.Label(dialog, text="Choose where to discard the selected card:").pack(anchor="w", padx=10, pady=(10, 5))
    choices = tk.Listbox(dialog, exportselection=False, width=42, height=min(12, len(destinations)))
    choices.pack(fill="both", expand=True, padx=10)
    for name, pile_index, personal in destinations:
        choices.insert("end", name)
    choices.selection_set(0)

    def discard():
        selection = choices.curselection()
        if not selection:
            return
        _discard_to_destination(game, hand_frame, gui_log, status_panel, selected, destinations[selection[0]])
        dialog.destroy()

    buttons = tk.Frame(dialog)
    buttons.pack(fill="x", padx=10, pady=10)
    tk.Button(buttons, text="Discard", command=discard).pack(side="right")
    tk.Button(buttons, text="Cancel", command=dialog.destroy).pack(side="right", padx=5)
    choices.bind("<Double-1>", lambda _event: discard())
    dialog.wait_window()


def _current_player_discard_destinations(game):
    destinations = [
        (f"Shared discard {index + 1}", index, False)
        for index in range(len(game.discard_piles))
    ]
    destinations.extend(
        (f"Your personal discard {index + 1}", index, True)
        for index in range(len(game.personal_discard_piles[game.current_player_index]))
    )
    return destinations


def play_selected(game, hand_frame, table_frame, gui_log, status_panel):
    """Play the selected hand card at the end of the table's original line."""
    _play_from_hand_at(game, hand_frame, table_frame, None, gui_log, status_panel)


def play_selected_face_down(game, hand_frame, table_frame, gui_log, status_panel):
    selected = hand_frame.selected_index
    if selected is None:
        messagebox.showwarning("No selection", "Select a card from your hand first!")
        return
    position = table_frame.selected_position if game.allow_positioned_play else None
    card = game.play_to_table(selected + 1, position=position, face_up=False)
    if card:
        player = game.players[game.current_player_index].name
        hand_frame.selected_index = None
        hand_frame.update_hand()
        table_frame.clear_selection()
        status_panel.update_status()
        gui_log(f"{player} played a card face down onto the table.")
    else:
        messagebox.showwarning("Invalid", "The card could not be played at that spot.")


def flip_selected_table_card(game, table_frame, gui_log, status_panel):
    if table_frame.selected_index is None:
        messagebox.showwarning("No selection", "Select a face-down table card first!")
        return
    card = game.flip_table_card(table_frame.selected_index)
    if card is None:
        messagebox.showwarning("Invalid flip", "That card cannot be revealed yet.")
        return
    table_frame.clear_selection()
    status_panel.update_status()
    gui_log(f"A face-down card was revealed: {card}.")


def recycle_discard_into_deck(game, gui_log, status_panel, root):
    count = game.recycle_discard_into_deck()
    if not count:
        messagebox.showinfo("Cannot recycle", "The draw deck must be empty and the discard pile must contain cards.", parent=root)
        return
    status_panel.update_status()
    gui_log(f"The discard pile was recycled into the draw deck ({count} cards).")


def _play_from_hand_at(game, hand_frame, table_frame, position, gui_log, status_panel):
    selected = hand_frame.selected_index
    if selected is None:
        messagebox.showwarning("No selection", "Select a card from your hand first!")
        return

    card = game.play_to_table(selected + 1, position=position)
    if card:
        player_name = game.players[game.current_player_index].name
        hand_frame.selected_index = None
        hand_frame.update_hand()
        table_frame.clear_selection()
        status_panel.update_status()
        gui_log(f"{player_name} played {card} onto the table.")
    else:
        messagebox.showwarning("Invalid", "Invalid card selection!")


def play_at_selected_spot(game, hand_frame, table_frame, gui_log, status_panel):
    selected_hand = hand_frame.selected_index
    if selected_hand is None:
        messagebox.showwarning("No selection", "Select a card from your hand first!")
        return
    if table_frame.selected_position is None and table_frame.selected_index is not None:
        if game.occupied_slot_action == "invalid":
            messagebox.showwarning(
                "Occupied spot", "This spot is occupied. Choose an empty slot or enable swapping in Settings."
            )
            return
        result = game.swap_with_table(selected_hand + 1, table_frame.selected_index)
        if result is None:
            messagebox.showwarning("Invalid", "The selected card could not be swapped.")
            return
        played_card, returned_card = result
        player_name = game.players[game.current_player_index].name
        hand_frame.selected_index = None
        hand_frame.update_hand()
        table_frame.clear_selection()
        status_panel.update_status()
        gui_log(f"{player_name} swapped {played_card} for {returned_card} on the table.")
        return
    if table_frame.selected_position is None:
        messagebox.showwarning("No spot selected", "Select an empty spot on the table first!")
        return
    _play_from_hand_at(
        game, hand_frame, table_frame, table_frame.selected_position, gui_log, status_panel
    )


def take_selected_from_table(game, table_frame, hand_frame, gui_log, status_panel):
    selected = table_frame.selected_index
    if selected is None:
        messagebox.showwarning("No selection", "Select a table card first!")
        return
    card = game.take_from_table(selected)
    if card is None:
        messagebox.showwarning("Invalid", "That table card is no longer available!")
        table_frame.clear_selection()
        return
    player_name = game.players[game.current_player_index].name
    table_frame.selected_index = None
    table_frame.update_table()
    hand_frame.update_hand()
    status_panel.update_status()
    gui_log(f"{player_name} took {card} from the table.")


def move_selected_table_card_to_discard(game, table_frame, gui_log, status_panel):
    selected = table_frame.selected_index
    if selected is None:
        messagebox.showwarning("No selection", "Select a table card first!")
        return
    destinations = _current_player_discard_destinations(game)
    if len(destinations) > 1:
        dialog = tk.Toplevel(table_frame.winfo_toplevel())
        dialog.title("Choose a discard pile")
        dialog.transient(table_frame.winfo_toplevel())
        dialog.grab_set()
        tk.Label(dialog, text="Choose where to move this table card:").pack(anchor="w", padx=10, pady=(10, 5))
        choices = tk.Listbox(dialog, exportselection=False, width=42, height=min(12, len(destinations)))
        choices.pack(fill="both", expand=True, padx=10)
        for name, _pile_index, _personal in destinations:
            choices.insert("end", name)
        choices.selection_set(0)

        def move_to_selected():
            choice = choices.curselection()
            if not choice:
                return
            _finish_table_discard(game, table_frame, gui_log, status_panel, selected, destinations[choice[0]])
            dialog.destroy()

        buttons = tk.Frame(dialog)
        buttons.pack(fill="x", padx=10, pady=10)
        tk.Button(buttons, text="Move", command=move_to_selected).pack(side="right")
        tk.Button(buttons, text="Cancel", command=dialog.destroy).pack(side="right", padx=5)
        choices.bind("<Double-1>", lambda _event: move_to_selected())
        dialog.wait_window()
        return
    _finish_table_discard(game, table_frame, gui_log, status_panel, selected, destinations[0])


def _finish_table_discard(game, table_frame, gui_log, status_panel, selected, destination):
    name, pile_index, personal = destination
    card = game.move_table_card_to_discard(selected, pile_index, personal)
    if card is None:
        messagebox.showwarning("Invalid", "That table card is no longer available!")
        table_frame.clear_selection()
        return
    table_frame.selected_index = None
    table_frame.update_table()
    status_panel.update_status()
    gui_log(f"{card} was moved from the table to {name}.")


def move_selected_table_card(game, table_frame, gui_log, status_panel):
    """Move the selected table card to the selected empty table slot."""
    selected = table_frame.selected_index
    position = table_frame.selected_position
    if selected is None:
        messagebox.showwarning("No card selected", "Select a table card to move first!")
        return
    if position is None:
        messagebox.showwarning("No spot selected", "Select an empty table spot as the destination!")
        return
    card = game.move_table_card(selected, position)
    if card is None:
        messagebox.showwarning("Invalid move", "The selected card could not be moved to that spot!")
        return
    table_frame.clear_selection()
    status_panel.update_status()
    gui_log(f"{card} was moved to another spot on the table.")


def clear_table(game, table_frame, gui_log, status_panel):
    count = game.clear_table()
    table_frame.selected_index = None
    table_frame.update_table()
    status_panel.update_status()
    if count:
        gui_log(f"The table was cleared. {count} card(s) moved to the discard pile.")
    else:
        gui_log("The table is already empty.")


def end_turn(game, hand_frame, gui_log, status_panel, on_turn_start=None):
    """End current player's turn and move to next."""
    round_ended, cleared_count = game.finish_turn()
    hand_frame.selected_index = None
    hand_frame.update_hand()
    status_panel.update_status()
    if round_ended:
        gui_log("The round has ended.")
    if cleared_count:
        gui_log(f"The table was cleared. {cleared_count} card(s) moved to the discard pile.")
    gui_log(f"Turn ended. {game.players[game.current_player_index].name}'s turn starts.")
    if on_turn_start:
        on_turn_start()


def request_point(game, hand_frame, gui_log, status_panel):
    succeeded, message = game.request_point()
    gui_log(message)
    status_panel.update_status()
