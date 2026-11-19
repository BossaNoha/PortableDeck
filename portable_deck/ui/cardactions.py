# cardactions.py
from .sessionactions import execute_value
from ..core.playerview import build_player_discard_view
from ..core.pileoptions import discard_destinations
import tkinter as tk
from tkinter import messagebox

def draw_card(game, hand_frame, render_log, status_panel):
    """Current player draws a card."""
    player_name = game.players[game.current_player_index].name
    card = execute_value(game, "draw_card")


def draw_from_discard(game, hand_frame, render_log, status_panel, root):
    """Take the configured card from any shared or personal discard pile."""
    view = build_player_discard_view(game, game.current_player_index)
    if not view.enabled:
        return
    piles = [pile for pile in view.piles if pile.card_count]
    if not piles:
        messagebox.showinfo("Discard pile is empty", "There are no cards to take.", parent=root)
        return
    if view.mode == "any":
        _choose_discard_card(game, piles, hand_frame, render_log, status_panel, root)
    elif len(piles) == 1:
        _take_discard_card(game, piles[0].source_index, piles[0].cards[0].index, hand_frame, render_log, status_panel)
    else:
        _choose_discard_pile(game, piles, hand_frame, render_log, status_panel, root)


def _choose_discard_pile(game, piles, hand_frame, render_log, status_panel, root):
    dialog = tk.Toplevel(root)
    dialog.title("Choose a discard pile")
    dialog.transient(root)
    dialog.grab_set()
    tk.Label(dialog, text="Choose a pile; its top card will be taken:").pack(anchor="w", padx=10, pady=(10, 5))
    choices = tk.Listbox(dialog, exportselection=False, width=45, height=min(12, len(piles)))
    choices.pack(fill="both", expand=True, padx=10)
    for pile in piles:
        choices.insert("end", f"{pile.name} ({pile.card_count} cards): {pile.cards[0].card}")
    choices.selection_set(0)

    def take_selected():
        selected = choices.curselection()
        if not selected:
            return
        pile = piles[selected[0]]
        _take_discard_card(game, pile.source_index, pile.cards[0].index, hand_frame, render_log, status_panel)
        dialog.destroy()

    buttons = tk.Frame(dialog)
    buttons.pack(fill="x", padx=10, pady=10)
    tk.Button(buttons, text="Take top card", command=take_selected).pack(side="right")
    tk.Button(buttons, text="Cancel", command=dialog.destroy).pack(side="right", padx=5)
    choices.bind("<Double-1>", lambda _event: take_selected())
    dialog.wait_window()


def _choose_discard_card(game, piles, hand_frame, render_log, status_panel, root):
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
    for pile in piles:
        for card in pile.cards:
            marker = " (top)" if card.index == pile.card_count - 1 else ""
            card_sources.append((pile.source_index, card.index))
            card_list.insert("end", f"{pile.name}: {card.card}{marker}")
    card_list.selection_set(0)
    card_list.activate(0)

    buttons = tk.Frame(dialog)
    buttons.pack(fill="x", padx=10, pady=10)

    def take_selected():
        selection = card_list.curselection()
        if not selection:
            messagebox.showwarning("Select a card", "Choose a card from the list.", parent=dialog)
            return
        source, index = card_sources[selection[0]]
        _take_discard_card(game, source, index, hand_frame, render_log, status_panel)
        dialog.destroy()

    tk.Button(buttons, text="Take selected", command=take_selected).pack(side="right")
    tk.Button(buttons, text="Cancel", command=dialog.destroy).pack(side="right", padx=5)
    card_list.bind("<Double-1>", lambda _event: take_selected())
    dialog.wait_window()


def _take_discard_card(game, source, index, hand_frame, render_log, status_panel):
    card = execute_value(game, "draw_from_discard", source_index=source, card_index=index)
    if card is None:
        return
    player = game.players[game.current_player_index]
    hand_frame.game_gui.selection.hand_index = None


