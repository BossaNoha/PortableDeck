# Portable Deck

Portable Deck is a Python and Tkinter app for managing cards in tabletop games.
It provides a configurable deck, player hands, a shared table, turn actions,
and save/resume support. It does not enforce rules for a specific card game.

## Run

Use Python 3 with Tkinter available, then start the app from the project folder:

```bash
python main.py
```

On Windows, `py main.py` can be used if the Python launcher is installed.

For hotseat privacy, enable **Hide cards until the next player confirms
(hotseat)** under **Basic Settings**, then use the current settings. Next Turn
hides the game and options before advancing. Pass the device to the next player,
who selects **Start next turn — show cards**. Any score/pot approval prompts run
while the game remains hidden; the refreshed screen is shown afterward.
**Cancel handoff** restores the current player's screen without advancing.
The option is off by default and is an application preference, preserved when
loading presets and applied to new/resumed games; it does not change game rules.

Enable **Game Settings → Personal piles → Allow taking whole personal piles
into hand**, together with personal piles and the table, for **Take whole
personal pile…** (in the contextual **Table** menu). Choose an accessible,
nonempty pile. Its entire contents are appended to your hand in stored pile
order, from bottom to top, without marking received cards revealed. Public logs
show only the source and count. The action has one Undo step and one autosave.
This rule defaults to off, is stored in presets/saves and survives restart.
CLI: `--take-whole-personal-pile` enables the rule and personal piles for new
games; `take-pile 2 1` selects player 2's first pile, subject to access rules.

Enable **Game Settings → Personal piles → Allow transferring whole personal
piles**, together with personal piles and the table, for **Transfer personal
pile…** (in the contextual **Table** menu). Select a nonempty source and a
different destination. You must have access to both; the destination player must
be active. The whole group retains its internal order and is inserted at the
top or bottom according to the destination's time-order rule. A size-ordered
destination accepts the transfer only if its ordering remains valid without
reordering the group. Public logs contain names/counts, not card identities.
The rule defaults to off, is stored in presets/saves and survives restart.
Transfers have one Undo step and one autosave. CLI: `transfer-pile 1 1 2 1`
uses source player/pile and destination player/pile numbers, starting at 1.
`--transfer-personal-piles` enables the rule with two owner-only piles per player
for new CLI games; cross-player access follows the configured rules in loaded games.

Enable **Game Settings → Special actions → Enable special actions** and
**Allow drawing multiple cards at once** for **Draw multiple cards…**, also
available in the contextual **Special actions** menu. Enter a positive whole
number; all requested cards must remain in the draw deck. The batch uses the
same draw order and turn counter as individual draws, with one Undo step and
one autosave. Cancellation or insufficient cards leaves the game unchanged.
Public output never shows the drawn card identities. This rule defaults to off,
is stored in presets/saves and survives restart. CLI: `--draw-multiple-cards`,
then `draw-many 3`.

Enable **Game Settings → Special actions → Enable special actions** and
**Allow shuffling the remaining draw deck** for manual shuffling. Use **Shuffle
draw deck** (in the **Special actions** menu in contextual layout); no hand
selection is needed. Only remaining draw cards are shuffled. Public history and
logs never show their identities or order. At least two cards and no pending
approval are required. One shuffle creates one Undo step and one autosave;
Undo restores the previous order. The rule defaults to off, is stored in presets
and saves and survives restart. CLI: `--shuffle-draw-deck`, then `shuffle`.

Enable **Game Settings → Table → Table actions → Allow discarding multiple table
cards at once**, together with discarding individual table cards, to add
**Discard multiple table cards…**. Select at least two shared table cards with
Ctrl/Shift and one shared or your own personal discard destination. Cards move
in table order; the last selected card becomes the top card. Face-down cards
are unnamed in the selector and become public when discarded, like individual
table discards. The whole batch is validated before removal and creates one
Undo step and one autosave. The rule defaults to off, is stored in presets/saves
and survives restart. CLI: `--discard-multiple-table-cards` enables both table
discard rules for new games; use `discard-table-many shared 1 1 3` or
`discard-table-many personal 1 1 3` (pile/card numbers start at 1).

Enable **Game Settings → Table → Table actions → Allow taking multiple table
cards at once**, together with taking individual table cards, to add
**Take multiple table cards…**. Select at least two shared table cards with
Ctrl/Shift. They are appended to your hand in table order; remaining table
positions stay unchanged. Face-down cards are unnamed in the selector and public
logs. The entire selection is validated before moving any card and creates one
Undo step and one autosave. The rule defaults to off, is stored in presets/saves
and survives restart. CLI: `--take-multiple-cards` enables both taking rules for
new games; `take-many 1 3` uses table card numbers before the batch.

Enable **Game Settings → Player interactions → Enable interactions** and
**Give multiple selected cards to a chosen player** for batch handoff. In
**Player interactions**, choose that action and another active player, then
select at least two cards with Ctrl/Shift. Cards are appended to the recipient's
hand in original hand order; received cards are not marked revealed and follow
the configured hand visibility. Public logs show
only the count and recipient. The entire batch has one Undo step and one
autosave. This interaction defaults to off, is stored in presets/saves and
survives restart. CLI: enable `--give-multiple-cards` for new games and use
`give-many 2 1 3` (player and card numbers start at 1).

