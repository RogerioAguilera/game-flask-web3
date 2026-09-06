"""Integration check against a disposable Anvil on port 18545 (no real game data)."""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
from eth_account import Account
from web3 import Web3

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    from scoreboard_network import network_configuration
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rpc-url', default='http://127.0.0.1:18545')
    parser.add_argument('--chain-id', type=int, default=31337)
    args = parser.parse_args()
    network_configuration({'SCOREBOARD_RPC_URL': args.rpc_url, 'SCOREBOARD_CHAIN_ID': str(args.chain_id)})
    web3 = Web3(Web3.HTTPProvider(args.rpc_url, request_kwargs={'timeout': 10}))
    assert web3.eth.chain_id == args.chain_id
    key = Account.create().key.hex()
    artifact = json.loads((ROOT / 'contracts/out/GameScoreboard.sol/GameScoreboard.json').read_text())
    factory = web3.eth.contract(abi=artifact['abi'], bytecode=artifact['bytecode']['object'])
    player = web3.eth.accounts[1]
    receipt = web3.eth.wait_for_transaction_receipt(factory.constructor(Account.from_key(key).address).transact({'from': web3.eth.accounts[0]}))
    assert receipt.status == 1
    board = web3.eth.contract(address=receipt.contractAddress, abi=artifact['abi'])
    with tempfile.TemporaryDirectory() as tmp:
        os.environ.update(SCOREBOARD_CHAIN_ID=str(args.chain_id), SCOREBOARD_RPC_URL=args.rpc_url,
                          SCOREBOARD_CHAIN_NAME='Local integration', SCOREBOARD_SIGNER_KEY=key, SCOREBOARD_ADDRESS=receipt.contractAddress,
                          SECRET_KEY='integration-only-secret', QUESTIONS_FILE=tmp+'/questions.json', STATS_FILE=tmp+'/stats.json')
        Path(os.environ['QUESTIONS_FILE']).write_text(json.dumps({'questions': [{'id': 1, 'question': 'Herói?', 'yes': 2, 'no': 3}],
            'guesses': [{'id': 2, 'guess': 'Superman'}, {'id': 3, 'guess': 'Batman'}]}))
        import app
        with app.app.test_client() as client:
            assert client.get('/scoreboard/config').json['ready'] is True
            assert client.get('/scoreboard/scores/' + player).json['games'] == '0'
            client.post('/start_game')
            client.post('/answer', json={'answer': 'yes'})
            client.post('/feedback', json={'correct': True})
            response = client.post('/scoreboard/transaction', json={'player': player})
            assert response.status_code == 200
            tx = response.json
            tx['chainId'] = int(tx['chainId'], 16)
            tx['value'] = int(tx['value'], 16)
            tx['from'] = player
            receipt = web3.eth.wait_for_transaction_receipt(web3.eth.send_transaction(tx))
            assert receipt.status == 1
            assert list(board.functions.scores(player).call()) == [1, 1, 1]
            scores = client.get('/scoreboard/scores/' + player).json
            assert [scores['games'], scores['correctGuesses'], scores['totalQuestions']] == ['1', '1', '1']
            events = board.events.ResultRecorded().process_receipt(receipt)
            assert events[0]['args']['player'] == player
            tx['gas'] = 200000
            duplicate = web3.eth.wait_for_transaction_receipt(web3.eth.send_transaction(tx))
            assert duplicate.status == 0
    print('OK: Flask authorization → local transaction → score/event verified; replay rejected.')


if __name__ == '__main__':
    main()
