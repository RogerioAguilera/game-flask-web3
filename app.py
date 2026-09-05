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

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
QUESTIONS_FILE = os.getenv('QUESTIONS_FILE', os.path.join(BASE_DIR, 'questions.json'))
STATS_FILE = os.getenv('STATS_FILE', os.path.join(BASE_DIR, 'stats.json'))


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


def load_stats():
    if not os.path.exists(STATS_FILE):
        return {'questions': {}, 'guesses': {}}
    with open(STATS_FILE, encoding='utf-8') as f:
        return json.load(f)


def save_stats():
    with open(STATS_FILE, 'w', encoding='utf-8') as f:
        json.dump(STATS, f, ensure_ascii=False, indent=2)


def record_question_answer(question_id, answer):
    entry = STATS['questions'].setdefault(str(question_id), {'yes': 0, 'no': 0})
    entry[answer] += 1
    save_stats()


def record_guess_reached(guess_id):
    entry = STATS['guesses'].setdefault(str(guess_id), {'reached': 0, 'correct': 0, 'wrong': 0})
    entry['reached'] += 1
    save_stats()


def record_guess_feedback(guess_id, correct):
    entry = STATS['guesses'].setdefault(str(guess_id), {'reached': 0, 'correct': 0, 'wrong': 0})
    entry['correct' if correct else 'wrong'] += 1
    save_stats()


def get_json_body():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else None


def _normalize(text):
    return ' '.join(text.strip().casefold().split())


def find_guess_id_by_name(character):
    target = _normalize(character)
    for g in GUESSES.values():
        if _normalize(g['guess']) == target:
            return g['id']
    return None


def find_existing_disambiguator(wrong_guess_id, new_char_id, question_text):
    """Se essa mesma pergunta já separa exatamente esses dois personagens em algum
    ponto da árvore, devolve o id do nó existente (para reaproveitar em vez de duplicar)."""
    target = _normalize(question_text)
    for q in QUESTIONS.values():
        if _normalize(q['question']) == target and {q.get('yes'), q.get('no')} == {wrong_guess_id, new_char_id}:
            return q['id']
    return None


QUESTIONS, GUESSES = load_data()
STATS = load_stats()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/start_game', methods=['POST'])
def start_game():
    global QUESTIONS, GUESSES
    QUESTIONS, GUESSES = load_data()
    session['current_q'] = 1
    session['steps'] = 0
    return jsonify({'question': QUESTIONS[1]['question'], 'steps': 0})


@app.route('/answer', methods=['POST'])
def answer():
    data = get_json_body()
    if data is None:
        return jsonify({'error': 'Corpo da requisição deve ser JSON válido.'}), 400
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
    record_question_answer(current_q, user_answer)

    next_q = QUESTIONS.get(next_id)
    if next_q:
        session['current_q'] = next_id
        return jsonify({'question': next_q['question'], 'steps': steps})

    guess = GUESSES.get(next_id)
    session['current_q'] = next_id
    session['last_guess_id'] = next_id
    session['last_parent_q'] = current_q
    session['last_parent_dir'] = user_answer
    if guess:
        record_guess_reached(next_id)
        return jsonify({'guess': guess['guess'], 'emoji': guess.get('emoji', '🔮'), 'steps': steps})

    return jsonify({'error': 'Personagem não encontrado.'}), 400


@app.route('/feedback', methods=['POST'])
def feedback():
    guess_id = session.get('last_guess_id')
    if not guess_id or guess_id not in GUESSES:
        return jsonify({'error': 'Sessão inválida para feedback.'}), 400

    data = get_json_body()
    if data is None:
        return jsonify({'error': 'Corpo da requisição deve ser JSON válido.'}), 400
    correct = data.get('correct')
    if not isinstance(correct, bool):
        return jsonify({'error': 'Campo "correct" deve ser booleano.'}), 400

    record_guess_feedback(guess_id, correct)
    return jsonify({'success': True})


@app.route('/stats', methods=['GET'])
def stats():
    question_report = []
    for qid_str, counts in STATS['questions'].items():
        q = QUESTIONS.get(int(qid_str))
        if not q:
            continue
        asked = counts['yes'] + counts['no']
        yes_pct = (counts['yes'] / asked * 100) if asked else 0
        question_report.append({
            'id': q['id'],
            'question': q['question'],
            'asked': asked,
            'yes_pct': round(yes_pct, 1),
            'balance': round(abs(50 - yes_pct), 1),  # 0 = discrimina bem, 50 = quase nunca discrimina
        })
    question_report.sort(key=lambda r: (-r['balance'], -r['asked']))

    guess_report = []
    for gid_str, counts in STATS['guesses'].items():
        g = GUESSES.get(int(gid_str))
        if not g:
            continue
        feedback_total = counts['correct'] + counts['wrong']
        accuracy = (counts['correct'] / feedback_total * 100) if feedback_total else None
        guess_report.append({
            'id': g['id'],
            'guess': g['guess'],
            'reached': counts['reached'],
            'correct': counts['correct'],
            'wrong': counts['wrong'],
            'accuracy_pct': round(accuracy, 1) if accuracy is not None else None,
        })
    guess_report.sort(key=lambda r: (r['accuracy_pct'] if r['accuracy_pct'] is not None else 101, -r['wrong']))

    return jsonify({'questions': question_report, 'guesses': guess_report})


