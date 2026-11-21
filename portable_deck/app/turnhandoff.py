"""Client-independent hotseat handoff flow; no widgets or terminal handling."""
from ..core.session import ActionResult


class TurnHandoffController:
    def __init__(self, session, *, enabled=False, confirm_skip=False):
        self.session = session
        self.enabled = enabled
        self.confirm_skip_enabled = confirm_skip
        self.awaiting_skip = False
        self.pending = False
        self.completing = False
        self._advance = None

    def request(self, advance, *, next_player=None, skip_next=False):
        if self.pending:
            return ActionResult(False, message="Confirm or cancel the pending handoff first.", code="handoff_pending")
        if not self.session.end_turn_availability(next_player, skip_next=skip_next).allowed:
            return advance()
        if not self.enabled and not (skip_next and self.confirm_skip_enabled):
            return advance()
        self._advance = advance
        self._turn_parameters = {"next_player": next_player, "skip_next": skip_next}
        self.pending = True
        self.awaiting_skip = skip_next and self.confirm_skip_enabled
        if self.awaiting_skip:
            return ActionResult(True, message="Skip the next active player? Use confirm-skip or cancel.",
                                code="skip_confirmation_required")
        return self.handoff_result()

    @staticmethod
    def handoff_result():
        return ActionResult(True, message="Pass to the next player; use ready to start or cancel to go back.",
                            code="handoff_required")

    def confirm_skip(self):
        if not self.pending or not self.awaiting_skip:
            return ActionResult(False, message="No skip confirmation is pending.", code="skip_not_pending")
        available = self.session.end_turn_availability(**self._turn_parameters)
        if not available.allowed:
            return ActionResult(False, message=available.reason, code=available.code)
        self.awaiting_skip = False
        if self.enabled:
            return self.handoff_result()
        return self.confirm()

    def confirm(self):
        if not self.pending:
            return ActionResult(False, message="No turn handoff is pending.", code="handoff_not_pending")
        if self.completing:
            return ActionResult(False, message="The handoff is already being completed.", code="handoff_pending")
        if self.awaiting_skip:
            return ActionResult(False, message="Confirm the skip with confirm-skip or cancel first.",
                                code="skip_confirmation_required")
        self.completing = True
        try:
            result = self._advance()
            if result.success:
                self.pending = False
                self._advance = None
            return result
        finally:
            self.completing = False

    def cancel(self):
        if not self.pending or self.completing:
            return ActionResult(False, message="No cancellable turn handoff is pending.", code="handoff_not_pending")
        self.pending = False
        self._advance = None
        if self.awaiting_skip:
            self.awaiting_skip = False
            return ActionResult(True, message="Skip cancelled; the current turn is unchanged.", code="skip_cancelled")
        return ActionResult(True, message="Handoff cancelled; the current turn is unchanged.", code="handoff_cancelled")
