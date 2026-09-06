import os
from types import SimpleNamespace
import scoreboard as scoreboard_module
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
    class FakeEth:
        @property
        def chain_id(self):
            return int(os.getenv('SCOREBOARD_CHAIN_ID', '1337'))

        def get_code(self, address):
            return b'\x60\x00'

        def call(self, transaction):
            if transaction['data'] == Web3.keccak(text='authority()')[:4]:
                return encode(['address'], [Account.from_key(key).address])
            return encode(['uint256'] * 3, [0, 0, 0])

    monkeypatch.setattr(scoreboard_module, 'rpc_client', lambda url: SimpleNamespace(eth=FakeEth()))
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


@pytest.mark.parametrize("chain_id", [1337, 31337, 11155111])
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


@pytest.mark.parametrize('failure,message', [
    ('offline', 'indisponível'), ('chain', 'Rede incorreta'), ('missing', 'Contrato não encontrado'),
    ('authority', 'autoridade'), ('interface', 'incompatível')])
def test_health_blocks_registration(configured, monkeypatch, failure, message):
    client, _ = configured
    fake = scoreboard_module.rpc_client('unused')
    if failure == 'offline':
        # Simulate a transport error specifically on the RPC call.
        class Offline:
            @property
            def chain_id(self):
                raise ConnectionError('offline')
        fake.eth = Offline()
    elif failure == 'chain':
        fake.eth = SimpleNamespace(chain_id=1)
    elif failure == 'missing':
        fake.eth.get_code = lambda address: b''
    elif failure == 'authority':
        fake.eth.call = lambda tx: (encode(['address'], ['0x' + '56' * 20])
                                   if tx['data'] == Web3.keccak(text='authority()')[:4]
                                   else encode(['uint256'] * 3, [0, 0, 0]))
    else:
        fake.eth.call = lambda tx: b''
    monkeypatch.setattr(scoreboard_module, 'rpc_client', lambda url: fake)
    status = client.get('/scoreboard/config').json
    assert status['ready'] is False and message in status['error']
    client.post('/start_game')
    client.post('/answer', json={'answer': 'yes'})
    client.post('/feedback', json={'correct': True})
    response = client.post('/scoreboard/transaction', json={'player': '0x' + '34' * 20})
    assert response.status_code == 503 and 'data' not in response.json


def test_scores_preserve_large_integers_and_zero(configured, monkeypatch):
    client, _ = configured
    player = '0x' + '34' * 20
    zero = client.get('/scoreboard/scores/' + player)
    assert zero.status_code == 200 and zero.json['games'] == '0'
    fake = scoreboard_module.rpc_client('unused')
    original = fake.eth.call
    fake.eth.call = lambda tx: (original(tx) if tx['data'] == Web3.keccak(text='authority()')[:4]
                               else encode(['uint256'] * 3, [2**60, 2**59, 2**64]))
    monkeypatch.setattr(scoreboard_module, 'rpc_client', lambda url: fake)
    data = client.get('/scoreboard/scores/' + player).json
    assert data['games'] == str(2**60) and data['totalQuestions'] == str(2**64)
    assert client.get('/scoreboard/scores/invalid').status_code == 400


def test_sepolia_never_exposes_alchemy_key(configured, monkeypatch):
    client, _ = configured
    monkeypatch.setenv('SCOREBOARD_CHAIN_ID', '11155111')
    monkeypatch.setenv('SCOREBOARD_CHAIN_NAME', 'Sepolia')
    monkeypatch.setenv('SCOREBOARD_RPC_URL', 'https://eth-sepolia.g.alchemy.com/v2/private-test-token')
    response = client.get('/scoreboard/config')
    assert response.json['ready'] is True
    assert response.json['rpcUrl'] == 'https://ethereum-sepolia-rpc.publicnode.com'
    assert 'private-test-token' not in response.get_data(as_text=True)
    class Offline:
        @property
        def chain_id(self):
            raise ConnectionError('https://eth-sepolia.g.alchemy.com/v2/private-test-token')
    monkeypatch.setattr(scoreboard_module, 'rpc_client', lambda url: SimpleNamespace(eth=Offline()))
    response = client.get('/scoreboard/config')
    assert response.json['ready'] is False
    assert 'private-test-token' not in response.get_data(as_text=True)


@pytest.mark.parametrize('chain,url', [
    (1, 'https://eth-mainnet.g.alchemy.com/v2/test'),
    (1, 'https://eth-sepolia.g.alchemy.com/v2/test'),
    (11155111, 'http://eth-sepolia.g.alchemy.com/v2/test'),
    (11155111, 'https://eth-sepolia.g.alchemy.com.attacker.example/v2/test')])
def test_public_network_allowlist(chain, url):
    from scoreboard_network import network_configuration
    with pytest.raises(ValueError):
        network_configuration({'SCOREBOARD_CHAIN_ID': str(chain), 'SCOREBOARD_RPC_URL': url})
