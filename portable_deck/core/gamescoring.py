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
        self.log_action(self.players[requester].name, "point_requested", delta=delta)
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

    def score_notifications(self):
        from .scorenotifications import pending_score_notifications
        return pending_score_notifications(self)

    def acknowledge_score_notifications(self, notifications):
        from .scorenotifications import acknowledge_score_notifications
        acknowledge_score_notifications(self, notifications)

    def score_confirmation_notification(self):
        from .scorenotifications import score_confirmation_notification
        return score_confirmation_notification(self)

    def turn_score_alerts(self):
        """Legacy consume-and-return-text adapter for existing clients."""
        notices = self.score_notifications()
        self.acknowledge_score_notifications(notices)
        return [notice.message for notice in notices]
