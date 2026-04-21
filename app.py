
from flask import Flask, render_template, jsonify, request, session
from web3 import Web3
import os
import json

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'supersecretkey')

INFURA_URL = os.getenv('INFURA_URL', 'https://mainnet.infura.io/v3/YOUR_INFURA_PROJECT_ID')
w3 = Web3(Web3.HTTPProvider(INFURA_URL))

def load_questions():
    with open('questions.json', encoding='utf-8') as f:
        data = json.load(f)
    return data['questions'], data['guesses']

def get_question_by_id(qid, questions):
    for q in questions:
        if q['id'] == qid:
            return q
    return None

def get_guess_by_id(qid, guesses):
    for g in guesses:
        if g['id'] == qid:
            return g
    return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start_game', methods=['POST'])
def start_game():
    session['current_q'] = 1
    questions, _ = load_questions()
    return jsonify({'question': get_question_by_id(1, questions)['question']})

@app.route('/answer', methods=['POST'])
def answer():
    data = request.get_json()
    answer = data.get('answer')
    current_q = session.get('current_q', 1)
    questions, guesses = load_questions()
    q = get_question_by_id(current_q, questions)
    if not q:
        return jsonify({'error': 'Jogo já finalizado ou pergunta inválida.'}), 400
    # Se for pergunta, segue fluxo; se não, busca guess
    if 'question' in q:
        next_id = q[answer]
        next_q = get_question_by_id(next_id, questions)
        if next_q and 'question' in next_q:
            session['current_q'] = next_id
            return jsonify({'question': next_q['question']})
        else:
            guess = get_guess_by_id(next_id, guesses)
            session['current_q'] = next_id
            if guess:
                return jsonify({'guess': guess['guess']})
            else:
                return jsonify({'error': 'Personagem não encontrado.'}), 400
    else:
        return jsonify({'error': 'Jogo já finalizado.'}), 400

@app.route('/eth_balance', methods=['POST'])
def eth_balance():
    data = request.get_json()
    address = data.get('address')
    if not w3.isAddress(address):
        return jsonify({'error': 'Invalid address'}), 400
    balance = w3.eth.get_balance(address)
    eth_balance = w3.fromWei(balance, 'ether')
    return jsonify({'balance': str(eth_balance)})

if __name__ == '__main__':
    app.run(debug=True)
