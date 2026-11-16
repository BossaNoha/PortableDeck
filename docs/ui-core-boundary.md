# UI/core boundary audit

Game-changing card, chip, score, turn and player interaction actions in
`portable_deck/ui` now execute through `SessionController`. Model methods remain
available to core code. Selection and widget updates are local client state.

Legacy table positions are migrated in the core on session load and Undo.
Rendering the table no longer writes positions into game entries. Valid explicit
positions are preserved; legacy scalar positions keep their historical ordering.

Hands, table layouts, personal piles and discard browsing now render immutable
core projections. Full Deck preview renders an immutable definition. Discard
destinations and insertion ranges use `core.pileoptions`. These are useful local
client boundaries, but they do not yet form a complete remote-client interface.

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

Hand projections use an explicit validated viewer and existing player/team/dealer
permissions. Hidden card identities are replaced by `None`; revealed cards are
visible individually even without full-hand permission. Projections contain
immutable tuples and dataclasses, never live hand collections. Viewer selection
is not authentication: a future host must establish the caller's player identity.

The table projection removes every face-down card identity, even for its owner.
It preserves model indices, stacked positions, available targets and player lane
names. Table rendering reads this snapshot instead of raw table card entries.
Actions and selection still use local model/controller APIs; these projections
alone do not make the application a remote client.

Personal pile cards retain their current public visibility. Their immutable
projection separates viewer-specific access from turn/selection-dependent play
and take availability. The GUI reads pile data and destinations from this view;
session commands remain authoritative when executing an action.

Discard draw dialogs use immutable pile/card snapshots with original source and
card indices, without holding live pile lists or finding sources by object
identity. Empty piles retain their source indices. Top-only browsing omits deeper
identities; any-card browsing retains existing visibility. The controller checks
draw permissions and current indices again when a choice is submitted.

Discard destination dialogs no longer enumerate model pile lists. Insertion
dialogs receive counts, ranges and middle-position availability without reading
draw or discard card collections. These options are descriptive; execution
permissions, selection validity and position rules remain enforced by commands.

## Follow-up audit: remaining dependencies

This follow-up is a static review of `portable_deck/ui` and the supporting core
queries. The user reported that their manually exercised flows worked after the
preceding refactors; this is not a claim that every GUI flow was manually tested.
No gameplay implementation was changed as part of this audit.

| Priority | Boundary | Evidence and implication | Suggested isolated change |
| --- | --- | --- | --- |
| 1 | Duplicate chip button availability | `ui/chipbankui.py:update_action_buttons` checks the pot, pending withdrawal and balance itself. `ui/actionavailability.py` also updates those buttons through the shared API, including confirmation blocking. Different refresh paths can therefore use different conditions. | Make chip button refresh delegate to shared availability. Verify confirmation blocking, minimum bet, empty pot and pending withdrawal. Keep dialog input and rendering local. |
| 2 | Drag and context actions repeat rules | `ui/carddrag.py:drop` checks turn state, flags, positions and indices; `ui/cardcontextmenu.py:card_menu_entries` and `ui/contextactions.py:refresh` repeat parts of confirmation and action checks. Execution still goes through session commands. | Centralize the decision about a proposed drop and its command parameters. Then reuse shared availability in context menus. Preserve the default-position constraint of non-positioned play. |
| 3 | Interaction and player lifecycle dialogs inspect model players | `ui/interactionsui.py:show` builds targets from active players and reads chip balances; `ui/gameguiactions.py:choose_returning_player` uses departed players directly. Interaction target and amount validation currently occurs during execution, beyond the general availability query. | Add immutable action-specific options for targets and amount limits, with IDs/names and reasons, without passing Player objects. Revalidate on execution. |
| 4 | Selection still depends on secret model data | `core/selection.py:synchronize` copies actual hand identities and table entry contents to detect collection changes. `ui/cardcontextmenu.py:show_card_menu` and `ui/carddrag.py:drop` inspect model collection lengths. Redacted rendering alone therefore does not remove the client's model dependency. | Design revision/selection tokens or a snapshot-based synchronization contract before using projections remotely. Do not compare only redacted card values: hidden-card replacements must still invalidate stale selection. |
| 5 | Some read APIs perform compatibility writes | `Game.all_discard_piles` calls `ensure_discard_pile_state`, which can fill/rebuild fields. Core paths such as discard drawing and session persistence call it. New discard projections avoid it. | Move discard compatibility normalization to load/restore boundaries and make enumeration read-only. Review legacy-save and Undo coverage before removing the compatibility behavior. |

