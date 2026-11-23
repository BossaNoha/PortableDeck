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

    def log_snapshot(self):
        """Return ordered public log text without exposing the mutable list."""
        return tuple(self.game.game_log)

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

    def checkpoint_result(self):
        """Report explicit checkpoint completion without a gameplay Undo step."""
        error = self.checkpoint()
        if error:
            return ActionResult(False, message=error, checkpoint_error=error, code="checkpoint_failed")
        return ActionResult(True, message="Checkpoint completed.")

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
        if g.pending_shared_offer is not None and action != "choose_shared_offer":
            return ActionResult(False, message="Finish the shared offer first.", code="shared_offer_pending")
        card = parameters.get("card_index")
        position = parameters.get("target_position")
        context = ActionContext(hand_index=card, table_index=card, target_position=position,
                                owner=parameters.get("owner"), pile_index=parameters.get("pile_index"),
                                draw_pile_id=parameters.get("draw_pile_id", "main"))
        if action == "swap_table_card":
            context = ActionContext(hand_index=card, table_index=parameters.get("table_index"))
        lifecycle = {"confirm_point", "confirm_pot", "return_player"}
        if action == "end_turn":
            available = self.end_turn_availability(parameters.get("next_player"), parameters.get("skip_next", False))
            if not available.allowed:
                return ActionResult(False, message=available.reason, code=available.code)
        elif action in lifecycle:
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
            if reason:
                return ActionResult(False, message=reason, code=code)
        else:
            available = action_availability(g, action, context)
            if not available.allowed:
                return ActionResult(False, message=available.reason, code=available.code or "action_unavailable")
        from .sharedoffer import start_shared_offer, choose_shared_offer
        handlers = {
            "start_shared_offer": lambda: start_shared_offer(g, context.draw_pile_id),
            "choose_shared_offer": lambda: choose_shared_offer(g, card),
            "deal_cards": lambda: g.deal_cards(parameters.get("count"), context.draw_pile_id),
            "discard_whole_personal_pile": lambda: g.discard_whole_personal_pile(parameters.get("owner"), parameters.get("pile_index"), parameters.get("discard_pile_index", 0), parameters.get("personal", False)),
            "take_whole_personal_pile": lambda: g.take_whole_personal_pile(parameters.get("owner"), parameters.get("pile_index")),
            "transfer_personal_pile": lambda: self.transfer_personal_pile(parameters),
            "draw_cards": lambda: g.draw_cards(parameters.get("count"), context.draw_pile_id),
            "shuffle_draw_deck": lambda: g.shuffle_draw_deck(context.draw_pile_id),
            "play_cards": lambda: self.play_cards(parameters.get("card_indices")),
            "take_table_cards": lambda: self.take_table_cards(parameters.get("card_indices")),
            "discard_cards": lambda: self.discard_cards(parameters),
            "discard_table_cards": lambda: self.discard_table_cards(parameters),
            "reverse_turn_order": lambda: g.reverse_turn_order(),
            "draw_card": lambda: (g.deal_card_to_current() if context.draw_pile_id == "main" else g.deal_card_to_current(context.draw_pile_id)),
            "draw_from_discard": lambda: self.draw_from_discard(parameters),
            "end_turn": lambda: g.finish_turn(parameters.get("next_player"), parameters.get("skip_next", False)),
            "confirm_point": lambda: g.confirm_point_request(parameters.get("approved")),
            "confirm_pot": lambda: g.confirm_pot_withdrawal(parameters.get("approved")),
            "return_player": lambda: g.return_player(parameters["player_index"]),
            "move_table_card": lambda: g.move_table_card(card, position),
            "play_card": lambda: (g.play_to_table(card + 1) if g.enable_table else g.play_back_to_draw_pile(card + 1, context.draw_pile_id)),
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
            "insert_draw_deck": lambda: g.insert_hand_card(card + 1, "draw", parameters["position"], draw_pile_id=context.draw_pile_id),
            "insert_discard_pile": lambda: g.insert_hand_card(card + 1, "discard", parameters["position"], parameters.get("pile_index", 0)),
        }
        if action in INTERACTIONS:
            handlers[action] = lambda: g.interact(
                action, parameters.get("target"),
                None if card is None else card + 1, parameters.get("amount"))
            if action == "give_cards":
                handlers[action] = lambda: g.interact(action, parameters.get("target"),
                                                     card_indices=parameters.get("card_indices"))
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

    def transfer_personal_pile(self, parameters):
        from .piletransfer import transfer_personal_pile
        return transfer_personal_pile(self.game, parameters.get("source_owner"), parameters.get("source_pile"),
                                      parameters.get("target_owner"), parameters.get("target_pile"))

    def discard_table_cards(self, parameters):
        from .bulkdiscard import discard_table_cards
        return discard_table_cards(self.game, parameters.get("card_indices"),
                                   parameters.get("pile_index", 0), parameters.get("personal", False))

    def discard_cards(self, parameters):
        from .bulkdiscard import discard_cards
        return discard_cards(self.game, parameters.get("card_indices"),
                             parameters.get("pile_index", 0), parameters.get("personal", False))

    def take_table_cards(self, indices):
        from .bulktake import take_table_cards
        return take_table_cards(self.game, indices)

    def play_cards(self, indices):
        from .bulkplay import play_cards
        return play_cards(self.game, indices)

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

    def end_turn_availability(self, next_player=None, skip_next=False):
        """Describe whether this player can advance the turn right now."""
        from .actionavailability import ActionAvailability
        if self.game.pending_shared_offer is not None:
            return ActionAvailability(False, "Finish the shared offer first.", "shared_offer_pending")
        if type(skip_next) is not bool:
            return ActionAvailability(False, "skip_next must be true or false.", "invalid_parameters")
        if skip_next:
            if not self.game.allow_skip_next_player:
                return ActionAvailability(False, "Skipping the next player is disabled.", "action_disabled")
            if next_player is not None:
                return ActionAvailability(False, "Choose either a manual destination or skip.", "invalid_parameters")
            if len(self.game.active_player_indices()) < 2:
                return ActionAvailability(False, "At least two active players are needed to skip.", "not_enough_players")
        if not self.game.active_player_indices():
            return ActionAvailability(False, "No active players remain.", "no_active_players")
        if self.game.current_player_must_confirm_point() or self.game.current_player_must_confirm_pot_withdrawal():
            return ActionAvailability(False, "Complete the pending confirmation first.", "confirmation_required")
        if next_player is not None:
            from .turnorder import next_player_error
            error = next_player_error(self.game, next_player)
            if error:
                return ActionAvailability(False, str(error), error.code)
        return ActionAvailability(True)

    def next_player_options(self):
        from .turnorder import build_next_player_options
        return build_next_player_options(self.game)

    def return_player_options(self):
        """Prepare immutable return choices and availability for clients."""
        from .playerleaving import build_player_return_options
        return build_player_return_options(self.game)

    def undo_availability(self):
        """Describe Undo without exposing mutable history to clients."""
        from .actionavailability import ActionAvailability
        if not self.game.enable_undo:
            return ActionAvailability(False, "Undo is disabled by the game rules.", "action_disabled")
        if not self.game.undo_stack:
            return ActionAvailability(False, "There is no action to undo.", "empty_undo")
        return ActionAvailability(True)

    def undo_result(self):
        """Undo with an explicit refusal reason and checkpoint outcome."""
        self.last_checkpoint_error = None
        available = self.undo_availability()
        if not available.allowed:
            return ActionResult(False, message=available.reason, code=available.code)
        if not self.game.undo_last_action():
            return ActionResult(False, message="The action could not be undone.", code="action_rejected")
        return ActionResult(True, changed=True, message="Undone.", checkpoint_error=self.checkpoint())

    def undo(self):
        """Compatibility adapter for callers expecting a boolean."""
        return self.undo_result().success