def discard_selected(game, hand_frame, render_log, status_panel):
    """Discard the currently selected card."""
    if not game.enable_discard_pile:
        return
    selected = hand_frame.game_gui.selection.hand_index
    if selected is None:
        messagebox.showwarning("No selection", "Select a card first!")
        return

    destinations = _current_player_discard_destinations(game)
    if len(destinations) == 1:
        _discard_to_destination(game, hand_frame, render_log, status_panel, selected, destinations[0])
    else:
        _choose_discard_destination(game, hand_frame, render_log, status_panel, selected, destinations)


def _discard_to_destination(game, hand_frame, render_log, status_panel, selected, destination):
    name, pile_index, personal = destination
    result = game.session.execute("discard_card", card_index=selected, pile_index=pile_index, personal=personal)
    if result.success:
        hand_frame.game_gui.selection.hand_index = None
    else:
        messagebox.showwarning("Invalid", result.message)
    return result


def _choose_discard_destination(game, hand_frame, render_log, status_panel, selected, destinations):
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
        _discard_to_destination(game, hand_frame, render_log, status_panel, selected, destinations[selection[0]])
        dialog.destroy()

    buttons = tk.Frame(dialog)
    buttons.pack(fill="x", padx=10, pady=10)
    tk.Button(buttons, text="Discard", command=discard).pack(side="right")
    tk.Button(buttons, text="Cancel", command=dialog.destroy).pack(side="right", padx=5)
    choices.bind("<Double-1>", lambda _event: discard())
    dialog.wait_window()


def _current_player_discard_destinations(game):
    return [(target.name, target.pile_index, target.personal)
            for target in discard_destinations(game, game.current_player_index)]


def play_selected(game, hand_frame, table_frame, render_log, status_panel):
    """Play onto the table or return the card to the draw pile."""
    if not game.enable_table and not game.enable_discard_pile:
        selected = hand_frame.game_gui.selection.hand_index
        if selected is None:
            messagebox.showwarning("No selection", "Select a card from your hand first!")
            return
        result = game.session.execute("play_card", card_index=selected)
        if not result.success:
            messagebox.showwarning("Invalid", result.message)
            return result
        hand_frame.game_gui.selection.hand_index = None
        return result
    return _play_from_hand_at(game, hand_frame, table_frame, None, render_log, status_panel)


def play_selected_face_down(game, hand_frame, table_frame, render_log, status_panel):
    selected = hand_frame.game_gui.selection.hand_index
    if selected is None:
        messagebox.showwarning("No selection", "Select a card from your hand first!")
        return
    position = table_frame.selection.target_position if game.allow_positioned_play else None
    result = game.session.execute("play_face_down", card_index=selected, target_position=position)
    if result.success:
        hand_frame.game_gui.selection.hand_index = None
        _clear_table_selection(table_frame)
    else:
        messagebox.showwarning("Invalid", result.message)
    return result


def flip_selected_table_card(game, table_frame, render_log, status_panel):
    if table_frame.selection.table_index is None:
        messagebox.showwarning("No selection", "Select a table card first!")
        return
    card = execute_value(game, "flip_table_card", card_index=table_frame.selection.table_index)
    if card is None:
        messagebox.showwarning("Invalid flip", "That card cannot be revealed yet.")
        return
    _clear_table_selection(table_frame)


def recycle_discard_into_deck(game, render_log, status_panel, root):
    count = execute_value(game, "recycle_discard")
    if not count:
        messagebox.showinfo("Cannot recycle", "The draw deck must be empty and the discard pile must contain cards.", parent=root)
        return


def _play_from_hand_at(game, hand_frame, table_frame, position, render_log, status_panel):
    selected = hand_frame.game_gui.selection.hand_index
    if selected is None:
        messagebox.showwarning("No selection", "Select a card from your hand first!")
        return

    result = game.session.execute("play_at_position" if position is not None else "play_card", card_index=selected, target_position=position)
    if result.success:
        hand_frame.game_gui.selection.hand_index = None
        _clear_table_selection(table_frame)
    else:
        messagebox.showwarning("Invalid", result.message)
    return result


