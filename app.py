from flask import Flask, render_template, jsonify, request, session
from web3 import Web3
from dotenv import load_dotenv
import os
import json

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'supersecretkey')

# Sepolia testnet by default (public RPC, no API key required).
# Override with WEB3_PROVIDER_URL to point at Infura/Alchemy or another network.
WEB3_PROVIDER_URL = os.getenv('WEB3_PROVIDER_URL', 'https://ethereum-sepolia-rpc.publicnode.com')
w3 = Web3(Web3.HTTPProvider(WEB3_PROVIDER_URL))


@app.route('/network', methods=['GET'])
def network():
    connected = w3.is_connected()
    if not connected:
        return jsonify({'connected': False, 'provider': WEB3_PROVIDER_URL}), 503
    return jsonify({
        'connected': True,
        'provider': WEB3_PROVIDER_URL,
        'chain_id': w3.eth.chain_id,
        'latest_block': w3.eth.block_number,
    })

QUESTIONS_FILE = 'questions.json'


def load_data():
    with open(QUESTIONS_FILE, encoding='utf-8') as f:
        _data = json.load(f)
    return (
        {q['id']: q for q in _data['questions']},
        {g['id']: g for g in _data['guesses']},
    )


def save_data():
    data = {
        'questions': list(QUESTIONS.values()),
        'guesses': list(GUESSES.values()),
    }
    with open(QUESTIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


QUESTIONS, GUESSES = load_data()


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
    session['last_guess_id'] = next_id
    if guess:
        return jsonify({'guess': guess['guess'], 'emoji': guess.get('emoji', '🔮'), 'steps': steps})

    return jsonify({'error': 'Personagem não encontrado.'}), 400


@app.route('/learn', methods=['POST'])
def learn():
    wrong_guess_id = session.get('last_guess_id')
    if not wrong_guess_id or wrong_guess_id not in GUESSES:
        return jsonify({'error': 'Sessão inválida para aprendizado.'}), 400

    data = request.get_json()
    character = (data.get('character') or '').strip()
    emoji = (data.get('emoji') or '🎭').strip() or '🎭'
    question_text = (data.get('question') or '').strip()
    new_char_answer = data.get('new_char_answer')

    if not character or not question_text or new_char_answer not in ('yes', 'no'):
        return jsonify({'error': 'Dados incompletos para aprendizado.'}), 400

    # Find the parent question that leads to the wrong guess
    parent_q = None
    parent_dir = None
    for q in QUESTIONS.values():
        if q.get('yes') == wrong_guess_id:
            parent_q, parent_dir = q, 'yes'
            break
        if q.get('no') == wrong_guess_id:
            parent_q, parent_dir = q, 'no'
            break

    if not parent_q:
        return jsonify({'error': 'Não foi possível localizar o nó pai.'}), 400

    # Generate new IDs
    max_id = max(list(QUESTIONS.keys()) + list(GUESSES.keys()))
    new_q_id = max_id + 1
    new_char_id = max_id + 2

    # Build new question node: new character on its answer branch, old wrong guess on the other
    if new_char_answer == 'yes':
        new_question = {'id': new_q_id, 'question': question_text, 'yes': new_char_id, 'no': wrong_guess_id}
    else:
        new_question = {'id': new_q_id, 'question': question_text, 'yes': wrong_guess_id, 'no': new_char_id}

    QUESTIONS[new_q_id] = new_question
    GUESSES[new_char_id] = {'id': new_char_id, 'guess': character, 'emoji': emoji}
    parent_q[parent_dir] = new_q_id

    try:
        save_data()
    except Exception:
        # Rollback in-memory state
        del QUESTIONS[new_q_id]
        del GUESSES[new_char_id]
        parent_q[parent_dir] = wrong_guess_id
        return jsonify({'error': 'Erro ao salvar aprendizado.'}), 500

    return jsonify({'success': True, 'character': character})


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
