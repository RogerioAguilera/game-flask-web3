import json
from types import SimpleNamespace
import pytest
from eth_account import Account
from scripts import deploy_scoreboard as deploy


@pytest.fixture
def environment(tmp_path, monkeypatch):
    for key in list(deploy.os.environ):
        if key.startswith('SCOREBOARD_') or key == 'SECRET_KEY':
            monkeypatch.delenv(key)
    account = Account.create()
    (tmp_path / '.env').write_text('SCOREBOARD_SEPOLIA_RPC_URL=https://eth-sepolia.g.alchemy.com/v2/test-token\n'
                                 f'SCOREBOARD_DEPLOYER_KEY={account.key.hex()}\n')
    artifact = tmp_path / 'contracts/out/GameScoreboard.sol/GameScoreboard.json'
    artifact.parent.mkdir(parents=True)
    artifact.write_text(json.dumps({'abi': [], 'bytecode': {'object': '0x6000'}}))
    monkeypatch.setattr(deploy, 'ROOT', tmp_path)
    monkeypatch.setattr(deploy.subprocess, 'run', lambda *a, **kw: None)
    class Constructor:
        def estimate_gas(self, tx):
            return 100000
        def build_transaction(self, tx):
            return {**tx, 'data': '0x6000'}
    class Eth:
        chain_id = 11155111
        max_priority_fee = 2
        balance = 10**18
        sent = []
        @property
        def accounts(self):
            raise AssertionError('Public RPC must not use unlocked accounts')
        def contract(self, **kw):
            return SimpleNamespace(constructor=lambda authority: Constructor())
        def get_transaction_count(self, address, block):
            assert block == 'pending'
            return 0
        def get_block(self, block):
            return {'baseFeePerGas': 10}
        def get_balance(self, address, block):
            return self.balance
        def send_raw_transaction(self, raw):
            assert Account.recover_transaction(raw) == account.address
            self.sent.append(raw)
            return b'\x01' * 32
        def wait_for_transaction_receipt(self, hash, **kw):
            return SimpleNamespace(status=1, contractAddress='0x'+'12'*20)
    fake = SimpleNamespace(eth=Eth(), is_connected=lambda: True, from_wei=deploy.Web3.from_wei)
    # A callable factory with the provider constructor used by main.
    def web3_factory(provider):
        return fake
    web3_factory.HTTPProvider = lambda *a, **kw: None
    monkeypatch.setattr(deploy, 'Web3', web3_factory)
    return tmp_path, fake.eth


def test_preview_does_not_send_or_write_secrets(environment, monkeypatch, capsys):
    root, eth = environment
    monkeypatch.setattr(deploy.sys, 'argv', ['deploy', '--network', 'sepolia'])
    deploy.main()
    assert not eth.sent and not (root / '.env.scoreboard').exists()
    assert not (root / '.env.scoreboard.pending').exists()
    assert 'test-token' not in capsys.readouterr().out


def test_public_deployment_signs_locally_and_saves_configuration(environment, monkeypatch):
    root, eth = environment
    monkeypatch.setattr(deploy.sys, 'argv', ['deploy', '--network', 'sepolia', '--broadcast'])
    deploy.main()
    assert len(eth.sent) == 1
    saved = deploy.dotenv_values(root / '.env.scoreboard')
    assert saved['SCOREBOARD_CHAIN_ID'] == '11155111'
    assert saved['SCOREBOARD_ADDRESS'] == '0x'+'12'*20
    assert 'SCOREBOARD_DEPLOYER_KEY' not in saved
    assert (root / '.env.scoreboard').stat().st_mode & 0o777 == 0o600


def test_insufficient_balance_prevents_broadcast(environment, monkeypatch):
    root, eth = environment
    eth.balance = 0
    monkeypatch.setattr(deploy.sys, 'argv', ['deploy', '--network', 'sepolia', '--broadcast'])
    with pytest.raises(SystemExit, match='Saldo insuficiente'):
        deploy.main()
    assert not eth.sent


def test_timeout_keeps_recovery_information(environment, monkeypatch):
    root, eth = environment
    def timeout(*a, **kw):
        raise TimeoutError('provider failure')
    eth.wait_for_transaction_receipt = timeout
    monkeypatch.setattr(deploy.sys, 'argv', ['deploy', '--network', 'sepolia', '--broadcast'])
    with pytest.raises(TimeoutError):
        deploy.main()
    pending = deploy.dotenv_values(root / '.env.scoreboard.pending')
    assert pending['SCOREBOARD_DEPLOY_TX'].startswith('0x')
    assert pending['SCOREBOARD_SIGNER_KEY']
    assert not (root / '.env.scoreboard').exists()
    with pytest.raises(SystemExit, match='pendente'):
        deploy.main()
    assert len(eth.sent) == 1
