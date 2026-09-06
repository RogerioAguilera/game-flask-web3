"""Deploy the scoreboard locally or prepare a signed Sepolia deployment."""
import argparse
import sys
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import tempfile
from dotenv import dotenv_values
from eth_account import Account
from web3 import Web3

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scoreboard_network import PRESETS, network_configuration


def save_configuration(path, network, signer_key, secret, address):
    text = (f'SECRET_KEY={secret}\nSCOREBOARD_SIGNER_KEY={signer_key}\nSCOREBOARD_ADDRESS={address}\n'
            f"SCOREBOARD_RPC_URL={json.dumps(network['rpc_url'])}\n"
            f"SCOREBOARD_CHAIN_ID={network['chain_id']}\n"
            f"SCOREBOARD_CHAIN_NAME={json.dumps(network['name'])}\n")
    fd, name = tempfile.mkstemp(prefix='.env.scoreboard.', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as output:
            output.write(text)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def prepare_public_transaction(web3, constructor, deployer, chain_id):
    """Prepare only; never signs or sends. Bound the cost using the gas/fee caps."""
    transaction = {'from': deployer.address, 'chainId': chain_id,
                   'nonce': web3.eth.get_transaction_count(deployer.address, 'pending'), 'value': 0}
    block = web3.eth.get_block('latest')
    if 'baseFeePerGas' in block:
        tip = web3.eth.max_priority_fee
        transaction.update(maxPriorityFeePerGas=tip, maxFeePerGas=2 * block['baseFeePerGas'] + tip)
    else:
        transaction['gasPrice'] = web3.eth.gas_price
    transaction['gas'] = (constructor.estimate_gas(transaction) * 120 + 99) // 100
    transaction = constructor.build_transaction(transaction)
    maximum_cost = transaction['gas'] * transaction.get('maxFeePerGas', transaction.get('gasPrice', 0))
    if web3.eth.get_balance(deployer.address, 'pending') < maximum_cost:
        raise SystemExit('Saldo insuficiente na conta de implantação. Adicione ETH de teste Sepolia e tente novamente.')
    return transaction, maximum_cost


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--network', choices=PRESETS, help='Select Ganache, Anvil or Sepolia')
    parser.add_argument('--rpc-url', help='RPC URL (use the private env file for URLs containing API keys)')
    parser.add_argument('--chain-id', type=int, help='Expected eth_chainId, not net_version')
    parser.add_argument('--broadcast', action='store_true', help='Send the prepared Sepolia deployment')
    args = parser.parse_args()
    config_path = ROOT / '.env.scoreboard'
    previous = dotenv_values(config_path) if config_path.exists() else {}
    values = {**dotenv_values(ROOT / '.env'), **previous, **os.environ}
    if args.network:
        preset = PRESETS[args.network]
        rpc = preset['rpc_url']
        if args.network == 'sepolia':
            rpc = values.get('SCOREBOARD_SEPOLIA_RPC_URL') or (
                values.get('SCOREBOARD_RPC_URL') if str(values.get('SCOREBOARD_CHAIN_ID')) == '11155111' else None)
            if not rpc and not args.rpc_url:
                raise SystemExit('Configure SCOREBOARD_SEPOLIA_RPC_URL no .env com seu RPC Alchemy Sepolia.')
        values.update(SCOREBOARD_RPC_URL=rpc, SCOREBOARD_CHAIN_ID=str(preset['chain_id']),
                      SCOREBOARD_CHAIN_NAME=preset['name'])
    if args.rpc_url:
        values['SCOREBOARD_RPC_URL'] = args.rpc_url
    if args.chain_id is not None:
        values['SCOREBOARD_CHAIN_ID'] = str(args.chain_id)
    try:
        network = network_configuration(values)
    except ValueError:
        raise SystemExit('Configuração de rede inválida. Confira RPC, Chain ID e nome da rede.') from None
    deployer = None
    if network['public']:
        try:
            deployer = Account.from_key(values.get('SCOREBOARD_DEPLOYER_KEY') or '')
        except (ValueError, TypeError):
            raise SystemExit('Configure SCOREBOARD_DEPLOYER_KEY no .env com uma conta exclusiva de teste Sepolia.') from None
    web3 = Web3(Web3.HTTPProvider(network['rpc_url'], request_kwargs={'timeout': 10},
                                exception_retry_configuration=None))
    if not web3.is_connected():
        raise SystemExit('RPC indisponível. Confira a conexão, a rede e a chave de API no arquivo de configuração.')
    actual_chain_id = web3.eth.chain_id
    if actual_chain_id != network['chain_id']:
        raise SystemExit(f"Chain ID recebido: {actual_chain_id}; esperado: {network['chain_id']}. Implantação cancelada.")
    if not network['public'] and not web3.eth.accounts:
        raise SystemExit('Disponibilize uma conta local desbloqueada para implantar.')
    forge = shutil.which('forge') or str(Path.home() / '.foundry/bin/forge')
    subprocess.run([forge, 'build', '--root', str(ROOT / 'contracts')], check=True)
    key = values.get('SCOREBOARD_SIGNER_KEY') or Account.create().key.hex()
    secret = values.get('SECRET_KEY')
    if not secret or secret == 'supersecretkey':
        secret = secrets.token_hex(32)
    try:
        authority = Account.from_key(key).address
    except (ValueError, TypeError):
        raise SystemExit('SCOREBOARD_SIGNER_KEY inválida.') from None
    if deployer and deployer.address == authority:
        raise SystemExit('Use chaves diferentes para a conta de implantação e a autoridade de resultados.')
    artifact = json.loads((ROOT / 'contracts/out/GameScoreboard.sol/GameScoreboard.json').read_text())
    contract = web3.eth.contract(abi=artifact['abi'], bytecode=artifact['bytecode']['object'])
    constructor = contract.constructor(authority)
    if network['public']:
        transaction, maximum_cost = prepare_public_transaction(web3, constructor, deployer, network['chain_id'])
        print(f"Rede: {network['name']} (Chain ID {network['chain_id']})")
        print(f'Conta de implantação: {deployer.address}')
        print(f'Autoridade do contrato: {authority}')
        print(f"Limite de custo estimado: {web3.from_wei(maximum_cost, 'ether')} ETH de teste")
        if not args.broadcast:
            print('Prévia concluída; nenhuma transação enviada. Use --broadcast para implantar.')
            return
        # Keep recovery data before sending; no deployer key is written here.
        pending_path = ROOT / '.env.scoreboard.pending'
        if pending_path.exists():
            raise SystemExit('Existe uma implantação pendente. Confira o hash anterior antes de tentar outra; veja o README.')
        save_configuration(pending_path, network, key, secret, '')
        signed = deployer.sign_transaction(transaction)
        tx_hash = signed.hash
        # The locally computed hash remains available even if the provider times out.
        with pending_path.open('a') as output:
            output.write('SCOREBOARD_DEPLOY_TX=0x' + tx_hash.hex().removeprefix('0x') + '\n')
        print('Transação preparada: 0x' + tx_hash.hex().removeprefix('0x'), flush=True)
        web3.eth.send_raw_transaction(signed.raw_transaction)
    else:
        tx_hash = constructor.transact({'from': web3.eth.accounts[0]})
    receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
    if receipt.status != 1:
        if network['public']:
            pending_path.unlink()
        raise SystemExit('A implantação foi revertida.')
    if network['public'] and config_path.exists():
        backup = ROOT / '.env.scoreboard.backup'
        fd = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        os.chmod(backup, 0o600)
        with os.fdopen(fd, 'w') as output:
            output.write(config_path.read_text())
    save_configuration(config_path, network, key, secret, receipt.contractAddress)
    if network['public']:
        pending_path.unlink()
    print(f'Contrato implantado: {receipt.contractAddress}')
    print('Configuração salva em .env.scoreboard. Reinicie o Flask.')


if __name__ == '__main__':
    try:
        main()
    except Exception:
        # Provider exceptions can include the Alchemy URL/API key. Do not print them.
        raise SystemExit('Falha na implantação. Confira RPC, saldo e configuração. Se houver .env.scoreboard.pending, consulte o hash antes de reenviar.') from None
