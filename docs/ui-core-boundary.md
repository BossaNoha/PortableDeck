# UI/core boundary audit

Game-changing card, chip, score, turn and player interaction actions in
`portable_deck/ui` now execute through `SessionController`. Model methods remain
available to core code. Selection and widget updates are local client state.

Legacy table positions are migrated in the core on session load and Undo.
Rendering the table no longer writes positions into game entries. Valid explicit
positions are preserved; legacy scalar positions keep their historical ordering.

Remaining boundaries to address in separate changes:

- `TableFrame.capture_view` writes zoom and scroll offsets to
  `game.table_view_state`. This is client presentation state, saved with the
  session but excluded from Undo. Separate its ownership from shared game state
  while retaining compatibility with existing saves.
- `GameGUIActions.handle_turn_start` acknowledges score notifications directly.
  Acknowledgement changes saved `score_alerts_seen` state. Define controller
  orchestration without creating an extra gameplay Undo step.
- `GameGUIBuilder` calls `ensure_initial_log`. Move lifecycle initialization
  away from interface construction so attaching a client is read-only.
- Pot approval prompt data is still assembled in the GUI. Prepare a structured
  core notification, following score approvals.
- Rendering still reads model collections directly. Introduce player-specific
  views before using the model with remote clients; the status snapshot alone
  is not a complete player view.

This audit covers the game UI package. Application settings, save management
and full network authorization require separate reviews.
