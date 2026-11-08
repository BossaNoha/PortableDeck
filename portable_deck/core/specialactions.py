"""Place a hand card at an explicit top-based deck position."""
import random
import re

class SpecialActions:
    def initialize_special_actions(self, enabled=False, draw=False, discard=False):
        self.enable_special_actions = bool(enabled)
        self.allow_insert_draw_deck = bool(draw)
        self.allow_insert_discard_pile = bool(discard)

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
        self.history.append({"player": player.name, "action": "insert_hand_card", "card": card,
                             "destination": destination, "position": position, "pile_index": pile_index})
        return card