Additional boundaries for a later, larger milestone:

- `GameGUIBuilder` uses rule flags to choose which widgets exist. This is
  reasonable for the present client; consolidate client capabilities when
  defining a replacement UI contract, rather than adding a snapshot per flag.
- `GameGUI` retains the entire `Game`; independent projections do not provide
  authentication or transport. A host must choose the authorized viewer and
  filter action results/history. In particular, `ActionResult.events` is copied
  from internal history and must not automatically be broadcast to all clients.
- Save callbacks, checkpoint error reporting and application lifecycle are
  separate from widget layout. Their present direct model access is not evidence
  of game rules belonging to Tkinter.
- Public log rendering, resetting selection, scroll/zoom, dialog cancellation,
  label formatting and widget placement can remain client responsibilities.

### Availability follow-up

Priorities 1 and the availability portion of 2 above have now been addressed:

- Chip button refresh and chip dialog entry checks delegate to
  `action_availability`; modal input is followed by controller validation.
- `drop_availability` resolves the command and checks hand/table indices, rules
  and targets. Both drag highlighting and drop submission use it. Ordinary
  non-positioned hand drops retain their default-position restriction.
- Contextual give actions query shared availability. Move menus and destination
  dialogs use `available_move_targets`, or check the selected target directly.
- The shared check rejects departed current players for gameplay actions.
- `SessionController.execute` still checks availability immediately before
  executing commands. Model-level parameter and rule enforcement is retained.

The findings table describes the audit baseline. UI rules for widget visibility,
dialog layout and selection remain local. Interaction target options and the
other boundaries in priorities 3–5 remain separate follow-ups.

Interaction dialogs now use `build_interaction_options` for target IDs/names,
eligibility reasons and amount limits. They refresh options on action changes
and before submitting input. Shared target validation is reused by execution,
which rejects stale targets or changed balances without mutation. Departed
players remain listed with an explanation. Returning-player dialogs from
priority 3 remain a separate follow-up.

Regression checks cover stale UI approval followed by confirmation blocking,
chip-dialog state changes during input, unchanged state/Undo/checkpoints on
rejection, chip refresh states, invalid drops and filtered move destinations.

### Selection synchronization follow-up

The synchronization portion of priority 4 is now separated from secret client
data. `SelectionSnapshot` contains a session scope, current player, hand/table
counts and random opaque change markers. `SelectionState.synchronize` accepts
this DTO without a Game reference; GUI synchronization sites explicitly request
the DTO from the core. The old Game argument is retained as a local adapter.

`build_selection_snapshot` compares authoritative collection snapshots in a
private core cache and refreshes markers when queried after a change. No card
hashes, card values or private cache data enter the DTO or SelectionState.
Deep copies detect in-place table-position changes as well as hidden identity
replacement. Unchanged collections retain their markers; Undo is compared by
the same mechanism. New/loaded game instances have distinct session scopes.
Markers and cache are excluded from saves, gameplay snapshots and Undo.

These are change markers observed at query time, not a history of every
intermediate mutation or authorization tokens. They do not reject stale command
parameters by themselves; controller validation remains mandatory. A future
host can send the DTO to its authenticated current player. Full client/model
separation remains later work.

Hand and table click handlers and context menus now validate indices through
`SelectionSnapshot.contains` and synchronize from that snapshot. Context menus
no longer inspect real hand/table collections for bounds checks. Drag checks
already delegate to shared core availability. Layout/rule flags are still read
locally; no claim is made that these UI components can operate remotely yet.
Tests verify valid toggling, repeated context selection, retained move targets
and rejection of invalid indices without needing a client-side card collection.
