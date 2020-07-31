from aiohttp import web
import socketio
from pprint import pformat

import gameobjects
from gameobjects import Suit, Move, GameError

sio = socketio.AsyncServer()
app = web.Application()
sio.attach(app)
game = gameobjects.Game()
sid_to_num = {}
player_sids = []


class MsgError(Exception):
    """Raise when an incoming message cannot be parsed."""


def decode_target(data):
    target_player = None
    if 'suit' in data['target']:
        target = data['target']['suit']
    elif 'player' not in data['target']:
        raise MsgError("No target player specified.")
    elif 'stack' in data['target'] and 'card' in data['target']:
        target_player = data['target']['player']
        softened_suit = Suit(data['target']['card'][0])
        softened_pos = data['target']['card'][1]
        softened_card = target_player.stacks[softened_suit][softened_pos]
        target_suit = data['target']['stack']
        target_stack = target_player.stacks[target_suit]
        target = softened_card, target_stack
    elif 'stack' in data['target']:
        target_player = data['target']['player']
        suit = Suit(data['target']['stack'])
        target = target_player.stacks[suit]
    elif 'card' in data['target']:
        target_player = data['target']['player']
        suit = Suit(data['target']['card'][0])
        pos = data['target']['card'][1]
        target = target_player.stacks[suit][pos]
    else:
        raise MsgError("Invalid move target.")
    return target, target_player


def decode_move(data, player=None):
    # {
    # 'move':
    #   spy | capture | cross | soften | convince | cure | attack | martyr
    # 'source': {'stack': Suit} | {'card': Suit * Int}
    # 'target': {'player': Int, ('stack': Suit | 'card': Suit * Int)}
    #           | {'suit': Suit}
    # }
    if not all(key in data for key in ['move', 'source', 'target']):
        raise MsgError("Invalid move data.")
    if player is None:
        player = game.players[data['source']['player']]
    move = Move(data['move'])
    if 'stack' in data['source']:
        suit = Suit(data['source']['stack'])
        source = player.stacks[suit]
    elif 'card' in data['source']:
        suit = Suit(data['source']['card'][0])
        pos = data['source']['card'][1]
        source = player.stacks[suit][pos]
    else:
        raise MsgError("Invalid move source.")

    target, target_player = decode_target(data)
    return move, source, target, player, target_player


async def index(request):
    return web.Response(text=pformat(game.get_state()), content_type='text')

app.router.add_get('/', index)


@sio.event
async def connect(sid, environ):
    print("Connecting...")
    id = game.add_player()
    print("Connected Player %d." % (id+1))
    sid_to_num[sid] = id
    player_sids.append(sid)
    sio.emit('joined', id, room=sid)
    sio.emit('state_change', game.get_state())


@sio.event
async def start_game(sid):
    print("Starting game...")
    game.start()
    print("Game started.")
    sio.emit('state_change', game.get_state())


@sio.event
async def try_move(sid, data):
    player = game.players[sid_to_num[sid]]
    try:
        move, source, target, _, target_player = decode_move(
            data, player=player)
    except MsgError as err:
        sio.emit('msg_error', err.message, room=sid)
        return
    if game.move_is_challengeable(move, source, target):
        data['source']['player'] = player.id
        room = None if target_player is None else player_sids[target_player.id]
        sio.emit('offer_challenge', data, room=room)
    else:
        try:
            game.handle_move(move, source, target)
        except GameError as err:
            room = None if err.player is None else player_sids[err.player]
            sio.emit('game_error', err.message, room=room)
        else:
            sio.emit('state_change', game.get_state())


@sio.event
async def challenge(sid, data):
    target_player = game.players[sid_to_num[sid]]
    try:
        move, source, target, player, _ = decode_move(data)
        attacker_won = game.handle_challenge(move, source, target)
        if attacker_won:
            game.handle_move(move, source, target)
            sio.emit('state_change', game.get_state())
    except MsgError as err:
        sio.emit('msg_error', err.message, room=sid)
        return
    except GameError as err:
        room = None if err.player is None else player_sids[err.player]
        sio.emit('game_error', err.message, room=room)
        return
    sio.emit('challenge_results', {
        'winner': player.id if attacker_won else target_player.id,
        'loser': target_player.id if attacker_won else player.id
    })


@sio.event
async def punish(sid, data):
    player = game.players[sid_to_num[sid]]
    try:
        if 'move' in data:
            move = data['move']
        else:
            raise MsgError("No move specified for punishment.")
        target, _ = decode_target(data)
        game.handle_punish(player, move, target)
    except MsgError as err:
        sio.emit('msg_error', err.message, room=sid)
    except GameError as err:
        room = None if err.player is None else player_sids[err.player]
        sio.emit('game_error', err.message, room=room)
    else:
        sio.emit('state_change', game.get_state)


@sio.event
async def get_nplayers(sid):
    print(sid)
    print("There are %d players." % game.nplayers())
    async with sio.session(sid) as session:
        if 'id' in session:
            print("You are Player %d." % (session['id']+1))
        else:
            print("You are not in the game.")


if __name__ == '__main__':
    web.run_app(app)
