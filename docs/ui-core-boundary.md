# UI/core boundary audit

Optional whole-pile take: allow_take_whole_personal_pile defaults to False under
Personal piles, requiring table/personal piles. Session take_whole_personal_pile
accepts owner/pile_index and validates access and nonempty source before moving
the entire pile into the current hand in stored order. Received cards retain
normal hand visibility and are not marked revealed. Logs/results contain only
source/count, with one Undo/checkpoint. GUI uses immutable accessible pile options
shared with transfer, guards turn changes and revalidates on execution. CLI
take-pile shares the action; old single top-card behavior remains available.
Preset/save/legacy/restart, rollback, privacy and both native Tk layouts are covered.

Optional whole-pile transfer: allow_transfer_personal_piles defaults to False
under Personal piles, requiring table/personal piles. Core transfer_personal_pile
validates both indices, actor access, nonempty source, different destination and
active recipient before mutation. It preserves group order, honors destination
top/bottom time placement and rejects size-order conflicts without reordering.
Personal cards currently store names only; no face-state field is introduced.
Immutable options expose names/counts only; public logs contain no card values.
Session owns one Undo/checkpoint. GUI guards turn changes and revalidates on
execution; CLI transfer-pile uses the same action. Preset/save/legacy/restart,
rollback, access, order and both native Tk layouts are covered.

Optional batch draw: allow_draw_multiple_cards defaults to False under Special
actions and requires the parent feature. Session draw_cards accepts a positive
integer count, validates deck capacity before drawing and uses the single-card
draw path for identical order, private logging and per-turn draw counts. One
batch has one Undo/checkpoint; failures roll back the entire draw. GUI asks for
a count from a core status snapshot, then executes through shared availability.
Both layouts support it without hand selection; CLI draw-many shares the action.
Preset/save/legacy/restart, privacy, cancellation, stale-rule revalidation and
native Tk controls are covered.

Optional draw shuffle: allow_shuffle_draw_deck defaults to False under Special
actions and requires the parent feature. Core shuffle_draw_deck checks shared
availability, requires at least two remaining draw cards and no pending approval,
then shuffles only that list. Public event/log data contains no card identities
or order. Session execution provides one Undo/checkpoint, including when the
random permutation happens to match the previous order. GUI has a normal button
and a contextual Special actions menu independent of hand selection. CLI shuffle
shares the command; presets, saves, legacy defaults and restart retain the rule.
Native Tk checks cover setting, both layouts, Undo and one-card availability.

Optional batch table discard: allow_discard_multiple_table_cards defaults to
False under Table / Table actions, requiring table, discard and single-table
discard rules. Session discard_table_cards validates distinct zero-based
card_indices and pile_index/personal before removal, then uses existing table
discard semantics in one Undo/checkpoint transaction. Remaining positions stay
unchanged. GUI reuses table projections, stale-table guards and core destination
options. Face-down cards stay hidden until discarded. CLI discard-table-many
shares the same command. Preset/save/legacy/restart, rollback and both native
Tk layouts are covered.

Optional batch take: allow_take_multiple_cards defaults to False under Table /
Table actions, requiring allow_take_from_table. Session take_table_cards accepts
distinct zero-based card_indices into the shared table and validates all before
removal. Existing take behavior appends in table order in one Undo/checkpoint.
Batch index validation is shared with hand batches. GUI selects from table
projections and guards table revisions; face-down identities remain hidden.
Single and batch take logs now omit face-down identities. CLI take-many shares
the command; --take-multiple-cards enables both taking flags for new games.
Preset/save/legacy/restart, rollback and both native Tk layouts are covered.

Optional batch give: interaction_options.give_cards defaults to False and is
configured alongside other Player interactions. Session give_cards accepts a
target and distinct zero-based card_indices; core validates both before removal,
then appends cards in hand order in one Undo/checkpoint transaction. Sender
revealed indices are maintained; received cards are not marked revealed.
Public history/log output contains recipient and count only. GUI uses existing
interaction target options and shared batch selection with stale-hand checks;
execution revalidates the recipient. CLI give-many uses the same command and
never prints private action values. Preset/save/legacy/restart, rollback,
privacy and both native Tk interaction flows are covered.

Optional batch discard: allow_discard_multiple_cards defaults to False under
Discard pile. Session discard_cards accepts card_indices plus pile_index and
personal, validates the complete selection and destination before removal, and
uses existing single-card discard/log behavior in one Undo/checkpoint transaction.
Shared batch index validation is core-owned. GUI shares the batch selector with
play, uses immutable discard destination options, and guards stale hands. CLI
discard-many shared|personal PILE CARD CARD uses the same command. Preset, save,
legacy, restart, rollback and both native Tk layouts are covered.

Optional batch play: allow_play_multiple_cards defaults to False, under Table /
Table actions. Session play_cards accepts distinct zero-based card_indices,
sorts them into hand order, plans every automatic table position on a private
table copy, then plays the group face up in one transaction. Invalid selection
or insufficient space leaves all game state untouched. Unexpected execution
failure rolls back the entire batch. Revealed indices, Undo, checkpoint and
selection revision handling reuse existing mechanisms. GUI provides an extended
selection dialog built from player projections, guards stale hand revisions,
and supports both layouts. CLI play-many uses the same action. Presets, saves,
legacy defaults and restart are covered, alongside native Tk dialog checks.

Optional skip confirmation: confirm_skip is an application preference in Basic
Settings, default False, preserved across preset loads. The shared app handoff
controller holds a skip confirmation phase without mutating the game. GUI asks
yes/no; CLI exposes --confirm-skip and confirm-skip/cancel. Acceptance either
executes the existing skip transaction or enters the optional privacy handoff.
Ready cannot bypass skip confirmation. Cancellation, blocked commands and
revalidation are covered; successful execution retains one Undo/checkpoint.

Optional skip: allow_skip_next_player defaults to False under Turn order. Core
end_turn accepts skip_next=True, mutually exclusive with a manual destination.
Availability requires at least two active players and the usual turn checks.
Both clients defer the same command behind the optional hotseat curtain and
revalidate on ready. Traversal follows current direction and ignores departed
players. Crossing the seat boundary on either step ends the round exactly once.
Skip logs the affected player and shares one Undo/checkpoint with end turn.
Presets, saves, legacy defaults and restart preserve the configurable rule.
Native Tk checks cover setting, both layouts, cancellation, ready and Undo.

