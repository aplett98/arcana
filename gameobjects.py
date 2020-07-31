from enum import IntEnum
import random


class Suit(IntEnum):
    SPY = 0
    WIZARD = 1
    CONVINCER = 2
    WARRIOR = 3

    def __str__(self):
        return {
            Suit.SPY: 'spy',
            Suit.WIZARD: 'wizard',
            Suit.CONVINCER: 'convincer',
            Suit.WARRIOR: 'warrior'
        }[self]

    def to_card(self):
        return {
            Suit.SPY: SpyCard,
            Suit.WIZARD: WizardCard,
            Suit.CONVINCER: ConvincerCard,
            Suit.WARRIOR: WarriorCard
        }[self]

    def to_stack(self):
        return {
            Suit.SPY: SpyStack,
            Suit.WIZARD: WizardStack,
            Suit.CONVINCER: ConvincerStack,
            Suit.WARRIOR: WarriorStack
        }[self]


class Move(IntEnum):
    SPY = 0
    CAPTURE = 1
    CROSS = 2
    SOFTEN = 3
    CONVINCE = 4
    CURE = 5
    ATTACK = 6
    MARTYR = 7


class GameError(Exception):
    '''For when an invalid or illegal action is taken.'''
    def __init__(self, message, player=None):
        self.message = message
        self.player = player


class Game(object):
    def __init__(self):
        self.players = []
        self.started = False
        self.deck = Deck(self)

    def start(self):
        if self.started:
            return
        deal = self.deck.deal(self.nplayers())
        for suit in deal:
            for i, card in enumerate(deal[suit]):
                # add card to player i's relevant stack
                self.players[i].stacks[suit].add_card(card)
        self.started = True
        self.turn = 0
        self.start_turn()

    def add_player(self):
        id = self.nplayers()
        self.players.append(Player(id, self))
        return id

    def start_turn(self):
        self.used = {suit: False for suit in Suit}
        self.players[self.turn].draw()

    def next_turn(self):
        if self.started:
            self.turn = self.turn + 1 if self.turn < self.nplayers() else 0
            self.start_turn()

    def martyr(self, suit):
        for player in self.players:
            player.stacks[suit].empty()

    def nplayers(self):
        return len(self.players)

    def move_is_challengeable(self, move, source, target):
        # TODO
        pass

    def handle_move(self, move, source, target):
        # TODO
        pass

    def handle_challenge(self, move, source, target):
        # TODO
        pass

    def handle_punish(self, move, source, target):
        # TODO
        pass

    def get_state(self):
        state = {
            'started': self.started,
            'deck': self.deck.get_state(),
            'players': [player.get_state() for player in self.players],
        }
        if self.started:
            state = {**state, **{
                'turn': self.turn,
            }}
        return state


class Player(object):
    def __init__(self, id, game):
        self.id = id
        self.game = game
        self.stacks = {suit: suit.to_stack()(self) for suit in Suit}

    def add_card(self, card):
        self.stacks[card.suit].add_card(card)

    def draw(self):
        new_card = self.game.deck.pop_card()
        self.add_card(new_card)

    def get_state(self):
        return {
            str(suit):
                stack.get_state() for (suit, stack) in self.stacks.items()
            }


class Deck(object):
    '''This class represents the one deck in any game.'''
    def __init__(self, game):
        self.cards = []
        self.game = game
        card_id = 0
        for suit in Suit:
            for strength in range(1, 15):
                new_card = suit.to_card()(strength, card_id, self.game)
                self.cards.append(new_card)
                card_id += 1
        random.shuffle(self.cards)

    def pop_card(self):
        if self.size() > 1:
            card = self.cards.pop()
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
        return {
            Suit.SPY: spies[:nplayers],
            Suit.WIZARD: wizards[:nplayers],
            Suit.CONVINCER: convincers[:nplayers],
            Suit.WARRIOR: warriors[:nplayers],
        }

    def size(self):
        return len(self.cards)

    def get_state(self):
        return {'size': self.size()}


class Card(object):
    '''The general class for cards in the game.'''
    def __init__(self, strength, suit, id, game):
        self.id = id
        self.game = game
        self.strength = strength
        self.suit = suit
        self.stack = None
        self.shown = False
        self.owner = None
        self.softened = False

    def pop_from_stack(self):
        return self.stack.pop_card(self)

    def strength(self):
        return self.strength

    def get_state(self):
        return {
            'strength': self.strength,
            'softened': self.softened,
            'shown': self.shown,
        }


class Stack(object):
    '''The general class for stacks of a single suit.'''
    def __init__(self, suit, owner):
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
        return sum([card.strength for card in self.cards])

    def sort(self):
        self.cards.sort()
        self.cards.reverse()

    def add_card(self, card):
        card.stack = self
        card.owner = self.owner
        self.cards.append(card)
        self.sort()
        self.size += 1

    def pop_highest(self):
        return self.cards.pop(0)

    def pop_lowest(self):
        return self.cards.pop()

    def pop_card(self, target_card, position=None):
        if position is None:
            for i, card in self.cards:
                if card is target_card:
                    self.size -= 1
                    return self.cards.pop(i)
        else:
            return self.cards.pop(position)

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

    def get_state(self):
        return {
            'strength': self.strength(),
            'cards': [card.get_state() for card in self.cards]
        }


class SpyCard(Card):
    def __init__(self, strength, id, game):
        Card.__init__(self, strength, Suit.SPY, id, game)

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
    def __init__(self, strength, id, game):
        Card.__init__(self, strength, Suit.WIZARD, id, game)


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
    def __init__(self, strength, id, game):
        Card.__init__(self, strength, Suit.CONVINCER, id, game)

    def cure(self, target_card):
        target_card.softened = False


class ConvincerStack(Stack):
    def __init__(self, owner):
        Stack.__init__(self, Suit.CONVINCER, owner)

    def convince(self, target_stack):
        target_stack.pop_lowest()


class WarriorCard(Card):
    def __init__(self, strength, id, game):
        Card.__init__(self, strength, Suit.WARRIOR, id, game)


class WarriorStack(Stack):
    def __init__(self, owner):
        Stack.__init__(self, Suit.WARRIOR, owner)

    def attack(self, target_card):
        target_card.pop_from_stack()

    def martyr(self, suit):
        self.game.martyr(suit)
        if not self.is_empty():
            self.cards = [self.highest()]
