"""Chip-account and shared-pot operations for the Game model."""

class ChipBankActions:

    def buy_chips(self, player_index, amount):
        """Add chips to one player's account."""
        if (
            not self.enable_chip_accounts
            or not 0 <= player_index < len(self.players)
            or not isinstance(amount, int)
            or isinstance(amount, bool)
            or amount < 1
        ):
            return None
        self.chip_balances[player_index] += amount
        self.history.append({
            "player": self.players[player_index].name,
            "action": "buy_chips",
            "amount": amount,
        })
        return self.chip_balances[player_index]

    def play_chips(self, amount):
        """Put chips from the current player's account into the shared pot."""
        if not self.enable_chip_accounts:
            return False, "Chip accounts are disabled."
        if self.pending_pot_withdrawal is not None:
            return False, "Chip play is paused while the pot withdrawal is awaiting approval."
        if not isinstance(amount, int) or isinstance(amount, bool) or amount < self.minimum_bet:
            return False, f"The minimum bet is {self.minimum_bet} chips."
        player = self.players[self.current_player_index]
        if amount > self.chip_balances[self.current_player_index]:
            return False, f"{player.name} does not have enough chips."
        self.chip_balances[self.current_player_index] -= amount
        self.chip_pot += amount
        self.history.append({"player": player.name, "action": "play_chips", "amount": amount})
        return True, f"{player.name} put {amount} chips into the pot. Pot: {self.chip_pot}."

    def request_pot_withdrawal(self, recipient_index):
        """Request transferring the full pot to a chosen player's account."""
        if not self.enable_chip_accounts:
            return False, "Chip accounts are disabled."
        if not isinstance(recipient_index, int) or isinstance(recipient_index, bool) or not 0 <= recipient_index < len(self.players):
            return False, "Choose a valid player to receive the pot."
        if self.chip_pot < 1:
            return False, "There are no chips in the pot."
        if self.pending_pot_withdrawal is not None:
            return False, "A pot withdrawal request is already waiting for approval."

        requester = self.current_player_index
        recipient = self.players[recipient_index].name
        if self.require_pot_withdrawal_confirmation:
            other_players = [index for index in range(len(self.players)) if index != requester]
            if other_players:
                self.pending_pot_withdrawal = {
                    "requester": requester,
                    "recipient": recipient_index,
                    "confirmed_by": [],
                }
                self.history.append({
                    "player": self.players[requester].name,
                    "action": "pot_withdrawal_requested",
                    "recipient": recipient,
                    "amount": self.chip_pot,
                })
                return True, f"{self.players[requester].name} requested the pot for {recipient}. Other players must approve."
        return True, self._complete_pot_withdrawal(requester, recipient_index)

    def current_player_must_confirm_pot_withdrawal(self):
        request = self.pending_pot_withdrawal
        if request is None or self.current_player_index == request["requester"]:
            return False
        return self.current_player_index not in request["confirmed_by"]

    def confirm_pot_withdrawal(self, approved):
        if not self.current_player_must_confirm_pot_withdrawal():
            return False, "There is no pot withdrawal awaiting your confirmation."
        request = self.pending_pot_withdrawal
        voter = self.current_player_index
        voter_name = self.players[voter].name
        requester_name = self.players[request["requester"]].name
        recipient_index = request["recipient"]
        recipient_name = self.players[recipient_index].name
        if not approved:
            self.history.append({"player": voter_name, "action": "pot_withdrawal_denied"})
            self.pending_pot_withdrawal = None
            return True, f"{voter_name} rejected the pot withdrawal. The pot remains unchanged."

        request["confirmed_by"].append(voter)
        self.history.append({"player": voter_name, "action": "pot_withdrawal_approved"})
        other_players = [index for index in range(len(self.players)) if index != request["requester"]]
        if all(index in request["confirmed_by"] for index in other_players):
            return True, self._complete_pot_withdrawal(request["requester"], recipient_index)
        return True, f"{voter_name} approved. The remaining players will be asked on their turns."

    def _complete_pot_withdrawal(self, requester_index, recipient_index):
        amount = self.chip_pot
        self.chip_balances[recipient_index] += amount
        self.chip_pot = 0
        self.pending_pot_withdrawal = None
        recipient_name = self.players[recipient_index].name
        self.history.append({
            "player": self.players[requester_index].name,
            "action": "pot_withdrawn",
            "recipient": recipient_name,
            "amount": amount,
        })
        return f"{amount} chips were moved from the pot to {recipient_name}'s account."