Enable **Game Settings → Discard pile → Allow discarding multiple hand cards
at once** to add **Discard multiple cards…**. Select at least two hand cards
with Ctrl/Shift and a shared or your own personal discard pile. Cards move in
hand order; the last selected card becomes the top card. The whole batch is
validated before removal and creates one Undo step and one autosave. The rule
defaults to off, is stored in presets/saves and survives restart. CLI: enable
`--discard-multiple-cards` for new games, then use `discard-many shared 1 1 3`
or `discard-many personal 1 1 3` (pile and card numbers start at 1).

Enable **Game Settings → Table → Table actions → Allow playing multiple hand
cards at once** to add **Play multiple cards…**. Select at least two cards in
the dialog with Ctrl/Shift. The group plays face up in hand order at automatic
positions, using the existing table placement rules. Every card must fit;
otherwise the entire action is rejected. Successful play creates one Undo step
and one autosave. The rule defaults to off, is stored in presets/saves and is
preserved by restart. CLI: enable `--play-multiple-cards` for new games, then
use `play-many 1 3 4` (card numbers refer to the hand before the batch).

Enable **Game Settings → Turn order → Allow skipping the next player** to add
**Skip next player** in the GUI. This optional rule defaults to off. It ends the
current turn and skips one active player in the current direction; departed
players are ignored. With two active players, the current player takes another
turn. With fewer than two, skipping is unavailable. Crossing the seat boundary
on either step ends the round and performs any configured automatic cleanup once.
Skipping supports Undo and the optional hotseat handoff confirmation. The rule
is stored in presets and saves and preserved by restart. In the CLI, enable
`--skip-next-player` for new games and use `skip`.

Enable **Basic Settings → Confirm before skipping a player** for an additional
confirmation before a skip. It defaults to off and is an application preference
preserved when loading presets. Cancelling leaves the current turn unchanged.
With hotseat privacy enabled, accepting the skip opens the handoff screen;
the turn changes only when the next player is ready. In the CLI, use
`--confirm-skip`, then `confirm-skip` to accept or `cancel` to go back.
If `--confirm-next-turn` is also enabled, `ready` is required afterwards.

Enable **Game Settings → Turn order → Allow reversing turn direction** to add
**Reverse turn direction** in the GUI. This optional rule defaults to off. It
changes subsequent automatic turns without ending the current turn, skips
departed players, and supports Undo. The status panel shows the current direction.
An automatic wrap across the seat boundary ends the round in either direction;
manual handoff preserves the direction and does not end the round. Rules and
direction are saved; restart keeps the rule and resets the direction to forward.
In the CLI, enable `--reverse-turn-order` for new games and use `reverse`.

Enable **Game Settings → Turn order → Allow choosing the next player** to add
**Pass turn to…** beside Next Turn. Choose any active player, including the
current player for another turn. Ordinary Next Turn keeps its normal ordering.
A manual pass never ends a round or triggers automatic table cleanup; automatic
Next Turn retains the existing seat-wrap round behavior. The rule is off by
default, belongs to presets/saved sessions, supports Undo and uses the same
optional hotseat handoff. Older sessions default to disabled.

## Development CLI

New games from application settings can be created without Tkinter using
`portable_deck.app.newgame.create_game(values)`. It validates an independent
settings copy, resolves the deck path from the project, prepares configuration
metadata and deals the starting hands once. It returns a started Game or raises
a validation/IO error, without saving or changing the supplied dictionary.
GUI and CLI New game use this service. CLI-relative deck paths retain their
working-directory meaning; application settings resolve relative paths from
the project. Restart uses the same core construction/start operations with the
current session's effective rules, rather than current application settings.
`game.restart(keep_scores=False)` resets cards, turns, confirmations and Undo;
scores are optionally retained, while chip balances/pot follow the existing
`reset_chip_accounts_on_restart` rule. The original session is not modified.

Saves contain the session's deck definition as well as its remaining draw order.
Loading and restarting use this embedded definition without opening the original
deck file. Editing a deck file affects new games only. Older saves without an
embedded definition still require their external deck file.

`core.gamesession.export_session(game)` and `restore_session(Game, data)` convert
between a game and independent save data without file access. JSON files,
atomic writes, legacy external-deck lookup and named-save association belong to
`app.sessionstorage`. Use `save_session(game, path, client_state=...)` and
`load_session(Game, path)` from that module. The former Game persistence
methods have been removed; the save format is unchanged.
GUI load/resume, CLI load, named saves, table-view saves and checkpoints call
the application service directly.
GUI load/resume uses `load_session_with_view(Game, path)` to restore the game
and its separate table view from one file read. CLI still loads game state only.
Discard export on desktop exit uses `app.discardstorage.save_discard_pile`,
preserving the existing JSON list format and save-on-exit setting.

A small hotseat client exercises the shared core without Tkinter:

```bash
python -m portable_deck.cli --players 2 --hand 3
python -m portable_deck.cli --confirmations
python -m portable_deck.cli --load saves/session1.json
python -m portable_deck.cli --json --confirmations
python -m portable_deck.cli --confirm-next-turn
python -m portable_deck.cli --choose-next-player --confirm-next-turn
```

