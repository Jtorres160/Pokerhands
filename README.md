# Poker Odds Calculator

A professional Texas Hold'em Poker Odds Calculator desktop app built with Python and PyQt5.

## Features
- Calculate odds for Texas Hold'em hands at any stage (pre-flop, flop, turn, river)
- Input your hand, community cards, and number of players
- See your odds to win, tie, and the probability of making each hand type
- Beautiful, modern UI with poker-table-inspired theme
- Unicode card symbols and color for clarity
- Fast pre-flop analysis with disk-based caching (no need to recalculate for the same hand)
- Reset and recalculate instantly

## Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/poker-odds-calculator.git
   cd poker-odds-calculator
   ```
2. Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install PyQt5 deuces
   ```

## Usage
1. Run the app:
   ```bash
   python3 PokerOddsCalculator.py
   ```
2. Select your hand, community cards, and number of players.
3. Click **Calculate Odds** to see your odds and hand breakdown.
4. Use **Reset** to clear all fields.

- The first time you analyze a new pre-flop hand/player combo, it may take a few seconds (runs 500,000 simulations). After that, results are instant (cached).
- Community card scenarios are calculated live for maximum accuracy.

## Credits
- Poker odds logic powered by [deuces](https://github.com/worldveil/deuces)
- UI built with Python and PyQt5
- Designed and developed by [Your Name]

## License
MIT License (see LICENSE file) 