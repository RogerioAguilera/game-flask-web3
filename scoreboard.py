"""Local scoreboard transaction preparation; wallet sends the transaction."""
import os
import time
from eth_abi import encode
from eth_account import Account
from eth_account.messages import encode_defunct
from flask import Blueprint, current_app, jsonify, request, session
from web3 import Web3

scoreboard = Blueprint('scoreboard', __name__)


def configuration():
    address = os.getenv('SCOREBOARD_ADDRESS', '')
    key = os.getenv('SCOREBOARD_SIGNER_KEY', '')
    enabled = (Web3.is_address(address) and int(address, 16) != 0 and bool(key)
               and current_app.secret_key != 'supersecretkey')
    return address, key, enabled


@scoreboard.get('/scoreboard/config')
def config():
    address, _, enabled = configuration()
    return jsonify(enabled=enabled, address=address if enabled else None,
                   chainId='0x7a69', chainName='Anvil local', rpcUrl='http://127.0.0.1:8545')


@scoreboard.post('/scoreboard/transaction')
def transaction():
    address, key, enabled = configuration()
    if not enabled:
        return jsonify(error='Placar local não configurado.'), 503
    if 'result_correct' not in session or not session.get('game_id'):
        return jsonify(error='Conclua a partida e confirme o resultado primeiro.'), 409
    data = request.get_json(silent=True)
    player = data.get('player') if isinstance(data, dict) else None
    if not isinstance(player, str) or not Web3.is_address(player):
        return jsonify(error='Endereço da carteira inválido.'), 400
    player = Web3.to_checksum_address(player)
    address = Web3.to_checksum_address(address)
    deadline = int(time.time()) + 600
    game_id = bytes.fromhex(session['game_id'])
    correct, questions = session['result_correct'], session['steps']
    payload = Web3.keccak(encode(
        ['uint256', 'address', 'address', 'bytes32', 'bool', 'uint256', 'uint256'],
        [31337, address, player, game_id, correct, questions, deadline]))
    try:
        signature = Account.sign_message(encode_defunct(primitive=payload), key)
    except (ValueError, TypeError):
        return jsonify(error='Chave de assinatura do placar inválida.'), 503
    types = ['bytes32', 'bool', 'uint256', 'uint256', 'uint8', 'bytes32', 'bytes32']
    args = [game_id, correct, questions, deadline, signature.v,
            signature.r.to_bytes(32, 'big'), signature.s.to_bytes(32, 'big')]
    selector = Web3.keccak(text='recordResult(bytes32,bool,uint256,uint256,uint8,bytes32,bytes32)')[:4]
    return jsonify(to=address, data='0x' + (selector + encode(types, args)).hex(),
                   chainId='0x7a69', value='0x0')
