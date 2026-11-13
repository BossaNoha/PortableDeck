class FlippingCards:
    def initialize_flipping(self, enabled=False, hand=False, table=False, player_cards=False):
        self.enable_flipping = bool(enabled)
        self.allow_flip_hand = bool(hand)
        self.allow_flip_table = bool(table)
        self.allow_flip_player_cards = bool(player_cards)

    def flip_hand_card(self, index):
        if not self.enable_flipping or not self.allow_flip_hand or self.current_player_index in self.left_players:
            return None
        player = self.players[self.current_player_index]
        if not isinstance(index, int) or isinstance(index, bool) or not 0 <= index < len(player.hand):
            return None
        if index in player.revealed_indices:
            player.revealed_indices.remove(index)
        else:
            player.revealed_indices.add(index)
        self.log_action(player.name, "flip_hand_card")
        return player.hand[index]

    def can_flip_table_cards(self):
        return self.enable_flipping and self.enable_table and (self.allow_flip_player_cards if self.allow_play_in_front_of_players else self.allow_flip_table)
