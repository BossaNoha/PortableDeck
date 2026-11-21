"""Client-independent hotseat handoff flow; no widgets or terminal handling."""
from ..core.session import ActionResult


class TurnHandoffController:
    def __init__(self, session, *, enabled=False):
        self.session = session
        self.enabled = enabled
        self.pending = False
        self.completing = False
        self._advance = None

    def request(self, advance, *, next_player=None):
        if self.pending:
            return ActionResult(False, message="Confirm or cancel the pending handoff first.", code="handoff_pending")
        if not self.enabled or not self.session.end_turn_availability(next_player).allowed:
            return advance()
        self._advance = advance
        self.pending = True
        return ActionResult(True, message="Pass to the next player; use ready to start or cancel to go back.",
                            code="handoff_required")

    def confirm(self):
        if not self.pending:
            return ActionResult(False, message="No turn handoff is pending.", code="handoff_not_pending")
        if self.completing:
            return ActionResult(False, message="The handoff is already being completed.", code="handoff_pending")
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
        return ActionResult(True, message="Handoff cancelled; the current turn is unchanged.", code="handoff_cancelled")