def play_at_selected_spot(game, hand_frame, table_frame, render_log, status_panel):
    selected_hand = hand_frame.game_gui.selection.hand_index
    if selected_hand is None:
        messagebox.showwarning("No selection", "Select a card from your hand first!")
        return
    if table_frame.selection.target_position is None and table_frame.selection.table_index is not None:
        result = game.session.execute("swap_table_card", card_index=selected_hand,
                                      table_index=table_frame.selection.table_index)
        if not result.success:
            messagebox.showwarning("Cannot swap cards", result.message)
            return result
        hand_frame.game_gui.selection.hand_index = None
        _clear_table_selection(table_frame)
        return result
    if table_frame.selection.target_position is None:
        messagebox.showwarning("No spot selected", "Select an empty spot on the table first!")
        return
    return _play_from_hand_at(
        game, hand_frame, table_frame, table_frame.selection.target_position, render_log, status_panel
    )


def take_selected_from_table(game, table_frame, hand_frame, render_log, status_panel):
    selected = table_frame.selection.table_index
    if selected is None:
        messagebox.showwarning("No selection", "Select a table card first!")
        return
    result = game.session.execute("take_table_card", card_index=selected)
    if not result.success:
        messagebox.showwarning("Invalid", result.message)
        return result
    table_frame.selection.table_index = None
    return result


def move_selected_table_card_to_discard(game, table_frame, render_log, status_panel):
    selected = table_frame.selection.table_index
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
            _finish_table_discard(game, table_frame, render_log, status_panel, selected, destinations[choice[0]])
            dialog.destroy()

        buttons = tk.Frame(dialog)
        buttons.pack(fill="x", padx=10, pady=10)
        tk.Button(buttons, text="Move", command=move_to_selected).pack(side="right")
        tk.Button(buttons, text="Cancel", command=dialog.destroy).pack(side="right", padx=5)
        choices.bind("<Double-1>", lambda _event: move_to_selected())
        dialog.wait_window()
        return
    _finish_table_discard(game, table_frame, render_log, status_panel, selected, destinations[0])


def _finish_table_discard(game, table_frame, render_log, status_panel, selected, destination):
    name, pile_index, personal = destination
    result = game.session.execute("discard_table_card", card_index=selected, pile_index=pile_index, personal=personal)
    if result.success:
        table_frame.selection.table_index = None
    else:
        messagebox.showwarning("Invalid", result.message)
    return result


def move_selected_table_card(game, table_frame, render_log, status_panel):
    """Move the selected table card to the selected empty table slot."""
    selected = table_frame.selection.table_index
    position = table_frame.selection.target_position
    if selected is None:
        messagebox.showwarning("No card selected", "Select a table card to move first!")
        return
    if position is None:
        messagebox.showwarning("No spot selected", "Select an empty table spot as the destination!")
        return
    result = game.session.execute("move_table_card", card_index=selected, target_position=position)
    if not result.success:
        messagebox.showwarning("Invalid move", result.message)
        return result
    _clear_table_selection(table_frame)
    return result


def clear_table(game, table_frame, render_log, status_panel):
    count = execute_value(game, "clear_table")
    table_frame.selection.table_index = None


def end_turn(game, hand_frame, render_log, status_panel, on_turn_start=None):
    """End current player's turn and move to next."""
    round_ended, cleared_count = execute_value(game, "end_turn")
    hand_frame.game_gui.selection.hand_index = None
    if on_turn_start:
        on_turn_start()


def request_point(game, hand_frame, render_log, status_panel):
    succeeded, message = execute_value(game, "request_point")


def _clear_table_selection(table_frame):
    table_frame.selection.table_index = None
    table_frame.selection.target_position = None
