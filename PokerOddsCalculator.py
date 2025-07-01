import sys
import os
import pickle
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QLabel, QComboBox, QPushButton, QSpinBox, QVBoxLayout, QWidget, QHBoxLayout, QTextEdit, QFrame, QSizePolicy, QSpacerItem
)
import re
from collections import Counter
import random
# Import Deuces
from deuces import Card, Evaluator, Deck
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QFont, QPalette, QColor

# Valid card ranks and suits
RANKS = '23456789TJQKA'
SUITS = 'shdc'
SUIT_SYMBOLS = {'s': '♠', 'h': '♥', 'd': '♦', 'c': '♣'}
CARD_PATTERN = re.compile(r'^[2-9TJQKA][shdc]$', re.IGNORECASE)
RANK_TO_VALUE = {r: i for i, r in enumerate(RANKS, 2)}

# Generate all card options as (code, label), grouped by suit then rank
SUIT_ORDER = 'cdhs'  # clubs, diamonds, hearts, spades
CARD_OPTIONS = [(f'{r}{s}', f'{r}{SUIT_SYMBOLS[s]}') for s in SUIT_ORDER for r in RANKS]

# Add color for suits in HTML using <font color>
# For dark mode: spades/clubs white, hearts/diamonds red
SUIT_HTML = {
    's': '<font color="#fff">&#9824;</font>',  # white spade
    'h': '<font color="red">&#9829;</font>',
    'd': '<font color="red">&#9830;</font>',
    'c': '<font color="#fff">&#9831;</font>'   # white club
}

CACHE_FILE = 'preflop_cache.pkl'

def parse_card(card):
    card = card.strip().lower()
    if CARD_PATTERN.match(card):
        return card
    return None


def analyze_hand(cards):
    if len(cards) < 5:
        return "Not enough cards for hand analysis."
    # Split into ranks and suits
    ranks = [c[0].upper() for c in cards]
    suits = [c[1].lower() for c in cards]
    rank_counts = Counter(ranks)
    suit_counts = Counter(suits)
    unique_ranks = sorted(set(ranks), key=lambda r: RANK_TO_VALUE[r], reverse=True)

    # Check for flush
    flush_suit = None
    for suit, count in suit_counts.items():
        if count >= 5:
            flush_suit = suit
            break
    flush_cards = [c for c in cards if c[1] == flush_suit] if flush_suit else []
    flush_ranks = [c[0].upper() for c in flush_cards]

    # Check for straight (and straight flush)
    def get_straight(ranks_list):
        values = sorted(set(RANK_TO_VALUE[r] for r in ranks_list), reverse=True)
        # Handle wheel (A-2-3-4-5)
        if set(['A', '2', '3', '4', '5']).issubset(set(ranks_list)):
            values.append(1)
        for i in range(len(values) - 4):
            if values[i] - values[i+4] == 4:
                return True, values[i]
        return False, None

    # Straight flush
    if flush_suit and len(flush_ranks) >= 5:
        is_sf, high_sf = get_straight(flush_ranks)
        if is_sf:
            if high_sf == 14:
                return "Royal Flush"
            return "Straight Flush"

    # Four of a kind
    if 4 in rank_counts.values():
        return "Four of a Kind"
    # Full house
    if 3 in rank_counts.values() and 2 in rank_counts.values():
        return "Full House"
    # Flush
    if flush_suit:
        return "Flush"
    # Straight
    is_straight, high_straight = get_straight(ranks)
    if is_straight:
        return "Straight"
    # Three of a kind
    if 3 in rank_counts.values():
        return "Three of a Kind"
    # Two pair
    if list(rank_counts.values()).count(2) >= 2:
        return "Two Pair"
    # Pair
    if 2 in rank_counts.values():
        return "Pair"
    # High card
    return f"High Card: {max(ranks, key=lambda r: RANK_TO_VALUE[r])}"


def to_deuces(card):
    # Convert 'As' to 'As' for Deuces (same format, but uppercase)
    return Card.new(card[0].upper() + card[1].lower())


