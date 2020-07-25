from enum import Enum
import random
from functools import total_ordering


class Args(object):
    pass


class Suit(Enum):
    SPY = 0
    WIZARD = 1
    CONVINCER = 2
    WARRIOR = 3

class TurnError(Exception):
    '''For when an invalid action is taken on a turn.'''
    pass


class Player(object):
    def __init__(self, id):
        self.id = id


class Deck(object):
    '''This class represents the one deck in any game.'''
    def __init__(self):
        self.cards = []
        self.size = 0
        card_id = 0
        for suit in suits:
            for value in range(2, 15):
                new_card = suit_to_card[suit](value, card_id)
                self.cards.append(new_card)
                self.size += 1
                card_id += 1
        random.shuffle(self.cards)

    def draw(self, player):
        if self.size > 1:
            card = self.cards.pop()
            self.size -= 1
            player.take(card)  # player.take needs to be implemented

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
        return [
            spies[:nplayers],
            wizards[:nplayers],
            convincers[:nplayers],
            warriors[:nplayers],
        ]


@total_ordering
class Card(object):
    '''The general class for cards in the game.'''
    def __init__(self, value, suit, id):
        self.id = id
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

    def soften(self):
        self.softened = True

    def show(self):
        self.shown = True


class Stack(object):
    '''The general class for stacks of a single suit.'''
    def __init__(self, suit, owner):
        self.size = 0
        self.owner = owner
        self.suit = suit
        self.cards = []

    def do_turn_action(self, args, action, target_punish, self_punish):
        challenged = False
        if not args.self_visible:
            challenged = args.target.decide_to_challenge()
        if args.legal or not challenged:
            action(args)
            if args.legal and challenged:
                target_punish(args)
        elif not args.legal and (challenged or not args.target_visible):
            self_punish(args)

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

    def add(self, card):
        card.stack = self
        card.owner = self.owner
        self.cards.append(card)
        self.sort()
        self.size += 1

    def destroy_highest(self):
        self.cards.pop(0)
        self.size -= 1

    def destroy_lowest(self):
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


class SpyCard(Card):
    def __init__(self, value, id):
        Card.__init__(self, value, Suit.SPY, id)

    def capture(self, target_card):
        # TODO
        pass


class SpyStack(Stack):
    def __init__(self, owner):
        Stack.__init__(self, Suit.SPY, owner)

    def spy(self, target_card):
        if self.size < 1:
            raise TurnError('You can only spy if you have a spy card.')
        target_card.show()


class WizardCard(Card):
    def __init__(self, value, id):
        Card.__init__(self, value, Suit.WIZARD, id)

class WizardStack(Stack):
    def __init__(self, owner):
        Stack.__init__(self, Suit.WIZARD, owner)
    
    def cross(self, target_stack):
        # TODO
        pass

    def soften(self, target_card):
        # TODO
        pass


class ConvincerCard(Card):
    def __init__(self, value, id):
        Card.__init__(self, value, Suit.CONVINCER, id)
    
    def cure(self, target_card):
        # TODO
        pass


class ConvincerStack(Stack):
    def __init__(self, owner):
        Stack.__init__(self, Suit.CONVINCER, owner)

    def convince(self, target_card):
        # TODO
        pass


class WarriorCard(Card):
    def __init__(self, value, id):
        Card.__init__(self, value, Suit.WARRIOR, id)


class WarriorStack(Stack):
    def __init__(self, owner):
        Stack.__init__(self, Suit.WARRIOR, owner)
    
    def attack(self, target_card):
        # TODO
        pass

    def martyr(self):
        # TODO
        pass


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
