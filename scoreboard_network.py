"""Shared local-chain and Sepolia configuration for Flask and deployment tools."""
import os
from urllib.parse import urlsplit

SEPOLIA_CHAIN_ID = 11155111
SEPOLIA_WALLET_RPC = 'https://ethereum-sepolia-rpc.publicnode.com'

PRESETS = {
    'sepolia': {'rpc_url': '', 'chain_id': SEPOLIA_CHAIN_ID, 'name': 'Sepolia'},
    'ganache': {'rpc_url': 'http://127.0.0.1:7545', 'chain_id': 1337, 'name': 'Ganache local'},
    'anvil': {'rpc_url': 'http://127.0.0.1:8545', 'chain_id': 31337, 'name': 'Anvil local'},
}


def network_configuration(values=None):
    values = os.environ if values is None else values
    rpc_url = values.get('SCOREBOARD_RPC_URL') or PRESETS['ganache']['rpc_url']
    chain_id = int(values.get('SCOREBOARD_CHAIN_ID') or 1337)
    name = values.get('SCOREBOARD_CHAIN_NAME') or 'Ganache local'
    url = urlsplit(rpc_url)
    local = url.hostname in ('localhost', '127.0.0.1', '::1')
    public_sepolia = (chain_id == SEPOLIA_CHAIN_ID and url.scheme == 'https'
                      and url.hostname in ('eth-sepolia.g.alchemy.com', 'ethereum-sepolia-rpc.publicnode.com')
                      and url.port in (None, 443))
    if (not ((local and url.scheme in ('http', 'https') and url.port) or public_sepolia)
            or url.username or url.password or url.query or url.fragment
            or not 0 < chain_id < 2**53 or not name.strip() or '\n' in name or '\r' in name):
        raise ValueError('Configure um RPC local com porta ou um RPC HTTPS Sepolia compatível, com Chain ID e nome válidos.')
    # Never expose a server-side Alchemy API key to the browser.
    wallet_rpc = SEPOLIA_WALLET_RPC if chain_id == SEPOLIA_CHAIN_ID else rpc_url
    return {'rpc_url': rpc_url, 'chain_id': chain_id, 'name': name,
            'wallet_rpc_url': wallet_rpc, 'public': chain_id == SEPOLIA_CHAIN_ID}
