# PortableDeck

PortableDeck is a simple virtual card game engine built with **Python (Tkinter)**.  
It supports multiple players, deck management, card drawing, discarding, turn-based gameplay, and a live GUI log.

---

##  Features

-  Dynamic deck loading from JSON files
- Multiple players support
-  Turn-based gameplay system
- Tkinter GUI interface
- Live status panel (hands, deck, discard pile)
- In-game action log
- Card discard system with validation
- Save discard pile to JSON file

---

## Project Structure

```
PortableDeck/
├── main.py              # Entry point
├── game.py              # Core game logic
├── deck.py              # Deck loading & handling
├── player.py            # Player class
│
├── guibase.py           # Main GUI window
├── handframe.py         # Player hand UI
├── statuspanel.py      # Game status UI
├── cardactions.py      # Button actions (draw, discard, end turn)
│
├── decks/
│   ├── demodeck.json    # Example deck
│   └── discard.json     # Saved discard pile
```

---

## How to Run

### Requirements

- Python 3.8+
- Tkinter (included by default with most Python installations)

### Start the game

```bash
python main.py
```

---

## How to Play

- **Draw Card** → Draw a card from the deck
- **Discard Selected** → Discard selected card from hand
- **Next Turn** → Switch to the next player
- Click cards in your hand to select them

---

## Deck Format

```json
{
  "types": ["Hearts", "Diamonds", "Clubs", "Spades"],
  "cards": [
    ["A", "2", "3", "4"],
    ["A", "2", "3", "4"],
    ["A", "2", "3", "4"],
    ["A", "2", "3", "4"]
  ]
}
```

---

## Architecture Overview

- Game logic separated from GUI
- Turn-based system with player rotation
- Action history tracking system
- Modular design for easy extension

---

## Possible Improvements

- Online multiplayer support
- Drag & drop cards
- AI opponents
- Animations and effects
- Custom rule engine

---

## License

This project is intended for educational and personal use.
