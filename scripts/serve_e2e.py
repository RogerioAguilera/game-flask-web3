"""Disposable Flask server for Cypress only. Never used by production app.py."""
import json
import os
from pathlib import Path
import secrets
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TREE = {
    'questions': [
        {'id': 1, 'question': 'É uma saga?', 'yes': 4, 'no': 2},
        {'id': 2, 'question': 'Voa?', 'yes': 10, 'no': 11},
        {'id': 4, 'question': 'É sobre Lanternas Verdes?', 'yes': 12, 'no': 13},
    ],
    'guesses': [
        {'id': 10, 'guess': 'Superman', 'emoji': '🦸'},
        {'id': 11, 'guess': 'Batman', 'emoji': '🦇'},
        {'id': 12, 'guess': 'Crepúsculo Esmeralda', 'emoji': '💍'},
        {'id': 13, 'guess': 'Saga desconhecida', 'emoji': '📚', 'unmatched': True},
    ],
}


def main():
    with tempfile.TemporaryDirectory(prefix='game-flask-e2e-') as directory:
        # Prevent loading personal .env files or contacting real RPCs.
        os.environ['PYTHON_DOTENV_DISABLED'] = '1'
        for key in list(os.environ):
            if key.startswith('SCOREBOARD_'):
                del os.environ[key]
        os.environ.update(QUESTIONS_FILE=str(Path(directory) / 'questions.json'),
                          STATS_FILE=str(Path(directory) / 'stats.json'),
                          SECRET_KEY=secrets.token_hex(32),
                          WEB3_PROVIDER_URL='http://127.0.0.1:1')
        Path(os.environ['QUESTIONS_FILE']).write_text(json.dumps(TREE), encoding='utf-8')
        sys.path.insert(0, str(ROOT))
        # dotenv 1.0 does not support PYTHON_DOTENV_DISABLED.
        import dotenv
        dotenv.load_dotenv = lambda *args, **kwargs: False
        import app as game

        @game.app.get('/__e2e/health')
        def health():
            return {'e2e': True}

        @game.app.post('/__e2e/reset')
        def reset():
            Path(game.QUESTIONS_FILE).write_text(json.dumps(TREE), encoding='utf-8')
            game.QUESTIONS, game.GUESSES = game.load_data()
            game.STATS = {'questions': {}, 'guesses': {}}
            game.save_stats()
            from flask import session
            session.clear()
            return {'reset': True}

        game.app.run(host='127.0.0.1', port=5055, debug=False, use_reloader=False)


if __name__ == '__main__':
    main()
