import copy
import json
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# app.py lê QUESTIONS_FILE/STATS_FILE assim que o módulo é importado. Como esses
# arquivos são dados de runtime (fora do git), redireciona ambos para uma pasta
# temporária ANTES do import, para os testes não dependerem de nada em disco.
_TMP_DIR = tempfile.mkdtemp(prefix="game-flask-tests-")
os.environ["QUESTIONS_FILE"] = os.path.join(_TMP_DIR, "questions.json")
os.environ["STATS_FILE"] = os.path.join(_TMP_DIR, "stats.json")

SAMPLE_TREE = {
    "questions": [
        {"id": 1, "question": "É um herói?", "yes": 2, "no": 3},
    ],
    "guesses": [
        {"id": 2, "guess": "Superman", "emoji": "💥"},
        {"id": 3, "guess": "Batman", "emoji": "🦇"},
    ],
}

with open(os.environ["QUESTIONS_FILE"], "w", encoding="utf-8") as f:
    json.dump(SAMPLE_TREE, f)

import app as app_module  # noqa: E402  (import após preparar o questions.json de teste)


@pytest.fixture
def client():
    """Reseta a árvore de teste e devolve um Flask test client isolado por teste."""
    with open(app_module.QUESTIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(copy.deepcopy(SAMPLE_TREE), f)
    if os.path.exists(app_module.STATS_FILE):
        os.remove(app_module.STATS_FILE)

    app_module.QUESTIONS, app_module.GUESSES = app_module.load_data()
    app_module.STATS = app_module.load_stats()
    app_module.app.config.update(TESTING=True)

    with app_module.app.test_client() as test_client:
        yield test_client
