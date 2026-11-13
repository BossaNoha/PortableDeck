"""Viewer permissions for hands, indexed by the hand's owner."""
import copy

class CardsVisibility:
    def initialize_cards_visibility(self, enabled=False, rules=None):
        self.enable_cards_visibility = bool(enabled)
        if rules is not None and not isinstance(rules, list):
            raise ValueError("Hand visibility rules must be a list.")
        self.cards_visibility = []
        for owner in range(len(self.players)):
            rule = rules[owner] if rules and owner < len(rules) else {"players": [owner], "teams": []}
            if (not isinstance(rule, dict) or not isinstance(rule.get("players"), list)
                    or not isinstance(rule.get("teams"), list)
                    or any(not isinstance(i, int) or isinstance(i, bool) or not 0 <= i < len(self.players) for i in rule["players"])
                    or any(not isinstance(team, str) for team in rule["teams"])):
                raise ValueError("Invalid hand visibility permissions.")
            self.cards_visibility.append(copy.deepcopy(rule))

    def can_view_hand(self, viewer, owner):
        if not 0 <= viewer < len(self.players) or not 0 <= owner < len(self.players):
            return False
        if not self.enable_cards_visibility:
            return viewer == owner
        rule = self.cards_visibility[owner]
        if viewer in rule["players"]:
            return True
        if self.enable_roles_teams:
            if self.enable_teams and self.player_teams[viewer] and self.player_teams[viewer] in rule["teams"]:
                return True
            if self.player_is_dealer(viewer) and "dealer" in rule["teams"]:
                return True
        return False

    def visible_hand(self, viewer, owner):
        if self.can_view_hand(viewer, owner):
            return list(self.players[owner].hand)
        player = self.players[owner]
        if not player.revealed_indices:
            return None
        return [card if i in player.revealed_indices else "Hidden card" for i, card in enumerate(player.hand)]
