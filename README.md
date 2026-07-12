# Web3 Adivinhador 🔮

Jogo de "20 perguntas" (estilo Akinator) feito em Flask: o "gênio" faz perguntas de Sim/Não e tenta adivinhar o personagem em quem você pensou. Se ele errar, você pode ensiná-lo, e a árvore de decisão do jogo cresce sozinha a cada rodada. O projeto também tem uma página para consultar saldo de uma carteira Ethereum via Web3.

## Funcionalidades

- Jogo de adivinhação por árvore de decisão binária (perguntas Sim/Não).
- Aprendizado: quando o gênio erra, o jogador ensina o personagem certo e uma pergunta que o diferencia do palpite errado — a árvore é persistida em `questions.json`.
- Estatísticas de uso: cada resposta e cada feedback (acertou/errou) são registrados em `stats.json`, com um relatório em `/stats` mostrando quais perguntas discriminam bem e quais palpites o gênio mais erra.
- Consulta de saldo de uma carteira Ethereum (rede Sepolia testnet por padrão) via [web3.py](https://web3py.readthedocs.io/).

## Pré-requisitos

- Python 3.10+
- pip

## Instalação

```bash
git clone <url-do-repositorio>
cd game-flask

python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

## Configuração

Copie o arquivo de exemplo de variáveis de ambiente:

```bash
cp .env.example .env
```

Variáveis disponíveis em `.env`:

| Variável            | Descrição                                                                 | Padrão                                          |
|---------------------|----------------------------------------------------------------------------|--------------------------------------------------|
| `SECRET_KEY`        | Chave usada pelo Flask para assinar a sessão do jogo.                     | `supersecretkey` (troque em produção)             |
| `WEB3_PROVIDER_URL` | URL do provedor RPC Ethereum (Sepolia testnet). Aceita Infura/Alchemy/etc. | `https://ethereum-sepolia-rpc.publicnode.com`     |

## Executando

```bash
python3 app.py
```

A aplicação sobe em modo debug em [http://localhost:5000](http://localhost:5000).

> Como as perguntas ficam carregadas em memória, reinicie o servidor sempre que `questions.json` for editado manualmente (fora do fluxo de aprendizado do próprio jogo).

## Como jogar

1. Abra a página inicial e clique em **Iniciar Jogo**.
2. Responda Sim/Não às perguntas (atalhos de teclado: `S` para Sim, `N` para Não, `Enter` para iniciar/jogar novamente).
3. Ao final, confirme se o palpite do gênio estava certo.
4. Se ele errou, preencha o formulário para ensiná-lo: nome do personagem, uma pergunta Sim/Não que o diferencia do palpite errado, e qual seria a resposta correta para o novo personagem.

## Rotas da API

| Rota            | Método | Descrição                                                                 |
|------------------|--------|----------------------------------------------------------------------------|
| `/`              | GET    | Página principal do jogo.                                                 |
| `/start_game`    | POST   | Inicia uma nova partida (reseta a sessão) e retorna a primeira pergunta.  |
| `/answer`        | POST   | Envia a resposta (`yes`/`no`) e retorna a próxima pergunta ou o palpite.  |
| `/feedback`      | POST   | Registra se o último palpite estava correto (`{"correct": true}` ou `{"correct": false}`). |
| `/learn`         | POST   | Ensina um novo personagem após um palpite errado, expandindo a árvore.   |
| `/stats`         | GET    | Relatório de perguntas menos discriminantes e palpites com mais erros.   |
| `/eth_balance`   | POST   | Consulta o saldo (em ETH) de um endereço Ethereum.                       |
| `/network`       | GET    | Verifica a conexão com o provedor Web3 configurado.                      |

## Estrutura do projeto

```
game-flask/
├── app.py               # Rotas Flask, lógica do jogo, integração Web3
├── questions.json        # Árvore de decisão (perguntas e personagens) — gerada/editada em runtime, não versionada
├── stats.json             # Estatísticas de uso do jogo — gerada em runtime, não versionada
├── templates/
│   └── index.html        # Front-end (HTML/CSS/JS) do jogo e da consulta Web3
├── requirements.txt
└── .env.example
```

> `questions.json` e `stats.json` estão no `.gitignore`: são dados que o próprio jogo lê e escreve em runtime, não código-fonte. Se quiser versionar uma árvore de personagens "base", remova a entrada do `.gitignore` e faça o commit manualmente.

## Testando manualmente

Sem front-end, dá pra jogar direto pela API com `curl` (mantendo o cookie de sessão):

```bash
curl -c cookies.txt -X POST http://localhost:5000/start_game
curl -b cookies.txt -c cookies.txt -X POST http://localhost:5000/answer \
  -H "Content-Type: application/json" -d '{"answer": "yes"}'
```