def deuces_hand_strength(hand_cards, board_cards):
    evaluator = Evaluator()
    hand = [to_deuces(c) for c in hand_cards]
    board = [to_deuces(c) for c in board_cards]
    rank = evaluator.evaluate(board, hand)
    class_str = evaluator.class_to_string(evaluator.get_rank_class(rank))
    return class_str


def monte_carlo_odds(hand_cards, board_cards, num_players, num_trials=1000):
    evaluator = Evaluator()
    wins = 0
    ties = 0
    losses = 0
    hand = [to_deuces(c) for c in hand_cards]
    board = [to_deuces(c) for c in board_cards]
    known = set(hand + board)
    for _ in range(num_trials):
        deck = Deck()
        # Remove known cards from deck
        for c in hand_cards + board_cards:
            deck.cards.remove(to_deuces(c))
        # Draw remaining community cards
        needed = 5 - len(board)
        sim_board = board + [deck.draw(1) for _ in range(needed)] if needed > 0 else board
        # Draw opponents' hands
        opp_hands = []
        for _ in range(num_players - 1):
            opp_hand = [deck.draw(1), deck.draw(1)]
            opp_hands.append(opp_hand)
        # Evaluate hero hand
        hero_score = evaluator.evaluate(sim_board, hand)
        opp_scores = [evaluator.evaluate(sim_board, opp) for opp in opp_hands]
        if hero_score < min(opp_scores):
            wins += 1
        elif hero_score == min(opp_scores):
            ties += 1
        else:
            losses += 1
    win_pct = 100 * wins / num_trials
    tie_pct = 100 * ties / num_trials
    return win_pct, tie_pct


def card_label_html(card):
    if not card:
        return ''
    r, s = card[0].upper(), card[1].lower()
    return f'{r}{SUIT_HTML[s]}'


def monte_carlo_hand_distribution(hand_cards, board_cards, num_trials=1000):
    evaluator = Evaluator()
    hand = [to_deuces(c) for c in hand_cards]
    board = [to_deuces(c) for c in board_cards]
    hand_type_counts = {i: 0 for i in range(1, 10)}  # 1-9 hand classes
    for _ in range(num_trials):
        deck = Deck()
        for c in hand_cards + board_cards:
            deck.cards.remove(to_deuces(c))
        needed = 5 - len(board)
        sim_board = board + [deck.draw(1) for _ in range(needed)] if needed > 0 else board
        rank = evaluator.evaluate(sim_board, hand)
        hand_class = evaluator.get_rank_class(rank)
        hand_type_counts[hand_class] += 1
    return hand_type_counts


def monte_carlo_preflop_distributions(hand_cards, num_players, num_trials=75000):
    evaluator = Evaluator()
    hand = [to_deuces(c) for c in hand_cards]
    flop_counts = {i: 0 for i in range(1, 10)}
    turn_counts = {i: 0 for i in range(1, 10)}
    river_counts = {i: 0 for i in range(1, 10)}
    win = 0
    tie = 0
    for _ in range(num_trials):
        deck = Deck()
        for c in hand_cards:
            deck.cards.remove(to_deuces(c))
        # Flop
        flop = [deck.draw(1) for _ in range(3)]
        flop_rank = evaluator.evaluate(flop, hand)
        flop_class = evaluator.get_rank_class(flop_rank)
        flop_counts[flop_class] += 1
        # Turn
        turn = flop + [deck.draw(1)]
        turn_rank = evaluator.evaluate(turn, hand)
        turn_class = evaluator.get_rank_class(turn_rank)
        turn_counts[turn_class] += 1
        # River
        river = turn + [deck.draw(1)]
        river_rank = evaluator.evaluate(river, hand)
        river_class = evaluator.get_rank_class(river_rank)
        river_counts[river_class] += 1
        # Win odds vs. random hands
        opp_hands = []
        for _ in range(num_players - 1):
            opp_hand = [deck.draw(1), deck.draw(1)]
            opp_hands.append(opp_hand)
        hero_score = river_rank
        opp_scores = [evaluator.evaluate(river, opp) for opp in opp_hands]
        if hero_score < min(opp_scores):
            win += 1
        elif hero_score == min(opp_scores):
            tie += 1
    return flop_counts, turn_counts, river_counts, win, tie


