"""Personal table piles, access checks and card ordering."""


class PersonalPileActions:
    def initialize_personal_piles(self, enabled=False, count=1, configurations=None):
        if not isinstance(count, int) or isinstance(count, bool) or not 1 <= count <= 20:
            raise ValueError("Personal pile count must be between 1 and 20.")
        self.enable_personal_piles = bool(enabled)
        self.personal_pile_count = count
        self.personal_pile_settings = []
        configurations = configurations or []
        if not isinstance(configurations, list) or any(not isinstance(group, list) for group in configurations):
            raise ValueError("Personal pile settings must be grouped by player.")
        for owner in range(len(self.players)):
            group = []
            for pile in range(count):
                config = (configurations[owner][pile] if owner < len(configurations)
                          and pile < len(configurations[owner]) else {})
                if not isinstance(config, dict):
                    raise ValueError("Each personal pile must have its own settings object.")
                rule = {"access": config.get("access", "owner"), "ordered": bool(config.get("ordered", False)),
                        "order_by": config.get("order_by", "time"), "new_card": config.get("new_card", "top"),
                        "size_order": config.get("size_order", "up")}
                if rule["access"] not in {"everyone", "team", "owner"} or rule["order_by"] not in {"time", "size"} or rule["new_card"] not in {"top", "bottom"} or rule["size_order"] not in {"up", "down"}:
                    raise ValueError("Invalid personal pile settings.")
                group.append(rule)
            self.personal_pile_settings.append(group)
        self.personal_piles = [[[] for _ in range(count)] for _ in self.players]

    def can_access_personal_pile(self, owner, pile):
        if not self.enable_personal_piles or not self.enable_table:
            return False
        if not 0 <= owner < len(self.players) or not 0 <= pile < self.personal_pile_count:
            return False
        return (owner == self.current_player_index
                or self.personal_pile_settings[owner][pile]["access"] == "everyone")

    @staticmethod
    def personal_card_sort_key(card):
        rank, _, symbol = card.rpartition(" of ")
        faces = {"j": 11, "jack": 11, "knight": 11, "q": 12, "queen": 12,
                 "k": 13, "king": 13, "a": 14, "ace": 14}
        try:
            return 0, float(rank), symbol
        except ValueError:
            if rank.casefold() in faces:
                return 0, faces[rank.casefold()], symbol
            return 1, rank.casefold(), symbol

    def play_to_personal_pile(self, hand_index, owner, pile):
        if not self.can_access_personal_pile(owner, pile):
            return None
        card = self.players[self.current_player_index].play_card(hand_index)
        if card is None:
            return None
        cards = self.personal_piles[owner][pile]
        rule = self.personal_pile_settings[owner][pile]
        if rule["ordered"] and rule["order_by"] == "time" and rule["new_card"] == "bottom":
            cards.insert(0, card)
        else:
            cards.append(card)
        if rule["ordered"] and rule["order_by"] == "size":
            cards.sort(key=self.personal_card_sort_key, reverse=rule["size_order"] == "down")
        self.log_action(self.players[self.current_player_index].name, "play_to_personal_pile", card)
        return card

    def take_from_personal_pile(self, owner, pile):
        if not self.can_access_personal_pile(owner, pile) or not self.personal_piles[owner][pile]:
            return None
        card = self.personal_piles[owner][pile].pop()
        self.players[self.current_player_index].draw_card(card)
        self.log_action(self.players[self.current_player_index].name, "take_from_personal_pile", card)
        return card
