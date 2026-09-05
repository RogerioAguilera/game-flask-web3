# Web3 Adivinhador 🔮

Jogo de adivinhação feito em Flask. Pense em um personagem, responda às perguntas de Sim/Não e confirme o palpite do gênio. Quando ele erra, você pode ensinar um novo personagem.

O projeto inclui consulta de saldo Ethereum e um placar opcional em contrato inteligente, para desenvolvimento na rede local Anvil. O jogo funciona sem carteira e sem blockchain.

## O que está implementado

- Árvore de decisão com perguntas e personagens em `questions.json`.
- Aprendizado de personagens pela interface, com persistência local.
- Recarga das perguntas ao iniciar cada partida.
- Interface responsiva para desktop e celular, com histórico, placar da sessão e atalhos de teclado.
- Estatísticas locais de respostas e palpites, disponíveis em `/stats` como JSON.
- Consulta de saldo de ETH pelo endereço público da carteira, na Sepolia por padrão.
- Contrato Solidity que registra partidas, acertos do gênio e perguntas acumuladas por carteira.
- Autorização de resultados pelo Flask e envio da transação pela carteira do jogador.
- Testes Python, Solidity, carteira simulada e integração com Anvil.

## Tecnologias e organização

| Componente | Tecnologia e função |
| --- | --- |
| Backend | Python, Flask, sessões assinadas e rotas JSON |
| Interface | HTML, CSS e JavaScript; estilos base no template e personalização em `static/game.css` |
| Ethereum | Web3.py para consultas, implantação e preparação de transações |
| Contrato | Solidity 0.8.24, compilado e testado com Forge |
| Rede local | Anvil, parte do Foundry |
| Carteira | Provedor Ethereum do navegador, como MetaMask |
| Persistência | Arquivos JSON locais; ainda não há banco de dados |

```text
game-flask/
├── app.py                         # Jogo, aprendizado, estatísticas e consulta Ethereum
├── scoreboard.py                  # Configuração e autorização do placar on-chain
├── templates/index.html           # Interface e JavaScript do jogo
├── static/
│   ├── game.css                   # Visual responsivo
│   ├── game-reference.png         # Imagem usada na composição do gênio
│   └── scoreboard.js              # Conexão à carteira e registro do resultado
├── contracts/
│   ├── foundry.toml               # Configuração do compilador e Forge
│   ├── src/GameScoreboard.sol     # Contrato do placar
│   └── test/GameScoreboard.t.sol  # Testes Solidity
├── scripts/
│   ├── deploy_scoreboard.py       # Compila e implanta na Anvil da porta 8545
│   ├── check_scoreboard.py        # Integração em rede descartável na porta 18545
│   └── simulate_games.py          # Simulação de partidas
├── tests/                         # Testes Flask e carteira simulada
├── .github/workflows/             # CI: testes Python em push/PR para main
├── .env.example                   # Modelo público de configuração
├── requirements.txt
├── requirements-dev.txt
└── README.md
```

Os arquivos `questions.json`, `stats.json`, `.env` e `.env.scoreboard` são locais e não acompanham um clone. Artefatos Foundry ficam em `contracts/out/`, `contracts/cache/` e `contracts/broadcast/`, também ignorados pelo Git.

## Executar somente o jogo

Pré-requisitos: Python 3.10+ e pip. Os comandos abaixo são para Linux/macOS e devem ser executados na pasta do projeto.

### 1. Instalar dependências

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
```

Se já tiver um `.env`, preserve sua configuração em vez de copiá-lo novamente. No Windows, use `.venv\Scripts\python.exe` no lugar de `.venv/bin/python`.

### 2. Preparar a base de personagens

**`questions.json` precisa existir antes de iniciar o Flask.** O app lê esse arquivo na inicialização; ele não cria a base automaticamente.

Se já possui uma base local, mantenha-a. Em um clone novo, crie `questions.json` na raiz com este exemplo mínimo:

```json
{
  "questions": [
    {"id": 1, "question": "Seu personagem usa uma capa vermelha?", "yes": 2, "no": 3}
  ],
  "guesses": [
    {"id": 2, "guess": "Superman", "emoji": "🦸"},
    {"id": 3, "guess": "Batman", "emoji": "🦇"}
  ]
}
```

A pergunta inicial deve ter ID `1`. Cada ID deve ser único entre perguntas e palpites; os campos `yes` e `no` precisam apontar para IDs existentes. Evite ciclos na árvore. Novos personagens podem ser ensinados pela interface.

`stats.json` é criado quando houver gravação de estatísticas. Faça backup dos dois arquivos para preservar personagens aprendidos e histórico de uso.

### 3. Iniciar

```bash
.venv/bin/python app.py
```

Abra **http://127.0.0.1:5000**. O servidor de desenvolvimento inicia com debug **desligado** por padrão. Reinicie o Flask após mudar a configuração; após editar as perguntas, basta iniciar uma nova partida.

## Como jogar

1. Pense em um personagem e clique em **Iniciar Jogo**.
2. Responda **Sim** ou **Não**. No teclado, use `S`/`N`; `Enter` inicia uma partida na tela inicial ou após um palpite.
3. Confirme **Acertou!** ou **Errou!** quando o gênio apresentar o nome.
4. Se ele errou, informe o personagem correto, uma pergunta que o diferencia do palpite e a resposta correta para essa pergunta.
5. Use **Histórico** para revisar as respostas e **Reiniciar** para começar de novo.

O contador da interface é mantido em memória no navegador e reinicia ao recarregar a página. As estatísticas JSON e os registros no contrato são armazenamentos separados.

## Configuração

| Variável | Finalidade | Padrão |
| --- | --- | --- |
| `SECRET_KEY` | Assina a sessão Flask | `supersecretkey`, apenas exemplo; substitua por um segredo aleatório |
| `FLASK_DEBUG` | Ativa debug com `true`, `1` ou `yes` | `false` |
| `QUESTIONS_FILE` | Caminho da base de perguntas | `questions.json` na pasta de `app.py` |
| `STATS_FILE` | Caminho das estatísticas | `stats.json` na pasta de `app.py` |
| `WEB3_PROVIDER_URL` | RPC usado pela consulta de saldo e `/network` | `https://ethereum-sepolia-rpc.publicnode.com` |
| `SCOREBOARD_ADDRESS` | Endereço do contrato na Anvil | Vazio: placar desabilitado |
| `SCOREBOARD_SIGNER_KEY` | Chave dedicada do servidor para autorizar resultados | Vazio: placar desabilitado |