HAND_CLASS_NAMES = [
    "High Card", "Pair", "Two Pair", "Three of a Kind", "Straight", "Flush", "Full House", "Four of a Kind", "Straight Flush"
]

# Concise Unicode examples for each hand type
HAND_TYPE_EXAMPLES = {
    1: lambda: card_label_html('As'),  # High Card
    2: lambda: card_label_html('As') + card_label_html('Ah'),  # Pair
    3: lambda: card_label_html('As') + card_label_html('Ah') + card_label_html('Ks') + card_label_html('Kh'),  # Two Pair
    4: lambda: card_label_html('As') + card_label_html('Ah') + card_label_html('Ad'),  # Three of a Kind
    5: lambda: ''.join([card_label_html(r + 's') for r in ['A', 'K', 'Q', 'J', 'T']]),  # Straight
    6: lambda: ''.join([card_label_html(r + 's') for r in ['A', 'J', '8', '4', '2']]),  # Flush
    7: lambda: card_label_html('As') + card_label_html('Ah') + card_label_html('Ad') + card_label_html('Ks') + card_label_html('Kh'),  # Full House
    8: lambda: card_label_html('As') + card_label_html('Ah') + card_label_html('Ad') + card_label_html('Ac'),  # Four of a Kind
    9: lambda: ''.join([card_label_html(r + 's') for r in ['A', 'K', 'Q', 'J', 'T']]),  # Straight Flush
}

