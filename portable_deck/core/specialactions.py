"""Optional deck placement and manual draw-deck shuffling."""
import random
import re

class SpecialActions:
    def initialize_special_actions(self, enabled=False, draw=False, discard=False, shuffle=False, draw_multiple=False, deal=False, offer=False):
        if not isinstance(shuffle, bool):
            raise ValueError("allow_shuffle_draw_deck must be true or false")
        self.enable_special_actions = bool(enabled)
        self.allow_insert_draw_deck = bool(draw)
        self.allow_insert_discard_pile = bool(discard)
        self.allow_shuffle_draw_deck = shuffle
        if not isinstance(draw_multiple, bool):
            raise ValueError("allow_draw_multiple_cards must be true or false")
        self.allow_draw_multiple_cards = draw_multiple
        if not isinstance(deal, bool):
            raise ValueError("allow_deal_cards must be true or false")
        self.allow_deal_cards = deal
        if not isinstance(offer, bool):
            raise ValueError("allow_shared_offer must be true or false")
        self.allow_shared_offer = offer

    def deal_cards(self, count, draw_pile_id="main"):
        from .actionavailability import ActionContext, action_availability
        from .actionerrors import ActionValidationError
        available = action_availability(self, "deal_cards", ActionContext(draw_pile_id=draw_pile_id))
        if not available.allowed:
            raise ActionValidationError(available.code, available.reason)
        from .drawpiles import resolve_draw_pile
        pile = resolve_draw_pile(self, draw_pile_id)
        if type(count) is not int or count < 1:
            raise ActionValidationError("invalid_count", "Choose a positive whole number of cards per player.")
        players = self.active_player_indices()
        if self.turn_direction == -1:
            players = list(reversed(players))
        start = players.index(self.current_player_index)
        players = players[start:] + players[:start]
        total = count * len(players)
        if total > len(pile.cards):
            raise ActionValidationError("insufficient_cards", "The draw deck has too few cards for the entire deal.")
        for _ in range(count):
            for player in players:
                card = (self.deck if draw_pile_id == "main" else pile).draw_card()
                if card is None:
                    raise ActionValidationError("action_rejected", "The cards could not be dealt.")
                self.players[player].draw_card(card)
        self.log_action(self.players[self.current_player_index].name, "deal_cards", count=count,
                        recipients=tuple(self.players[player].name for player in players), draw_pile_id=draw_pile_id)
        return total

    def draw_cards(self, count, draw_pile_id="main"):
        from .actionavailability import ActionContext, action_availability
        from .actionerrors import ActionValidationError
        available = action_availability(self, "draw_cards", ActionContext(draw_pile_id=draw_pile_id))
        if not available.allowed:
            raise ActionValidationError(available.code, available.reason)
        from .drawpiles import resolve_draw_pile
        pile = resolve_draw_pile(self, draw_pile_id)
        if type(count) is not int or count < 1:
            raise ActionValidationError("invalid_count", "Choose a positive whole number of cards.")
        if count > len(pile.cards):
            raise ActionValidationError("insufficient_cards", "The draw deck has too few cards for this draw.")
        cards = []
        for _ in range(count):
            card = self.deal_card_to_current() if draw_pile_id == "main" else self.deal_card_to_current(draw_pile_id)
            if card is None:
                raise ActionValidationError("action_rejected", "The cards could not be drawn.")
            cards.append(card)
        return tuple(cards)

    def shuffle_draw_deck(self, draw_pile_id="main"):
        from .actionavailability import ActionContext, action_availability
        from .actionerrors import ActionValidationError
        available = action_availability(self, "shuffle_draw_deck", ActionContext(draw_pile_id=draw_pile_id))
        if not available.allowed:
            raise ActionValidationError(available.code, available.reason)
        from .drawpiles import resolve_draw_pile
        pile = resolve_draw_pile(self, draw_pile_id)
        random.shuffle(pile.cards)
        self.log_action(self.players[self.current_player_index].name, "shuffle_draw_deck", draw_pile_id=draw_pile_id)
        return len(pile.cards)

    def insert_hand_card(self, hand_index, destination, position, pile_index=0):
        if not self.enable_special_actions:
            raise ValueError("Special actions are disabled.")
        if self.current_player_index in self.left_players:
            raise ValueError("This player has left the session.")
        if self.pending_point_request is not None or self.pending_pot_withdrawal is not None:
            raise ValueError("Complete the pending confirmation first.")
        if destination == "draw" and self.allow_insert_draw_deck:
            pile = self.deck.flat_deck
        elif destination == "discard" and self.allow_insert_discard_pile and self.enable_discard_pile:
            if not isinstance(pile_index, int) or isinstance(pile_index, bool) or not 0 <= pile_index < len(self.discard_piles):
                raise ValueError("Choose a valid discard pile.")
            pile = self.discard_piles[pile_index]
        else:
            raise ValueError("This placement is disabled.")
        if isinstance(position, str):
            position = position.strip()
            if position.casefold() == "x":
                position = "X"
            elif re.fullmatch(r"-?(?:[1-9]|10)", position):
                position = int(position)
            else:
                raise ValueError("Use 1–10 (from top), -1–-10 (from bottom), or X (outside both ten-position ranges).")
        if position != "X" and (not isinstance(position, int) or isinstance(position, bool)
                                or not 1 <= abs(position) <= 10):
            raise ValueError("Use 1–10 (from top), -1–-10 (from bottom), or X (outside both ten-position ranges).")
        if position != "X" and abs(position) > len(pile) + 1:
            raise ValueError(f"This pile only has {len(pile) + 1} available positions from either end.")
        if position == "X" and len(pile) < 20:
            raise ValueError("No middle position is available outside the first and last ten positions.")
        player = self.players[self.current_player_index]
        if not isinstance(hand_index, int) or isinstance(hand_index, bool) or not 1 <= hand_index <= len(player.hand):
            raise ValueError("Select a card in your hand first.")
        top_offset = (random.randrange(10, len(pile) - 9) if position == "X" else
                      position - 1 if position > 0 else len(pile) + position + 1)
        offset = top_offset if destination == "draw" else len(pile) - top_offset
        card = player.play_card(hand_index)
        pile.insert(offset, card)
        self.record_event({"player": player.name, "action": "insert_hand_card", "card": card,
                             "destination": destination, "position": position, "pile_index": pile_index})
        return card
