from enum import IntEnum
import random


class Suit(IntEnum):
    SPY = 0
    WIZARD = 1
    CONVINCER = 2
    WARRIOR = 3

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

    def moves(self):
        return {
            Suit.SPY: {Move.SPY, Move.CAPTURE},
            Suit.WIZARD: {Move.CROSS, Move.SOFTEN},
            Suit.CONVINCER: {Move.CONVINCE, Move.CURE},
            Suit.WARRIOR: {Move.ATTACK, Move.MARTYR}
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

    def suit(self):
        return {
            move: suit for suit in Suit for move in suit.moves()
        }[self]

    def from_card(self):
        return self in {Move.CAPTURE, Move.CURE}

    def execute(self):
        return {
                Move.SPY: SpyStack.spy,
                Move.CAPTURE: SpyCard.capture,
                Move.CROSS: WizardStack.cross,
                Move.SOFTEN: WizardStack.soften,
                Move.CONVINCE: ConvincerStack.convince,
                Move.CURE: ConvincerCard.cure,
                Move.ATTACK: WarriorStack.attack,
                Move.MARTYR: WarriorStack.martyr,
            }[self]


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
            self.turn = self.turn + 1 if self.turn < self.nplayers()-1 else 0
            if self.players[self.turn].eliminated():
                # if player is eliminated, skip them
                self.next_turn()
            else:
                self.start_turn()

    def martyr(self, suit):
        for player in self.players:
            player.stacks[suit].empty()

    def nplayers(self):
        return len(self.players)

    def move_is_challengeable(self, move, source, target):
        """
            Returns True if the given move is challengeable,
            and False otherwise.
        """
        if move is Move.SPY:
            return False
        elif move is Move.MARTYR:
            return source.min_known_strength() < 10
        elif move is Move.CONVINCE:
            softened = target[0]
            return source.min_known_strength <= softened.min_known_strength()
        else:
            return source.min_known_strength() <= target.min_known_strength()

    def handle_move(self, move, source, target):
        """Update game state according to the move."""
        if move is Move.CONVINCE and type(target) is tuple:
            # target should be a tuple of softened, target_stack
            target = target[1]
        elif move is Move.CONVINCE or type(target) is tuple:
            raise GameError(
                "Invalid target.", player=source.owner.id)
        try:
            make_move = move.execute()
            make_move(source, target)
        except AttributeError:
            raise GameError(
                "This move is illegal.", player=source.owner.id)

    def handle_challenge(self, move, source, target):
        """
            Returns True if the attacker (source) won the challenge,
            and False otherwise.
            If the attacker won, execute the move.
        """
        if move is Move.CONVINCE and type(target) is tuple:
            # target should be a tuple of softened, target_stack
            softened = target[0]
            source.show()
            softened.show()
            if source.strength() <= softened.strength():
                return False
        elif move is Move.CONVINCE or type(target) is tuple:
            raise GameError(
                "Invalid target.", player=source.owner.id)
        elif move is move.SPY:
            raise GameError("Spying cannot be challenged.")
        elif move is move.MARTYR:
            source.show()
            if source.strength() < 10:
                return False
        else:
            source.show()
            target.show()
            if source.strength() <= target.strength():
                return False
        # at this point, the attacker has won the challenge.
        self.handle_move(move, source, target)
        return True

    def handle_punish(self, player, move, target):
        suit = move.suit()
        # dummy card with infinite strength
        captain_card = suit.to_card()(100, -1, self)
        if move.from_card():
            captain = captain_card
            captain.owner = player
        else:
            # dummy stack with infinite strength
            captain = suit.to_stack()(player).add_card(captain_card)
        self.handle_move(move, captain, target)

    def check_win_condition(self):
        """
        If a player meets the win condition, return their pid.
        Otherwise, return None.
        """
        remaining = [
            player for player in self.players if not player.eliminated()
        ]
        return remaining[0] if len(remaining) == 1 else None

    def get_state(self, pid=None):
        state = {
            'started': self.started,
            'deck': self.deck.get_state(),
            'players': [
                player.get_state(private=(id == pid))
                for id, player in enumerate(self.players)
            ],
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

    def eliminated(self):
        return all(stack.is_empty() for stack in self.stacks.values())

    def get_state(self, private=False):
        return {
            suit.value:
                stack.get_state(private=private)
                for (suit, stack) in self.stacks.items()
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
            return self.cards.pop()

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


class Suited():
    """Superclass for cards and stacks."""
    def __init__(self, suit, owner=None):
        self.suit = suit
        self.owner = owner

    def strength(self) -> int:
        raise NotImplementedError("Implement this function.")

    def min_known_strength(self) -> int:
        raise NotImplementedError("Implement this function.")

    def show(self):
        raise NotImplementedError("Implement this function.")


class Card(Suited):
    '''The general class for cards in the game.'''
    def __init__(self, value, suit, id, game):
        Suited.__init__(self, suit)
        self.id = id
        self.game = game
        self.value = value
        self.stack = None
        self.shown = False
        self.softened = False

    def pop_from_stack(self):
        return self.stack.pop_card(self)

    def min_known_strength(self):
        return self.strength() if self.shown else 1

    def strength(self):
        return self.value

    def show(self):
        self.shown = True

    def get_state(self, private=True):
        return {
            'strength':
                self.strength() if private or self.shown
                else self.min_known_strength(),
            'softened': self.softened,
            'shown': self.shown,
        }


class Stack(Suited):
    '''The general class for stacks of a single suit.'''
    def __init__(self, suit, owner):
        Suited.__init__(self, suit, owner)
        self.game = self.owner.game
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

    def min_known_strength(self):
        return sum(card.min_known_strength() for card in self.cards)

    def strength(self):
        return sum(card.strength() for card in self.cards)

    def sort(self):
        self.cards.sort(key=Card.strength)
        self.cards.reverse()

    def add_card(self, card):
        card.stack = self
        card.owner = self.owner
        self.cards.append(card)
        self.sort()

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

    def show(self):
        for card in self.cards:
            card.show()

    def get_state(self, private=False):
        return {
            'strength':
                self.strength() if private
                else self.min_known_strength(),
            'cards': [card.get_state(private=private) for card in self.cards]
        }


class SpyCard(Card):
    def __init__(self, strength, id, game):
        Card.__init__(self, strength, Suit.SPY, id, game)

    def capture(self, target_card):
        new_card = target_card.pop_from_stack()
        self.owner.add_card(new_card)
        self.pop_from_stack()
        self.game.next_turn()


class SpyStack(Stack):
    def __init__(self, owner):
        Stack.__init__(self, Suit.SPY, owner)

    def spy(self, target_card):
        target_card.show()
        self.game.next_turn()


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
        target_card.shown = True


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