Commands are `show`, `draw`, `play CARD`, `end`, `ready`, `cancel`, `undo`, `pending`, `approve`,
`reject`, `point`, `bet AMOUNT`, `pot PLAYER`, `help` and `quit`. Card and player
numbers start at 1. `show` prints the current player's combined view as JSON;
action output prints public messages without internal events or private draw
results. `pending` displays the next core-ordered approval request. Score notices
are acknowledged after display. `--confirmations` enables score/chip approvals
for a new game; loaded sessions retain their saved rules. EOF also exits.
This development client has no save command or autosave and does not overwrite
a loaded session file. The regular `python main.py` GUI entry point is unchanged.

With `--confirm-next-turn` (also usable with `--load`), `end` requests a handoff
without advancing; `ready` commits the turn and `cancel` leaves it unchanged.
While pending, game commands and `show` are blocked; help/quit remain available.
`ready` is separate from `approve`/`reject` for score/pot votes. JSON results use
`handoff_required`, `handoff_pending`, `handoff_cancelled` and `handoff_not_pending`.
The CLI does not clear the terminal or its scrollback. Both clients share
`app.turnhandoff.TurnHandoffController`, independent of Tkinter/terminal handling.
With the manual-turn rule enabled, `end PLAYER` chooses a one-based player
(for example `end 3`); `end` remains automatic. `--choose-next-player` enables
the rule for new CLI games; loaded games retain their saved rule. With handoff
confirmation enabled, the choice is executed only on `ready` and revalidated.

`--json` switches command-stream output to JSON Lines. Each line has a `type`:
`message`, `result`, `error`, `view`, `notification`, `confirmation` or
`checkpoint_error`. Command results include `action`, `success`, `changed`,
`code`, `message` and, for executed commands, public `messages` and
`checkpoint_error`. Internal event/value payloads are excluded. Local input
errors use `invalid_command`; absent approvals use `confirmation_not_required`.
Score and pot confirmation actions accept only boolean `approved` values;
missing/non-boolean decisions return `invalid_confirmation` without changing
game state, Undo or checkpoints. Direct model calls reject these values too.
`Game.request_point(delta)` accepts only integer `-1` or `1`; invalid values
raise `ActionValidationError` with code `invalid_score_change` before mutation.
`Player.play_card` accepts only in-range one-based integer indices, excluding
booleans/floats. Invalid input returns `None` without changing hand/reveal state.
Controller card indices remain zero-based and retain `invalid_selection` errors.
Table-card take, flip, move, swap and discard operations also reject non-integer
or out-of-range indices before mutation, including direct model calls.
Discarding from hand/table validates the destination before removing a card:
`pile_index` must be an in-range integer excluding bool, and `personal` a bool.
Invalid destinations return `invalid_pile` through the controller or `None`
from direct model calls, preserving the source card and reveal state.
Personal-pile access validates owner, pile and viewer indices as in-range
integers excluding bool before permission checks or card transfers.

`app.deckcatalog.list_decks(directory)` supplies immutable deck-library entries
without Tkinter: filename/path, display name, card count, symbol names and any
read/validation error. Invalid decks remain entries; listing errors propagate.
Missing folders return an empty catalog without creating directories.
`app.deckfiles` handles validated import/export, JSON extension completion and
same-file rejection. Existing destinations require `overwrite=True`; GUI dialogs
collect consent. Transfers revalidate the source immediately before copying.
Deck editor saves use `app.deckstorage` for validated definition preparation
and atomic UTF-8 JSON writes. The editor collects fields and overwrite consent;
storage failures preserve the previous file and keep the editor open.
`app.settingspresets.load_preset` returns prepared settings, compatibility data
and notice text without displaying warnings. Settings GUI displays those notices
and applies the result; `read_preset` retains its legacy warning/callback API.
`save_preset` returns independent validated settings with the saved configuration
name/baseline after successful atomic writing; `write_preset` remains available.
`app.deckcheck.check_deck(path, players, cards_per_player)` returns immutable
available/required card counts without dealing or saving. It shares starting-hand
limits and capacity calculation with new-game validation (1–20 players,
non-negative integer hand size).
`app.settingsapplication` prepares validated form settings with independent
configuration metadata. Applying settings writes them before returning success;
preparing a named preset leaves current application settings untouched.
Restoring defaults uses the same validation/write service and only replaces
active/form settings after success. Missing default files retain built-in fallback.
Current settings are serialized before writing and replaced atomically, so a
failed write/replacement preserves the previous settings file.
Startup uses `load_settings_result()` to retain loaded/default values in memory
and warn if settings cannot be saved. The menu can still open; this does not
guarantee that other application directories are writable.
`tests/test_appboundary.py` guards extracted services against GUI imports,
including function-local imports, and imports them with GUI dependencies blocked
in a clean process. Add newly extracted services to its explicit service set.
`show` emits a structured player view rather than an encoded JSON string.
Argument-parser help/startup errors retain argparse's usual output.

## Main menu

- **New game** starts a new game using the current settings.
- **Resume game** restores the latest automatic checkpoint from `saves/last_session.json`.
- **Load save** opens a session library with player/turn details and actions to load,
  rename, or delete a named save. **Browse…** can open a JSON save elsewhere.
- **Settings** configures player count, starting hand size, deck, optional player
  names, and game actions.
- **Quit** closes the app.

## In a game

