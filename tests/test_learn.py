import json

import app as app_module


def _play(client, answers):
    client.post("/start_game")
    data = None
    for a in answers:
        data = client.post("/answer", json={"answer": a}).get_json()
    return data


def _tree():
    with open(app_module.QUESTIONS_FILE, encoding="utf-8") as f:
        return json.load(f)


def test_learn_after_wrong_guess_adds_new_character(client):
    data = _play(client, ["yes"])  # Superman (errado)
    assert data["guess"] == "Superman"

    r = client.post("/learn", json={
        "character": "Flash",
        "emoji": "⚡",
        "question": "É o herói mais rápido?",
        "new_char_answer": "yes",
    })
    assert r.status_code == 200
    assert r.get_json()["character"] == "Flash"

    tree = _tree()
    assert len(tree["questions"]) == 2
    assert len(tree["guesses"]) == 3
    assert any(g["guess"] == "Flash" for g in tree["guesses"])


def test_learn_without_wrong_guess_returns_400(client):
    r = client.post("/learn", json={
        "character": "Flash",
        "question": "É rápido?",
        "new_char_answer": "yes",
    })
    assert r.status_code == 400


def test_learn_missing_fields_returns_400(client):
    _play(client, ["yes"])
    r = client.post("/learn", json={"character": "", "question": "", "new_char_answer": "yes"})
    assert r.status_code == 400


def test_learn_twice_same_session_without_replay_fails(client):
    """Ensinar duas vezes sem jogar de novo entre uma tentativa e outra deve falhar
    com um erro claro, em vez de mexer num ramo errado da árvore."""
    _play(client, ["yes"])
    payload = {
        "character": "Flash",
        "emoji": "⚡",
        "question": "É o herói mais rápido?",
        "new_char_answer": "yes",
    }
    first = client.post("/learn", json=payload)
    assert first.status_code == 200

    second = client.post("/learn", json=payload)
    assert second.status_code == 400


def test_learn_is_idempotent_when_replaying_same_lesson(client):
    """Reproduz o bug real do 'Saga de Gêmeos': ensinar exatamente a mesma coisa de
    novo, numa nova partida que percorre o mesmo caminho, não deve duplicar nada."""
    _play(client, ["yes"])
    payload = {
        "character": "Flash",
        "emoji": "⚡",
        "question": "É o herói mais rápido?",
        "new_char_answer": "yes",
    }
    client.post("/learn", json=payload)
    tree_after_first_learn = _tree()

    # replay: Q1 "yes" agora leva à nova pergunta; "no" nela leva de volta ao Superman
    data = _play(client, ["yes", "no"])
    assert data["guess"] == "Superman"

    r = client.post("/learn", json=payload)
    assert r.status_code == 200

    tree_after_second_learn = _tree()
    assert tree_after_second_learn == tree_after_first_learn


def test_learn_reuses_existing_character_via_different_path(client):
    """Personagem já conhecido, ensinado de novo por um caminho diferente com uma
    pergunta nova: deve reaproveitar o personagem (sem duplicar) e só criar 1 nó novo."""
    _play(client, ["yes"])
    client.post("/learn", json={
        "character": "Flash",
        "emoji": "⚡",
        "question": "É o herói mais rápido?",
        "new_char_answer": "yes",
    })

    _play(client, ["no"])  # Batman (errado)
    r = client.post("/learn", json={
        "character": "Flash",
        "emoji": "⚡",
        "question": "Usa a Força de Aceleração?",
        "new_char_answer": "yes",
    })
    assert r.status_code == 200

    tree = _tree()
    assert len(tree["questions"]) == 3
    flash_entries = [g for g in tree["guesses"] if g["guess"] == "Flash"]
    assert len(flash_entries) == 1
