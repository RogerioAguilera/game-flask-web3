# Web3 Adivinhador 🔮

Jogo de adivinhação feito em Flask. Pense em um personagem, responda às perguntas de Sim/Não e confirme o palpite do gênio. Quando ele erra, você pode ensinar um novo personagem.

O projeto inclui consulta de saldo Ethereum e um placar opcional em contrato inteligente, para desenvolvimento em Ganache/Anvil locais e na testnet pública Sepolia via Alchemy. O jogo funciona sem carteira e sem blockchain.

## O que está implementado

- Árvore de decisão com perguntas e personagens em `questions.json`.
- Aprendizado de personagens pela interface, com persistência local.
- Recarga das perguntas ao iniciar cada partida.
- Botão “Voltar à pergunta anterior” para corrigir respostas, inclusive após o palpite, antes de confirmar Acertou/Errou. A correção restaura as possibilidades e remove a resposta desfeita das estatísticas.
- Respostas Sim, Não, Não sei e Talvez. Não sei preserva os ramos; Talvez dá peso maior ao Sim sem excluir o Não. Perguntas já respondidas não se repetem; quando acabam, o jogo escolhe o palpite de maior peso (empates seguem a ordem da árvore).
- O aprendizado após um erro exige uma partida com respostas Sim/Não para alterar um ramo definido da árvore.
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
| Redes do placar | Ganache por padrão; Anvil e Sepolia também suportados |
| Carteira | Provedor Ethereum do navegador, como MetaMask |
| Persistência | Arquivos JSON locais; ainda não há banco de dados |

```text
game-flask/
├── app.py                         # Jogo, aprendizado, estatísticas e consulta Ethereum
├── scoreboard.py                  # Configuração e autorização do placar on-chain
├── scoreboard_network.py          # RPC privado, RPC da carteira e Chain ID
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
│   ├── deploy_scoreboard.py       # Implantação local e prévia/envio na Sepolia
│   ├── check_scoreboard.py        # Integração em rede descartável na porta 18545
│   └── simulate_games.py          # Simulação de partidas
├── tests/                         # Testes Flask e carteira simulada
├── .github/workflows/             # CI: Python, carteira, Solidity e Ganache
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
| `SCOREBOARD_RPC_URL` | RPC do servidor; na Sepolia a carteira recebe um RPC público separado | `http://127.0.0.1:7545` |
| `SCOREBOARD_CHAIN_ID` | Chain ID usado para assinar e enviar transações | `1337` |
| `SCOREBOARD_CHAIN_NAME` | Nome da rede exibido na interface | `Ganache local` |
| `SCOREBOARD_ADDRESS` | Endereço do contrato na rede escolhida | Vazio: placar desabilitado |
| `SCOREBOARD_SEPOLIA_RPC_URL` | RPC privado Alchemy utilizado pelo preset `--network sepolia` | Vazio |
| `SCOREBOARD_DEPLOYER_KEY` | Conta de teste que assina e paga a implantação na Sepolia | Vazio; usada apenas pelo script de implantação |
| `SCOREBOARD_SIGNER_KEY` | Chave dedicada do servidor para autorizar resultados | Vazio: placar desabilitado |

Prioridade de configuração do Flask: **variáveis exportadas no terminal → `.env.scoreboard` → `.env` → padrões do código**. O script de implantação gera `.env.scoreboard` com uma chave de sessão aleatória, uma chave de assinatura dedicada e o endereço do contrato. O script respeita essa mesma prioridade para as chaves de assinatura e sessão, gerando valores quando faltam (ou substituindo a chave de sessão de exemplo). Ele reutiliza as chaves existentes e atualiza o endereço após uma implantação bem-sucedida. A chave de implantação fica no `.env` privado e não é copiada para `.env.scoreboard`.

`.env.example` pode ser publicado como modelo, com valores fictícios ou vazios. Chaves privadas, segredos de sessão e URLs com tokens devem ficar nos arquivos locais ignorados pelo Git. A chave do servidor não é a chave da carteira do jogador nem a chave da conta de implantação.

## Consulta de saldo Ethereum

Expanda **Consultar saldo Ethereum**, informe um endereço público `0x...` e clique em **Consultar**. A consulta não exige conectar a carteira: o Flask solicita o saldo ao RPC, converte wei para ETH e devolve o resultado.

A configuração padrão consulta **Sepolia**, uma rede de testes. Não inclui tokens como USDT nem NFTs. Essa consulta é independente do placar: configurar Ganache ou Anvil para registrar partidas não altera `WEB3_PROVIDER_URL`.

## Placar em contrato inteligente

### O que o contrato registra

`GameScoreboard.sol` armazena, por carteira:

- Quantidade de partidas registradas.
- Quantidade de palpites confirmados como corretos.
- Total de perguntas dessas partidas.

