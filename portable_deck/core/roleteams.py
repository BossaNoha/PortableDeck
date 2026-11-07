"""Team membership and dealer metadata; these roles grant no privileges."""


class RolesTeams:
    def initialize_roles_teams(self, enabled=False, dealer=False, teams=False, count=1,
                               names=None, assignments=None, dealer_players=None):
        players = len(self.players)
        if not isinstance(count, int) or isinstance(count, bool) or not 1 <= count <= players:
            raise ValueError("The total team count, including Dealer, cannot exceed the player count.")
        self.enable_roles_teams = bool(enabled)
        self.enable_dealer = bool(dealer)
        self.enable_teams = bool(teams)
        self.team_count = count
        self.team_names = list(names or [])
        if any(not isinstance(name, str) or not name.strip() for name in self.team_names):
            raise ValueError("Team names must be non-empty text.")
        regular_count = count - int(self.enable_dealer) if self.enable_teams else 0
        self.teams = [{"id": f"team_{i + 1}",
                       "name": self.team_names[i] if i < len(self.team_names) else f"Team {i + 1}"}
                      for i in range(regular_count)]
        if self.enable_dealer:
            self.teams.insert(0, {"id": "dealer", "name": "Dealer"})
        valid = {team["id"] for team in self.teams if team["id"] != "dealer"}
        self.player_teams = list(assignments) if assignments is not None else [None] * players
        self.dealer_players = (list(dealer_players) if dealer_players is not None
                               else [team == "dealer" for team in self.player_teams])
        self.player_teams = [None if team == "dealer" else team for team in self.player_teams]
        if len(self.dealer_players) != players or any(not isinstance(value, bool) for value in self.dealer_players):
            raise ValueError("Provide a dealer flag for each player.")
        if len(self.player_teams) != players or any(team is not None and team not in valid for team in self.player_teams):
            raise ValueError("Assign each player to an existing team or leave them unassigned.")

    def player_team_name(self, player_index):
        if not self.enable_roles_teams:
            return None
        team_id = self.player_teams[player_index]
        return next((team["name"] for team in self.teams if team["id"] == team_id), None)

    def player_is_dealer(self, player_index):
        return self.enable_roles_teams and self.enable_dealer and self.dealer_players[player_index]

    def initialize_team_resources(self, chips=False, score=False, team_score=False, pool=False):
        active = self.enable_roles_teams and self.enable_teams
        self.share_team_chips = bool(chips and active and self.enable_chip_accounts)
        self.share_team_score = bool(score and active and self.score_enabled)
        self.enable_team_score = bool(team_score and active and self.score_enabled)
        self.team_scores = {team["id"]: 0 for team in self.teams if team["id"] != "dealer"}
        if pool and self.share_team_chips:
            for team in self.team_scores:
                members = [i for i, value in enumerate(self.player_teams) if value == team]
                if members:
                    total = sum(self.chip_balances[i] for i in members)
                    for i in members:
                        self.chip_balances[i] = 0
                    self.chip_balances[members[0]] = total

    def chip_account_index(self, player):
        team = self.player_teams[player]
        if self.share_team_chips and team:
            return self.player_teams.index(team)
        return player

    def chip_balance(self, player):
        return self.chip_balances[self.chip_account_index(player)]

    def award_point(self, player, delta=1):
        team = self.player_teams[player] if self.enable_roles_teams and self.enable_teams else None
        members = ([i for i, value in enumerate(self.player_teams) if value == team]
                   if team and self.share_team_score else [player])
        for member in members:
            self.scores[member] += delta
        if team and self.enable_team_score:
            self.team_scores[team] += delta