Players can draw, discard, play cards onto the table, and end their turn. The
table and action buttons depend on the options enabled in **Settings → Game
Settings → Table settings**. These options include taking table cards, moving
cards to the discard pile, clearing the table, placing cards in table positions,
moving cards between positions, and showing a separate card row in front of each
player. If player rows are enabled, **Play Selected Card** plays in front of the
current player; **Play at Selected Spot** can target another player's row.

In **Game Settings → Discard pile**, enable **Allow drawing from the discard
pile** to add **Take from Discard** during a game. Choose whether the action
always takes the top card or lets the current player choose any card.
Set the number of shared discard piles and the number of personal piles each
player gets. When there is more than one available destination, discarding a
card asks which pile to use. Players can draw from the selected pile; the
"any card" option lists cards across all shared and personal piles.

When enabled, **Play Selected Face Down** places a hidden card on the table and
**Flip Selected Table Card** reveals an eligible one. **Move Selected Table
Card** can move a face-up card together with the cards below it in its column.
**Recycle Discard into Deck** becomes available when the draw deck is empty.

Game Settings also provide general card-handling options for flexible table
layouts: play cards face down and reveal them, move face-up sequences together,
and recycle the discard pile into an empty draw deck. These are individual
actions for custom games. Portable Deck currently has no preconfigured game
rules or game presets.

**View Full Deck** shows every card from the deck definition, including cards
already dealt or drawn. The preview uses the deck's symbol order and sorts card
values within each symbol.

Game settings also offer optional score counters and point confirmation.
When **Enable Undo** is checked, the Undo button reverses the latest action that
changed the game state. Undo history is included in game saves and checkpoints.

**Enable Chip Accounts** gives every player a starting chip balance and shows
the configured minimum bet. **Play Chips** moves chips from the current
player's account into a shared pot and enforces that minimum. **Take Pot** moves
the full pot to a chosen player's account. Optionally, every other player must
approve the withdrawal on their turn. **Buy Chips** adds chips to any player's
account. Balances, the pot, and any pending approval are saved and can be
restored with Undo. The app does not implement poker rounds or decide who wins
the pot; players manage those decisions themselves.

The table window grows when more space is needed for cards. Restart starts a
fresh game with the same setup and can keep or reset scores when scoring is on.

## Saves and checkpoints

`portable_deck.app.sessioncatalog.list_sessions(directory, source="saves")`
returns immutable metadata entries; `source="autosaves"` includes the latest
checkpoint followed by archived saves. Entries contain filename/path, player
names, next player, configuration, modification flag, timestamp and a per-file
error. Corrupt files remain listed without hiding healthy sessions. Missing
folders produce an empty catalog and are not created; directory access errors
propagate. Metadata reading does not load or validate the full game or expose
card identities. The browser formats these values for display.

`portable_deck.app.namedsaves` provides GUI-independent named-save operations:
`next_session_number(directory)`, `validate_named_save_path(path)` and
`save_named_session(game, path, client_state=None, overwrite=False)` (the last
two arguments are keyword-only). Existing files require explicit overwrite
authorization. Reserved checkpoint destinations are rejected, and the game's
associated named-save path changes only after a successful write. Clients choose
paths and collect overwrite decisions; exceptions are left for clients to display.

`portable_deck.app.sessionfiles.rename_session(path, new_name)` renames within
the source directory, appends `.json` when needed and rejects invalid names,
collisions and the reserved `last_session.json` name. Archived autosaves can
still be renamed within their archive directory.
`delete_session(path, confirmed=True)` deletes one file; without explicit
confirmation it does nothing. Deleting an autosave after confirmation remains
available, as in the original browser. GUI dialogs collect these decisions.

Other clients can use `portable_deck.app.checkpoints.save_checkpoint(game, path,
enabled=True, count=5, client_state=None)` without Tkinter. Retention includes
the latest checkpoint. The service returns `None` on success or an error string
and can be attached to `game.session.checkpoint_callback` via a function that
supplies the destination path. Optional client metadata remains separate from
the game model.

**Save** creates a named JSON save in `saves/`. The suggested name is
`sessionX.json`, where `X` is one greater than the largest numbered session save.
The app asks before replacing an existing save.

**Load save** lists named sessions with their players, next player, and save time.
Sessions can be loaded, renamed, or deleted from this list; Browse can select a
JSON save outside the saves folder.

When Autosave is enabled, the app updates `saves/last_session.json` when a game starts,
after game actions, and when leaving a game. **Resume game** loads this checkpoint,
including the game log and available Undo history. It is separate from named
saves. With Require exit confirmation enabled, exit actions ask whether to create a named save; choosing No still
leaves the latest automatic checkpoint available for Resume if Autosave is enabled.

## Settings files

- `configs/settings.json` stores the current settings.
- `configs/default_settings.json` stores the values used by **Restore Defaults**.

Settings can also be changed in the in-app Settings screen. Relative deck paths
are resolved from the project folder.

## Deck format

Deck definitions are JSON files containing a `types` array and a `cards` array.
Each group in `cards` corresponds by index to one entry in `types`:

```json
{
  "types": ["Hearts", "Spades"],
  "cards": [
    ["2", "3", "A"],
    ["2", "3", "A"]
  ]
}
```

