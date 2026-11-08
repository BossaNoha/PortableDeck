"""Point requests, scoring, and player confirmations for the Game model."""

class GameScoringActions:

    def reduce_score(self):
        if not self.allow_reduce_score:
            return False, "Reducing score is disabled."
        return self.request_point(delta=-1)

    def request_point(self, delta=1):
        if delta == -1 and not self.allow_reduce_score:
            return False, "Reducing score is disabled."
        if delta not in (-1, 1):
            raise ValueError("Score changes must be one point.")
        if not self.score_enabled:
            return False, "Point scoring is disabled."
        if self.pending_point_request is not None:
            return False, "A point request is already waiting for a decision."

        requester = self.current_player_index
        if not self.require_point_confirmation:
            player_name = self.players[requester].name
            self.award_point(requester, delta)
            self.log_action(player_name, "point_awarded" if delta == 1 else "score_reduced")
            return True, f"{player_name} had their score changed by {delta:+d}."

        other_players = [index for index in self.active_player_indices() if index != requester]
        if not other_players:
            player_name = self.players[requester].name
            self.award_point(requester, delta)
            self.log_action(player_name, "point_awarded" if delta == 1 else "score_reduced")
            return True, f"{player_name} had their score changed by {delta:+d} (no other players to confirm)."

        self.pending_point_request = {"requester": requester, "confirmed_by": [], "delta": delta}
        self.log_action(self.players[requester].name, "point_requested")
        return True, f"{self.players[requester].name} requested a score change of {delta:+d}."

    def current_player_must_confirm_point(self):
        request = self.pending_point_request
        if request is None or self.current_player_index == request["requester"]:
            return False
        return self.current_player_index not in request["confirmed_by"]

    def confirm_point_request(self, approved):
        if not self.current_player_must_confirm_point():
            return False, "There is no point request awaiting your confirmation."

        request = self.pending_point_request
        delta = request.get("delta", 1)
        voter_name = self.players[self.current_player_index].name
        requester_name = self.players[request["requester"]].name
        if not approved:
            self.log_action(voter_name, "point_denied")
            self.pending_point_request = None
            return True, f"{voter_name} denied the request. No point was awarded."

        request["confirmed_by"].append(self.current_player_index)
        self.log_action(voter_name, "point_confirmed")
        other_players = [index for index in self.active_player_indices() if index != request["requester"]]
        if all(index in request["confirmed_by"] for index in other_players):
            self.award_point(request["requester"], delta)
            self.log_action(requester_name, "point_awarded" if delta == 1 else "score_reduced")
            self.pending_point_request = None
            return True, f"All players approved. {requester_name} had their score changed by {delta:+d}."
        return True, f"{voter_name} approved the request. The remaining players will be asked on their turns."


    def initialize_score_limits(self, enabled=False, target=100, warning_enabled=False, warning=80):
        if (not isinstance(target, int) or isinstance(target, bool) or target < 1
                or not isinstance(warning, int) or isinstance(warning, bool) or warning < 0
                or (enabled and warning_enabled and warning >= target)):
            raise ValueError("Invalid target score or warning threshold.")
        self.enable_target_score, self.target_score = bool(enabled), target
        self.enable_score_warning, self.score_warning = bool(warning_enabled), warning
        self.score_alerts_seen = {}

    def turn_score_alerts(self):
        if not self.score_enabled or not self.enable_target_score:
            return []
        active = {}
        warning_owners = {}
        for i, score in enumerate(self.scores):
            label = self.players[i].name
            identity = f"player_{i}"
            if self.share_team_score and self.player_teams[i]:
                identity = self.player_teams[i]
                label = self.player_team_name(i)
            if score >= self.target_score:
                active[f"target:{identity}"] = f"{label} reached the target score ({score}/{self.target_score})."
            elif self.enable_score_warning and score >= self.score_warning:
                key = f"warning:{identity}"
                active[key] = f"{label} reached the warning threshold: {score} points (threshold {self.score_warning})."
                warning_owners.setdefault(key, set()).add(i)
        if self.enable_team_score:
            for team in self.teams:
                if team["id"] == "dealer":
                    continue
                score = self.team_scores[team["id"]]
                if score >= self.target_score:
                    active[f"target:team_counter:{team['id']}"] = f"Team {team['name']} reached the target score ({score}/{self.target_score})."
                elif self.enable_score_warning and score >= self.score_warning:
                    key = f"warning:team_counter:{team['id']}"
                    active[key] = f"Team {team['name']} reached the warning threshold: {score} points."
                    warning_owners[key] = {i for i, team_id in enumerate(self.player_teams) if team_id == team["id"]}
        for viewer in list(self.score_alerts_seen):
            self.score_alerts_seen[viewer] = [key for key in self.score_alerts_seen[viewer] if key in active]
        viewer = str(self.current_player_index)
        seen = self.score_alerts_seen.get(viewer, [])
        messages = [message for key, message in active.items()
                    if key not in seen and self.current_player_index not in warning_owners.get(key, set())]
        self.score_alerts_seen[viewer] = list(active)
        return messages