Optional reverse turns: allow_reverse_turn_order defaults to False under Turn
order. The core reverse_turn_order action validates availability and changes
turn_direction (1/-1) without advancing the player. Automatic turns skip departed
players in either direction; only crossing the seat boundary ends a round.
Explicit handoff leaves direction unchanged. Saves and Undo preserve direction;
legacy saves default to forward, restart preserves the rule and resets direction.
GUI controls (including contextual layout), status projection and CLI reverse
share the core action and transaction. Presets and CLI --reverse-turn-order
configure the rule. Native Tk checks cover setting, both layouts, next and Undo.

Optional manual turns: allow_choose_next_player is a game rule under Turn order
(default False), persisted in presets/saves and preserved by restart. Core
turnorder validates active targets and supplies immutable choices. Session
end_turn accepts a zero-based next_player; ordinary calls keep automatic order.
Explicit targets, including the current player, never end a round or clear the
table. Normal automatic seat-wrap cleanup is unchanged. GUI Pass turn to… and
CLI end PLAYER use the same command, log and Undo/checkpoint transaction.
The shared hotseat controller checks the target before deferring and execution
revalidates it when ready. Tests cover malformed/disabled/departed targets,
pending decisions, same-player/lower-index handoff, cleanup semantics, snapshots,
preset/save/legacy/restart, CLI and deferred target changes. A temporary native
Tk probe verified the setting/category, cancellation, optional curtain and
one successful Undo/checkpoint. The enabled rule appears in the rules overview.

Hotseat handoff: confirm_next_turn is an application preference (default False),
offered in Basic Settings and preserved across preset loads. Next Turn checks
availability, then the client hides the entire game/options area before any
turn mutation. A ready button executes the existing end-turn transaction with
turn-start decisions while still covered, then reveals the refreshed screen.
Cancellation does not advance or checkpoint. Execution revalidates; refusal
keeps the curtain and valid selection until retry/cancel. This is transient client
state, not a new core confirmation or saved-session rule. Tests cover privacy
sequencing, cancel/reentry, changed availability, grouped score/pot approvals,
Undo/checkpoint counts and preference handling. A temporary native Tk probe
verified hidden pack managers and normal restore, plus the disabled-option path.

Handoff orchestration now lives in app.turnhandoff.TurnHandoffController, reused
by the GUI curtain and CLI. It owns pending/completing state, request/confirm/
cancel results and deferred execution; the callback retains each client's
existing transaction/turn-start behavior. CLI --confirm-next-turn adds end →
ready/cancel, suppresses new state/commands while pending and reports stable
handoff codes in JSON. It does not clear terminal history. Tests cover both
client flows, changed availability, cancellation, duplicate requests/ready,
score-vote ordering and CLI subprocesses without Tkinter. A native Tk probe
verified shared-state synchronization with the actual curtain and Undo/checkpoint.

Settings failure recovery (2026-11-21): application settings now serialize before
an atomic temporary-file replacement; partial-write/replacement failures preserve
the previous file. Startup uses load_settings_result to retain readable/default
settings if persistence fails and displays one warning after opening the menu.
The legacy load_settings API retains exception propagation. Tests cover partial
output, replacement denial, serialization failure, default fallback without a
writable config directory and MainMenu starting a game after write failure.
A temporary native Tk probe passed the same startup/new-game recovery using
isolated settings/saves; it was removed. This does not promise recovery from
unrelated save-library directory failures.

## Current assessment — 2026-11-20

The local hotseat core and extracted application services can run without
Tkinter. Named action execution, transaction/Undo/checkpoint behavior, player
projections, turn-start decisions, saves, deck-library operations, presets and
settings application/default restoration have independent entry points. The
latest full suite passed 505 tests; native Tk probes for session, deck and preset
lifecycles are recorded below. This audit changes documentation only and does
not claim a new exhaustive native/manual test run.

A replacement local client is feasible using these entry points. The present
Tk client still owns a Game and invokes queries directly; there is no complete
client-neutral facade. That alone is not a blocker for replacing widgets. The
remaining work should address concrete duplicated interpretation rather than
wrap every model field or introduce a network protocol in advance.

### Prioritized next changes

| Priority | Evidence and impact | Small next commit and acceptance criteria |
| --- | --- | --- |
| 1. Action-result migration — completed | Card, turn, score, player lifecycle and chip handlers preserve ActionResult. The final chip callers migrated and ui/sessionactions.py was removed. Valid selection is retained on failure; stale sources still clear through synchronization. | Regression tests cover failure messages/codes, valid effects, cancellation, one refresh/checkpoint/Undo and restored state. Hand/table drop tests route through CardDrag.drop, the GUI transaction and actual handlers. |
| 2. Score/leave control availability — completed | `update_point_button` and `update_leave_button` now refresh their actions through the same mapping/core availability used by full refresh. Reduce-score rules and pending confirmations are no longer approximated in these helpers. | Tests cover rule changes, pending approvals, all-left/return/Undo and temporary dialog blocking. Broader turn-button resets and Undo/return-specific queries remain separate scope. Execution continues revalidating every command. |
| 3. Prepare only the capabilities a replacement client needs | `ui/gameguibuilder.py`, context menus and SpecialActionsUI construct controls from rule flags; `GameGUI` installs the checkpoint callback and renders game_log directly. These local reads work today but tie this client to the Game shape. | Once the replacement UI's first screen is chosen, define its minimal capability/log/lifecycle input and reuse the existing projections. Convert one screen or menu group per commit. Do not add a copy of every flag or a broad facade before a concrete consumer exists. |

The first bounded result-handling and score/leave availability changes are
complete without a persistence-format change. Capability preparation (row 3)
should be driven by a concrete replacement screen; other card handlers can
migrate to ActionResult in independent small commits when needed.

Table take/move handlers now also return ActionResult and display its failure
message, preserving still-valid selection on refusal. Success retains existing
selection clearing and outer transaction/refresh behavior. Regression tests
cover disabled actions, occupied destinations, valid take/move/sequence moves,
single checkpoint/Undo/refresh, and CardDrag.drop routing for both single cards
and sequences. This extends result preservation without changing drag targeting
or the core movement rules.

