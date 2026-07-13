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
    r = client.post("/answer", json={"answer": "maybe"})
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