O contrato emite `ResultRecorded` a cada registro. O painel **Placar na blockchain** mostra partidas, acertos do gênio e perguntas da carteira conectada. Clique em **Conectar carteira** para autorizar a consulta e em **Atualizar placar** para recarregar os dados. A página não solicita conexão automaticamente; ela consulta silenciosamente contas já autorizadas. Os totais também podem ser consultados com `cast`, conforme abaixo.

Ao carregar a página e atualizar o placar, o Flask verifica o Chain ID do RPC, a presença de código no endereço configurado, a interface de consulta e a autoridade de assinatura do contrato. Falhas deixam o registro desabilitado e mostram uma orientação no painel. A verificação é repetida antes de autorizar cada transação, com timeout de três segundos por chamada RPC e sem retries automáticos.

Após uma partida concluída e seu feedback, o Flask prepara uma autorização assinada com validade de dez minutos, vinculada à carteira, partida, contrato e rede. A carteira envia a transação, e o contrato verifica a assinatura e impede reutilizar o mesmo identificador de partida. O site mostra os estados de envio, confirmação, cancelamento e erro. Após a confirmação, atualiza o placar. Ao trocar ou desconectar a conta, esconde os dados anteriores; respostas atrasadas não substituem o placar da nova carteira. A leitura usa a rede configurada no servidor, mesmo quando outra rede está selecionada na carteira. Para registrar, a carteira precisa mudar para a rede correta.

**É um protótipo de testes:** a confirmação de acerto vem do jogador. A assinatura protege os campos autorizados pelo servidor, mas não prova habilidade nem impede feedback falso ou múltiplas sessões. Não há tokens, NFTs, recompensas financeiras ou ranking competitivo.

### Iniciar Ganache e implantar

Abra seu workspace no Ganache e confira o servidor RPC. Os padrões do projeto são `http://127.0.0.1:7545` e Chain ID `1337`. O **Network ID** exibido no Ganache (frequentemente `5777`) é diferente do **Chain ID**, obtido por `eth_chainId`.

O Ganache 7.9.2 foi validado neste projeto com Node.js 22. O Node.js 12 encontrado no ambiente apresentou incompatibilidade ao iniciar o CLI. Confira a versão com `node --version`.

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

### Sepolia via Alchemy

Para usar a testnet pública, configure um aplicativo Ethereum Sepolia na Alchemy e coloque no **`.env` privado**:

```dotenv
SCOREBOARD_SEPOLIA_RPC_URL=https://eth-sepolia.g.alchemy.com/v2/SUA_API_KEY
SCOREBOARD_DEPLOYER_KEY=SUA_CHAVE_PRIVADA_DE_TESTE_SEPOLIA
```

Use uma conta exclusiva para testes, com ETH **da Sepolia**, e mantenha sua chave diferente de `SCOREBOARD_SIGNER_KEY`. A conta de implantação paga o deploy; a autoridade de assinatura apenas autoriza resultados e não precisa de saldo. A carteira do jogador também precisa de ETH Sepolia para registrar partidas. Não compartilhe essas chaves nem as coloque no `.env.example`.

Primeiro, prepare uma prévia sem enviar transações:

```bash
.venv/bin/python scripts/deploy_scoreboard.py --network sepolia
```

O script verifica o Chain ID, compila o contrato, calcula gas e limite de custo e consulta o saldo. Para enviar a implantação:

```bash
.venv/bin/python scripts/deploy_scoreboard.py --network sepolia --broadcast
.venv/bin/python app.py
```

A implantação é assinada localmente e enviada como transação bruta; Alchemy não precisa disponibilizar contas desbloqueadas. O comando de envio recalcula a estimativa com as condições da rede naquele momento. Após confirmação, a configuração ativa passa a ser Sepolia em `.env.scoreboard`, e a configuração anterior é preservada em `.env.scoreboard.backup`. Reinicie Flask e atualize a página. Nenhum registro do Ganache é migrado.

A URL privada Alchemy fica no servidor. `/scoreboard/config` fornece à carteira `https://ethereum-sepolia-rpc.publicnode.com`, sem chave de API. A carteira pode usar seu próprio RPC Sepolia já cadastrado. `/network` também omite caminhos e credenciais da URL do provedor. A consulta de saldo continua independente: para usar Alchemy nela, configure `WEB3_PROVIDER_URL` no `.env`.