Table flip, discard recycling and manual table cleanup handlers now also return
ActionResult directly. Refusal displays the core message, preserves still-valid
selection and does not create Undo/checkpoints. Cleanup now reports a refusal
instead of silently clearing selection. Success retains existing selection
behavior and a single outer refresh/checkpoint/Undo step. Regression tests
verify disabled actions, non-empty draw deck, flip visibility, recycling content,
cleanup destination and Undo restoration. Core rule/execution behavior is
unchanged.

Draw, end-turn and point-request helpers now also preserve ActionResult and
display its failure message. End-turn clears hand selection and invokes its
turn-start callback only on success; an unsuccessful result is no longer
unpacked as a successful tuple. Tests cover pending-confirmation rejection,
empty deck, disabled scoring, valid effects, preserved valid selection/state,
no failed-action checkpoint/Undo, callback ordering and one successful outer
refresh/checkpoint/Undo.

Discard drawing now preserves ActionResult through the direct, pile-choice and
card-choice paths. Failure displays the core message and leaves valid hand
selection unchanged; success clears it. Dialog cancellation still returns None,
and existing close-after-submission behavior remains. Regression tests cover
top/any modes, shared/personal sources, one checkpoint/Undo/refresh and an offered
card removed before submission. A temporary native Tk probe verified both modal
paths return success/failure results; it was removed afterward. This reuses the
existing index/top-card revalidation, not a new revision/concurrency mechanism.
`ui/cardactions.py` no longer uses execute_value.

Player leave/return handlers now execute through SessionController and preserve
ActionResult. Leave returns its result from the GUI transaction; the return
dialog's submit callback returns it too (the asynchronous dialog-opening method
does not wait for a result). Failure displays the core message without clearing
valid hand selection or starting turn handling. A failed return leaves its
dialog open; success retains existing close/turn behavior. Tests cover disabled
leave, stale return choices, the last active player, successful Undo/checkpoint/
refresh counts and failure state preservation.

Hand flip and score reduction now also return ActionResult and display the core
failure message. Tests verify valid hand selection/state on refusal, flip reveal,
immediate reduction and confirmation-request reduction, plus one successful
refresh/checkpoint/Undo and full Undo restoration. GameGUIActions no longer
imports execute_value.

The final adapter callers in ChipBankUI now execute via SessionController and
return ActionResult through the existing transaction decorator. Purchase errors
retain the core message, as do bets and pot requests. Canceled dialogs and
preflight-blocked actions still return None without executing a command. Tests
cover purchase/bet/pot success, confirmation-required withdrawal, typed failures,
selection/state preservation, one checkpoint/Undo/refresh and cancellation.
No execute_value/sessionactions references remain in application code or tests,
so the unused compatibility module was removed.

The post-migration integration regression now links GUI point/pot requests,
blocked end-turn handling, grouped approval decisions and persisted Undo state.
A temporary native Tk probe passed actual GameGUI widgets across refused and
successful card/chip actions, automatic hand drop onto an occupied table,
dialog blocking, grouped score/pot decisions, Undo and player leave/return.
It checked exact core failure messages, retained valid selection, no rejected
action Undo/checkpoint and one successful transaction Undo/checkpoint, plus
restored score/leave control states. Checkpoint counts were observed via a
callback rather than real autosave writes. Probe files/windows were removed.
No application-code fix was needed. This is targeted automated native GUI
verification, not exhaustive manual testing of all settings/modes.

`SessionController.undo_availability()` now exposes immutable ActionAvailability
without revealing the Undo stack: disabled rules return action_disabled, empty
history returns empty_undo, otherwise Undo is allowed. The GUI Undo button uses
this query rather than game.undo_stack. Session undo rechecks availability and
retains its bool result and model-side guard. Tests cover read-only snapshots,
availability changes before execution, no checkpoint/history mutation on refusal,
successful restoration/checkpoint, GUI state transitions and headless import/use.

`SessionController.undo_result()` now returns ActionResult, revalidates current
availability and resets stale checkpoint errors. Refusal carries the availability
code/message; success carries changed=True and any checkpoint error without
exposing restored private history. The existing undo() delegates and retains its
bool API. GUI uses the structured result, displays refusal and updates selection/
turn UI only on success. CLI emits the core result fields (empty_undo replaces
its former client-only nothing_to_undo code); text mode also reports checkpoint
failure. A failed checkpoint does not convert successful Undo into a refusal.
Tests cover state restoration, refusal without side effects, stale errors,
checkpoint failure and both clients.

`checkpoint_result()` now wraps the existing checkpoint operation in ActionResult:
success or checkpoint_failed with message/checkpoint_error. changed remains False
because this is persistence, not a gameplay action; existing failure log/history
entries remain observable. No callback is still a successful no-op, as before.
The original checkpoint() error-string/None API remains for automatic action/
Undo paths. The GUI checkpoint wrapper returns the new result after capturing
view state and rendering the existing log, without adding modal dialogs (the
wrapper is also used at initialization/exit). Tests cover callback success,
returned errors/exceptions, stale-error reset, no new Undo and GUI propagation.

`SessionController.log_snapshot()` now returns an ordered tuple of existing
public log text, independent of the mutable game_log list. GameGUI.render_log
reads one snapshot and no longer accesses that list. Tests verify snapshot
independence/order, Undo restoration, checkpoint failure messages, empty/full
rendering without model access and headless use. Log formatting, save/Undo
contents and existing public/private message rules are unchanged; this is not
a new remote-log authorization or filtering protocol.

`tests/test_uistateboundary.py` scans every Python module under portable_deck/ui
and rejects attribute access to game_log, legacy gui_log and undo_stack, including
writes/deletes and literal getattr/setattr/delattr/hasattr calls. Diagnostics
name the replacement session APIs. Guard fixtures verify deferred accesses and
allow show_game_log, comments, text and public queries. This static guard does
not infer arbitrary computed attribute names or general data flow. Application
storage/core implementations remain outside its intentionally narrow UI scope.
No application-code change was needed.

`SessionController.end_turn_availability()` now supplies immutable availability
for advancing the turn. Both execute(end_turn) and the GUI Next turn mapping
use it, including tooltip/selected-action queries and the lifecycle control
refresh. Existing semantics remain: the requester may advance, voters must
complete pending score/pot decisions, and no active players blocks advancement.
Temporary dialog blocking remains. Tests verify query/command agreement without
mutation/checkpoints on refusal, pending votes, all-left/return/Undo transitions,
GUI state/reasons and headless use.

