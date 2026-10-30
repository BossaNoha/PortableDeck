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

- **Play** starts a new game using the current settings.
- **Resume** restores the latest automatic checkpoint from `saves/last_session.json`.
- **Load** opens a session library with player/turn details and actions to load,
  rename, or delete a named save. **Browse…** can open a JSON save elsewhere.
- **Settings** configures player count, starting hand size, deck, optional player
  names, and game actions.
- **Quit** closes the app.

## In a game

Players can draw, discard, play cards onto the table, and end their turn. The
table and action buttons depend on the options enabled in **Settings → Advanced
Settings → Table actions**. These options include taking table cards, moving
cards to the discard pile, clearing the table, placing cards in table positions,
moving cards between positions, and showing a separate card row in front of each
player. If player rows are enabled, **Play Selected Card** plays in front of the
current player; **Play at Selected Spot** can target another player's row.

In **Advanced Settings → Deck actions**, enable **Allow drawing from the discard
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

Advanced Settings also provide general card-handling options for flexible table
layouts: play cards face down and reveal them, move face-up sequences together,
and recycle the discard pile into an empty draw deck. These are individual
actions for custom games. Portable Deck currently has no preconfigured game
rules or game presets.

**View Full Deck** shows every card from the deck definition, including cards
already dealt or drawn. The preview uses the deck's symbol order and sorts card
values within each symbol.

Advanced settings also offer optional score counters and point confirmation.
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

**Load** lists named sessions with their players, next player, and save time.
Sessions can be loaded, renamed, or deleted from this list; Browse can select a
JSON save outside the saves folder.

The app also updates `saves/last_session.json` automatically when a game starts,
after game actions, and when leaving a game. **Resume** loads this checkpoint,
including the game log and available Undo history. It is separate from named
saves. The exit actions ask whether to create a named save; choosing No still
leaves the automatic checkpoint available for Resume.

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