Prioridade de configuração: **variáveis exportadas no terminal → `.env.scoreboard` → `.env` → padrões do código**. O script de implantação gera `.env.scoreboard` com uma chave de sessão aleatória, uma chave de assinatura dedicada e o endereço do contrato. Ele reutiliza as chaves desse arquivo nas próximas implantações e atualiza o endereço.

`.env.example` pode ser publicado como modelo, com valores fictícios ou vazios. Chaves privadas, segredos de sessão e URLs com tokens devem ficar nos arquivos locais ignorados pelo Git. A chave do servidor não é a chave da carteira do jogador.

## Consulta de saldo Ethereum

Expanda **Consultar saldo Ethereum**, informe um endereço público `0x...` e clique em **Consultar**. A consulta não exige conectar a carteira: o Flask solicita o saldo ao RPC, converte wei para ETH e devolve o resultado.

A configuração padrão consulta **Sepolia**, uma rede de testes. Não inclui tokens como USDT nem NFTs. Essa consulta é independente do placar: configurar Anvil para registrar partidas não altera `WEB3_PROVIDER_URL`.

## Placar em contrato inteligente

### O que o contrato registra

`GameScoreboard.sol` armazena, por carteira:

- Quantidade de partidas registradas.
- Quantidade de palpites confirmados como corretos.
- Total de perguntas dessas partidas.

O contrato emite `ResultRecorded` a cada registro. A interface oferece o registro do resultado; a consulta aos totais on-chain pode ser feita com `cast`, conforme abaixo.

Após uma partida concluída e seu feedback, o Flask prepara uma autorização assinada com validade de dez minutos, vinculada à carteira, partida, contrato e rede. A carteira envia a transação, e o contrato verifica a assinatura e impede reutilizar o mesmo identificador de partida. O site mostra os estados de envio, confirmação, cancelamento e erro.

**É um protótipo local:** a confirmação de acerto vem do jogador. A assinatura protege os campos autorizados pelo servidor, mas não prova habilidade nem impede feedback falso ou múltiplas sessões. Não há tokens, NFTs, recompensas financeiras ou ranking competitivo.

### Iniciar a rede e implantar

