"""Point requests, scoring, and player confirmations for the Game model."""

class GameScoringActions:

    def request_point(self):
        if not self.score_enabled:
            return False, "Point scoring is disabled."
        if self.pending_point_request is not None:
            return False, "A point request is already waiting for a decision."

        requester = self.current_player_index
        if not self.require_point_confirmation:
            player_name = self.players[requester].name
            self.scores[requester] += 1
            self.log_action(player_name, "point_awarded")
            return True, f"{player_name} received a point."

        other_players = [index for index in range(len(self.players)) if index != requester]
        if not other_players:
            player_name = self.players[requester].name
            self.scores[requester] += 1
            self.log_action(player_name, "point_awarded")
            return True, f"{player_name} received a point (no other players to confirm)."

        self.pending_point_request = {"requester": requester, "confirmed_by": []}
        self.log_action(self.players[requester].name, "point_requested")
        return True, f"{self.players[requester].name} requested a point."

    def current_player_must_confirm_point(self):
        request = self.pending_point_request
        if request is None or self.current_player_index == request["requester"]:
            return False
        return self.current_player_index not in request["confirmed_by"]

    def confirm_point_request(self, approved):
        if not self.current_player_must_confirm_point():
            return False, "There is no point request awaiting your confirmation."

        request = self.pending_point_request
        voter_name = self.players[self.current_player_index].name
        requester_name = self.players[request["requester"]].name
        if not approved:
            self.log_action(voter_name, "point_denied")
            self.pending_point_request = None
            return True, f"{voter_name} denied the request. No point was awarded."

        request["confirmed_by"].append(self.current_player_index)
        self.log_action(voter_name, "point_confirmed")
        other_players = [index for index in range(len(self.players)) if index != request["requester"]]
        if all(index in request["confirmed_by"] for index in other_players):
            self.scores[request["requester"]] += 1
            self.log_action(requester_name, "point_awarded")
            self.pending_point_request = None
            return True, f"All players approved. {requester_name} received a point."
        return True, f"{voter_name} approved the request. The remaining players will be asked on their turns."