`SessionController.return_player_options()` now exposes the existing immutable
return choices/availability to clients. The GUI dialog and Return player button
mapping/tooltip use the same query, refreshed with lifecycle controls. No departed
players, disabled return or pending score/pot requests disable the button;
all-players-left does not, so return remains possible. Execution still rechecks
the shared model reason. Tests cover these transitions, immutable prior options,
return/Undo, state/reason agreement and headless use. Dialog submission tests
continue covering stale choices without premature selection/turn changes.

A combined lifecycle-control regression now drives the actual GUI transaction,
turn-start and Undo methods together, checking Next turn/Undo/Return player
against controller availability after every stage. A temporary native Tk probe
also passed empty Undo, concurrent score/pot requests, disabled controls during
dialogs, grouped decisions, Undo restoring pending requests, all players leaving,
return through the actual button/dialog and Undo back to all-left. No manual
state reset overrode the final controller result. No application-code fix was
needed; probe files/windows were removed. Checkpoints used a callback stub and
no user files were written. This was targeted automated GUI verification.

### Reads and responsibilities that can stay in the client

The persistence dependency migration removed Game.save_session, Game.load_session
and Game.save_discard_pile after repository-wide caller inspection found only
tests still using them. Tests now call app.sessionstorage/app.discardstorage;
application clients already did. External Python callers must migrate to
save_session(game, path), load_session(Game, path) and save_discard_pile(game,
path) respectively. Saved JSON and GUI/CLI behavior are unchanged. Core AST
import checks now reject ordinary app/UI/Tk imports even inside functions, and
the existing clean-process core query test also checks no app/UI modules load.

A separate standalone-core lifecycle regression now actively blocks app/UI/CLI/
Tkinter imports in a clean process, recording even caught attempts. It constructs
a deck in memory with a nonexistent source path, blocks file opening, then runs
configured creation/start, cards, score/pot requests, in-memory checkpoints,
JSON data round trip, blocked end-turn, approvals/rejection, structured Undo,
player/log queries and restart with retained scores. It verifies source-state
independence and no files in the temporary working directory. All steps passed
without application-code changes. File-storage behavior remains covered by the
application-service tests; this regression exercises core data serialization.

- Tk widget/layout construction, dialog presentation and consent, selection,
  drag feedback, zoom/scroll and form text conversion are client work.
- Names, current-player IDs and rule flags read for display/control construction
  are not equivalent to duplicating game rules or mutating authoritative cards.
  Remove a read only when an existing projection or concrete client input fits.
- `MainMenu` may orchestrate starting/loading/restarting a local Game through
  services. Persistence belongs to application services; the former Game
  persistence compatibility delegates have now been removed.
- Deck editor comma/newline parsing and loading remain widget-oriented. They
  need extraction only if another editor/client will reuse that representation.

### Separate future online milestone

Player projections and action codes do not provide actor authentication,
authorization for remote callers, revision/concurrency control, transport or
private-result filtering. Full save data, internal history and raw ActionResult
values/events must not be treated as a broadcast payload. These concerns should
be designed for the actual hosting/session model, independently of the local
Tk replacement. Core import checks now prohibit dependencies on application
and GUI modules, including function-local ordinary imports.

## Implementation evidence and earlier audits

`tests/test_appboundary.py` protects the 17 explicitly extracted application
service modules. AST inspection checks ordinary absolute/relative imports,
including function-local imports, against Tkinter, `portable_deck.ui` and app
modules outside the service set. A separate clean process imports every service
with GUI dependencies actively blocked, also checking that import creates no
files in its temporary working directory. New extracted services must be added
to this explicit set. Existing per-feature headless behavior tests remain;
the boundary check supplements them rather than claiming to exercise every
deferred/dynamic execution path. No application-code change was required.

Score/pot confirmation inputs now share strict boolean validation in the model.
Available confirmation commands with missing/non-boolean `approved` values
return `invalid_confirmation`; direct model calls raise the corresponding
`ActionValidationError`. Availability still takes precedence when no vote is
required. Invalid decisions leave state, Undo, events and checkpoints unchanged.
True/False approvals retain existing effects and can be undone.

`Game.request_point(delta)` also validates the score change before any effects
or option checks: only integer -1/1 are accepted, excluding booleans and floats.
Invalid values raise `ActionValidationError` (`invalid_score_change`) and leave
direct/transactional calls, Undo and checkpoints untouched. Named controller
actions still supply fixed +1/-1 values; no new command parameter was added.
Tests cover valid changes with/without confirmation, Undo and disabled reduction.

Hand removal now validates integer type (excluding bool) and one-based range in
`Player.play_card` before changing revealed indices or popping a card. Invalid
direct model inputs return None, preserving the existing refusal contract.
Controller play commands retain zero-based indices and `invalid_selection`.
Regression coverage includes hand/reveal preservation, direct table placement,
normal/positioned/face-down controller play, checkpoints and valid Undo. Other
actions using Player.play_card inherit the same guard.

Table-card take, flip, move (including sequences), swap and discard now share
`_valid_table_card_index`: zero-based in-range integers excluding bool. Invalid
direct calls return None before any effect, including hand removal during swap.
Controller commands preserve `invalid_selection`. Regression tests cover direct
and controller failures, unchanged hand/reveal/table/log/Undo/checkpoints, and
successful operations with Undo, including sequence movement.

Hand/table discards resolve the destination with `core.discardvalidation`
before removing a source card. It validates enabled discard, an integer
non-boolean pile index, boolean personal/shared selection and existing range.
Empty destinations remain valid; missing destinations return None. Direct
model calls retain None on refusal, while available controller actions return
`invalid_pile`. Regression tests verify source/reveal/log/Undo/checkpoint
preservation for malformed targets and successful shared/personal transfers
with Undo. Table discard now also respects disabled discard on direct calls.

Special-action insertion audit found that hand index, destination and insertion
position already validate before source removal, and random middle-position
selection happens only after validation. No application-code change was needed.
Expanded regression tests cover malformed direct/controller inputs, hand/reveal
and log preservation, no Undo/checkpoint/events and no random selection on
rejection. Existing top/bottom/middle position and successful Undo tests remain.
Invalid selections retain `invalid_selection`; other malformed insertion
parameters currently retain `invalid_parameters`.

