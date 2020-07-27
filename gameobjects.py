from enum import Enum
import random
from functools import total_ordering


class Suit(Enum):
    SPY = 0
    WIZARD = 1
    CONVINCER = 2
    WARRIOR = 3


class TurnError(Exception):
    '''For when an invalid action is taken on a turn.'''
    pass


class Game(object):
    def __init__(self, nplayers):
        self.nplayers = nplayers
        self.players = [Player(i, self) for i in range(self.nplayers)]
        self.deck = Deck(self)
        self.turn = 0
        deal = self.deck.deal(self.nplayers)
        for suit in deal:
            for i, card in enumerate(deal[suit]):
                # add card to player i's relevant stack
                self.players[i].stacks[suit].add_card(card)

    def next_turn(self):
        self.turn = self.turn + 1 if self.turn < self.nplayers else 0

    def martyr(self, suit):
        for player in self.players:
            player.stacks[suit].empty()


class Player(object):
    def __init__(self, id, game):
        self.id = id
        self.game = game
        self.stacks = {suit: suit_to_stack[suit](self) for suit in suits}

    def add_card(self, card):
        self.stacks[card.suit].add_card(card)

    def draw(self):
        new_card = self.game.deck.pop_card()
        self.add_card(new_card)


class Deck(object):
    '''This class represents the one deck in any game.'''
    def __init__(self, game):
        self.cards = []
        self.size = 0
        self.game = game
        card_id = 0
        for suit in suits:
            for value in range(1, 15):
                new_card = suit_to_card[suit](value, card_id, self.game)
                self.cards.append(new_card)
                self.size += 1
                card_id += 1
        random.shuffle(self.cards)

    def pop_card(self):
        if self.size > 1:
            card = self.cards.pop()
            self.size -= 1
            return card

    def deal(self, nplayers):
        spies = [c for c in self.cards if c.suit is Suit.SPY]
        wizards = [c for c in self.cards if c.suit is Suit.WIZARD]
        convincers = [c for c in self.cards if c.suit is Suit.CONVINCER]
        warriors = [c for c in self.cards if c.suit is Suit.WARRIOR]
        remaining = (
            spies[nplayers:] + wizards[nplayers:] +
            convincers[nplayers:] + warriors[nplayers:]
        )
        random.shuffle(remaining)
        self.cards = remaining
        self.size = len(self.cards)
        return {
            Suit.SPY: spies[:nplayers],
            Suit.WIZARD: wizards[:nplayers],
            Suit.CONVINCER: convincers[:nplayers],
            Suit.WARRIOR: warriors[:nplayers],
        }


@total_ordering
class Card(object):
    '''The general class for cards in the game.'''
    def __init__(self, value, suit, id, game):
        self.id = id
        self.game = game
        self.value = value
        self.suit = suit
        self.stack = None
        self.shown = False
        self.owner = None
        self.softened = False

    def __add__(self, other):
        new = self
        new.value += other.value
        return new

    def __radd__(self, other):
        if other is 0:
            return self
        else:
            return self.__add__(other)

    def __sub__(self, other):
        new = self
        new.value -= other.value
        new.value = new.value if new.value >= 0 else 0
        return new

    def __lt__(self, other):
        return self.value < other.value

    def __eq__(self, other):
        return self.value == other.value

    def pop_from_stack(self):
        return self.stack.pop_card(self)


class Stack(object):
    '''The general class for stacks of a single suit.'''
    def __init__(self, suit, owner):
        self.size = 0
        self.owner = owner
        self.suit = suit
        self.cards = []

    def highest(self, n=None):
        if n is None:
            return self.cards[0]
        elif n > 0:
            return self.cards[:n]

    def lowest(self, n=None):
        if n is None:
            return self.cards[-1]
        elif n > 0:
            return reversed(self.cards[-int(n):])

    def strength(self):
        return sum(self.cards).value

    def sort(self):
        self.cards.sort().reverse()

    def add_card(self, card):
        card.stack = self
        card.owner = self.owner
        self.cards.append(card)
        self.sort()
        self.size += 1

    def pop_highest(self):
        self.cards.pop(0)
        self.size -= 1

    def pop_lowest(self):
        self.cards.pop()
        self.size -= 1

    def pop_card(self, target_card):
        for i, card in self.cards:
            if card is target_card:
                self.size -= 1
                return self.cards.pop(i)

    def has_hidden(self):
        for card in self.cards:
            if not card.shown:
                return True
        return False

    def empty(self):
        self.cards = []
        self.size = 0

    def is_empty(self):
        return not self.cards


class SpyCard(Card):
    def __init__(self, value, id):
        Card.__init__(self, value, Suit.SPY, id)

    def capture(self, target_card):
        new_card = target_card.pop_from_stack()
        self.owner.add_card(new_card)
        self.pop_from_stack()


class SpyStack(Stack):
    def __init__(self, owner):
        Stack.__init__(self, Suit.SPY, owner)

    def spy(self, target_card):
        target_card.shown = True


class WizardCard(Card):
    def __init__(self, value, id):
        Card.__init__(self, value, Suit.WIZARD, id)


class WizardStack(Stack):
    def __init__(self, owner):
        Stack.__init__(self, Suit.WIZARD, owner)

    def cross(self, target_stack):
        highest = target_stack.highest()
        highest -= target_stack.lowest()
        target_stack.cards = [highest]

    def soften(self, target_card):
        target_card.softened = True


class ConvincerCard(Card):
    def __init__(self, value, id):
        Card.__init__(self, value, Suit.CONVINCER, id)

    def cure(self, target_card):
        target_card.softened = False


class ConvincerStack(Stack):
    def __init__(self, owner):
        Stack.__init__(self, Suit.CONVINCER, owner)

    def convince(self, target_stack):
        target_stack.pop_lowest()


class WarriorCard(Card):
    def __init__(self, value, id):
        Card.__init__(self, value, Suit.WARRIOR, id)


class WarriorStack(Stack):
    def __init__(self, owner):
        Stack.__init__(self, Suit.WARRIOR, owner)

    def attack(self, target_card):
        target_card.pop_from_stack()

    def martyr(self, suit):
        self.game.martyr(suit)
        if not self.is_empty():
            self.cards = [self.highest()]


suits = [Suit.SPY, Suit.WIZARD, Suit.CONVINCER, Suit.WARRIOR]
suit_to_card = {
    Suit.SPY: SpyCard,
    Suit.WIZARD: WizardCard,
    Suit.CONVINCER: ConvincerCard,
    Suit.WARRIOR: WarriorCard
}
suit_to_stack = {
    Suit.SPY: SpyStack,
    Suit.WIZARD: WizardStack,
    Suit.CONVINCER: ConvincerStack,
    Suit.WARRIOR: WarriorStack
}
