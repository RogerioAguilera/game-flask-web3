# Web3 Adivinhador 🔮

Jogo de adivinhação feito em Flask. Pense em um personagem, responda às perguntas de Sim/Não e confirme o palpite do gênio. Quando ele erra, você pode ensinar um novo personagem.

O projeto inclui consulta de saldo Ethereum e um placar opcional em contrato inteligente, para desenvolvimento em Ganache ou Anvil locais. O jogo funciona sem carteira e sem blockchain.

## O que está implementado

- Árvore de decisão com perguntas e personagens em `questions.json`.
- Aprendizado de personagens pela interface, com persistência local.
- Recarga das perguntas ao iniciar cada partida.
- Interface responsiva para desktop e celular, com histórico, placar da sessão e atalhos de teclado.
- Estatísticas locais de respostas e palpites, disponíveis em `/stats` como JSON.
- Consulta de saldo de ETH pelo endereço público da carteira, na Sepolia por padrão.
- Contrato Solidity que registra partidas, acertos do gênio e perguntas acumuladas por carteira.
- Autorização de resultados pelo Flask e envio da transação pela carteira do jogador.
- Testes Python, Solidity, carteira simulada e integração com uma blockchain local.

## Tecnologias e organização

| Componente | Tecnologia e função |
| --- | --- |
| Backend | Python, Flask, sessões assinadas e rotas JSON |
| Interface | HTML, CSS e JavaScript; estilos base no template e personalização em `static/game.css` |
| Ethereum | Web3.py para consultas, implantação e preparação de transações |
| Contrato | Solidity 0.8.24, compilado e testado com Forge |
| Rede local | Ganache por padrão; Anvil também suportado |
| Carteira | Provedor Ethereum do navegador, como MetaMask |
| Persistência | Arquivos JSON locais; ainda não há banco de dados |

```text
game-flask/
├── app.py                         # Jogo, aprendizado, estatísticas e consulta Ethereum
├── scoreboard.py                  # Configuração e autorização do placar on-chain
├── scoreboard_network.py          # RPC, Chain ID e nome da rede local
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
│   ├── deploy_scoreboard.py       # Compila e implanta no Ganache ou Anvil
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
| `SCOREBOARD_RPC_URL` | RPC local compartilhado pelo deploy e carteira | `http://127.0.0.1:7545` |
| `SCOREBOARD_CHAIN_ID` | Chain ID usado para assinar e enviar transações | `1337` |
| `SCOREBOARD_CHAIN_NAME` | Nome da rede exibido na interface | `Ganache local` |
| `SCOREBOARD_ADDRESS` | Endereço do contrato na rede local | Vazio: placar desabilitado |
| `SCOREBOARD_SIGNER_KEY` | Chave dedicada do servidor para autorizar resultados | Vazio: placar desabilitado |

Prioridade de configuração: **variáveis exportadas no terminal → `.env.scoreboard` → `.env` → padrões do código**. O script de implantação gera `.env.scoreboard` com uma chave de sessão aleatória, uma chave de assinatura dedicada e o endereço do contrato. Ele reutiliza as chaves desse arquivo nas próximas implantações e atualiza o endereço.

`.env.example` pode ser publicado como modelo, com valores fictícios ou vazios. Chaves privadas, segredos de sessão e URLs com tokens devem ficar nos arquivos locais ignorados pelo Git. A chave do servidor não é a chave da carteira do jogador.

## Consulta de saldo Ethereum

Expanda **Consultar saldo Ethereum**, informe um endereço público `0x...` e clique em **Consultar**. A consulta não exige conectar a carteira: o Flask solicita o saldo ao RPC, converte wei para ETH e devolve o resultado.

A configuração padrão consulta **Sepolia**, uma rede de testes. Não inclui tokens como USDT nem NFTs. Essa consulta é independente do placar: configurar Ganache ou Anvil para registrar partidas não altera `WEB3_PROVIDER_URL`.

## Placar em contrato inteligente

### O que o contrato registra

`GameScoreboard.sol` armazena, por carteira:

