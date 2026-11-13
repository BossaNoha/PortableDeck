"""Personal table piles, access checks and card ordering."""


class PersonalPileActions:
    def initialize_personal_piles(self, enabled=False, count=1, configurations=None, unequal=False, counts=None, team_access=False, dealer_access=False):
        if not isinstance(count, int) or isinstance(count, bool) or not 1 <= count <= 20:
            raise ValueError("Personal pile count must be between 1 and 20.")
        self.enable_team_pile_access = bool(team_access)
        self.enable_dealer_pile_access = bool(dealer_access)
        self.enable_personal_piles = bool(enabled)
        self.personal_pile_count = count
        self.unequal_personal_piles = bool(unequal)
        self.personal_pile_counts = list(counts) if unequal and counts is not None else [count] * len(self.players)
        if (len(self.personal_pile_counts) != len(self.players)
                or any(not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 20
                       for value in self.personal_pile_counts)):
            raise ValueError("Provide a personal pile count between 0 and 20 for each player.")
        self.personal_pile_settings = []
        configurations = configurations or []
        if not isinstance(configurations, list) or any(not isinstance(group, list) for group in configurations):
            raise ValueError("Personal pile settings must be grouped by player.")
        for owner in range(len(self.players)):
            group = []
            for pile in range(self.personal_pile_counts[owner]):
                config = (configurations[owner][pile] if owner < len(configurations)
                          and pile < len(configurations[owner]) else {})
                if not isinstance(config, dict):
                    raise ValueError("Each personal pile must have its own settings object.")
                rule = {"access": config.get("access", "owner"), "ordered": bool(config.get("ordered", False)),
                        "order_by": config.get("order_by", "time"), "new_card": config.get("new_card", "top"),
                        "size_order": config.get("size_order", "up")}
                if rule["access"] not in {"everyone", "team", "owner", "team_dealer", "dealer_only", "owner_dealer", "everyone_but_owner", "team_but_member"} or rule["order_by"] not in {"time", "size"} or rule["new_card"] not in {"top", "bottom"} or rule["size_order"] not in {"up", "down"}:
                    raise ValueError("Invalid personal pile settings.")
                group.append(rule)
            self.personal_pile_settings.append(group)
        self.personal_piles = [[[] for _ in range(amount)] for amount in self.personal_pile_counts]

    def can_access_personal_pile(self, owner, pile):
        if self.current_player_index in self.left_players or not self.enable_personal_piles or not self.enable_table:
            return False
        if not 0 <= owner < len(self.players) or not 0 <= pile < self.personal_pile_counts[owner]:
            return False
        viewer = self.current_player_index
        access = self.personal_pile_settings[owner][pile]["access"]
        if access == "everyone_but_owner":
            return viewer != owner
        if access == "team_but_member":
            return bool(viewer != owner and self.enable_team_pile_access
                        and self.enable_roles_teams and self.enable_teams
                        and self.player_teams[owner] is not None
                        and self.player_teams[owner] == self.player_teams[viewer])
        dealer = self.player_is_dealer(viewer)
        if access == "dealer_only":
            return dealer
        if owner == viewer or access == "everyone":
            return True
        if dealer and (access in {"team_dealer", "owner_dealer"} or self.enable_dealer_pile_access):
            return True
        return bool(access in {"team", "team_dealer"} and self.enable_team_pile_access
                    and self.enable_roles_teams and self.enable_teams
                    and self.player_teams[owner] is not None
                    and self.player_teams[owner] == self.player_teams[viewer])

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
        self.log_action(self.players[self.current_player_index].name, "play_to_personal_pile", card, owner=self.players[owner].name, pile=pile)
        return card

    def take_from_personal_pile(self, owner, pile):
        if not self.can_access_personal_pile(owner, pile) or not self.personal_piles[owner][pile]:
            return None
        card = self.personal_piles[owner][pile].pop()
        self.players[self.current_player_index].draw_card(card)
        self.log_action(self.players[self.current_player_index].name, "take_from_personal_pile", card)
        return card
