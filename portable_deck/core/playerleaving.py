"""Conditional departures preserve player indices and skip departed turns."""
class PlayerLeaving:
    def initialize_leaving(self, enabled=False, conditions=None, allow_return=False):
        self.enable_player_return = bool(allow_return)
        defaults = {"match": "all", "own_score": False, "own_score_at": "target",
                    "opponent_score": False, "opponent_score_at": "target", "no_chips": False}
        saved = dict(conditions or {})
        if saved.pop("any_time", False):
            saved.update(own_score=False, opponent_score=False, no_chips=False)
        defaults.update({key: value for key, value in saved.items() if key in defaults})
        if defaults["own_score_at"] not in {"target", "warning"} or defaults["opponent_score_at"] not in {"target", "warning"}:
            raise ValueError("Invalid leaving score condition.")
        if defaults["match"] not in {"all", "any"}:
            raise ValueError("Leaving conditions must match all or any.")
        self.enable_player_leaving = bool(enabled)
        self.leave_conditions = defaults
        self.left_players = []

    def active_player_indices(self):
        return [i for i in range(len(self.players)) if i not in self.left_players]

    def score_condition_met(self, player, mode):
        if not self.score_enabled or not self.enable_target_score:
            return False
        if mode == "warning" and not self.enable_score_warning:
            return False
        threshold = self.score_warning if mode == "warning" else self.target_score
        team = self.player_teams[player]
        return (self.scores[player] >= threshold or
                bool(self.enable_team_score and team and self.team_scores.get(team, 0) >= threshold))

    def can_leave_session(self, player=None):
        player = self.current_player_index if player is None else player
        if not self.enable_player_leaving or player not in self.active_player_indices():
            return False
        if self.pending_point_request is not None or self.pending_pot_withdrawal is not None:
            return False
        rule = self.leave_conditions
        score_available = self.score_enabled and self.enable_target_score
        results = []
        if rule["own_score"] and score_available:
            results.append(self.score_condition_met(player, rule["own_score_at"]))
        team = self.player_teams[player] if self.enable_roles_teams and self.enable_teams else None
        if rule["opponent_score"] and score_available:
            results.append(any(
                i != player and (not team or self.player_teams[i] != team)
                and self.score_condition_met(i, rule["opponent_score_at"])
                for i in self.active_player_indices()))
        if rule["no_chips"] and self.enable_chip_accounts:
            results.append(self.chip_balance(player) <= 0)
        return not results or (all(results) if rule["match"] == "all" else any(results))

    def leave_session(self):
        if not self.can_leave_session():
            return False, "The conditions for leaving are not met, or a confirmation is pending."
        player = self.current_player_index
        self.left_players.append(player)
        self.log_action(self.players[player].name, "left_session")
        self.finish_turn()
        return True, f"{self.players[player].name} left the session."

    def return_player(self, player):
        if not self.enable_player_return:
            return False, "Player return is disabled."
        if not isinstance(player, int) or isinstance(player, bool) or player not in self.left_players:
            return False, "Choose a player who left the session."
        if self.pending_point_request is not None or self.pending_pot_withdrawal is not None:
            return False, "Complete the pending confirmation first."
        was_empty = not self.active_player_indices()
        self.left_players.remove(player)
        if was_empty:
            self.current_player_index = player
        self.log_action(self.players[player].name, "returned_to_session")
        return True, f"{self.players[player].name} returned to the session."
