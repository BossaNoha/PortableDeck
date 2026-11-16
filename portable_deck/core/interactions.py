"""Optional player-to-player actions with model-level permission checks."""
import random
from dataclasses import dataclass

INTERACTIONS = {
    "take_random_card": "Take a random card from a chosen player",
    "discard_random_card": "Discard a random card from a random player",
    "give_card": "Give a selected card to a chosen player",
    "steal_chips": "Steal chips from a chosen player",
    "peek_random_card": "Look at a random card of a chosen player",
    "peek_all_cards": "Look at all cards of a chosen player",
}


def interaction_target_reason(game, action, target):
    if (not isinstance(target, int) or isinstance(target, bool)
            or not 0 <= target < len(game.players) or target == game.current_player_index):
        return "Choose another player."
    if target in game.left_players:
        return "This player has left the session."
    if action in {"take_random_card", "discard_random_card", "peek_random_card", "peek_all_cards"} and not game.players[target].hand:
        return "The chosen player has no cards."
    if action == "steal_chips":
        if game.chip_account_index(target) == game.chip_account_index(game.current_player_index):
            return "Both players share the same chip account."
        if game.pending_pot_withdrawal is not None:
            return "Wait for the pending pot withdrawal to finish."
        if game.chip_balance(target) < 1:
            return "This player has no chips to steal."
    return ""


@dataclass(frozen=True)
class InteractionTarget:
    index: int
    name: str
    allowed: bool
    reason: str
    max_amount: int | None


@dataclass(frozen=True)
class InteractionOptions:
    action: str
    label: str
    allowed: bool
    reason: str
    random_target: bool
    targets: tuple[InteractionTarget, ...]


def build_interaction_options(game, action, hand_index=None):
    """Immutable options for the current actor, containing no hand identities."""
    from .actionavailability import ActionContext, action_availability
    if action not in INTERACTIONS:
        raise ValueError(f"Unknown interaction: {action}")
    available = action_availability(game, action, ActionContext(hand_index=hand_index))
    targets = []
    for index, player in enumerate(game.players):
        if index == game.current_player_index:
            continue
        reason = available.reason or interaction_target_reason(game, action, index)
        maximum = game.chip_balance(index) if action == "steal_chips" and game.enable_chip_accounts else None
        targets.append(InteractionTarget(index, player.name, not reason, reason, maximum))
    allowed = available.allowed and any(target.allowed for target in targets)
    reason = available.reason if not available.allowed else "" if allowed else "No eligible players for this interaction."
    return InteractionOptions(action, INTERACTIONS[action], allowed, reason,
                              action == "discard_random_card", tuple(targets))


class PlayerInteractions:
    def initialize_interactions(self, enabled=False, options=None):
        self.enable_interactions = bool(enabled)
        self.interaction_options = {key: bool((options or {}).get(key, False)) for key in INTERACTIONS}

    def interaction_allowed(self, action):
        return (self.enable_interactions and self.interaction_options.get(action, False)
                and (action != "steal_chips" or self.enable_chip_accounts)
                and (action != "discard_random_card" or self.enable_discard_pile))

    def interact(self, action, target=None, hand_index=None, amount=None):
        if not self.interaction_allowed(action):
            raise ValueError("This interaction is disabled.")
        if self.current_player_must_confirm_point() or self.current_player_must_confirm_pot_withdrawal():
            raise ValueError("Complete the pending confirmation first.")
        actor = self.current_player_index
        if action == "discard_random_card":
            candidates = [i for i, player in enumerate(self.players) if i != actor and i not in self.left_players and player.hand]
            if not candidates:
                raise ValueError("No other player has cards to discard.")
            target = random.choice(candidates)
        reason = interaction_target_reason(self, action, target)
        if reason:
            raise ValueError(reason)
        other = self.players[target]
        result = {"target": target}
        if action == "give_card":
            if not isinstance(hand_index, int) or isinstance(hand_index, bool) or not 1 <= hand_index <= len(self.players[actor].hand):
                raise ValueError("Select a card in your hand first.")
            card = self.players[actor].play_card(hand_index)
            other.draw_card(card)
            result["card"] = card
        elif action == "steal_chips":
            source, destination = self.chip_account_index(target), self.chip_account_index(actor)
            if not isinstance(amount, int) or isinstance(amount, bool) or not 1 <= amount <= self.chip_balance(target):
                raise ValueError("Choose an amount available in the target's account.")
            self.chip_balances[source] -= amount
            self.chip_balances[destination] += amount
            result["amount"] = amount
        elif action in {"peek_random_card", "peek_all_cards"}:
            result["cards"] = [random.choice(other.hand)] if action == "peek_random_card" else list(other.hand)
        else:
            card = other.play_card(random.randrange(len(other.hand)) + 1)
            if action == "take_random_card":
                self.players[actor].draw_card(card)
            else:
                self.discard_pile.append(card)
            result["card"] = card
        entry = {"player": self.players[actor].name, "action": action, "target": other.name}
        # Revealed cards stay in the private dialog, outside logs and saved history.
        entry.update({key: result[key] for key in ("card", "amount") if key in result})
        self.record_event(entry)
        return result