@app.route('/learn', methods=['POST'])
def learn():
    wrong_guess_id = session.get('last_guess_id')
    if not wrong_guess_id or wrong_guess_id not in GUESSES:
        return jsonify({'error': 'Sessão inválida para aprendizado.'}), 400

    data = get_json_body()
    if data is None:
        return jsonify({'error': 'Corpo da requisição deve ser JSON válido.'}), 400
    character = (data.get('character') or '').strip()
    emoji = (data.get('emoji') or '🎭').strip() or '🎭'
    question_text = (data.get('question') or '').strip()
    new_char_answer = data.get('new_char_answer')

    if not character or not question_text or new_char_answer not in ('yes', 'no'):
        return jsonify({'error': 'Dados incompletos para aprendizado.'}), 400

    # Nó pai é o que foi realmente percorrido nesta partida (evita pegar o primeiro
    # nó "parecido" quando o mesmo personagem é reaproveitado em vários ramos).
    parent_id = session.get('last_parent_q')
    parent_dir = session.get('last_parent_dir')
    parent_q = QUESTIONS.get(parent_id)
    if not parent_q or parent_dir not in ('yes', 'no') or parent_q.get(parent_dir) != wrong_guess_id:
        return jsonify({'error': 'Não foi possível localizar o nó pai.'}), 400

    # Reaproveita o personagem se ele já existir na árvore (evita nomes duplicados).
    existing_char_id = find_guess_id_by_name(character)

    # Se essa mesma pergunta já separa exatamente esse par de personagens em algum
    # ponto da árvore, reaproveita o nó existente em vez de duplicar a pergunta.
    if existing_char_id is not None:
        existing_node_id = find_existing_disambiguator(wrong_guess_id, existing_char_id, question_text)
        if existing_node_id == parent_id:
            # O próprio nó pai já é o disambiguador certo (a árvore já sabia a resposta) — nada a fazer.
            return jsonify({'success': True, 'character': GUESSES[existing_char_id]['guess']})
        if existing_node_id is not None:
            parent_q[parent_dir] = existing_node_id
            try:
                save_data()
            except Exception:
                parent_q[parent_dir] = wrong_guess_id
                return jsonify({'error': 'Erro ao salvar aprendizado.'}), 500
            return jsonify({'success': True, 'character': GUESSES[existing_char_id]['guess']})

    # Generate new IDs
    max_id = max(list(QUESTIONS.keys()) + list(GUESSES.keys()))
    new_q_id = max_id + 1
    new_char_id = existing_char_id if existing_char_id is not None else max_id + 2

    # Build new question node: new character on its answer branch, old wrong guess on the other
    if new_char_answer == 'yes':
        new_question = {'id': new_q_id, 'question': question_text, 'yes': new_char_id, 'no': wrong_guess_id}
    else:
        new_question = {'id': new_q_id, 'question': question_text, 'yes': wrong_guess_id, 'no': new_char_id}

    QUESTIONS[new_q_id] = new_question
    if existing_char_id is None:
        GUESSES[new_char_id] = {'id': new_char_id, 'guess': character, 'emoji': emoji}
    parent_q[parent_dir] = new_q_id

    try:
        save_data()
    except Exception:
        # Rollback in-memory state
        del QUESTIONS[new_q_id]
        if existing_char_id is None:
            del GUESSES[new_char_id]
        parent_q[parent_dir] = wrong_guess_id
        return jsonify({'error': 'Erro ao salvar aprendizado.'}), 500

    return jsonify({'success': True, 'character': GUESSES[new_char_id]['guess']})


@app.route('/eth_balance', methods=['POST'])
def eth_balance():
    data = get_json_body()
    if data is None:
        return jsonify({'error': 'Corpo da requisição deve ser JSON válido.'}), 400
    address = (data.get('address') or '').strip()
    if not w3.is_address(address):
        return jsonify({'error': 'Endereço Ethereum inválido'}), 400
    try:
        balance = w3.eth.get_balance(address)
    except Exception:
        return jsonify({'error': 'Erro ao consultar o provedor Ethereum. Tente novamente mais tarde.'}), 502
    eth = w3.from_wei(balance, 'ether')
    return jsonify({'balance': str(eth)})


if __name__ == '__main__':
    debug = os.getenv('FLASK_DEBUG', 'false').lower() in ('1', 'true', 'yes')
    app.run(debug=debug)
