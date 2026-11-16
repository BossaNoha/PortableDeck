# UI/core boundary audit

Game-changing card, chip, score, turn and player interaction actions in
`portable_deck/ui` now execute through `SessionController`. Model methods remain
available to core code. Selection and widget updates are local client state.

Legacy table positions are migrated in the core on session load and Undo.
Rendering the table no longer writes positions into game entries. Valid explicit
positions are preserved; legacy scalar positions keep their historical ordering.

Remaining boundaries to address in separate changes:

- Rendering still reads model collections directly. Introduce player-specific
  views before using the model with remote clients; the status snapshot alone
  is not a complete player view.

This audit covers the game UI package. Application settings, save management
and full network authorization require separate reviews.

Initial turn logging belongs to core lifecycle operations: `Game.start` (also
used by restart) and session loading. Loading a legacy session with an empty log
adds a turn entry for an active current player; existing log text is preserved.
GUI construction only renders this log. Turn-start UI acknowledges score
notifications through the controller and may request approval decisions.

`session.acknowledge_score_notifications` persists changed read state without
an independent gameplay Undo step. Nested acknowledgments share their enclosing
checkpoint; Undo of a gameplay action restores its prior notification state.

Pot approval prompts are prepared by `game.pot_confirmation_notification()`.
The immutable result distinguishes the voting player (`recipient`) from the
player receiving the pot (`beneficiary`). GUI code only displays the prompt and
submits `confirm_pot` through the controller.

Table zoom and scroll offsets belong to client-owned `TableViewState`, passed
to the GUI separately from `Game`. Named saves and checkpoints store it under
`client_state.table_view`. The application reads legacy `table_view_state` on
load. Core-only saves omit client metadata unless explicitly supplied; loading
with `Game.load_session` intentionally restores only the game, not client views.
New games and restarts use the default view. Presentation state is excluded from
gameplay snapshots and Undo.