Pré-requisitos adicionais: [Foundry](https://getfoundry.sh/) instalado e carteira Ethereum no navegador. Forge pode precisar de internet no primeiro build para baixar o compilador Solidity.

Terminal 1:

```bash
export PATH="$HOME/.foundry/bin:$PATH"
anvil --host 127.0.0.1
```

Terminal 2, na pasta do projeto:

```bash
.venv/bin/python scripts/deploy_scoreboard.py
.venv/bin/python app.py
```

O script usa a primeira conta desbloqueada da Anvil para implantar e grava `.env.scoreboard` com permissões restritas. Ele não imprime as chaves privadas. Se o Flask já estiver rodando, pare-o e inicie novamente após a implantação.

### Registrar pela carteira

1. Use uma conta de teste da Anvil na carteira. As chaves exibidas pelo Anvil são públicas e servem **somente para desenvolvimento**, sem fundos reais.
2. Conclua uma partida e confirme **Acertou!** ou **Errou!**.
3. Clique em **Registrar resultado na Anvil**.
4. Autorize a conexão, selecione a rede local quando solicitado e confirme a transação usando ETH de teste.
5. Aguarde a confirmação na tela; o hash também permite acompanhar a transação pela carteira.

| Rede do placar | Valor |
| --- | --- |
| Nome | Anvil local |
| RPC | `http://127.0.0.1:8545` |
| Chain ID | `31337` |
| Moeda | ETH de teste |

O placar atual está restrito a essa rede. O endereço de loopback se refere ao computador que executa o navegador: a configuração não oferece acesso automático à Anvil a partir de outro aparelho, como um celular.

Ao reiniciar Anvil sem persistência, os registros desaparecem. Implante novamente e reinicie Flask. Uma nova implantação cria outro placar; ela não migra registros do contrato anterior.

### Consultar os totais

Substitua os dois endereços:

```bash
export PATH="$HOME/.foundry/bin:$PATH"
cast call ENDERECO_DO_CONTRATO 'scores(address)(uint256,uint256,uint256)' ENDERECO_DA_CARTEIRA --rpc-url http://127.0.0.1:8545
```

A resposta contém partidas, acertos do gênio e perguntas acumuladas, nessa ordem.

## Testes

Execute os comandos na raiz do projeto.

| Verificação | Comando | Requisitos |
| --- | --- | --- |
| Flask e autorização do placar | `.venv/bin/python -m pytest -q` | Dependências de desenvolvimento |
| Contrato Solidity | `forge test --root contracts -vv` | Foundry no PATH |
| Carteira simulada | `node tests/test_scoreboard_wallet.cjs` | Node.js; sem pacotes npm adicionais |
| Integração Flask → contrato | `.venv/bin/python scripts/check_scoreboard.py` | Contrato compilado e Anvil na porta 18545 |

Instale as dependências Python de testes:

```bash
.venv/bin/python -m pip install -r requirements-dev.txt
```

Para a integração, execute em um terminal:

```bash
export PATH="$HOME/.foundry/bin:$PATH"
forge build --root contracts
anvil --host 127.0.0.1 --port 18545 --silent
```

Em outro terminal:

```bash
.venv/bin/python scripts/check_scoreboard.py
```

Os testes Python e a integração usam perguntas e estatísticas temporárias, sem alterar a base real do jogo. A integração implanta um contrato, registra uma partida, consulta os totais/evento e verifica a rejeição de duplicação. Os testes da carteira usam um provedor simulado; não substituem uma conferência manual com a extensão real.

O workflow atual do GitHub Actions executa apenas pytest em push e pull request para `main`. Os testes Foundry, carteira e integração são executados separadamente pelos comandos acima.

## Rotas

| Método | Rota | Função |
| --- | --- | --- |
| GET | `/` | Interface do jogo |
| POST | `/start_game` | Recarrega perguntas e inicia uma nova partida |
| POST | `/answer` | Recebe `{"answer":"yes"}` ou `{"answer":"no"}` |
| POST | `/feedback` | Recebe `{"correct":true}` ou `{"correct":false}`; aceita um feedback por sessão de partida |
| POST | `/learn` | Aprende um personagem após palpite errado |
| GET | `/stats` | Relatório JSON de perguntas e palpites |
| POST | `/eth_balance` | Consulta ETH do endereço em `{"address":"0x..."}` |
| GET | `/network` | Verifica o RPC da consulta de saldo |
| GET | `/scoreboard/config` | Configuração pública do placar, sem chave privada |
| POST | `/scoreboard/transaction` | Recebe `{"player":"0x..."}` e prepara a transação autorizada; não a envia |

## Solução de problemas

| Sintoma | O que conferir |
| --- | --- |
| Erro ao abrir `questions.json` | Crie a base inicial ou configure `QUESTIONS_FILE` com um caminho existente |
| Perguntas antigas | Inicie uma nova partida; confira qual arquivo está configurado |
| Visual antigo | Atualize com `Ctrl+Shift+R`; reinicie Flask para carregar alterações de template |
| `forge` ou `anvil` não encontrado | Adicione `$HOME/.foundry/bin` ao PATH |
| Botão de registro ausente | Confira `.env.scoreboard`, reinicie Flask e confirme o palpite; `supersecretkey` desabilita o placar |
| Contrato não encontrado | Verifique a rede da carteira e implante novamente após reiniciar Anvil |
| Registro cancelado ou pendente | Consulte a carteira; enviar uma transação não significa que ela foi confirmada |
| Saldo inesperado | Confira `WEB3_PROVIDER_URL`: Sepolia e Anvil têm saldos independentes |

## Versionamento e limites atuais

Publique código, contratos, testes, `static/`, README e `.env.example`. O `.gitignore` exclui configurações privadas, ambientes virtuais, caches, bases locais, artefatos Foundry, estados locais da Anvil e referências em `output/imagegen/`. Arquivos já rastreados precisam ser retirados do índice para que uma nova regra de ignore tenha efeito.

A persistência JSON e o estado global do Flask ainda não foram preparados para gravações concorrentes por vários processos. O servidor iniciado por `app.py` é de desenvolvimento. Antes de publicar para múltiplos usuários, são próximos passos migrar a persistência, revisar autenticação/validação de resultados e configurar um servidor de produção. O suporte ao placar em redes públicas ainda não está implementado.
