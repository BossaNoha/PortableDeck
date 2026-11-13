"""Translate Tkinter buttons/selection to the shared action-availability API."""
from ..core.actionavailability import ActionContext, action_availability

BUTTON_ACTIONS = {'draw_button': 'draw_card',
 'discard_button': 'discard_card',
 'play_button': 'play_card',
 'play_face_down_button': 'play_face_down',
 'personal_pile_button': 'play_personal_pile',
 'flip_hand_button': 'flip_hand_card',
 'play_at_spot_button': 'play_at_position',
 'take_table_button': 'take_table_card',
 'table_discard_button': 'discard_table_card',
 'flip_table_card_button': 'flip_table_card',
 'move_table_card_button': 'move_table_card',
 'point_button': 'request_point',
 'reduce_score_button': 'reduce_score',
 'discard_draw_button': 'draw_from_discard',
 'recycle_discard_button': 'recycle_discard',
 'clear_table_button': 'clear_table',
 'leave_session_button': 'leave_session'}


def gui_action_bindings(gui):
    bindings = [(getattr(gui, name), action) for name, action in BUTTON_ACTIONS.items()
                if getattr(gui, name, None) is not None]
    chips = getattr(gui, "chip_bank_ui", None)
    if chips is not None:
        for name, action in (("buy_button", "buy_chips"), ("play_button", "play_chips"), ("take_button", "take_pot")):
            button = getattr(chips, name, None)
            if button is not None:
                bindings.append((button, action))
    for button in getattr(getattr(gui, "special_actions_ui", None), "buttons", []):
        bindings.append((button, button.action_id))
    return bindings


def action_reason(gui, button):
    action = next((action for widget, action in gui_action_bindings(gui) if widget is button), None)
    if action is None:
        return ""
    context = ActionContext(hand_index=gui.selection.hand_index,
                            table_index=gui.selection.table_index,
                            target_position=gui.selection.target_position)
    return action_availability(gui.game, action, context).reason


def refresh_action_availability(gui):
    from .tooltip import Tooltip
    if not hasattr(gui, "chip_bank_ui"):
        return
    for button, action in gui_action_bindings(gui):
        button.configure(state="disabled" if action_reason(gui, button) else "normal")
        if not hasattr(button, "_availability_tooltip"):
            button._availability_tooltip = Tooltip(button, lambda b=button: action_reason(gui, b))
