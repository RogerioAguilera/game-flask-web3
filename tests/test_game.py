import json
from pathlib import Path

import app as app_module


def test_start_game_reloads_questions_from_disk(client):
    client.post("/start_game")
    path = Path(app_module.QUESTIONS_FILE)
    data = json.loads(path.read_text(encoding="utf-8"))
    data["questions"][0]["question"] = "Seu personagem é russo?"
    data["guesses"][0]["guess"] = "Andrey Arshavin"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    response = client.post("/start_game")
    assert response.get_json()["question"] == "Seu personagem é russo?"
    response = client.post("/answer", json={"answer": "yes"})
    assert response.get_json()["guess"] == "Andrey Arshavin"


def test_start_game_returns_first_question(client):
    r = client.post("/start_game")
    assert r.status_code == 200
    assert r.get_json() == {"question": "É um herói?", "steps": 0}


def test_answer_yes_reaches_superman(client):
    client.post("/start_game")
    r = client.post("/answer", json={"answer": "yes"})
    data = r.get_json()
    assert data["guess"] == "Superman"
    assert data["emoji"] == "💥"
    assert data["steps"] == 1


def test_answer_no_reaches_batman(client):
    client.post("/start_game")
    r = client.post("/answer", json={"answer": "no"})
    assert r.get_json()["guess"] == "Batman"


def test_answer_invalid_value_returns_400(client):
    client.post("/start_game")
    r = client.post("/answer", json={"answer": "invalid"})
    assert r.status_code == 400


def test_answer_after_game_finished_returns_400(client):
    client.post("/start_game")
    client.post("/answer", json={"answer": "yes"})  # chega no palpite (Superman)
    r = client.post("/answer", json={"answer": "yes"})  # joga de novo sem reiniciar
    assert r.status_code == 400


def test_feedback_records_result(client):
    client.post("/start_game")
    client.post("/answer", json={"answer": "yes"})  # Superman
    r = client.post("/feedback", json={"correct": True})
    assert r.status_code == 200
    assert r.get_json() == {"success": True}


def test_feedback_without_active_guess_returns_400(client):
    r = client.post("/feedback", json={"correct": True})
    assert r.status_code == 400


def test_feedback_requires_boolean(client):
    client.post("/start_game")
    client.post("/answer", json={"answer": "yes"})
    r = client.post("/feedback", json={"correct": "yes"})
    assert r.status_code == 400


def test_stats_reports_questions_and_guesses(client):
    client.post("/start_game")
    client.post("/answer", json={"answer": "yes"})  # Superman
    client.post("/feedback", json={"correct": True})

    r = client.get("/stats")
    assert r.status_code == 200
    data = r.get_json()

    question_stats = data["questions"][0]
    assert question_stats["id"] == 1
    assert question_stats["asked"] == 1
    assert question_stats["yes_pct"] == 100.0

    guess_stats = {g["guess"]: g for g in data["guesses"]}
    assert guess_stats["Superman"] == {
        "id": 2,
        "guess": "Superman",
        "reached": 1,
        "correct": 1,
        "wrong": 0,
        "accuracy_pct": 100.0,
    }


def test_maybe_prefers_yes_without_enabling_learning(client):
    client.post('/start_game')
    result = client.post('/answer', json={'answer': 'maybe'}).get_json()
    assert result['guess'] == 'Superman'
    assert result['can_learn'] is False
    stats = client.get('/stats').get_json()['questions'][0]
    assert stats['maybe'] == 1
    assert stats['yes_pct'] == 0


def test_unknown_explores_unasked_questions_and_restart_clears_state(client):
    client.post('/start_game')
    app_module.QUESTIONS[1]['no'] = 4
    app_module.QUESTIONS[4] = {'id': 4, 'question': 'Usa capa?', 'yes': 3, 'no': 2}
    result = client.post('/answer', json={'answer': 'unknown'}).get_json()
    assert result['question'] == 'Usa capa?'
    result = client.post('/answer', json={'answer': 'no'}).get_json()
    assert result['guess'] == 'Superman'
    assert result['can_learn'] is False
    client.post('/start_game')
    with client.session_transaction() as session:
        assert 'uncertain_root' not in session
        assert 'uncertain_answers' not in session


def test_all_unknown_answers_finish_without_repeating(client):
    client.post('/start_game')
    app_module.QUESTIONS[1]['no'] = 4
    app_module.QUESTIONS[4] = {'id': 4, 'question': 'Usa capa?', 'yes': 3, 'no': 2}
    first = client.post('/answer', json={'answer': 'unknown'}).get_json()
    assert first['question'] == 'Usa capa?'
    final = client.post('/answer', json={'answer': 'unknown'}).get_json()
    assert final['guess'] in ('Batman', 'Superman')
    assert final['steps'] == 2
    assert client.post('/answer', json={'answer': 'unknown'}).status_code == 400
    assert client.post('/learn', json={'character': 'Novo', 'question': 'Nova?',
                                     'new_char_answer': 'yes'}).status_code == 400


def test_maybe_keeps_no_branch_available(client):
    client.post('/start_game')
    app_module.QUESTIONS[1]['yes'] = 4
    app_module.QUESTIONS[4] = {'id': 4, 'question': 'Voa?', 'yes': 3, 'no': 2}
    first = client.post('/answer', json={'answer': 'maybe'}).get_json()
    assert first['question'] == 'Voa?'
    final = client.post('/answer', json={'answer': 'yes'}).get_json()
    assert final['guess'] == 'Batman'
    assert final['can_learn'] is False


def test_undo_guess_allows_correcting_answer_and_statistics(client):
    client.post('/start_game')
    client.post('/answer', json={'answer': 'yes'})
    result = client.post('/undo_answer')
    assert result.get_json() == {'question': 'É um herói?', 'steps': 0}
    assert client.post('/feedback', json={'correct': True}).status_code == 400
    assert app_module.STATS['questions']['1']['yes'] == 0
    assert app_module.STATS['guesses']['2']['reached'] == 0
    assert client.post('/answer', json={'answer': 'no'}).get_json()['guess'] == 'Batman'
    with client.session_transaction() as state:
        assert state['last_parent_dir'] == 'no'


def test_undo_uncertain_restores_candidates_and_binary_learning(client):
    client.post('/start_game')
    app_module.QUESTIONS[1]['no'] = 4
    app_module.QUESTIONS[4] = {'id': 4, 'question': 'Usa capa?', 'yes': 3, 'no': 2}
    client.post('/answer', json={'answer': 'unknown'})
    client.post('/answer', json={'answer': 'maybe'})
    assert client.post('/undo_answer').get_json()['question'] == 'Usa capa?'
    with client.session_transaction() as state:
        assert state['uncertain_answers'] == {'1': 'unknown'}
    assert client.post('/undo_answer').get_json()['steps'] == 0
    with client.session_transaction() as state:
        assert 'uncertain_root' not in state
    result = client.post('/answer', json={'answer': 'yes'}).get_json()
    assert result['guess'] == 'Superman'
    assert result.get('can_learn', True)


def test_undo_is_blocked_after_feedback_and_reset_clears_history(client):
    assert client.post('/undo_answer').status_code == 400
    client.post('/start_game')
    client.post('/answer', json={'answer': 'yes'})
    client.post('/feedback', json={'correct': False})
    assert client.post('/undo_answer').status_code == 409
    client.post('/start_game')
    assert client.post('/undo_answer').status_code == 400


def test_invalid_answer_does_not_create_undo_history(client):
    client.post('/start_game')
    client.post('/answer', json={'answer': 'invalid'})
    assert client.post('/undo_answer').status_code == 400