Se houver timeout após preparar o envio, o script preserva `.env.scoreboard.pending`, com hash, autoridade e configuração, e bloqueia outra implantação pública enquanto esse arquivo existir. Confira o hash no [explorador Sepolia](https://sepolia.etherscan.io). Se confirmou com sucesso, copie o endereço do contrato para `SCOREBOARD_ADDRESS` no arquivo pendente e use essa configuração como `.env.scoreboard`, preservando uma cópia da anterior. Se a transação foi revertida ou comprovadamente não foi enviada, remova apenas o arquivo pendente antes de tentar outra implantação. Não repita o envio de uma transação ainda pendente.

A integração pública depende da sua configuração e saldo. Os testes automatizados não usam chaves Alchemy reais: validam assinatura, privacidade e preparação/envio por RPC simulado. A integração real do CI continua em Ganache descartável. Referência: [Ethereum Sepolia na Alchemy](https://www.alchemy.com/rpc/ethereum-sepolia).

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

O placar aceita RPCs locais (localhost, 127.0.0.1 ou ::1) com porta explícita e os RPCs HTTPS Sepolia Alchemy/PublicNode com Chain ID `11155111`. RPCs públicos de mainnet não são aceitos. O endereço de loopback se refere ao computador que executa o navegador: a configuração não oferece acesso automático à rede local a partir de outro aparelho, como um celular.

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

Para executar a integração em um workspace Ganache **descartável**, após compilar o contrato:

```bash
.venv/bin/python scripts/check_scoreboard.py --rpc-url http://127.0.0.1:7545 --chain-id 1337
```

Esse teste implanta seu próprio contrato e envia transações de teste; não atualiza `.env.scoreboard`.

Os testes Python e a integração usam perguntas e estatísticas temporárias, sem alterar a base real do jogo. A integração implanta um contrato, registra uma partida, consulta os totais/evento e verifica a rejeição de duplicação. Os testes da carteira usam um provedor simulado; não substituem uma conferência manual com a extensão real.

O workflow `.github/workflows/tests.yml` executa automaticamente em push e pull request para `main`, além de permitir execução manual pela aba **Actions → Tests → Run workflow**.

São três jobs independentes:

- **pytest:** testes Python com Python 3.10.
- **wallet:** testes da carteira simulada com Node.js 22.
- **blockchain:** compilação e testes Solidity com Foundry v1.2.3, seguidos da integração Flask/contrato com Ganache 7.9.2.

A integração inicia uma rede descartável em `127.0.0.1:18545` (Chain ID `1337`), espera o RPC responder e encerra o processo ao terminar, inclusive em caso de falha. Usa contas de teste e arquivos temporários; não exige secrets do GitHub nem publica o aplicativo ou contratos em redes públicas. O token do workflow tem apenas permissão de leitura do conteúdo. Os resultados ficam nos logs de cada job; execuções anteriores da mesma referência são canceladas quando uma nova começa.

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
| GET | `/scoreboard/config` | Configuração pública, estado `ready` e diagnóstico da rede/contrato, sem chave privada |
| GET | `/scoreboard/scores/<player>` | Totais da carteira na rede configurada; inteiros retornados como strings decimais |
| POST | `/scoreboard/transaction` | Recebe `{"player":"0x..."}` e prepara a transação autorizada; não a envia |

## Solução de problemas

| Sintoma | O que conferir |
| --- | --- |
| Erro ao abrir `questions.json` | Crie a base inicial ou configure `QUESTIONS_FILE` com um caminho existente |
| Perguntas antigas | Inicie uma nova partida; confira qual arquivo está configurado |
| Visual antigo | Atualize com `Ctrl+Shift+R`; reinicie Flask para carregar alterações de template |
| Ganache imprime código JavaScript e encerra | Confira `node --version`; a integração foi validada com Node.js 22 e Ganache 7.9.2 |
| `forge` ou `anvil` não encontrado | Adicione `$HOME/.foundry/bin` ao PATH |
| Botão de registro ausente | Confira `.env.scoreboard`, reinicie Flask e confirme o palpite; `supersecretkey` desabilita o placar |
| Registro desabilitado ou placar indisponível | Abra **Placar na blockchain**, confira o diagnóstico e clique em **Atualizar placar** após corrigir a rede ou configuração |
| Autoridade de assinatura incorreta | Confira se `.env.scoreboard` corresponde ao contrato implantado e se uma variável exportada sobrescreve a chave |
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

A persistência JSON e o estado global do Flask ainda não foram preparados para gravações concorrentes por vários processos. O servidor iniciado por `app.py` é de desenvolvimento. Antes de publicar para múltiplos usuários, são próximos passos migrar a persistência, revisar autenticação/validação de resultados e configurar um servidor de produção. A única rede pública suportada pelo placar é a testnet Sepolia. O projeto ainda não foi preparado para mainnet ou uso competitivo.

Referências de configuração: [opções Ganache CLI](https://github.com/ConsenSys-archive/ganache) e [padrões do workspace Ganache](https://archive.trufflesuite.com/docs/ganache/reference/workspace-default-configuration/).