Personal-pile access now validates owner/pile/viewer integer types (excluding
bool) and ranges before looking up settings or evaluating access rules. Invalid
queries return False and direct play/take calls return None before moving cards.
This also rejects invalid viewers for public piles. Existing owner/team/dealer,
departure and feature checks remain. Tests cover malformed direct targets and
viewers, controller refusal without Undo/checkpoints, plus existing permission,
ordering, valid-transfer and Undo regressions.

The final card-index audit found existing pre-mutation type/range validation
in hand flipping and discard draws. No application-code fix was required.
Regression tests now cover malformed inputs through direct core helpers and
controller commands, preserving hand/reveal/pile/log state with no Undo or
checkpoint. Draw tests include shared/all-source indices, empty sources,
top-only restrictions and top/any modes. Valid hand reveal/hide and shared or
personal-source draws retain their existing effects and Undo. This closes the
scoped card-input audit; broader rule authorization and remote-client security
remain separate work.

The three-player lifecycle regression now covers draw, face-down play, concurrent
score/pot requests, first-voter approvals, saving pending decisions, loading into
the CLI, blocking premature actions, final approvals, persisted Undo, reloading
that Undo state, denial and return to the first player's turn. Player-view
serialization still omits hidden identities, internal history and draw order.

A separate probe using actual Tk widgets and scripted dialog answers passed
actions, first-voter approvals, checkpoint/load, final approval/denial, Undo and
alternate decisions. Probe files and checkpoint files were temporary. This was
automated Tk execution, not exhaustive manual testing of every settings/editor
flow. This original audit passed all 223 tests; no application-code fix was required.

The subsequent persistence integration audit uses application new-game,
named-save, checkpoint and load services. It removes the original deck file,
restores game/view and checkpoint state, runs persisted Undo through a separate
headless CLI process without overwriting its input save, and restarts using the
embedded definition. The pending-confirmation lifecycle regression also now
uses application storage rather than Game compatibility wrappers.

A temporary native Tk probe passed actions, checkpointing, named save/load,
table zoom restoration, GUI Undo and restart without the source deck. Opening
the restored GUI acknowledges turn notifications as designed; gameplay state is
preserved. The probe used a hidden window and temporary files, which were
removed. All 272 tests passed; no application-code change was necessary.

### Subsystem status and supporting detail

| Area | Current evidence | Next bounded step |
| --- | --- | --- |
| Save application services | Checkpoints, named writes, rename/delete and metadata catalog reads now use headless application services. `SessionBrowser` renders entries and collects user decisions. | Basic save management is separated; add services only for concrete new client needs. |
| Deck library | Catalog, import/export and editor validation/atomic writes use services without Tkinter. | Editor text parsing/loading still lives in GUI; separate it for concrete client reuse. |
| Presets | `load_preset` returns settings/compatibility/notices; `save_preset` returns validated settings with saved configuration metadata after atomic writing. Legacy read/write entry points remain. | Keep existing recovery/player-count policies; separate further operations only where GUI still owns reusable logic. |
| Deck capacity check | `app.deckcheck` loads/resolves the deck; `core.deckcapacity` supplies shared input limits and immutable counts. GUI only collects fields/displays results. | New-game validation uses the same counts/limits; no separate GUI capacity policy. |
| Chip input data | `core/chipoptions.py` now supplies immutable players/accounts, amount bounds, pot and availability to chip controls/dialogs. | Input separation is complete; retain execution revalidation as clients evolve. |
| Client lifecycle/capabilities | GUI/CLI new games and model restart share core construction/start operations. `GameGUI` still owns Game and client state; widget construction reads rule flags. | Define a broader client facade only for concrete replacement-client needs; do not add a snapshot per widget flag. |
| Structured result completeness | Stable codes exist, but some model failures still use generic fallbacks. Internal ActionResult events may contain private authoritative data. | Extend typed failures per feature as clients need them; do not broadcast raw results/history to remote clients. |

Save services and chip dialog inputs are now separated. Remaining local-client
work concerns lifecycle/capabilities and result completeness, rather than card
interaction or drag-and-drop. Authentication, actor authorization, revision checks, transport
and concurrency remain a future online milestone, separate from replacing the
local GUI. Existing player snapshots alone do not implement those guarantees.

The sections below retain original findings and implementation notes. The
prioritized next work is the current assessment at the beginning of this file;
test counts attached to older probes describe those runs.

Deck catalog loading is now owned by `app.deckcatalog.list_decks`, with the
existing case-insensitive JSON filename ordering, deck validation and invalid
rows retained. Missing directories return an empty tuple without writes;
directory enumeration failures propagate, while per-entry failures become error
entries. Opening DeckLibrary still creates its working directory. GUI refresh
only formats metadata and restores the selected filename. Selection validation
and editor operations are unchanged. Tests cover Unicode,
counts/duplicates, immutability, invalid JSON/schema/encoding, listing failures,
GUI row/selection rendering and use in a process without Tkinter.

`app.deckfiles` now owns import/export source validation, destination extension,
same-file rejection (including filesystem aliases), overwrite enforcement and
copying. Import preflight prepares a target for GUI overwrite consent; execution
revalidates the source. Export retains the native save dialog's overwrite
consent. GUI collects paths/consent, displays errors and updates the selection
only after successful import. Services raise InvalidDeckError, SameDeckFileError
or filesystem errors; no widgets are imported. Copies retain source bytes and
metadata via copy2, with the existing non-atomic write behavior. Tests cover
extensions, exact copies, invalid/changed source, explicit overwrite, same file,
IO failures, canceled/declined GUI paths, success callbacks and headless use.

`app.deckstorage.prepare_deck_definition` copies and validates editor data;
`save_deck_definition` revalidates, enforces explicit overwrite and atomically
writes UTF-8 JSON with existing indentation, Unicode and trailing newline.
Failed filesystem operations clean up the temporary file where possible and
propagate errors. DeckBuilder retains widget parsing, field-specific prompts,
path dialogs and overwrite consent, then calls storage. New, edit and duplicate
flows preserve callbacks/closing only after success. Tests cover independent
prepared data, file format, invalid definitions, overwrite, failed replacement,
temporary-file cleanup, GUI cancellation/failure/success and headless use.

The deck lifecycle integration regression now chains definition creation,
editing, duplication, export/import, catalog reads and application new-game
creation. Editing/removing the external source leaves an existing game's
definition/state unchanged; session load, Undo and restart retain that original
definition. A temporary native Tk probe also passed real editor/library widgets,
scripted save/edit confirmations, canceled dialogs, callback/selection updates,
transfers and starting a game from the selected import. Probe files/windows
were removed. This is automated GUI verification, not an exhaustive manual
review. No application-code fix was needed.

