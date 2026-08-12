#!/usr/bin/env python3
"""Simula partidas com respostas aleatórias contra a árvore real (questions.json)
e resume o relatório de /stats, para achar perguntas que discriminam mal e
personagens raramente alcançados.

As estatísticas da simulação vão para um arquivo temporário à parte — o
stats.json real (de uso de verdade) não é tocado.

Uso: python3 scripts/simulate_games.py [numero_de_partidas]
"""
import os
import random
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

N_GAMES = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
MAX_STEPS_PER_GAME = 50  # trava de segurança contra ciclos/árvore malformada

os.environ.setdefault("QUESTIONS_FILE", os.path.join(ROOT, "questions.json"))
os.environ["STATS_FILE"] = tempfile.mktemp(prefix="game-flask-sim-stats-", suffix=".json")

import app as app_module  # noqa: E402

app_module.app.config.update(TESTING=True)
random.seed(42)


def simulate_one_game(client):
    resp = client.post("/start_game").get_json()
    for _ in range(MAX_STEPS_PER_GAME):
        if "guess" in resp:
            return True
        if "error" in resp:
            return False
        answer = random.choice(["yes", "no"])
        resp = client.post("/answer", json={"answer": answer}).get_json()
    return False  # excedeu MAX_STEPS_PER_GAME — provável ciclo na árvore


def check_tree_integrity():
    reachable_q, reachable_g = set(), set()
    stack = [1]
    while stack:
        nid = stack.pop()
        if nid in reachable_q or nid in reachable_g:
            continue
        if nid in app_module.QUESTIONS:
            reachable_q.add(nid)
            q = app_module.QUESTIONS[nid]
            stack += [q["yes"], q["no"]]
        elif nid in app_module.GUESSES:
            reachable_g.add(nid)
    orphan_questions = sorted(set(app_module.QUESTIONS) - reachable_q)
    orphan_guesses = sorted(set(app_module.GUESSES) - reachable_g)
    return orphan_questions, orphan_guesses


def main():
    errors = 0
    with app_module.app.test_client() as client:
        for _ in range(N_GAMES):
            if not simulate_one_game(client):
                errors += 1
        stats_resp = client.get("/stats").get_json()

    orphan_questions, orphan_guesses = check_tree_integrity()

    print(f"=== Simulação de {N_GAMES} partidas aleatórias ===\n")
    print(f"Árvore: {len(app_module.QUESTIONS)} perguntas, {len(app_module.GUESSES)} personagens")

    if errors:
        print(f"⚠ {errors} partida(s) não terminaram em palpite (erro ou possível ciclo na árvore).")

    if orphan_questions:
        print(f"⚠ {len(orphan_questions)} pergunta(s) inalcançável(is) a partir da raiz: {orphan_questions}")
    if orphan_guesses:
        nomes = [app_module.GUESSES[i]["guess"] for i in orphan_guesses]
        print(f"⚠ {len(orphan_guesses)} personagem(ns) inalcançável(is) a partir da raiz: {nomes}")
    if not orphan_questions and not orphan_guesses:
        print("✓ Todos os nós são alcançáveis a partir da raiz.")

    print("\n--- Perguntas que menos discriminam (balance perto de 50 = pergunta fraca) ---")
    for r in stats_resp["questions"][:8]:
        print(f"  [balance {r['balance']:>4.1f}] ({r['asked']:>4}x) {r['question']}")

    print("\n--- Personagens menos alcançados (ramos raros ou muito profundos) ---")
    rarest = sorted(stats_resp["guesses"], key=lambda r: r["reached"])[:8]
    for r in rarest:
        print(f"  {r['reached']:>4}x  {r['guess']}")

    never_reached = [g for g in app_module.GUESSES.values() if g["id"] not in {r["id"] for r in stats_resp["guesses"]}]
    if never_reached:
        nomes = [g["guess"] for g in never_reached]
        print(f"\n⚠ {len(never_reached)} personagem(ns) nunca alcançado(s) em {N_GAMES} partidas aleatórias: {nomes}")

    print(
        "\n(Isto usa respostas aleatórias — bom para achar perguntas mal balanceadas e "
        "nós inalcançáveis/raros na árvore. Acurácia real de acerto/erro só vem do "
        "stats.json de uso de verdade, que este script não altera.)"
    )


if __name__ == "__main__":
    main()