This produces cards such as `2 of Hearts` and `A of Spades`. The example deck is
`decks/demodeck.json`. **Check deck** in Settings validates the JSON structure
and card count before starting. Decks need at least one non-empty type name,
one card list per type, and at least one card overall. Card values can be text
or numbers. **Preview deck** shows every card in a responsive table-style grid,
with up to 10 cards per row, grouped in the deck's symbol order and sorted by
card value within each symbol.
**Create deck…** in Settings opens an editor where each symbol has
its own card list. Duplicate a group to reuse its cards with a different symbol;
the saved deck is selected automatically. **Manage decks…** lists available
decks with card counts and symbols, and lets you select, preview, edit, duplicate,
import, or export one.

## Project layout

- `main.py` starts the application; `portable_deck/` contains the Python package.
- `portable_deck/app/` contains the main menu, settings/configuration, and save
  management.
- `portable_deck/core/` contains game state and actions, players and decks,
  table placement, undo/scoring/chip logic, and save
  serialization.
- `portable_deck/ui/` contains the game window and its interface components,
  including hand, table, status, and chip controls.
- `portable_deck/data/` stores internal app data such as the optional discard
  pile output; it is not listed as a user deck.
- `configs/`, `decks/`, and `saves/` remain at the project root for user data.
- `portable_deck_documentation.txt` contains the longer project guide.


## Basic Settings

**Autosave** enables automatic checkpoints after game actions and when leaving a
session. **Autosaves to keep** (1–1000, default 5) includes the latest checkpoint
used by Resume. Earlier versions are available through **Autosaves** in the main
menu. Unchanged checkpoints do not create another version. Disabling Autosave
stops new automatic saves and keeps existing saves available.

**Require exit confirmation** controls the save/confirmation dialog when leaving
a game and the confirmation when quitting from the main menu. When disabled,
leaving is immediate; use **Save** during a game to create a named save manually.

**Game Settings -> Table settings -> Enable table** shows the table and enables
playing cards onto it. **Game Settings -> Discard pile -> Enable discard pile**
enables discarding, discard draws and recycling. Both are enabled by default.
Disabling the discard pile also disables clearing the table into discard.
These choices are preserved in game saves and on restart.

## Personal piles on table

**Game Settings -> Personal piles on table** enables personal piles and sets
the number per player (1-20). Each player/pile has independent access and
ordering preferences. **Everyone** permits all players to play and take cards.
**Owner** and **Team** both give the pile owner access. **Team** also gives
teammates access when teams and **Enable team access to Team personal piles**
are enabled. **Enable dealer access to personal piles** grants dealers
access to **Owner** and **Team** piles.

Choose **Not ordered**, **Ordered by time**, or **Ordered by size**. Time ordering lets new cards
go on top or underneath the stack. Size ordering offers **up** (smallest at the bottom, largest on top)
and **down** (largest at the bottom, smallest on top) (J, Q, K, A follow 10). Unordered piles put new
cards on top. The game shows piles top first; use **Play to Personal Pile** to
play and **Take top card** to draw from an accessible pile.

Personal piles require an enabled table and remain separate from discard piles.
Discard recycling and table cleanup do not empty them. State, access rules and
ordering are included in saves, restart settings and Undo.

Enable **Unequal amount of personal piles** to set a separate count (0-20)
for each player. Disabling it returns to the shared count. Individual counts
and pile preferences remain available when switching back.

## Roles/teams

In **Game Settings -> Roles/teams**, enable the category to activate its
controls. **Enable dealer** creates the fixed **Dealer** team; assigned players
receive the dealer role without additional privileges. **Enable teams** allows
a total team count, including Dealer, up to the number of players. Each player
can belong to one regular team or remain unassigned. Dealer membership is
independent, so a dealer can also belong to a regular team. Dealer is listed first. With **Custom player names** on,
regular teams can also have custom names. Roles and memberships appear in game
status and survive save/load and restart.

## Player interactions

**Game Settings -> Player interactions -> Enable interactions** enables the
category. Allow each action separately: take a random card from a chosen player,
discard a random card from another randomly selected player, give the selected
hand card to a chosen player, steal a chosen amount of chips, or privately view
a random card/all cards of a chosen player. Discarding requires a discard pile;
stealing requires chip accounts. Players sharing an account cannot steal from
each other. Private card views are not included in logs or saved history.
Use **Player interactions** during a session. Permissions survive save/load and
restart; state-changing actions support Undo.

**Use current settings** applies the form for playing. **Save settings** stores
a named configuration (including player/team names) under `configs/presets/`
by default. **Load settings** fills the form from a saved configuration; apply
it with **Use current settings**. These files are separate from game saves.

Game-rule presets exclude Basic Settings (Autosave, retained autosaves, exit
confirmation and Undo) and the player count. Loading a preset preserves these
current values, and changing them does not mark the rule preset as modified.

**Basic Settings -> Use contextual actions and session menus** enables an
optional session layout. Draw Card, Next Turn and Undo stay visible. Selecting
a hand card, table card or empty spot reveals applicable card actions. Players,
Chips, Score, Table and View menus contain the other enabled actions. Turning
the option off keeps the original buttons. This UI preference is excluded from
game-rule presets.

Cards can be dragged from a hand onto a permitted empty table slot, or between
table positions when moving table cards is enabled. Empty targets highlight
during dragging. Escape cancels; dropping outside a valid slot leaves the card
in place. Dragging uses the usual game log, checkpoint and Undo actions.

## Action availability API

Action availability is independent of Tkinter and can be queried from a CLI:

