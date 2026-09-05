"""Deploy only to local Anvil and save private server configuration."""
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


def main():
    forge = shutil.which('forge') or str(Path.home() / '.foundry/bin/forge')
    subprocess.run([forge, 'build', '--root', str(ROOT / 'contracts')], check=True)
    web3 = Web3(Web3.HTTPProvider('http://127.0.0.1:8545', request_kwargs={'timeout': 10}))
    if not web3.is_connected() or web3.eth.chain_id != 31337:
        raise SystemExit('Inicie Anvil local na porta 8545, com chain ID 31337.')
    config_path = ROOT / '.env.scoreboard'
    previous = dotenv_values(config_path) if config_path.exists() else {}
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
    print(f'Contrato implantado: {receipt.contractAddress}')
    print('Configuração salva em .env.scoreboard. Reinicie o Flask.')


if __name__ == '__main__':
    main()