class PokerOddsCalculator(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Poker Odds Calculator')
        self.setMinimumSize(600, 600)
        # Set a dark green poker table background with a subtle gradient
        self.setStyleSheet('''
            QMainWindow { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #234d20, stop:1 #1a2e16); }
            QWidget { background: transparent; color: #e0e0e0; font-family: "Segoe UI", "Inter", "Roboto", Arial, sans-serif; }
            QLabel#Header { color: #fff; font-size: 2.1em; font-weight: bold; letter-spacing: 2px; margin-bottom: 18px; }
            QLabel.SectionTitle { color: #7ed957; font-size: 1.2em; font-weight: bold; margin-bottom: 6px; margin-top: 12px; }
            QFrame.CardGroup { background: #263a29; border-radius: 18px; border: 2px solid #2e4d2f; box-shadow: 0 4px 16px #0008; padding: 18px 18px 12px 18px; margin-bottom: 18px; }
            QComboBox.CardSlot { background: #1a2e16; color: #fff; border: 2px solid #7ed957; border-radius: 10px; font-size: 1.3em; font-weight: bold; min-width: 70px; min-height: 38px; margin-right: 8px; padding: 2px 12px; }
            QComboBox.CardSlot QAbstractItemView { background: #263a29; color: #fff; selection-background-color: #7ed957; }
            QPushButton.Primary { background-color: #7ed957; color: #1a2e16; border-radius: 10px; font-size: 1.1em; font-weight: bold; padding: 10px 32px; margin: 0 8px; }
            QPushButton.Primary:hover { background-color: #a6ff7a; }
            QPushButton.Secondary { background-color: #444; color: #fff; border-radius: 10px; font-size: 1.1em; font-weight: bold; padding: 10px 32px; margin: 0 8px; }
            QPushButton.Secondary:hover { background-color: #666; }
            QTextEdit#ResultsArea { background: #181a20; color: #fff; border: 2px solid #7ed957; border-radius: 14px; padding: 18px; font-size: 1.15em; box-shadow: 0 4px 16px #000a; }
            QSpinBox { background: #1a2e16; color: #fff; border: 2px solid #7ed957; border-radius: 10px; font-size: 1.1em; min-width: 60px; min-height: 32px; }
        ''')
        font = QFont('Segoe UI', 11)
        self.setFont(font)

        # Main layout
        central_widget = QWidget()
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(32, 24, 32, 24)
        main_layout.setSpacing(18)

        # Header
        header = QLabel('Poker Odds Calculator')
        header.setObjectName('Header')
        main_layout.addWidget(header, alignment=Qt.AlignHCenter)

        # Your Hand group
        hand_group = QFrame()
        hand_group.setObjectName('CardGroup')
        hand_group.setFrameShape(QFrame.StyledPanel)
        hand_group.setFrameShadow(QFrame.Raised)
        hand_layout = QVBoxLayout()
        hand_title = QLabel('Your Hand')
        hand_title.setObjectName('SectionTitle')
        hand_title.setProperty('class', 'SectionTitle')
        hand_layout.addWidget(hand_title)
        hand_cards_layout = QHBoxLayout()
        self.hand1_input = QComboBox()
        self.hand2_input = QComboBox()
        self._populate_card_dropdown(self.hand1_input)
        self._populate_card_dropdown(self.hand2_input)
        for cb in [self.hand1_input, self.hand2_input]:
            cb.setFixedWidth(90)
            cb.setObjectName('CardSlot')
            cb.setProperty('class', 'CardSlot')
        hand_cards_layout.addWidget(self.hand1_input)
        hand_cards_layout.addWidget(self.hand2_input)
        hand_cards_layout.addStretch()
        hand_layout.addLayout(hand_cards_layout)
        hand_group.setLayout(hand_layout)
        hand_group.setProperty('class', 'CardGroup')
        main_layout.addWidget(hand_group)

        # Community Cards group
        comm_group = QFrame()
        comm_group.setObjectName('CardGroup')
        comm_group.setFrameShape(QFrame.StyledPanel)
        comm_group.setFrameShadow(QFrame.Raised)
        comm_layout = QVBoxLayout()
        comm_title = QLabel('Community Cards')
        comm_title.setObjectName('SectionTitle')
        comm_title.setProperty('class', 'SectionTitle')
        comm_layout.addWidget(comm_title)
        comm_cards_layout = QHBoxLayout()
        self.flop1_input = QComboBox(); self._populate_card_dropdown(self.flop1_input)
        self.flop2_input = QComboBox(); self._populate_card_dropdown(self.flop2_input)
        self.flop3_input = QComboBox(); self._populate_card_dropdown(self.flop3_input)
        self.turn_input = QComboBox(); self._populate_card_dropdown(self.turn_input)
        self.river_input = QComboBox(); self._populate_card_dropdown(self.river_input)
        for cb in [self.flop1_input, self.flop2_input, self.flop3_input, self.turn_input, self.river_input]:
            cb.setFixedWidth(90)
            cb.setObjectName('CardSlot')
            cb.setProperty('class', 'CardSlot')
        comm_cards_layout.addWidget(self.flop1_input)
        comm_cards_layout.addWidget(self.flop2_input)
        comm_cards_layout.addWidget(self.flop3_input)
        comm_cards_layout.addWidget(self.turn_input)
        comm_cards_layout.addWidget(self.river_input)
        comm_cards_layout.addStretch()
        comm_layout.addLayout(comm_cards_layout)
        comm_group.setLayout(comm_layout)
        comm_group.setProperty('class', 'CardGroup')
        main_layout.addWidget(comm_group)

        # Number of Players
        players_title = QLabel('Number of Players')
        players_title.setObjectName('SectionTitle')
        players_title.setProperty('class', 'SectionTitle')
        main_layout.addWidget(players_title)
        players_layout = QHBoxLayout()
        self.players_spin = QSpinBox()
        self.players_spin.setMinimum(2)
        self.players_spin.setMaximum(10)
        self.players_spin.setValue(2)
        self.players_spin.setFixedWidth(90)
        players_layout.addWidget(self.players_spin)
        players_layout.addStretch()
        main_layout.addLayout(players_layout)

        # Spacer before buttons
        main_layout.addItem(QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # Buttons
        self.calc_button = QPushButton('Calculate Odds')
        self.calc_button.setObjectName('Primary')
        self.calc_button.setProperty('class', 'Primary')
        self.calc_button.setFont(QFont('Segoe UI', 12, QFont.Bold))
        self.calc_button.setFixedHeight(44)
        self.calc_button.clicked.connect(self.calculate_odds)
        self.reset_button = QPushButton('Reset')
        self.reset_button.setObjectName('Secondary')
        self.reset_button.setProperty('class', 'Secondary')
        self.reset_button.setFont(QFont('Segoe UI', 12, QFont.Bold))
        self.reset_button.setFixedHeight(44)
        self.reset_button.clicked.connect(self.reset_fields)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(self.calc_button)
        btn_layout.addSpacing(20)
        btn_layout.addWidget(self.reset_button)
        btn_layout.addStretch()
        main_layout.addLayout(btn_layout)

        # Spacer before results
        main_layout.addItem(QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # Results area
        results_title = QLabel('Results')
        results_title.setObjectName('SectionTitle')
        results_title.setProperty('class', 'SectionTitle')
        main_layout.addWidget(results_title)
        self.results_area = QTextEdit()
        self.results_area.setObjectName('ResultsArea')
        self.results_area.setReadOnly(True)
        self.results_area.setMinimumHeight(260)
        self.results_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        main_layout.addWidget(self.results_area, stretch=1)

        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        # Load pre-flop cache from disk if available
        self.preflop_cache = self.load_preflop_cache()

    def _populate_card_dropdown(self, cb):
        cb.clear()
        cb.setEditable(False)
        cb.addItem('')  # Empty option
        for code, label in CARD_OPTIONS:
            cb.addItem(label, code)
        cb.setMinimumWidth(60)

    def _get_card(self, cb):
        code = cb.currentData()
        return code if code else ''

    def load_preflop_cache(self):
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, 'rb') as f:
                    return pickle.load(f)
            except Exception:
                return {}
        return {}

    def save_preflop_cache(self):
        try:
            with open(CACHE_FILE, 'wb') as f:
                pickle.dump(self.preflop_cache, f)
        except Exception:
            pass

    def calculate_odds(self):
        # Gather all card inputs from dropdowns
        card_inputs = [
            self._get_card(self.hand1_input), self._get_card(self.hand2_input),
            self._get_card(self.flop1_input), self._get_card(self.flop2_input), self._get_card(self.flop3_input),
            self._get_card(self.turn_input), self._get_card(self.river_input)
        ]
        players = self.players_spin.value()

        # Parse and validate cards
        parsed_cards = []
        errors = []
        for idx, card in enumerate(card_inputs):
            if card.strip() == '':
                continue  # Allow blanks for community cards
            parsed = parse_card(card)
            if not parsed:
                errors.append(f"Invalid card: '{card}' (use e.g. As, Td, 9h)")
            else:
                parsed_cards.append(parsed)

        # Check for duplicates
        if len(parsed_cards) != len(set(parsed_cards)):
            errors.append("Duplicate cards detected!")

        if errors:
            self.results_area.setText('\n'.join(errors))
            return

        # Success: show parsed cards and hand analysis
        hand = [self._get_card(self.hand1_input), self._get_card(self.hand2_input)]
        community = [self._get_card(self.flop1_input), self._get_card(self.flop2_input), self._get_card(self.flop3_input),
                     self._get_card(self.turn_input), self._get_card(self.river_input)]
        hand = [c for c in hand if c]
        board = [c for c in community if c]
        all_cards = hand + board
        hand_analysis = analyze_hand(all_cards)

        # Deuces hand strength
        if len(hand) == 2 and len(all_cards) >= 5:
            deuces_strength = deuces_hand_strength(hand, board)
        else:
            deuces_strength = "(Not enough cards for Deuces evaluation)"

        # Monte Carlo odds
        odds_str = ""
        hand_dist_str = ""
        if len(hand) == 2 and len(all_cards) >= 5:
            win_pct, tie_pct = monte_carlo_odds(hand, board, players, num_trials=75000)
            odds_str = f"Win: {win_pct:.1f}%, Tie: {tie_pct:.1f}% (est.)"
            # Hand distribution
            hand_type_counts = monte_carlo_hand_distribution(hand, board, num_trials=75000)
            total = sum(hand_type_counts.values())
            hand_dist_str = "<b>Possible Hands:</b><br>"
            for i in range(1, 10):
                name = Evaluator.class_to_string(None, i)
                pct = 100 * hand_type_counts.get(i, 0) / total if total else 0
                hand_dist_str += f"{name}: {pct:.1f}%<br>"
        else:
            odds_str = "(Not enough cards for odds simulation)"
            hand_dist_str = ""

        # Pre-flop only: show hand type odds for flop, turn, river
        if len(hand) == 2 and all(c == '' for c in board):
            key = tuple(sorted(hand)) + (players,)
            if key in self.preflop_cache:
                flop_counts, turn_counts, river_counts, win, tie = self.preflop_cache[key]
            else:
                flop_counts, turn_counts, river_counts, win, tie = monte_carlo_preflop_distributions(hand, players, num_trials=500000)
                self.preflop_cache[key] = (flop_counts, turn_counts, river_counts, win, tie)
                self.save_preflop_cache()
            flop_total = sum(flop_counts.values())
            turn_total = sum(turn_counts.values())
            river_total = sum(river_counts.values())
            win_pct = 100 * win / 500000
            tie_pct = 100 * tie / 500000
            hand_dist_str = "<b>Possible Hands by Flop, Turn, River:</b><br>"
            hand_dist_str += "<table style='width:100%;text-align:left;font-size:12pt; border-collapse:collapse;'>"
            hand_dist_str += "<tr><th style='padding-right:12px;'>Hand (Example)</th><th>Flop</th><th>Turn</th><th>River</th></tr>"
            for i in range(1, 10):
                name = Evaluator.class_to_string(None, i)
                example = HAND_TYPE_EXAMPLES[i]()
                flop_pct = 100 * flop_counts.get(i, 0) / flop_total if flop_total else 0
                turn_pct = 100 * turn_counts.get(i, 0) / turn_total if turn_total else 0
                river_pct = 100 * river_counts.get(i, 0) / river_total if river_total else 0
                hand_dist_str += f"<tr><td style='padding-right:12px;'>{example} <b>({name})</b></td><td>{flop_pct:.1f}%</td><td>{turn_pct:.1f}%</td><td>{river_pct:.1f}%</td></tr>"
            hand_dist_str += "</table>"
            hand_dist_str += "<div style='font-size:10pt; color:#aaa; margin-top:8px;'>Legend: <b>A</b>=Ace, <b>K</b>=King, <b>Q</b>=Queen, <b>J</b>=Jack, <b>T</b>=Ten, <span style='color:red;'>♥♦</span>=Hearts/Diamonds, <span style='color:#fff;'>♠♣</span>=Spades/Clubs</div>"
            odds_str = f"Win: {win_pct:.1f}%, Tie: {tie_pct:.1f}% (est. by river)"
            hand_html = ' '.join(card_label_html(c) for c in hand)
            result = (
                f"<b>Your hand:</b> {hand_html}<br>"
                f"<b>Players:</b> {players}<br>"
                f"<b>Pre-Flop Analysis</b><br>"
                f"<b>Odds to win:</b> {odds_str}<br>"
                f"{hand_dist_str}"
            )
            self.results_area.setHtml(result)
            self.results_area.moveCursor(0)
            return

        # Use HTML for colored cards
        hand_html = ' '.join(card_label_html(c) for c in hand)
        board_html = ' '.join(card_label_html(c) for c in board)
        result = (
            f"<b>Your hand:</b> {hand_html}<br>"
            f"<b>Community:</b> {board_html}<br>"
            f"<b>Players:</b> {players}<br>"
            f"<b>Best hand:</b> {hand_analysis}<br>"
            f"<b>Deuces hand strength:</b> {deuces_strength}<br>"
            f"<b>Odds to win:</b> {odds_str}<br>"
            f"{hand_dist_str}"
        )
        self.results_area.setHtml(result)
        self.results_area.moveCursor(0)  # Scroll to top

    def reset_fields(self):
        # Reset all dropdowns to empty
        for cb in [self.hand1_input, self.hand2_input, self.flop1_input, self.flop2_input, self.flop3_input, self.turn_input, self.river_input]:
            cb.setCurrentIndex(0)
        self.players_spin.setValue(2)
        self.results_area.clear()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = PokerOddsCalculator()
    window.show()
    sys.exit(app.exec_()) 