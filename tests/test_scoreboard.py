import pytest
from eth_abi import decode, encode
from eth_account import Account
from eth_account.messages import encode_defunct
from web3 import Web3
import app as app_module


@pytest.fixture
def configured(client, monkeypatch):
    key = Account.create().key.hex()
    monkeypatch.setenv('SCOREBOARD_SIGNER_KEY', key)
    monkeypatch.setenv('SCOREBOARD_ADDRESS', '0x' + '12' * 20)
    monkeypatch.setitem(app_module.app.config, 'SECRET_KEY', 'test-only-random-session-key')
    return client, key


def test_disabled_without_configuration(client, monkeypatch):
    monkeypatch.delenv('SCOREBOARD_ADDRESS', raising=False)
    assert client.get('/scoreboard/config').json['enabled'] is False
    assert client.post('/scoreboard/transaction').status_code == 503


def test_requires_completed_game(configured):
    client, _ = configured
    client.post('/start_game')
    assert client.post('/scoreboard/transaction', json={}).status_code == 409
    assert client.post('/feedback', json={'correct': True}).status_code == 400


@pytest.mark.parametrize("chain_id", [1337, 31337])
def test_signed_result_uses_server_values(configured, monkeypatch, chain_id):
    monkeypatch.setenv("SCOREBOARD_CHAIN_ID", str(chain_id))
    client, key = configured
    client.post('/start_game')
    client.post('/answer', json={'answer': 'yes'})
    assert client.post('/feedback', json={'correct': True}).status_code == 200
    player = '0x' + '34' * 20
    response = client.post('/scoreboard/transaction', json={'player': player, 'questions': 999, 'correct': False})
    assert response.status_code == 200
    tx = response.json
    assert tx['chainId'] == hex(chain_id)
    game, correct, questions, deadline, v, r, s = decode(
        ['bytes32', 'bool', 'uint256', 'uint256', 'uint8', 'bytes32', 'bytes32'], bytes.fromhex(tx['data'][10:]))
    assert correct is True and questions == 1
    payload = Web3.keccak(encode(['uint256', 'address', 'address', 'bytes32', 'bool', 'uint256', 'uint256'],
                                [chain_id, tx['to'], player, game, correct, questions, deadline]))
    recovered = Account.recover_message(encode_defunct(primitive=payload), vrs=(v, int.from_bytes(r, 'big'), int.from_bytes(s, 'big')))
    assert recovered == Account.from_key(key).address
    assert client.post('/scoreboard/transaction', json={'player': []}).status_code == 400
    assert client.post('/feedback', json={'correct': False}).status_code == 409
    client.post('/start_game')
    assert client.post('/scoreboard/transaction', json={'player': player}).status_code == 409


@pytest.mark.parametrize('chain_id,name,port', [(1337, 'Ganache local', 7545), (31337, 'Anvil local', 8545)])
def test_network_config(configured, monkeypatch, chain_id, name, port):
    client, _ = configured
    monkeypatch.setenv('SCOREBOARD_CHAIN_ID', str(chain_id))
    monkeypatch.setenv('SCOREBOARD_CHAIN_NAME', name)
    monkeypatch.setenv('SCOREBOARD_RPC_URL', f'http://127.0.0.1:{port}')
    data = client.get('/scoreboard/config').json
    assert data['chainId'] == hex(chain_id)
    assert data['chainName'] == name
    assert data['rpcUrl'] == f'http://127.0.0.1:{port}'
    assert 'SCOREBOARD_SIGNER_KEY' not in data


@pytest.mark.parametrize('key,value', [('SCOREBOARD_CHAIN_ID', 'invalid'), ('SCOREBOARD_CHAIN_ID', '0'),
                                      ('SCOREBOARD_RPC_URL', 'https://example.com:8545')])
def test_invalid_network_fails_closed(configured, monkeypatch, key, value):
    client, _ = configured
    monkeypatch.setenv(key, value)
    assert client.get('/scoreboard/config').status_code == 503
    assert client.post('/scoreboard/transaction', json={}).status_code == 503
