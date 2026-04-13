# cardactions.py
from tkinter import messagebox

def draw_card(game, hand_frame, gui_log, status_panel):
    """Current player draws a card."""
    game.deal_card_to_current()
    hand_frame.update_hand()
    status_panel.update_status()
    gui_log(f"{game.players[game.current_player_index].name} drew a card.")


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


def end_turn(game, hand_frame, gui_log, status_panel):
    """End current player's turn and move to next."""
    game.log_draws_for_turn()
    game.current_player_index = (game.current_player_index + 1) % len(game.players)
    hand_frame.selected_index = None
    hand_frame.update_hand()
    status_panel.update_status()
    gui_log(f"Turn ended. {game.players[game.current_player_index].name}'s turn starts.")