```python
from portable_deck.core.actionavailability import ActionContext, action_availability

result = action_availability(game, "move_table_card",
    ActionContext(table_index=0, target_position=(0, 1)))
print("Available" if result.allowed else result.reason)
```

Card indices are zero-based. Queries do not execute an action or change game
state. Unknown action identifiers raise ValueError. GUI controls and tooltips
use this same API; the GUI layer only maps widgets and selection to action IDs
and ActionContext. Game model methods still enforce execution rules.

Chip controls and contextual give/move actions use shared availability checks.
`drop_availability(game, source, index, position)` resolves and checks a drag
proposal; `available_move_targets(game, table_index)` filters destination choices.
The GUI checks again when opening chip dialogs or dropping a card, and
`session.execute` always checks current availability before executing commands.
UI checks never replace execution validation, including after modal input.

## Shared session actions

GUI and non-graphical clients can use the same session controller:

```python
from portable_deck.core.game import Game

game = Game(2, "decks/demodeck.json", enable_undo=True)
result = game.session.execute("draw_card")
if result.success:
    print(result.value)
else:
    print(result.message)
game.session.undo()
```

`game.session.undo_result()` returns an `ActionResult` with refusal code/message
or successful restoration and `checkpoint_error`. `undo()` remains a boolean
compatibility wrapper. GUI and CLI use the structured result; CLI empty-history
failures use the core `empty_undo` code.
`game.session.checkpoint_result()` returns checkpoint status as `ActionResult`,
with `checkpoint_failed`/`checkpoint_error` on failure and no gameplay Undo step.
The original `checkpoint()` error-string/`None` API remains supported.
`game.session.log_snapshot()` returns an immutable ordered tuple of public log
messages; GUI rendering uses it instead of the mutable model list.
`tests/test_uistateboundary.py` prevents GUI access to `game_log`, `gui_log` and
`undo_stack`, directing clients to session log/Undo APIs instead.
`game.session.end_turn_availability()` supplies the same availability/reason used
by end-turn execution and the GUI Next turn button.
`game.session.return_player_options()` supplies immutable return choices and
availability shared by the GUI Return player button and dialog.

Card indices are zero-based. For example, `execute("play_card", card_index=0)`
plays the first card; `execute("move_table_card", card_index=0,
target_position=(0, 1))` moves a table card. Other actions include discard,
flipping, chips, scoring, confirmations, leaving/returning and ending a turn.
Availability is checked before execution. Results include `success`, `changed`,
`value`, `message` and `checkpoint_error`.

`ActionResult.code` is a stable machine-readable rejection code; successful
commands use an empty string, including a successful denial of an approval
request. `ActionAvailability.code` supplies the same identifiers for rule checks.
Existing `message`/`reason` text remains for display; clients should branch on
codes rather than translated wording. Examples include `empty_deck`,
`selection_required`, `invalid_selection`, `invalid_target`, `table_full`,
`confirmation_required` and `confirmation_not_required`. Shared rule checks also
identify disabled actions, inactive/departed players, empty resources and chip
balance restrictions. Model validation exceptions currently use the broader
`invalid_parameters`, other model refusals `action_rejected`, and unavailable
returns `return_unavailable`. Unknown action IDs still raise `ValueError`.
`checkpoint_error` remains separate: a successful move with a failed checkpoint
keeps an empty command error code. Newly added fields preserve previous positional
arguments, and GUI/CLI display text is unchanged.

Interactions also identify `target_left`, `target_hand_empty`,
`shared_chip_account`, `no_eligible_targets`, `invalid_target`, `invalid_amount`
and `insufficient_chips`. Target options expose `code` alongside their reasons;
the same target validation runs at execution time. Chip parameter validation
adds `minimum_bet_not_met` and distinguishes invalid amounts from overdrafts.
Global rule/turn restrictions are checked before command parameters.
Typed model validation exceptions remain subclasses of `ValueError`; existing
direct chip methods keep their tuple/optional-value return contracts.

Personal table piles use `execute("play_personal_pile", card_index=0, owner=0,
pile_index=0)` and `execute("take_personal_pile", owner=0, pile_index=0)`.
Player and pile indices are zero-based. Both commands enforce access permissions
and participate in Undo and checkpoints. Availability queries can include
`ActionContext(owner=0, pile_index=0)` to check a particular pile.

Player interactions use their interaction IDs as session commands, for example
`execute("give_card", target=1, card_index=0)` or
`execute("steal_chips", target=1, amount=5)`. Random discard chooses its own target.
Private peek commands return cards only in `ActionResult.value["cards"]`, outside
public events and messages. They still record that a peek occurred, so the
history change participates in Undo and checkpoints.

`portable_deck.core.interactions.build_interaction_options(game, action,
hand_index=None)` prepares immutable target IDs, names, eligibility reasons and
chip amount limits for the current player. No hand identities are included.
Random discard marks that its target is selected by the core. Dialogs refresh
these options before prompting; commands still revalidate targets and amounts
after input, so stale options cannot authorize execution.

Swap a hand card with an occupied table slot using
`execute("swap_table_card", card_index=0, table_index=1)`. Both indices are
zero-based and refer to different collections. The command requires an enabled
table, positioned play and the `swap` occupied-slot rule. It preserves the slot's
position and face orientation and returns `(played_card, returned_card)`.

