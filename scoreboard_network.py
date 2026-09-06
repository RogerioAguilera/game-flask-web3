"""Shared local-chain configuration for Flask and deployment tools."""
import os
from urllib.parse import urlsplit

PRESETS = {
    'ganache': {'rpc_url': 'http://127.0.0.1:7545', 'chain_id': 1337, 'name': 'Ganache local'},
    'anvil': {'rpc_url': 'http://127.0.0.1:8545', 'chain_id': 31337, 'name': 'Anvil local'},
}


def network_configuration(values=None):
    values = os.environ if values is None else values
    rpc_url = values.get('SCOREBOARD_RPC_URL') or PRESETS['ganache']['rpc_url']
    chain_id = int(values.get('SCOREBOARD_CHAIN_ID') or 1337)
    name = values.get('SCOREBOARD_CHAIN_NAME') or 'Ganache local'
    url = urlsplit(rpc_url)
    if (url.scheme not in ('http', 'https') or url.hostname not in ('localhost', '127.0.0.1', '::1')
            or url.username or url.password or url.query or url.fragment or not url.port
            or not 0 < chain_id < 2**53 or not name.strip() or '\n' in name or '\r' in name):
        raise ValueError('Configure um RPC local com porta, Chain ID positivo e nome de rede válido.')
    return {'rpc_url': rpc_url, 'chain_id': chain_id, 'name': name}