Preset loading was already largely implemented without Tkinter in
`settingspresets.read_preset`. The new `load_preset` entry point returns a
PresetLoadResult (independent mutable settings, immutable notice tuple and
compatibility report) without calling presentation callbacks or emitting Python
warnings. SettingsWindow now displays the returned notices after successful
loading and then rebuilds its form. Existing read_preset delegates and retains
callback/warnings behavior. Recovery, nested-option filtering, current app
preferences/player count, team adjustment, configuration baseline and legacy
file shapes are unchanged. Tests cover returned notices, adapter equivalence,
input independence, GUI application/cancellation/failure and headless loading.

Preset saving now returns independent validated settings with configuration
name/baseline from `save_preset` after successful atomic replacement. GUI only
collects the destination, applies returned settings and displays success; it no
longer prepares configuration metadata itself. `write_preset` delegates while
preserving its no-result API. Stored preset shape and exclusion of application
preferences/metadata are unchanged. Tests cover initial unmodified status,
later rule-change detection, preserved app preferences, input independence,
failed replacement/cleanup and GUI success/cancellation/failure.

The preset lifecycle integration test now chains save, load with changed current
preferences/player count, legacy-option recovery and new-game creation. It
checks configuration baseline/modified status before and after a rule edit.
A temporary native Tk probe passed the same flow through actual settings form
buttons/variables, including legacy warning display and canceled loading. It
preserved current player count, Undo/autosave preferences and game rules, then
created a game with modified configuration metadata. The probe used temporary
presets and intercepted application-settings persistence; no user configuration
was written. Probe files/windows were removed. No application-code fix was
needed; this was automated GUI verification rather than exhaustive manual QA.

`SettingsWindow.check_deck` now calls `app.deckcheck.check_deck`, which resolves
project-relative paths, validates player/hand counts and loads the deck without
shuffling, dealing or writing. `core.deckcapacity` returns immutable counts and
the sufficient flag; new-game settings validation shares these rules/calculation
while retaining SettingsValidationError field reporting. Check deck now also
rejects more than 20 players, matching application new-game limits. GUI retains
numeric field parsing and existing success/warning/error dialogs. Tests compare
capacity with actual new-game acceptance at exact/insufficient/zero-hand limits,
reject malformed inputs/files, verify dialogs and run headlessly.

`app.settingsapplication.prepare_settings` validates form values and independently
copies the current configuration name/baseline. `apply_settings` also writes
current application settings before returning. SettingsWriteError distinguishes
file-write failure from validation/deck-read failure, preserving GUI error
titles. SettingsWindow only collects fields, chooses apply versus named-preset
preparation, and updates form/menu after success. Named preparation does not
write current settings. No game is started. Existing settings-file format/write
behavior is unchanged. Tests cover
real temporary settings persistence, independent inputs/metadata, validation and
IO errors, unchanged form/menu on failure, named/use separation and headless use.

Restore Defaults now calls `settingsapplication.restore_default_settings`, which
loads default values and applies the shared validation/persistence pipeline with
the defaults' own configuration metadata. Existing built-in fallback for
missing/unreadable/default JSON files is retained by load_default_settings.
Invalid effective defaults fail validation before writing. GUI retains consent
and errors but replaces active settings/clears the form only after success;
it no longer mutates first or retries load_settings after failure. Tests cover
saved-default persistence/metadata, missing-file fallback, invalid defaults,
cancel/read/write/validation failures and update ordering on success.

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
with `app.sessionstorage.load_session` intentionally restores only the game, not client views.
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
priority 3 now use `build_player_return_options` for immutable IDs, names and
eligibility reasons. The shared `return_player_reason` is used by options,
controller execution and the model. A rejected stale choice leaves the dialog
open and displays its current reason. Tests cover disabled return, empty lists,
pending confirmations, already-returned players and return/Undo when everyone
has departed.

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

### Ordinary-table target display

For ordinary play without positioned placement, player lanes or table movement,
the table projection now exposes only the automatic next-card position. This
prevents rendering surrounding empty slots that reject hand drops. The model's
spatial-position API is unchanged, and movement/positioned modes retain their
targets. Full or disabled tables expose no empty target. Shared availability and
controller checks remain in force. Native Tk mouse-event verification covered
two successive hand drops, each with exactly one displayed empty target.

### Automatic table-surface drops

Ordinary hand drops now accept the whole table area rather than requiring a hit
on the automatic empty slot. Widget hit testing stays in the GUI; the shared
`drop_availability` resolves an ordinary hand drop to `play_card` and the current
automatic target. Occupied cards and blank table space are accepted surface
hits; outside drops cancel. Positioned play/player lanes and table-card movement
still require specific targets. Full tables, confirmations, departed players and
invalid indices remain blocked. Controller validation remains mandatory.
Native Tk mouse-event verification covered blank-table and occupied-card drops,
both resulting in automatic placement.

### Discard normalization follow-up

Priority 5 is addressed: `all_discard_piles` only enumerates existing piles and
preserves collection identities. It still returns live pile references for core
actions; clients should use immutable projections. Session saving no longer
normalizes model fields. Loading and Undo restoration explicitly normalize
legacy/missing discard fields before they can be queried or used by commands.
The existing personal-discard-to-table-pile migration remains supported.

An explicitly configured zero shared piles is preserved when personal discard
piles are enabled. Queries and saving no longer silently add a shared pile.
Tests cover legacy single-pile saves, incomplete old Undo state, personal-only
configurations, draw/Undo and read/save operations preserving pile identities.

### Combined player presentation snapshot

`build_player_session_view` composes status, hands, table, personal piles and
discard browsing into an immutable `PlayerSessionView`. Existing builders remain
the source of visibility and availability rules. The Visible hands dialog is the
first GUI consumer; other components still use individual builders.

Serialization tests verify hidden hand/table identities, draw order and internal
history are absent, while permitted and individually revealed cards remain.
The caller establishes the viewer identity and ensures the model is stable
during construction. This snapshot does not include logs, action results,
notifications, selection state or command authorization and is not a complete
network protocol or a replacement for saves.

### Shared status/personal-pile refresh

