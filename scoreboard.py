"""Scoreboard transaction preparation; wallet sends the transaction."""
import os
import time
from eth_abi import encode, decode
from functools import lru_cache
from eth_account import Account
from eth_account.messages import encode_defunct
from flask import Blueprint, current_app, jsonify, request, session
from web3 import Web3
from scoreboard_network import network_configuration

scoreboard = Blueprint('scoreboard', __name__)


def configuration():
    address = os.getenv('SCOREBOARD_ADDRESS', '')
    key = os.getenv('SCOREBOARD_SIGNER_KEY', '')
    enabled = (Web3.is_address(address) and int(address, 16) != 0 and bool(key)
               and current_app.secret_key != 'supersecretkey')
    return address, key, enabled


class ScoreboardUnavailable(Exception):
    pass


@lru_cache(maxsize=4)
def rpc_client(url):
    return Web3(Web3.HTTPProvider(url, request_kwargs={'timeout': 3},
                                exception_retry_configuration=None))


def read_scores(client, address, player):
    data = Web3.keccak(text='scores(address)')[:4] + encode(['address'], [player])
    return decode(['uint256', 'uint256', 'uint256'], client.eth.call({'to': address, 'data': data}))


def validated_contract(network, address, key):
    try:
        signer = Account.from_key(key).address
    except (ValueError, TypeError):
        raise ScoreboardUnavailable('Chave de assinatura inválida. Confira a configuração do servidor.')
    client = rpc_client(network['rpc_url'])
    try:
        actual_chain = client.eth.chain_id
    except Exception:
        raise ScoreboardUnavailable('Rede indisponível. Confira o RPC e a conexão; em redes locais, inicie Ganache ou Anvil.')
    if actual_chain != network['chain_id']:
        raise ScoreboardUnavailable(f"Rede incorreta: Chain ID {actual_chain}; esperado {network['chain_id']}.")
    address = Web3.to_checksum_address(address)
    try:
        code = client.eth.get_code(address)
    except Exception:
        raise ScoreboardUnavailable('Não foi possível consultar o contrato. Verifique a rede configurada.')
    if not code:
        raise ScoreboardUnavailable('Contrato não encontrado. Implante o placar novamente e reinicie Flask.')
    try:
        result = client.eth.call({'to': address, 'data': Web3.keccak(text='authority()')[:4]})
        authority = Web3.to_checksum_address(decode(['address'], result)[0])
        read_scores(client, address, '0x' + '00' * 20)
    except Exception:
        raise ScoreboardUnavailable('Contrato incompatível ou consulta indisponível. Confira o endereço do placar.')
    if authority != signer:
        raise ScoreboardUnavailable('A chave do servidor não corresponde à autoridade do contrato. Confira a implantação.')
    return client, address


@scoreboard.get('/scoreboard/config')
def config():
    address, _, enabled = configuration()
    try:
        network = network_configuration()
    except ValueError as error:
        return jsonify(enabled=False, error=str(error)), 503
    error = None
    ready = False
    if enabled:
        try:
            validated_contract(network, address, configuration()[1])
            ready = True
        except ScoreboardUnavailable as failure:
            error = str(failure)
    else:
        error = 'Placar não configurado. Implante o contrato na rede configurada para habilitar o registro.'
    return jsonify(enabled=enabled, ready=ready, error=error, address=address if enabled else None,
                   chainId=hex(network['chain_id']), chainName=network['name'], rpcUrl=network['wallet_rpc_url'])


@scoreboard.post('/scoreboard/transaction')
def transaction():
    address, key, enabled = configuration()
    try:
        network = network_configuration()
    except ValueError as error:
        return jsonify(error=str(error)), 503
    if not enabled:
        return jsonify(error='Placar não configurado.'), 503
    if 'result_correct' not in session or not session.get('game_id'):
        return jsonify(error='Conclua a partida e confirme o resultado primeiro.'), 409
    data = request.get_json(silent=True)
    player = data.get('player') if isinstance(data, dict) else None
    if not isinstance(player, str) or not Web3.is_address(player):
        return jsonify(error='Endereço da carteira inválido.'), 400
    player = Web3.to_checksum_address(player)
    try:
        _, address = validated_contract(network, address, key)
    except ScoreboardUnavailable as error:
        return jsonify(error=str(error)), 503
    deadline = int(time.time()) + 600
    game_id = bytes.fromhex(session['game_id'])
    correct, questions = session['result_correct'], session['steps']
    payload = Web3.keccak(encode(
        ['uint256', 'address', 'address', 'bytes32', 'bool', 'uint256', 'uint256'],
        [network['chain_id'], address, player, game_id, correct, questions, deadline]))
    try:
        signature = Account.sign_message(encode_defunct(primitive=payload), key)
    except (ValueError, TypeError):
        return jsonify(error='Chave de assinatura do placar inválida.'), 503
    types = ['bytes32', 'bool', 'uint256', 'uint256', 'uint8', 'bytes32', 'bytes32']
    args = [game_id, correct, questions, deadline, signature.v,
            signature.r.to_bytes(32, 'big'), signature.s.to_bytes(32, 'big')]
    selector = Web3.keccak(text='recordResult(bytes32,bool,uint256,uint256,uint8,bytes32,bytes32)')[:4]
    return jsonify(to=address, data='0x' + (selector + encode(types, args)).hex(),
                   chainId=hex(network['chain_id']), value='0x0')


@scoreboard.get('/scoreboard/scores/<player>')
def scores(player):
    if not Web3.is_address(player):
        return jsonify(error='Endereço da carteira inválido.'), 400
    address, key, enabled = configuration()
    if not enabled:
        return jsonify(error='Placar não configurado.'), 503
    try:
        network = network_configuration()
        client, address = validated_contract(network, address, key)
    except (ValueError, ScoreboardUnavailable) as error:
        return jsonify(error=str(error)), 503
    try:
        games, correct, questions = read_scores(client, address, Web3.to_checksum_address(player))
    except Exception:
        return jsonify(error='Não foi possível carregar o placar. Tente atualizar novamente.'), 503
    # Decimal strings preserve uint256 precision in the browser.
    response = jsonify(player=Web3.to_checksum_address(player), chainId=hex(network['chain_id']),
                       contract=address, games=str(games), correctGuesses=str(correct), totalQuestions=str(questions))
    response.headers['Cache-Control'] = 'no-store'
    return response
