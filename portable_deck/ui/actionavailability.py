"""Explain temporary action restrictions using the current game state."""

def action_reason(gui, button):
    g = gui.game
    name = next((key for key, value in vars(gui).items() if value is button), "")
    chips = gui.chip_bank_ui
    chip_name = next((key for key, value in vars(chips).items() if value is button), "")
    if not g.active_player_indices():
        return "All players have left. Return a player or restart the game."
    if g.current_player_must_confirm_point() or g.current_player_must_confirm_pot_withdrawal():
        return "Complete the pending confirmation first."
    if name in {"point_button", "reduce_score_button"} and g.pending_point_request:
        return "Wait for the other players to confirm the previous score change."
    if chip_name in {"play_button", "take_button"} and g.pending_pot_withdrawal:
        return "Wait for the pending pot withdrawal to be approved."
    if chip_name == "play_button" and g.chip_balance(g.current_player_index) < g.minimum_bet:
        return f"Minimum bet: {g.minimum_bet} chips. Available: {g.chip_balance(g.current_player_index)}."
    if chip_name == "take_button" and g.chip_pot == 0:
        return "The pot is empty."
    if name == "draw_button" and not g.deck.flat_deck:
        return "The draw deck is empty."
    if name == "discard_draw_button" and not any(pile for _, pile in g.all_discard_piles()):
        return "All discard piles are empty."
    if name == "recycle_discard_button":
        if g.deck.flat_deck:
            return "The draw deck must be empty before recycling."
        if not any(pile for _, pile in g.all_discard_piles()):
            return "There are no discarded cards to recycle."
    if name == "clear_table_button" and not g.table_cards:
        return "The table is empty."
    if name == "leave_session_button" and not g.can_leave_session():
        if g.pending_point_request or g.pending_pot_withdrawal:
            return "Complete the pending confirmation before leaving."
        rule = g.leave_conditions
        details = []
        for key, label in (("own_score", "Your score"), ("opponent_score", "An opponent's score")):
            if rule[key] and g.score_enabled and g.enable_target_score:
                threshold = g.score_warning if rule[key + "_at"] == "warning" else g.target_score
                suffix = f" Current personal score: {g.scores[g.current_player_index]}." if key == "own_score" else ""
                details.append(f"{label} must reach {threshold}.{suffix}")
        if rule["no_chips"] and g.enable_chip_accounts:
            details.append(f"Your chip account must be empty. Available: {g.chip_balance(g.current_player_index)}.")
        return ("All conditions required. " if rule["match"] == "all" else "At least one condition required. ") + " ".join(details)
    hand_actions = {"play_button", "discard_button", "play_face_down_button", "personal_pile_button", "flip_hand_button", "play_at_spot_button"}
    if (name in hand_actions or button in getattr(getattr(gui, "special_actions_ui", None), "buttons", [])) and gui.hand_frame.selected_index is None:
        return "Select a card in your hand first."
    if name in {"take_table_button", "table_discard_button", "flip_table_card_button", "move_table_card_button"} and gui.table_frame.selected_index is None:
        return "Select a card on the table first."
    if name in {"play_at_spot_button", "move_table_card_button"} and gui.table_frame.selected_position is None:
        return "Select an empty target position on the table."
    if name in {"play_button", "play_face_down_button"} and g.enable_table and not g.available_table_positions():
        return "The table has no empty positions within its limits."
    return ""


def refresh_action_availability(gui):
    from .tooltip import Tooltip
    if not hasattr(gui, "chip_bank_ui"):
        return
    buttons = [getattr(gui, name, None) for name in ("draw_button", "discard_button", "play_button",
        "play_face_down_button", "personal_pile_button", "flip_hand_button", "play_at_spot_button",
        "take_table_button", "table_discard_button", "flip_table_card_button", "move_table_card_button",
        "point_button", "reduce_score_button", "discard_draw_button", "recycle_discard_button",
        "clear_table_button", "leave_session_button")]
    buttons += gui.chip_bank_ui.buttons
    buttons += getattr(getattr(gui, "special_actions_ui", None), "buttons", [])
    for button in buttons:
        if button is None:
            continue
        button.configure(state="disabled" if action_reason(gui, button) else "normal")
        if not hasattr(button, "_availability_tooltip"):
            button._availability_tooltip = Tooltip(button, lambda b=button: action_reason(gui, b))