Set `game.session.checkpoint_callback` to a function accepting the game to save
changed sessions automatically. A save failure is reported without reversing
the action. `session.run(operation)` groups nested operations and presentation
log updates into one Undo step and one checkpoint. Unexpected operation errors
restore the previous game state and are re-raised. The core controller imports
no Tkinter; dialogs and rendering remain in the GUI.

### Selection state

Returning-player dialogs use
`portable_deck.core.playerleaving.build_player_return_options(game)` for an
immutable list of departed player IDs/names and eligibility reasons. Pending
confirmations and disabled return rules are checked again by
`session.execute("return_player", player_index=...)`; stale options cannot
authorize a return. Returning the first player to an empty session resumes their
turn and participates in Undo and checkpoints.

`portable_deck.core.selection.SelectionState` holds transient hand/table indices
and the target table position without importing Tkinter. GUI controls share one
instance; the frames only render that selection. Use `select_hand`,
`select_table`, `select_target` and `clear` to control it. Selection methods
support toggling and keeping a table card selected while choosing its destination.
Call `synchronize(build_selection_snapshot(game))` after game changes, importing
`build_selection_snapshot` from `portable_deck.core.selectionsnapshot`.
Changing players or sessions clears selection,
and changing a card collection clears its selection to avoid targeting a different
card at the old index. The immutable snapshot carries only random opaque change
markers, player index and collection counts. It can be serialized with
`dataclasses.asdict`; synchronization needs no card identities or Game reference.
The core privately compares collections to refresh markers, including direct
model changes and Undo. Markers are transient and are not card hashes or stable
card IDs. The old `synchronize(game)` call remains a local compatibility adapter.
`SelectionSnapshot.contains("hand" or "table", index)` checks collection bounds
without exposing cards. Click handlers and context menus use this before changing
selection; boolean, stale out-of-range and unknown-location indices are rejected.
Selection is local input state and is excluded from saves,
Undo and game rules. A CLI can use it or pass action parameters directly.

### Settings validation and preset compatibility

`portable_deck.core.settingsvalidation.validate_settings(values)` validates a
settings dictionary without importing Tkinter and returns an independent copy
with missing defaults filled in. The settings form and preset loader share this
validation, including types, ranges, names, deck capacity and game configuration.

Loading presets compares their rule fields with the current schema. A warning
lists missing and unknown fields or fields with incorrect types. Missing fields
use application defaults and unknown fields are ignored. Invalid preset values
are replaced with defaults (or valid dependent defaults) and listed in the warning;
unrelated valid settings are retained. Manual form editing and saving remain strict.
Malformed JSON or a missing file still prevents loading. Basic settings, player count and configuration metadata are excluded
from the comparison. `read_preset(..., on_warning=callback)` supplies warning text
to another interface; without a callback it emits a Python warning.

### Shared rules overview

Overview rules reads a snapshot prepared by the core, including preset metadata
and enabled rule sections. The GUI only renders these values. Other clients can
use the structured data (`RulesOverview`, `RuleSection`, `RuleEntry`) or plain text:

```python
from portable_deck.core.rulesoverview import build_rules_overview, format_rules_overview

overview = build_rules_overview(game)
print(format_rules_overview(overview))
```

The snapshot is immutable, imports no Tkinter and does not change the session.
It lists rules and permissions without exposing cards in players' hands.

### Turn entry work

`portable_deck.core.turnstart.build_turn_start_view(game)` returns immutable
current-player work: `active`, `notifications` and ordered `confirmations`.
Clients display and acknowledge score notices first. Each confirmation contains
the session `action` and its structured `notice`; `next_confirmation` selects
score approval before pot approval. Submit the decision through
`session.execute(prompt.action, approved=...)` and rebuild the view after each
decision. Querying does not acknowledge notices or change game state, and an
inactive current player receives no work. The GUI follows this same protocol.

### Shared score notifications

`game.score_notifications()` prepares immutable notifications for the current
player, with title, message, recipient, kind, score and threshold. Querying does
not mark them as read. A client displays them and then calls
`game.session.acknowledge_score_notifications(notices)` (also with an empty sequence when
there is nothing to display). This removes expired events and allows later
threshold crossings to notify again. The GUI acknowledges after the user closes
the notice; CLI clients can use the same protocol without Tkinter.

Acknowledgment checkpoints changed read state without adding a gameplay Undo
step. Inside `session.run`, it shares the enclosing checkpoint and is restored
with that gameplay action on Undo. A transaction that only changes notification
read state also creates no Undo step. Results report `changed` and
`checkpoint_error`; an unchanged acknowledgment does not save again.
`game.acknowledge_score_notifications` remains a low-level compatibility method
without persistence orchestration.

`game.score_confirmation_notification()` prepares a pending score approval
prompt, including requester and delta. Submit the decision through
`game.session.execute("confirm_point", approved=True)` or `approved=False`.
The existing `turn_score_alerts()` method remains a compatibility adapter that
returns message strings and acknowledges them immediately.

`game.pot_confirmation_notification()` similarly returns an immutable pot
approval prompt, or `None` when the current player has nothing to approve.
It includes `kind`, `recipient` (the voter), `requester`, `beneficiary` (the player
receiving the pot), `amount`, `title` and `message`. Querying changes no state.
Submit the decision using `game.session.execute("confirm_pot", approved=True)`
or `approved=False`; the query does not authorize or execute the withdrawal.

### Core-owned game log

