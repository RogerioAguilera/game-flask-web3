from flask import Flask, render_template, jsonify, request, session
from web3 import Web3
import os
import json

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'supersecretkey')

INFURA_URL = os.getenv('INFURA_URL', 'https://mainnet.infura.io/v3/YOUR_INFURA_PROJECT_ID')
w3 = Web3(Web3.HTTPProvider(INFURA_URL))

with open('questions.json', encoding='utf-8') as f:
    _data = json.load(f)

QUESTIONS = {q['id']: q for q in _data['questions']}
GUESSES = {g['id']: g for g in _data['guesses']}


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/start_game', methods=['POST'])
def start_game():
    session['current_q'] = 1
    session['steps'] = 0
    return jsonify({'question': QUESTIONS[1]['question'], 'steps': 0})


@app.route('/answer', methods=['POST'])
def answer():
    data = request.get_json()
    user_answer = data.get('answer')
    current_q = session.get('current_q', 1)

    q = QUESTIONS.get(current_q)
    if not q:
        return jsonify({'error': 'Jogo já finalizado ou pergunta inválida.'}), 400

    next_id = q.get(user_answer)
    if next_id is None:
        return jsonify({'error': 'Resposta inválida. Use "yes" ou "no".'}), 400

    steps = session.get('steps', 0) + 1
    session['steps'] = steps

    next_q = QUESTIONS.get(next_id)
    if next_q:
        session['current_q'] = next_id
        return jsonify({'question': next_q['question'], 'steps': steps})

    guess = GUESSES.get(next_id)
    session['current_q'] = next_id
    if guess:
        return jsonify({'guess': guess['guess'], 'emoji': guess.get('emoji', '🔮'), 'steps': steps})

    return jsonify({'error': 'Personagem não encontrado.'}), 400


@app.route('/eth_balance', methods=['POST'])
def eth_balance():
    data = request.get_json()
    address = data.get('address', '').strip()
    if not w3.is_address(address):
        return jsonify({'error': 'Endereço Ethereum inválido'}), 400
    balance = w3.eth.get_balance(address)
    eth = w3.from_wei(balance, 'ether')
    return jsonify({'balance': str(eth)})


if __name__ == '__main__':
    app.run(debug=True)
