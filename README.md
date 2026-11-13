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
ordering preferences. **Everyone** permits all players to play and take cards;
**Team** currently permits only the owner, as does **Owner**.

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