`GameGUIActions.refresh_session_panels` builds one combined view and supplies its
status and personal-pile sections to both panels. Initial refresh, action
completion and turn-start/approval refreshes use this path. Renderers accept
supplied snapshots without reading the game; their no-argument refresh methods
remain available for existing individual action helpers. Those helpers may
still perform intermediate panel refreshes before the common final refresh.
Hand/table rendering and drag-and-drop are unchanged in this step.

### Shared hand/table refresh

The common refresh now synchronizes selection first, builds one session view,
and passes its sections to all four main panels (status, personal piles, hand
and table). Hand/table renderers accept prepared sections without querying the
model for card data or synchronizing again. Their no-argument methods preserve
standalone refresh behavior for existing action helpers and selection callbacks.
Availability and execution checks remain independent of rendering.

Tests cover turn changes, Undo and snapshot-only rendering. Native Tk mouse
events verified successive automatic hand drops, a positioned table move and
Undo. Intermediate standalone refreshes in action helpers remain to be removed
in a separate change.

### Action refresh coalescing

Gameplay action helpers now change selection and submit commands without
refreshing panels. The outer `GameGUIActions.run_action` performs the common
panel/log refresh after the session transaction and checkpoint. Nested GUI
actions share that final refresh; chip actions use the same wrapper. Direct
helper callers must use this wrapper to update the interface.

Turn changes without dialogs defer to the final refresh. Score notices and
approval prompts retain a pre-dialog shared refresh so the current player's
state is visible when deciding; a second prompt can require another refresh
after a decision. Standalone initialization and Undo refresh through turn-start
handling. Selection clicks and view interactions keep their independent refresh
paths. Tests cover refresh counts, grouped Undo/checkpoints and error recovery;
native Tk events verified hand/table dragging, Undo, chip status and next turn.

### Core-owned turn entry work

`build_turn_start_view` prepares an immutable current-player work list: score
notices followed by score approval and pot approval, with command identifiers
and structured prompts. Inactive players receive no work. GUI code displays and
acknowledges initial notices, then submits each next decision through the
controller and queries again. It no longer determines approval ordering or
constructs an independent queue from game flags. Rejected decisions display a
reason and stop the loop rather than repeating a stale prompt.

The query is read-only, does not execute actions and does not authenticate a
remote caller. New threshold notices created by approval remain pending for the
next turn-entry notification pass, matching the prior behavior. Tests cover
concurrent pending requests, GUI dialog order, approval/denial, explicit notice
acknowledgment, inactive players and Undo restoration.

### Development CLI client

`python -m portable_deck.cli` exercises the core through a second client. It
constructs or loads Game at startup, uses the combined player presentation view
for `show`, the turn-entry query for ordered prompts and the session controller
for gameplay, acknowledgments and Undo. It does not read player/card collections
or pending-request dictionaries. Card/player command input is one-based and is
translated at the client boundary.

Command output uses public ActionResult messages; internal event/value payloads
are not printed. There is no persistence callback or save command, so loaded
files remain untouched. Tests cover commands, invalid inputs, hidden draw
results, approval order and process execution without Tkinter. This is a local
development hotseat client, not network transport or an authentication layer.

### Stable action rejection codes

Availability branches now produce codes alongside their original display text.
Session execution propagates them into `ActionResult.code`, including lifecycle
codes for absent/required confirmations. Codes are assigned by validation
branches, never inferred from English messages. Unknown actions still raise;
model exceptions and refusals currently use broad fallback codes rather than
pretending every model-level reason has a specialized identifier.

Success (including denial of an approval request) uses an empty code. Checkpoint
errors remain a separate field. Tests exercise empty draws, invalid play
selection/targets, blocked turns, absent confirmations, malformed parameters,
wording-independent propagation and unchanged rejection state/Undo/checkpoints.
This prepares client branching and future translation without changing current
GUI or CLI wording; it does not implement localization.

### Interaction and chip validation codes

Interaction target validation now returns typed failures reused by target
options and model execution. Options include codes for departed/empty targets,
shared chip accounts and unavailable balances. Interaction execution propagates
these through `ActionValidationError`, a ValueError-compatible exception, into
ActionResult without parsing message text. Random discard identifies the lack
of eligible targets separately; stealing distinguishes invalid amount from
insufficient funds.

Chip model methods and session parameter validation use `chip_action_error` for
recipient, amount, minimum-bet and balance checks. Direct model return types
remain compatible. The controller still applies global availability first and
restores failed transactions. Tests cover stale targets, changed balances,
matching target/result codes and rejection without state/Undo/checkpoint changes.

### Client use of rejection codes

CLI `--json` emits typed JSON Lines with stable command codes and public result
messages. It does not serialize raw ActionResult objects, internal events or
private values. Player views and pending notices/prompts have separate record
types; ordinary terminal output remains compatible.

The interaction dialog now refreshes options after execution rejection as well
as before input. It refreshes all rejection types, so unknown future codes do
not leave stale targets/limits behind. The next attempt queries current options
and still executes through the controller. Tests simulate a reduced balance
during modal input and verify the subsequent amount range, plus JSON-line
parsing, process entry, private-result exclusion and unchanged text-mode tests.

### Checkpoint application service

`app.checkpoints.save_checkpoint` is independent of Tkinter and takes the game,
latest path, autosave enabled flag, retention count and optional client metadata.
It returns None or an error string compatible with the session checkpoint
callback. The main menu now only adapts its settings and view metadata.

Retention includes the latest file; unchanged content does not add an archived
version. Decreasing retention also prunes older versions. Atomic session storage
is reused. A failed latest-file replacement preserves the previous
checkpoint; errors archiving or pruning are reported after the latest save may
already have succeeded, matching existing behavior. Tests cover disabled saves,
invalid limits, unchanged content, rotation, metadata, write/cleanup failures
and use from a process that never imports Tkinter.

### Named-save write service

`app.namedsaves` owns reserved checkpoint-path checks, session-number suggestions
and named writes with optional client metadata. It requires an explicit overwrite
flag for existing files and updates the game's named path only after successful
serialization. It raises ordinary filesystem/validation exceptions for clients.
The Tk adapter retains path selection, overwrite consent and message display;
ordinary Save intentionally overwrites the already-associated named file.

Tests cover missing directories, numbering, reserved names/directories,
explicit overwrite, metadata, atomic replacement failures, canceled dialogs,
declined overwrites and standalone use without importing Tkinter. This extraction
does not add a concurrency protocol or change browser rename/delete behavior.

