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
- **Load** opens a named save or another JSON save file.
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

Advanced settings also offer optional score counters and point confirmation.
When **Enable Undo** is checked, the Undo button reverses the latest action that
changed the game state. Undo history is included in game saves and checkpoints.

The table window grows when more space is needed for cards. Restart starts a
fresh game with the same setup and can keep or reset scores when scoring is on.

## Saves and checkpoints

**Save** creates a named JSON save in `saves/`. The suggested name is
`sessionX.json`, where `X` is one greater than the largest numbered session save.
The app asks before replacing an existing save.

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
`decks/demodeck.json`. The app checks that the deck has enough cards to deal the
configured starting hands.

## Project layout

- `main.py` starts the application.
- `mainmenu.py` contains the main menu, settings form, and game lifecycle.
- `game.py` contains game state, actions, undo, and save/load logic.
- `guibase.py`, `handframe.py`, `tableframe.py`, and `statuspanel.py` build the
  Tkinter game interface.
- `cardactions.py` connects game actions to the interface.
- `deck.py` loads and shuffles deck definitions; `player.py` stores player hands.
- `portable_deck_documentation.txt` contains the longer project guide.
- `saves/` stores named saves and the automatic checkpoint.

