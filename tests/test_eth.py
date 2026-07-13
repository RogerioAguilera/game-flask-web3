import app as app_module


class FakeEth:
    def __init__(self, chain_id=11155111, block_number=12345, balance=10 ** 18):
        self.chain_id = chain_id
        self.block_number = block_number
        self._balance = balance

    def get_balance(self, address):
        return self._balance


class FakeW3:
    def __init__(self, connected=True, valid_address=True, **eth_kwargs):
        self._connected = connected
        self._valid_address = valid_address
        self.eth = FakeEth(**eth_kwargs)

    def is_connected(self):
        return self._connected

    def is_address(self, address):
        return self._valid_address

    def from_wei(self, wei, unit):
        return wei / 10 ** 18


def test_eth_balance_invalid_address_returns_400(client, monkeypatch):
    monkeypatch.setattr(app_module, "w3", FakeW3(valid_address=False))
    r = client.post("/eth_balance", json={"address": "not-an-address"})
    assert r.status_code == 400


def test_eth_balance_valid_address(client, monkeypatch):
    monkeypatch.setattr(app_module, "w3", FakeW3(valid_address=True, balance=10 ** 18))
    r = client.post("/eth_balance", json={"address": "0x0000000000000000000000000000000000dEaD"})
    assert r.status_code == 200
    assert r.get_json() == {"balance": "1.0"}


def test_network_reports_disconnected(client, monkeypatch):
    monkeypatch.setattr(app_module, "w3", FakeW3(connected=False))
    r = client.get("/network")
    assert r.status_code == 503
    assert r.get_json()["connected"] is False


def test_network_reports_connected(client, monkeypatch):
    monkeypatch.setattr(app_module, "w3", FakeW3(connected=True, chain_id=11155111, block_number=999))
    r = client.get("/network")
    assert r.status_code == 200
    assert r.get_json() == {
        "connected": True,
        "provider": app_module.WEB3_PROVIDER_URL,
        "chain_id": 11155111,
        "latest_block": 999,
    }
