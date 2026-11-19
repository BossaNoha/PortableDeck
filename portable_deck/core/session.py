"""Shared execution, Undo and checkpoint orchestration without GUI dependencies."""
import copy
from dataclasses import dataclass
from .actionavailability import ActionContext, action_availability
from .interactions import INTERACTIONS
from .playerleaving import return_player_reason
from .actionerrors import ActionValidationError
from .discardvalidation import discard_destination
from .chipvalidation import chip_action_error

@dataclass(frozen=True)
class ActionResult:
    success: bool
    changed: bool = False
    value: object = None
    message: str = ""
    checkpoint_error: str | None = None
    events: tuple = ()
    messages: tuple[str, ...] = ()
    code: str = ""


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
        if self.last_checkpoint_error:
            self.game.log_action("", "autosave_failed", error=self.last_checkpoint_error)
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
        after = self.game.capture_undo_state()
        changed = before != after
        gameplay_changed = any(before[key] != after[key] for key in before if key != "score_alerts_seen")
        if gameplay_changed and self.game.enable_undo:
            self.game.undo_stack.append(before)
        return changed

    def acknowledge_score_notifications(self, notifications):
        """Persist delivered notices without creating a separate gameplay Undo step.

        Inside a transaction, defer persistence to its checkpoint. A gameplay
        action's snapshot still restores the earlier notification state on Undo.
        """
        before = copy.deepcopy(self.game.score_alerts_seen)
        if not self.depth:
            self.last_checkpoint_error = None
        self.game.acknowledge_score_notifications(notifications)
        changed = before != self.game.score_alerts_seen
        if changed and not self.depth:
            self.checkpoint()
        return ActionResult(True, changed=changed, checkpoint_error=self.last_checkpoint_error)

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
        context = ActionContext(hand_index=card, table_index=card, target_position=position,
                                owner=parameters.get("owner"), pile_index=parameters.get("pile_index"))
        if action == "swap_table_card":
            context = ActionContext(hand_index=card, table_index=parameters.get("table_index"))
        lifecycle = {"end_turn", "confirm_point", "confirm_pot", "return_player"}
        if action in lifecycle:
            reason = ""
            code = ""
            if action == "return_player":
                reason = return_player_reason(g, parameters.get("player_index"))
                code = "return_unavailable"
            elif not g.active_player_indices():
                reason = "No active players remain."
                code = "no_active_players"
            elif action == "confirm_point" and not g.current_player_must_confirm_point():
                reason = "No score confirmation is required from this player."
                code = "confirmation_not_required"
            elif action == "confirm_pot" and not g.current_player_must_confirm_pot_withdrawal():
                reason = "No pot confirmation is required from this player."
                code = "confirmation_not_required"
            elif action == "end_turn" and (g.current_player_must_confirm_point() or g.current_player_must_confirm_pot_withdrawal()):
                reason = "Complete the pending confirmation first."
                code = "confirmation_required"
            if reason:
                return ActionResult(False, message=reason, code=code)
        else:
            available = action_availability(g, action, context)
            if not available.allowed:
                return ActionResult(False, message=available.reason, code=available.code or "action_unavailable")
        handlers = {
            "draw_card": lambda: g.deal_card_to_current(),
            "draw_from_discard": lambda: self.draw_from_discard(parameters),
            "end_turn": lambda: g.finish_turn(),
            "confirm_point": lambda: g.confirm_point_request(parameters.get("approved")),
            "confirm_pot": lambda: g.confirm_pot_withdrawal(parameters.get("approved")),
            "return_player": lambda: g.return_player(parameters["player_index"]),
            "move_table_card": lambda: g.move_table_card(card, position),
            "play_card": lambda: (g.play_to_table(card + 1) if g.enable_table else g.play_back_to_draw_pile(card + 1)),
            "play_at_position": lambda: g.play_to_table(card + 1, position),
            "play_face_down": lambda: g.play_to_table(card + 1, position, face_up=False),
            "discard_card": lambda: g.discard_from_current(card + 1, parameters.get("pile_index", 0), parameters.get("personal", False)),
            "take_table_card": lambda: g.take_from_table(card),
            "swap_table_card": lambda: g.swap_with_table(card + 1, parameters["table_index"]),
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
            "take_personal_pile": lambda: g.take_from_personal_pile(parameters["owner"], parameters["pile_index"]),
            "insert_draw_deck": lambda: g.insert_hand_card(card + 1, "draw", parameters["position"]),
            "insert_discard_pile": lambda: g.insert_hand_card(card + 1, "discard", parameters["position"], parameters.get("pile_index", 0)),
        }
        if action in INTERACTIONS:
            handlers[action] = lambda: g.interact(
                action, parameters.get("target"),
                None if card is None else card + 1, parameters.get("amount"))
        if action not in handlers:
            raise ValueError(f"No execution handler for action: {action}")
        before = g.capture_undo_state()
        event_offset, log_offset = len(g.history), len(g.game_log)
        def perform():
            try:
                if action in {"discard_card", "discard_table_card"} and discard_destination(
                        g, parameters.get("pile_index", 0), parameters.get("personal", False)) is None:
                    raise ActionValidationError("invalid_pile", "Choose a valid discard destination.")
                if action in {"buy_chips", "play_chips", "take_pot"}:
                    error = chip_action_error(g, action, parameters.get("player_index"), parameters.get("amount"))
                    if error:
                        raise error
                raw = handlers[action]()
                if action in {"play_chips", "take_pot", "request_point", "reduce_score", "leave_session", "return_player", "confirm_point", "confirm_pot"}:
                    success, message = raw
                else:
                    success = raw is not None and raw is not False
                    message = f"{action.replace('_', ' ').capitalize()} completed." if success else "The action could not be completed."
                if not success:
                    self.restore(before)
                    return ActionResult(False, value=raw, message=message, code="action_rejected")
                return ActionResult(True, before != g.capture_undo_state(), raw, message)
            except ActionValidationError as error:
                self.restore(before)
                return ActionResult(False, message=str(error), code=error.code)
            except (ValueError, TypeError, KeyError, IndexError) as error:
                self.restore(before)
                return ActionResult(False, message=str(error), code="invalid_parameters")
        result = self.run(perform)
        return ActionResult(result.success, result.changed, result.value, result.message, self.last_checkpoint_error,
                            tuple(copy.deepcopy(g.history[event_offset:])), tuple(g.game_log[log_offset:]), result.code)

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
        name = (g.all_discard_piles()[pile_index][0] if "source_index" in parameters else f"Shared discard {pile_index + 1}")
        g.log_action(player.name, "draw_from_discard", card, destination=name)
        return card

    def undo_availability(self):
        """Describe Undo without exposing mutable history to clients."""
        from .actionavailability import ActionAvailability
        if not self.game.enable_undo:
            return ActionAvailability(False, "Undo is disabled by the game rules.", "action_disabled")
        if not self.game.undo_stack:
            return ActionAvailability(False, "There is no action to undo.", "empty_undo")
        return ActionAvailability(True)

    def undo(self):
        if not self.undo_availability().allowed:
            return False
        if not self.game.undo_last_action():
            return False
        self.checkpoint()
        return True
