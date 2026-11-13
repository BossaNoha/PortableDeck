"""Core-owned game events and their public text representation."""
import copy


def format_game_event(event):
    """Format public output only; private peek/draw results never enter this text."""
    action = event["action"]
    player = event.get("player", "")
    card = event.get("card", "a card")
    target = event.get("target", "another player")
    amount = event.get("amount", 0)
    if action == "draw_multiple":
        return None  # History summary; individual draws already have public events.
    if action == "play":
        return f"{player} played {card} onto the table." if event.get("face_up", True) else f"{player} played a card face down onto the table."
    if action == "flip_hand_card":
        return f"{player} revealed {card}." if event.get("revealed") else f"{player} hid a hand card."
    if action == "flip_table_card":
        return f"Table card revealed: {card}." if event.get("face_up") else "Table card hidden."
    if action == "insert_hand_card":
        destination = "draw deck" if event["destination"] == "draw" else f"discard pile {event['pile_index'] + 1}"
        return f"{player} placed {card} at position {event['position']} in the {destination}."
    if action == "point_requested":
        return f"{player} requested a score change of {event.get('delta', 1):+d}."
    if action in {"point_awarded", "score_reduced"}:
        return f"{player} had their score changed by {1 if action == 'point_awarded' else -1:+d}."
    if action == "discard":
        return f"{player} discarded {card} to {event.get('destination', 'the discard pile')}."
    messages = {
        "draw_card": f"{player} drew a card.",
        "draw_from_discard": f"{player} took {card} from {event.get('destination', 'a discard pile')}.",
        "play_back_to_draw_pile": f"{player} played {card}; it was shuffled into the draw pile.",
        "swap_table_card": f"{player} swapped {card} for {event.get('returned_card', 'a table card')} on the table.",
        "take_from_table": f"{player} took {card} from the table.",
        "table_to_discard": f"{card} was moved from the table to {event.get('destination', 'the discard pile')}.",
        "move_table_card": f"{player} moved {card} to another spot on the table.",
        "move_table_sequence": f"{player} moved a sequence starting with {card} on the table.",
        "clear_table": f"The table was cleared. {event.get('count', 0)} card(s) moved to the discard pile.",
        "recycle_discard": f"The discard pile was recycled into the draw deck ({event.get('count', 0)} cards).",
        "round_ended": "The round has ended.",
        "turn_started": f"{player}'s turn starts.",
        "all_players_left": "All players have left the session.",
        "left_session": f"{player} left the session.",
        "returned_to_session": f"{player} returned to the session.",
        "point_confirmed": f"{player} approved the score change.",
        "point_denied": f"{player} denied the request. No point was awarded.",
        "buy_chips": f"{player} bought {amount} chips. New balance: {event.get('balance', '?')}.",
        "play_chips": f"{player} put {amount} chips into the pot. Pot: {event.get('pot', '?')}.",
        "pot_withdrawal_requested": f"{player} requested the pot for {event.get('recipient', '')}. Other players must approve.",
        "pot_withdrawal_denied": f"{player} rejected the pot withdrawal. The pot remains unchanged.",
        "pot_withdrawal_approved": f"{player} approved the pot withdrawal.",
        "pot_withdrawn": f"{amount} chips were moved from the pot to {event.get('recipient', '')}'s account.",
        "play_to_personal_pile": f"{player} played {card} to {event.get('owner', 'a player')}'s pile {event.get('pile', 0) + 1}.",
        "take_from_personal_pile": f"{player} took {card} from a personal pile.",
        "take_random_card": f"{player} took a random card from {target}.",
        "discard_random_card": f"{player} discarded {target}'s card: {card}.",
        "give_card": f"{player} gave {card} to {target}.",
        "steal_chips": f"{player} stole {amount} chips from {target}.",
        "peek_random_card": f"{player} looked at a random card of {target}.",
        "peek_all_cards": f"{player} looked at all cards of {target}.",
        "autosave_failed": f"Autosave failed: {event.get('error', '')}",
    }
    return messages.get(action)


class GameLog:
    @property
    def gui_log(self):
        """Legacy save/API alias; the log belongs to the core."""
        return self.game_log

    @gui_log.setter
    def gui_log(self, values):
        self.game_log = values

    def record_event(self, event):
        event = copy.deepcopy(event)
        self.history.append(event)
        message = format_game_event(event)
        if message:
            self.game_log.append(message)
        return event

    def log_action(self, player_name, action, card=None, **details):
        event = {"player": player_name, "action": action, **details}
        if card is not None:
            event["card"] = card
        return self.record_event(event)

    def ensure_initial_log(self):
        if not self.game_log and self.active_player_indices():
            self.log_action(self.players[self.current_player_index].name, "turn_started")
