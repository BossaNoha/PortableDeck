"""Shared execution, Undo and checkpoint orchestration without GUI dependencies."""
from dataclasses import dataclass
from .actionavailability import ActionContext, action_availability

@dataclass(frozen=True)
class ActionResult:
    success: bool
    changed: bool = False
    value: object = None
    message: str = ""
    checkpoint_error: str | None = None


class SessionController:
    def __init__(self, game, checkpoint=None):
        self.game = game
        self.checkpoint_callback = checkpoint
        self.depth = 0
        self.last_checkpoint_error = None

    def checkpoint(self):
        self.last_checkpoint_error = None
        if self.checkpoint_callback:
            try:
                self.last_checkpoint_error = self.checkpoint_callback(self.game) or None
            except (OSError, ValueError, TypeError) as error:
                self.last_checkpoint_error = str(error)
        return self.last_checkpoint_error

    def restore(self, state):
        g = self.game
        stack, enabled = g.undo_stack, g.enable_undo
        try:
            g.undo_stack = [state]
            g.enable_undo = True
            g.undo_last_action()
        finally:
            g.undo_stack, g.enable_undo = stack, enabled

    def record_state(self, before):
        changed = before != self.game.capture_undo_state()
        if changed and self.game.enable_undo:
            self.game.undo_stack.append(before)
        return changed

    def run(self, operation, *args, **kwargs):
        """Group nested model actions into one Undo step and one checkpoint.

        A caller may use this to finish its presentation/log updates before saving.
        """
        if self.depth:
            return operation(*args, **kwargs)
        self.last_checkpoint_error = None
        before = self.game.capture_undo_state()
        self.depth += 1
        try:
            value = operation(*args, **kwargs)
        except Exception:
            self.restore(before)
            raise
        finally:
            self.depth -= 1
        if self.record_state(before):
            self.checkpoint()
        return value

    def execute(self, action, **parameters):
        """Execute a named action. Card indices are zero-based for all clients."""
        if not self.depth:
            self.last_checkpoint_error = None
        g = self.game
        card = parameters.get("card_index")
        position = parameters.get("target_position")
        context = ActionContext(hand_index=card, table_index=card, target_position=position)
        lifecycle = {"end_turn", "confirm_point", "confirm_pot", "return_player"}
        if action in lifecycle:
            reason = ""
            if action == "return_player":
                if not g.enable_player_return or parameters.get("player_index") not in g.left_players:
                    reason = "Choose an eligible departed player."
                elif g.pending_point_request or g.pending_pot_withdrawal:
                    reason = "Complete the pending confirmation first."
            elif not g.active_player_indices():
                reason = "No active players remain."
            elif action == "confirm_point" and not g.current_player_must_confirm_point():
                reason = "No score confirmation is required from this player."
            elif action == "confirm_pot" and not g.current_player_must_confirm_pot_withdrawal():
                reason = "No pot confirmation is required from this player."
            elif action == "end_turn" and (g.current_player_must_confirm_point() or g.current_player_must_confirm_pot_withdrawal()):
                reason = "Complete the pending confirmation first."
            if reason:
                return ActionResult(False, message=reason)
        else:
            available = action_availability(g, action, context)
            if not available.allowed:
                return ActionResult(False, message=available.reason)
        handlers = {
            "draw_card": lambda: g.deal_card_to_current(),
            "draw_from_discard": lambda: self.draw_from_discard(parameters),
            "end_turn": lambda: g.finish_turn(),
            "confirm_point": lambda: g.confirm_point_request(parameters["approved"]),
            "confirm_pot": lambda: g.confirm_pot_withdrawal(parameters["approved"]),
            "return_player": lambda: g.return_player(parameters["player_index"]),
            "move_table_card": lambda: g.move_table_card(card, position),
            "play_card": lambda: (g.play_to_table(card + 1) if g.enable_table else g.play_back_to_draw_pile(card + 1)),
            "play_at_position": lambda: g.play_to_table(card + 1, position),
            "play_face_down": lambda: g.play_to_table(card + 1, position, face_up=False),
            "discard_card": lambda: g.discard_from_current(card + 1, parameters.get("pile_index", 0), parameters.get("personal", False)),
            "take_table_card": lambda: g.take_from_table(card),
            "discard_table_card": lambda: g.move_table_card_to_discard(card, parameters.get("pile_index", 0), parameters.get("personal", False)),
            "flip_hand_card": lambda: g.flip_hand_card(card),
            "flip_table_card": lambda: g.flip_table_card(card),
            "clear_table": lambda: g.clear_table(),
            "recycle_discard": lambda: g.recycle_discard_into_deck(),
            "buy_chips": lambda: g.buy_chips(parameters["player_index"], parameters["amount"]),
            "play_chips": lambda: g.play_chips(parameters["amount"]),
            "take_pot": lambda: g.request_pot_withdrawal(parameters["player_index"]),
            "request_point": lambda: g.request_point(),
            "reduce_score": lambda: g.reduce_score(),
            "leave_session": lambda: g.leave_session(),
            "play_personal_pile": lambda: g.play_to_personal_pile(card + 1, parameters["owner"], parameters["pile_index"]),
            "insert_draw_deck": lambda: g.insert_hand_card(card + 1, "draw", parameters["position"]),
            "insert_discard_pile": lambda: g.insert_hand_card(card + 1, "discard", parameters["position"], parameters.get("pile_index", 0)),
        }
        if action not in handlers:
            raise ValueError(f"No execution handler for action: {action}")
        before = g.capture_undo_state()
        def perform():
            try:
                raw = handlers[action]()
                if action in {"play_chips", "take_pot", "request_point", "reduce_score", "leave_session", "return_player", "confirm_point", "confirm_pot"}:
                    success, message = raw
                else:
                    success = raw is not None and raw is not False
                    message = f"{action.replace('_', ' ').capitalize()} completed." if success else "The action could not be completed."
                if not success:
                    self.restore(before)
                    return ActionResult(False, value=raw, message=message)
                # Draws are also tracked by end-of-turn summaries; keep an immediate event for CLI clients.
                if action == "end_turn":
                    g.log_action(g.players[g.current_player_index].name, "turn_started")
                if action == "draw_card":
                    g.log_action(g.players[g.current_player_index].name, "draw_card")
                return ActionResult(True, before != g.capture_undo_state(), raw, message)
            except (ValueError, TypeError, KeyError, IndexError) as error:
                self.restore(before)
                return ActionResult(False, message=str(error))
        result = self.run(perform)
        return ActionResult(result.success, result.changed, result.value, result.message, self.last_checkpoint_error)

    def draw_from_discard(self, parameters):
        g = self.game
        piles = ([pile for _name, pile in g.all_discard_piles()]
                 if "source_index" in parameters else g.discard_piles)
        pile_index = parameters.get("source_index", parameters.get("pile_index", 0))
        if not isinstance(pile_index, int) or isinstance(pile_index, bool) or not 0 <= pile_index < len(piles):
            raise ValueError("Choose a valid discard pile.")
        pile = piles[pile_index]
        card_index = parameters.get("card_index", len(pile) - 1)
        if not isinstance(card_index, int) or isinstance(card_index, bool) or not 0 <= card_index < len(pile):
            raise ValueError("Choose an available discarded card.")
        if g.draw_from_discard_mode == "top" and card_index != len(pile) - 1:
            raise ValueError("Only the top discard card may be drawn.")
        card = pile.pop(card_index)
        player = g.players[g.current_player_index]
        player.draw_card(card)
        g.log_action(player.name, "draw_from_discard", card)
        return card

    def undo(self):
        if not self.game.undo_last_action():
            return False
        self.checkpoint()
        return True
