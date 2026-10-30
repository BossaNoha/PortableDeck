"""Table placement and table-card operations for the Game model."""

import random
from .tableplacement import TablePlacementActions

class GameTableActions(TablePlacementActions):

    def flip_table_card(self, index):
        if not self.allow_face_down_table_cards or not 0 <= index < len(self.table_cards):
            return None
        entry = self.table_cards[index]
        if entry.get("face_up", True):
            return None
        position = entry.get("position")
        if isinstance(position, (tuple, list)) and len(position) == 2:
            if any(
                other is not entry
                and isinstance(other.get("position"), (tuple, list))
                and len(other["position"]) == 2
                and other["position"][1] == position[1]
                and other["position"][0] > position[0]
                for other in self.table_cards
            ):
                return None
        elif index != len(self.table_cards) - 1:
            return None
        entry["face_up"] = True
        self.log_action(self.players[self.current_player_index].name, "flip_table_card", entry["card"])
        return entry["card"]

    def recycle_discard_into_deck(self):
        if (
            not self.allow_recycle_discard_to_deck
            or self.deck.flat_deck
            or not any(pile for _, pile in self.all_discard_piles())
        ):
            return 0
        count = sum(len(pile) for _, pile in self.all_discard_piles())
        for _, pile in self.all_discard_piles():
            self.deck.flat_deck.extend(pile)
            pile.clear()
        random.shuffle(self.deck.flat_deck)
        self.log_action(self.players[self.current_player_index].name, "recycle_discard", None)
        return count

    def swap_with_table(self, hand_index, table_index):
        if (
            not self.allow_positioned_play
            or self.occupied_slot_action != "swap"
            or not 0 <= table_index < len(self.table_cards)
        ):
            return None
        player = self.players[self.current_player_index]
        replacement = player.play_card(hand_index)
        if replacement is None:
            return None
        table_entry = self.table_cards[table_index]
        returned_card = table_entry["card"]
        table_entry["card"] = replacement
        table_entry["player"] = player.name
        player.draw_card(returned_card)
        self.log_action(player.name, "swap_table_card", replacement)
        return replacement, returned_card

    def take_from_table(self, index):
        if not self.allow_take_from_table or not 0 <= index < len(self.table_cards):
            return None
        entry = self.table_cards.pop(index)
        if self.allow_positioned_play or self.allow_move_cards_on_table or self.allow_play_in_front_of_players:
            self._compact_main_line()
        card = entry["card"]
        player = self.players[self.current_player_index]
        player.draw_card(card)
        self.log_action(player.name, "take_from_table", card)
        return card

    def move_table_card_to_discard(self, index, pile_index=0, personal=False):
        if (
            not self.allow_move_table_card_to_discard
            or not 0 <= index < len(self.table_cards)
        ):
            return None
        entry = self.table_cards.pop(index)
        if self.allow_positioned_play or self.allow_move_cards_on_table or self.allow_play_in_front_of_players:
            self._compact_main_line()
        card = entry["card"]
        destination = (
            self.personal_discard_piles[self.current_player_index][pile_index]
            if personal else self.discard_piles[pile_index]
        )
        destination.append(card)
        self.log_action(self.players[self.current_player_index].name, "table_to_discard", card)
        return card

    def clear_table(self, automatic=False):
        if automatic:
            if not self.clear_table_on_round_end:
                return 0
        elif not self.allow_manual_table_cleanup:
            return 0
        count = len(self.table_cards)
        if count:
            self.discard_pile.extend(entry["card"] for entry in self.table_cards)
            self.table_cards.clear()
            self.history.append({
                "player": self.players[self.current_player_index].name,
                "action": "clear_table",
                "count": count,
            })
        return count

