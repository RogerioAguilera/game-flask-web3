"""Deploy to local Ganache or Anvil and save private server configuration."""
import argparse
import sys
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
from dotenv import dotenv_values
from eth_account import Account
from web3 import Web3

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scoreboard_network import PRESETS, network_configuration


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--network', choices=PRESETS, help='Select Ganache or Anvil defaults')
    parser.add_argument('--rpc-url', help='Local HTTP RPC URL')
    parser.add_argument('--chain-id', type=int, help='Expected eth_chainId, not net_version')
    args = parser.parse_args()
    config_path = ROOT / '.env.scoreboard'
    previous = dotenv_values(config_path) if config_path.exists() else {}
    values = {**dotenv_values(ROOT / '.env'), **previous, **os.environ}
    if args.network:
        preset = PRESETS[args.network]
        values.update(SCOREBOARD_RPC_URL=preset['rpc_url'], SCOREBOARD_CHAIN_ID=str(preset['chain_id']),
                      SCOREBOARD_CHAIN_NAME=preset['name'])
    if args.rpc_url:
        values['SCOREBOARD_RPC_URL'] = args.rpc_url
    if args.chain_id is not None:
        values['SCOREBOARD_CHAIN_ID'] = str(args.chain_id)
    try:
        network = network_configuration(values)
    except ValueError as error:
        raise SystemExit(str(error)) from error
    web3 = Web3(Web3.HTTPProvider(network['rpc_url'], request_kwargs={'timeout': 10}))
    if not web3.is_connected():
        raise SystemExit('Inicie a rede local no RPC configurado: ' + network['rpc_url'])
    actual_chain_id = web3.eth.chain_id
    if actual_chain_id != network['chain_id']:
        raise SystemExit(f"Chain ID recebido: {actual_chain_id}; esperado: {network['chain_id']}. "
                         'Confira eth_chainId e ajuste --chain-id antes de implantar.')
    if not web3.eth.accounts:
        raise SystemExit('Disponibilize uma conta local desbloqueada para implantar.')
    forge = shutil.which('forge') or str(Path.home() / '.foundry/bin/forge')
    subprocess.run([forge, 'build', '--root', str(ROOT / 'contracts')], check=True)
    key = previous.get('SCOREBOARD_SIGNER_KEY') or Account.create().key.hex()
    secret = previous.get('SECRET_KEY') or secrets.token_hex(32)
    artifact = json.loads((ROOT / 'contracts/out/GameScoreboard.sol/GameScoreboard.json').read_text())
    contract = web3.eth.contract(abi=artifact['abi'], bytecode=artifact['bytecode']['object'])
    receipt = web3.eth.wait_for_transaction_receipt(
        contract.constructor(Account.from_key(key).address).transact({'from': web3.eth.accounts[0]}))
    if receipt.status != 1:
        raise SystemExit('A implantação falhou.')
    fd = os.open(config_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    os.chmod(config_path, 0o600)
    with os.fdopen(fd, 'w') as output:
        output.write(f'SECRET_KEY={secret}\nSCOREBOARD_SIGNER_KEY={key}\nSCOREBOARD_ADDRESS={receipt.contractAddress}\n')
        output.write(f"SCOREBOARD_RPC_URL={json.dumps(network['rpc_url'])}\n"
                     f"SCOREBOARD_CHAIN_ID={network['chain_id']}\n"
                     f"SCOREBOARD_CHAIN_NAME={json.dumps(network['name'])}\n")
    print(f"Rede: {network['name']} (Chain ID {network['chain_id']})")
    print(f'Contrato implantado: {receipt.contractAddress}')
    print('Configuração salva em .env.scoreboard. Reinicie o Flask.')


if __name__ == '__main__':
    main()