- Quantidade de partidas registradas.
- Quantidade de palpites confirmados como corretos.
- Total de perguntas dessas partidas.

O contrato emite `ResultRecorded` a cada registro. A interface oferece o registro do resultado; a consulta aos totais on-chain pode ser feita com `cast`, conforme abaixo.

Após uma partida concluída e seu feedback, o Flask prepara uma autorização assinada com validade de dez minutos, vinculada à carteira, partida, contrato e rede. A carteira envia a transação, e o contrato verifica a assinatura e impede reutilizar o mesmo identificador de partida. O site mostra os estados de envio, confirmação, cancelamento e erro.

**É um protótipo local:** a confirmação de acerto vem do jogador. A assinatura protege os campos autorizados pelo servidor, mas não prova habilidade nem impede feedback falso ou múltiplas sessões. Não há tokens, NFTs, recompensas financeiras ou ranking competitivo.

### Iniciar Ganache e implantar

Abra seu workspace no Ganache e confira o servidor RPC. Os padrões do projeto são `http://127.0.0.1:7545` e Chain ID `1337`. O **Network ID** exibido no Ganache (frequentemente `5777`) é diferente do **Chain ID**, obtido por `eth_chainId`.

Se usar Ganache CLI já instalado, execute em um terminal:

```bash
ganache --server.host 127.0.0.1 --server.port 7545 --chain.chainId 1337
```

