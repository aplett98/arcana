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


class Player:
    def __init__(self, id):
        self.id = id


class Deck:
    '''This class represents the one deck in any game.'''
    def __init__(self):
        self.cards = []
        self.size = 0
        suits = [Suit.SPY, Suit.WIZARD, Suit.CONVINCER, Suit.WARRIOR]
        card_id = 0
        for suit in suits:
            for value in range(2, 15):
                self.cards.append(Card(value, suit, card_id))
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
class Card:
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
        new.value = new.value if new.value is >= 0 else 0
        return new

    def __lt__(self, other):
        return self.value < other.value

    def __eq__(self, other):
        return self.value == other.value

    def soften(self):
        self.softened = True

    def show(self):
        self.shown = True


class Stack:
    '''The general class for stacks of a single suit.'''
    def __init__(self, suit, owner):
        self.size = 0
        self.owner = owner
        self.suit = suit
        self.cards = []

    def do_turn_action(args, action, target_punish, self_punish):
        challenged = False
        if not args.self_visible:
            challenged = args.target.decide_to_challenge()
        if args.legal or not challenged:
            action(args)
            if args.legal and challenged:
                target_punish(args)
        elif not args.legal and (challenged or not args.target_visible):
            self_punish(args)

    def highest(self):
        return self.cards[0]

    def lowest(self):
        return self.cards[self.size - 1]

    def strength(self):
        return sum(self.cards).value

    def sort(self):
        self.cards.sort().reverse()

    def get_crossed(self):
        if self.size > 1:
            new = self.highest() - self.lowest()
            self.cards = [new]
            self.size = 1

    def get_softened(self):
        if self.size is 1:
            self.cards[0].soften()

    def add(self, card):
        card.stack = self
        card.owner = owner
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
                return cards.pop(i)

    def has_hidden(self):
        for card in self.cards:
            if not card.shown:
                return True
        return False


class SpyStack(Stack):
    def __init__(self, owner):
        Stack.__init__(self, Suits.SPY, owner)

    def spy(self, target_card):
        if self.size < 1:
            raise TurnError('You can only spy if you have a spy card.')
        target_card.show()

    def capture(self, target_card):
        def action(a):
            self.owner.add(a.target_obj.stack.pop_card(a.target_obj))
            a.target_obj.show()
            self.destroy_highest()

        def target_punish(a):
            punish_stack = a.target.choose_stack(a.target)
            punish_stack.destroy_highest()

        def self_punish(a):
            punish_card = a.target.choose_card(self.owner)
            a.target.add(punish_card.stack.pop_card(punish_card))

        args = Args()
        args.self_visible = self.highest().shown
        args.target_visible = target_card.shown
        fully_visible = self_visible and target_visible
        args.legal = self.highest().value > target_card.value
        args.target_obj = target_card
        if self.size < 1:
            raise TurnError('You can only capture if you have a spy card.')
        if fully_visible and not args.legal:
            raise TurnError('Your highest spy card must be stronger.')
        self.do_turn_action(args, action, target_punish, self_punish)


class WizardStack(Stack):
    def __init__(self, owner):
        Stack.__init__(self, Suits.WIZARD, owner)

    def soften(self, target_stack, challenged):
        if target_stack.size > 1:
            return TurnError(
                'You can only soften a card if it is the only card in its '
                'stack.'
            )
        legal = self.strength() > target_stack.strength()
        target = target_stack.owner
        if legal or not challenged:
            target_stack.get_softened()
            if legal and challenged:
                punish_stack = target.choose_stack(target)
                punish_stack.destroy_highest()
        elif not legal and challenged:
            if self.size <= 1:
                self.destroy_highest()
            else:
                self.get_crossed()

    def cross(self, target_stack, challenged):
        if target_stack.size < 2:
            return TurnError(
                'You can only cross a stack if it has at least two cards.'
            )
        legal = self.strength() > target_stack.strength()
        target = target_stack.owner
        if legal or not challenged:
            target_stack.get_crossed()
            if legal and challenged:
                punish_stack = target.choose_stack(target)
                punish_stack.destroy_highest()
        elif not legal and challenged:
            if self.size <= 1:
                self.destroy_highest()
            else:
                self.get_crossed()


class ConvincerStack(Stack):
    def __init__(self, owner):
        Stack.__init__(self, Suit.CONVINCER, owner)

    def