Game operations record structured events in `game.history` and public messages
in `game.game_log`, including when called directly without the GUI. The shared
formatter in `portable_deck.core.gamelog` owns message wording. GUI code only
renders the resulting log; CLI clients can print it or use `ActionResult.events`
and `ActionResult.messages` for output from a particular session action.

Hidden draws, face-down plays and private peek results are excluded from public
messages. Undo and failed transactions restore both history and messages. New
saves use `game_log`; older saves with `gui_log` remain readable, and the old
attribute is retained as a compatibility alias. Existing saved text is preserved.

### Combined player session view

`portable_deck.core.playersessionview.build_player_session_view(game, viewer,
hand_index=None)` combines `status`, `hands`, `table`, `personal_piles` and
`discard` into one immutable snapshot. It reuses the individual projections and
supports `json.dumps(dataclasses.asdict(view))`. The optional hand selection is
used for personal-pile play availability. Visible hands is the first GUI consumer.
Build the snapshot while game state is stable; the query does not add locking or
authenticate the viewer. Internal history, logs, private action results and draw
order are excluded. It is a presentation snapshot, not a save or command API.

### Player-specific hands

`portable_deck.core.playerview.build_player_hands_view(game, viewer)` returns an
immutable hand snapshot for a zero-based player index. Hidden card slots contain
`card=None`; individually revealed cards remain visible. Player, team and dealer
permissions determine full-hand access. Both hand interfaces render this shared
projection. It supports `dataclasses.asdict` and does not import Tkinter or change
the game. This is the first part of a player view, not a complete network payload
or authentication boundary; remote callers must not choose arbitrary viewers.

### Player-specific table

`build_player_table_view(game, viewer)` in the same module prepares immutable
table cards, positions, available targets and player lane names. Face-down cards
always have `card=None`, including for the player who played them. Card indices
retain their model meaning, including stacked cards. Disabled tables expose no
cards or targets. Both table layouts render this projection; it does not include
personal piles or public action history yet.

With positioned play and table movement disabled, the table view exposes only
the automatic next-card target instead of surrounding empty slots. Positioned
play, player lanes and table movement retain spatial targets. These display
choices do not replace command availability checks.

In ordinary play, dragging a hand card anywhere onto the table area (including
an occupied card) plays it at the automatic next position. Dropping outside the
table cancels. Positioned play and player lanes still require an explicit empty
slot; dragging an existing table card still uses the movement rules.

### Player-specific personal piles

`build_player_personal_piles_view(game, viewer, hand_index=None)` returns immutable
pile snapshots with owner, indices, ordering rules and cards in model order (top
last). Cards remain public regardless of manipulation access. `accessible` is
viewer-specific; `play` and `take` contain availability and reasons for the
current turn. Play availability uses the optional zero-based hand selection.
Disabled personal piles expose no entries. The GUI renders this view and uses
it to offer destinations; execution still revalidates through the controller.

### Discard browsing

`build_player_discard_view(game, viewer)` returns immutable shared and personal
discard pile snapshots. In `top` mode only the top identity is copied; `any`
mode lists cards top first with their original zero-based card indices.
`source_index` includes empty piles and can be passed to the session's
`draw_from_discard` command. The view does not grant permission to draw, and
execution rechecks the current rules. No draw-deck order is included.
The separate Full Deck preview displays the deck definition, not remaining order.

`portable_deck.core.deckpreview.build_deck_preview(deck)` prepares an immutable
definition snapshot with a card count and symbol groups. Symbol order and
duplicate values are preserved, while values are sorted for display. It never
reads the remaining draw order. The session, settings and library previews all
render this shared data without preparing their own card ordering.

### Shared session status

`portable_deck.core.chipoptions.build_chip_options(game)` prepares immutable
chip input data: player IDs/names and account references, unique accounts,
current player, bet bounds, default purchase amount, pot and shared action
availability. Shared team balances are represented once per account; player
rows reference that account. Chip dialogs consume this snapshot rather than
live Player objects. Submitted amounts and recipients are still revalidated
by session commands against the current state.

Pile dialogs use `portable_deck.core.pileoptions.discard_destinations(game, viewer)`
for shared and the viewer's personal discard destinations, and
`insertion_options(game, "draw")` or `"discard"` for insertion counts and ranges.
These immutable options contain no card identities and do not authorize actions;
the session controller revalidates submitted commands.

Table zoom and scroll offsets are client state, separate from `Game`. The desktop
app stores them under `client_state.table_view` in named saves and checkpoints,
and reads the legacy `table_view_state` field from older saves. Other clients can
save optional metadata using `app.sessionstorage.save_session(game, path, client_state=...)`;
`app.sessionstorage.load_session(Game, path)` restores game data only. View changes do not affect Undo.

`portable_deck.core.sessionstatus.build_session_status(game)` prepares an immutable
snapshot of player names, card counts, active/current state, roles, team membership,
scores, chip accounts, pot and pile counts. Shared chip accounts have stable IDs,
member indices and one balance per account; player rows reference those IDs.
`score_owner` distinguishes shared scores from personal scores and `team_score`
is the separate team counter. Disabled resources use `None`, distinct from zero.

The snapshot does not contain card identities or change the game. Tkinter only
renders the snapshot and retains display choices such as showing "many". A CLI
or another GUI can use the same data, for example `dataclasses.asdict(status)`.