Com [Foundry](https://getfoundry.sh/) instalado, execute na pasta do projeto:

```bash
.venv/bin/python scripts/deploy_scoreboard.py --network ganache
.venv/bin/python app.py
```

O script verifica o Chain ID antes de implantar e usa a primeira conta local desbloqueada. Forge pode precisar de internet no primeiro build para baixar o compilador. O contrato usa o alvo EVM Paris, evitando a instrução PUSH0 para compatibilidade com Ganache anterior a Shanghai.

Para um workspace com outra porta ou Chain ID:

```bash
.venv/bin/python scripts/deploy_scoreboard.py --network ganache --rpc-url http://127.0.0.1:7545 --chain-id 1337
```

Substitua os valores pelos do workspace. O script informa o Chain ID recebido se houver divergência. Os parâmetros explícitos têm prioridade na implantação. Sem parâmetros, ele usa as variáveis de ambiente e arquivos de configuração; os padrões novos são do Ganache.

O endereço do contrato, RPC, Chain ID, nome da rede e chaves locais são salvos em `.env.scoreboard`, sem imprimir segredos. Reinicie Flask após implantar. Remova variáveis `SCOREBOARD_*` antigas exportadas no terminal caso elas sobrescrevam esse arquivo. Ao migrar de Anvil para Ganache, use `--network ganache` e implante novamente: os registros do Anvil não são transferidos.

### Alternativa: Anvil

Terminal 1:

```bash
export PATH="$HOME/.foundry/bin:$PATH"
anvil --host 127.0.0.1
```

Terminal 2:

```bash
.venv/bin/python scripts/deploy_scoreboard.py --network anvil
.venv/bin/python app.py
```

Esse preset grava RPC `http://127.0.0.1:8545`, Chain ID `31337` e nome `Anvil local`.

### Registrar pela carteira

1. Use uma conta de teste da rede escolhida na carteira. Contas locais e chaves de desenvolvimento servem **somente para desenvolvimento**, sem fundos reais.
2. Conclua uma partida e confirme **Acertou!** ou **Errou!**.
3. Clique em **Registrar resultado em Ganache local** (ou o nome da rede configurada).
4. Autorize a conexão, selecione a rede local quando solicitado e confirme a transação usando ETH de teste.
5. Aguarde a confirmação na tela; o hash também permite acompanhar a transação pela carteira.

| Rede do placar | Valor |
| --- | --- |
| Nome | Ganache local |
| RPC | `http://127.0.0.1:7545` |
| Chain ID | `1337` |
| Moeda | ETH de teste |

O placar aceita apenas RPCs locais (localhost, 127.0.0.1 ou ::1), com porta explícita. O endereço de loopback se refere ao computador que executa o navegador: a configuração não oferece acesso automático à rede local a partir de outro aparelho, como um celular.

Ao reiniciar a rede sem persistência, os registros desaparecem. Implante novamente e reinicie Flask. Uma nova implantação cria outro placar; ela não migra registros do contrato anterior.

### Persistir os dados do Ganache CLI

Para guardar a blockchain local entre execuções, inicie o Ganache na raiz do projeto com:

```bash
ganache --server.host 127.0.0.1 --server.port 7545 --chain.chainId 1337 --database.dbPath ./ganache-data
```

Encerre a instância anterior antes de usar a mesma porta. Nas próximas execuções, use o mesmo comando e diretório. Preserve também as contas do workspace e `.env.scoreboard`; enquanto o contrato existir na rede persistida, não é necessário implantá-lo novamente. Esse comando não migra os dados de uma instância anterior iniciada sem persistência.

A pasta `ganache-data/` na raiz está no `.gitignore`. Ela contém dados locais da blockchain e não deve ser publicada. Se escolher outro diretório dentro do repositório, adicione seu caminho ao `.gitignore` antes de commitar.

### Consultar os totais

Substitua os dois endereços:

```bash
export PATH="$HOME/.foundry/bin:$PATH"
cast call ENDERECO_DO_CONTRATO 'scores(address)(uint256,uint256,uint256)' ENDERECO_DA_CARTEIRA --rpc-url http://127.0.0.1:7545
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
| Contrato não encontrado | Verifique a rede da carteira e implante novamente se a rede local tiver sido resetada |
| Registro cancelado ou pendente | Consulte a carteira; enviar uma transação não significa que ela foi confirmada |
| Saldo inesperado | Confira `WEB3_PROVIDER_URL`: Sepolia, Ganache e Anvil têm saldos independentes |

## Versionamento e limites atuais

Publique código, contratos, testes, `static/`, README e `.env.example`, mantendo apenas valores fictícios ou vazios nesse modelo.

O `.gitignore` mantém fora do repositório:

| Arquivos ou diretórios | Motivo |
| --- | --- |
| `.env`, `.env.scoreboard` e demais `.env.*` (exceto `.env.example`) | Configurações privadas e chaves |
| `.venv/`, `node_modules/` | Dependências instaladas localmente |
| `.ganache/`, `ganache-data/` na raiz | Workspace e dados locais do Ganache |
| `anvil-state*.json`, `anvil-state*.json.gz`, `keystores/` | Estado local da Anvil e arquivos de carteira |
| `contracts/out/`, `contracts/cache/`, `contracts/broadcast/` | Compilação, cache e registros de implantação Foundry |
| `questions.json`, `stats.json` | Base de personagens e estatísticas locais |
| Caches Python, pytest e relatórios de cobertura | Arquivos gerados durante execução e testes |
| `output/imagegen/` | Imagens de referência; os recursos usados pelo jogo ficam em `static/` |

Confira `git status --short` antes do commit. Para verificar uma regra, use `git check-ignore -v CAMINHO_DO_ARQUIVO`. Arquivos já rastreados precisam ser retirados do índice com `git rm --cached` para que uma nova regra de ignore tenha efeito; isso mantém a cópia local, mas não remove versões do histórico anterior.

A persistência JSON e o estado global do Flask ainda não foram preparados para gravações concorrentes por vários processos. O servidor iniciado por `app.py` é de desenvolvimento. Antes de publicar para múltiplos usuários, são próximos passos migrar a persistência, revisar autenticação/validação de resultados e configurar um servidor de produção. O suporte ao placar em redes públicas ainda não está implementado.

Para executar a integração em um workspace Ganache **descartável**, após compilar o contrato:

```bash
.venv/bin/python scripts/check_scoreboard.py --rpc-url http://127.0.0.1:7545 --chain-id 1337
```

Esse teste implanta seu próprio contrato e envia transações de teste; não atualiza `.env.scoreboard`.
Referências de configuração: [opções Ganache CLI](https://github.com/ConsenSys-archive/ganache) e [padrões do workspace Ganache](https://archive.trufflesuite.com/docs/ganache/reference/workspace-default-configuration/).
