# cardactions.py
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


def discard_selected(game, hand_frame, gui_log, status_panel):
    """Discard the currently selected card."""
    selected = hand_frame.selected_index
    if selected is None:
        messagebox.showwarning("No selection", "Select a card first!")
        return

    card = game.discard_from_current(selected + 1)  # 1-based index in Game class
    if card:
        hand_frame.selected_index = None
        hand_frame.update_hand()
        status_panel.update_status()
        gui_log(f"{game.players[game.current_player_index].name} discarded {card}")
    else:
        messagebox.showwarning("Invalid", "Invalid card selection!")


def play_selected(game, hand_frame, table_frame, gui_log, status_panel):
    """Move the selected card from the current hand onto the shared table."""
    selected = hand_frame.selected_index
    if selected is None:
        messagebox.showwarning("No selection", "Select a card first!")
        return

    card = game.play_to_table(selected + 1)
    if card:
        player_name = game.players[game.current_player_index].name
        hand_frame.selected_index = None
        hand_frame.update_hand()
        table_frame.update_table()
        status_panel.update_status()
        gui_log(f"{player_name} played {card} onto the table.")
    else:
        messagebox.showwarning("Invalid", "Invalid card selection!")


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
    card = game.move_table_card_to_discard(selected)
    if card is None:
        messagebox.showwarning("Invalid", "That table card is no longer available!")
        table_frame.clear_selection()
        return
    table_frame.selected_index = None
    table_frame.update_table()
    status_panel.update_status()
    gui_log(f"{card} was moved from the table to the discard pile.")


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
    gui_log(f"Turn ended. {game.players[game.current_player_index].name}'s turn starts.")
    if round_ended:
        gui_log("The round has ended.")
    if cleared_count:
        gui_log(f"The table was cleared. {cleared_count} card(s) moved to the discard pile.")
    if on_turn_start:
        on_turn_start()


def request_point(game, hand_frame, gui_log, status_panel):
    succeeded, message = game.request_point()
    gui_log(message)
    status_panel.update_status()