### Session rename/delete service

`app.sessionfiles` now owns filename validation, same-directory renaming,
collision checks and explicitly confirmed single-file deletion. Both source and
destination reject the latest-checkpoint name for rename. Archived autosaves can
still be renamed, and latest/archived autosaves can still be deleted after
confirmation, preserving existing library policy. Nothing recursively deletes
directories. The browser only collects input/confirmation, invokes the service,
shows errors and refreshes after success.

Tests cover unchanged bytes on rename, invalid/reserved names, collisions,
missing files, IO failures, refused deletion, canceled GUI input and service
execution without Tkinter. Read-only session metadata listing remains in the
browser; these file operations do not update an already-open game's associated
save path, matching prior behavior.

### Read-only session catalog

`app.sessioncatalog` prepares immutable SessionEntry records with paths, names,
turn/configuration metadata, timestamps and per-file errors. It lists named
saves or latest-plus-archived checkpoints. The GUI handles formatting, source
selection and list selection, without parsing save JSON or creating directories
while refreshing. Missing folders are empty; directory access failures remain
errors rather than silently appearing empty. Individual corrupt/unreadable
files remain error entries and do not prevent healthy rows from being listed.

This is metadata inspection, not full Game validation or card data projection.
Tests cover ordering, missing archives, malformed JSON/metadata/UTF-8, missing
files, access errors, immutable rows, browser rendering and headless execution.

### Immutable chip dialog inputs

`build_chip_options` composes existing status and availability APIs into player
IDs/names, account references and unique account balances, current bet bounds,
purchase default and pot. Controls and modal purchase/pot dialogs no longer
read live players or model balance/minimum fields. Menu positions map back to
explicit player IDs, so filtered or reordered option lists do not change targets.

Session execution continues to validate current recipients, amounts and rules
after input. Tests cover team accounts, disabled resources, insufficient chips,
confirmation blocking, immutable snapshots and reduced balances during input.
Both purchase and pot dialogs were also exercised with actual Tk widgets and
automated confirmation, without saving or changing any user game.

### GUI-independent new-game creation

`app.newgame.create_game` validates settings, prepares configuration metadata and
starts a game once. `validate_settings_and_game` reuses the game already built
for deck/configuration validation, avoiding a second deck load. The existing
`validate_settings` API still returns only validated settings. MainMenu now
delegates startup and keeps screen transitions/error display in the client.

The service does not persist or mutate input settings. Tests cover single
load/start, card conservation, custom/default names, teams/resources, metadata,
invalid/insufficient decks, menu failure handling and use outside the project
working directory without Tkinter. CLI startup and restart are intentionally
separate follow-ups.

CLI startup now also uses the shared new-game service, mapping command options
to settings without constructing/dealing Game independently. Explicit CLI deck
paths are made absolute at the client boundary to preserve their existing
working-directory interpretation. Loading saved sessions is unchanged. Tests
cover CLI parameter mapping, confirmation defaults, invalid setup and headless
startup with a deck relative to a different working directory. Restart remains
the next separate lifecycle task.

### Shared construction and restart

`core.gamecreation` now owns configured construction and starting, reused by
settings validation/application startup and restart. `Game.restart` is a
compatibility entry point. Restart derives constructor parameters from current
effective game rules (with explicit player-count, deck-definition and name aliases),
not global app settings. Configuration collections are independently copied;
there is no second hand-written list of all constructor options.

Scores/team scores follow `keep_scores`; chip accounts/pot follow the existing
reset setting. New session state clears turns, departures, pending approvals,
cards on the table/piles, revealed cards, notices, history and Undo. Starting
hands and initial log are recreated. Save association/checkpoint callbacks are
not copied. Tests cover restart after load with concurrent pending approvals,
all score/chip policies, preserved names/teams/permissions, independent rules and
headless execution. The source session remains unchanged.

### Session deck portability

The existing `deck_types` and `deck_cards` save fields are authoritative for
loading and restart; `deck_path` is source metadata. `Deck.from_definition`
validates and copies these fields without file access. Restart constructs a
fresh deck from the session definition, rather than reopening its source.
Remaining draw order and Undo remain separate session state. Only legacy saves
with both definition fields absent fall back to the external file; incomplete
or invalid embedded definitions are rejected. Tests cover changed, deleted and
invalid source files, legacy fallback, Undo and independent restart definitions.

### Save data and file storage

`core.gamesession.export_session` returns a deep copy of resumable game data;
`restore_session` copies its input and performs restoration/legacy state
normalization without opening files. Neither operation includes named-save
association or client state. Embedded deck definitions are required at this
boundary. This full private save state is not a player-facing view.

`app.sessionstorage` owns JSON encoding/decoding, atomic replacement/cleanup,
optional client state, named-save association and external-deck resolution for
legacy saves. Former Game compatibility delegates were subsequently removed;
clients use this application service directly. The on-disk shape and
existing GUI/CLI behavior are unchanged. Tests verify a JSON round trip with
file access blocked, pending confirmations, draw order, Undo, independent
mutable state, and the existing storage failure and legacy-save cases.

GUI load/resume calls `app.sessionstorage.load_session_with_view`, returning
the game and separate table view from a single file read. CLI load uses
`app.sessionstorage.load_session` for game state only. Both share restoration,
legacy deck resolution and named-save association. `table_view_from_state`
shares current/legacy metadata decoding with standalone `load_table_view`.
Tests verify one read for both GUI paths, default/invalid/legacy views and Undo.
Named-save, checkpoint and table-view services likewise use
`app.sessionstorage.save_session`, leaving the Game methods as compatibility
entry points only. Cancellation/reserved-path tests assert that the storage
service is not called; the existing round-trip, client-state, retention and
write-failure tests cover the application routes.

### Discard export on exit

`app.discardstorage.save_discard_pile` owns directory creation and UTF-8 JSON
writing of the existing shared-discard list. Desktop exit calls this service
directly when discard is enabled and `save_discard_on_exit` is selected.
The former `Game.save_discard_pile` compatibility delegate was subsequently
removed. Game performs no persistence writes. A canceled/failed requested session save still
prevents export and exit. Discard write errors still show a dialog before the
application closes. Tests cover format/state preservation, both option flags,
cancellation and write failure. This remains a separate export, not a session
save or an atomic replacement.
