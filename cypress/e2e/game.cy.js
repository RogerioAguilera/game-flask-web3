const start = () => {
  cy.contains('button', 'Iniciar Jogo').click();
  cy.get('#questionText').should('have.text', 'É uma saga?');
};
const answer = (id, next) => {
  cy.get(id).should('be.enabled').click();
  if (next) cy.get('#questionText').should('have.text', next);
};

beforeEach(() => {
  cy.request('/__e2e/health').its('body.e2e').should('eq', true);
  cy.request('POST', '/__e2e/reset');
  cy.visit('/');
});

it('corrects an answer and confirms a guess', () => {
  start();
  answer('#btnNo', 'Voa?');
  answer('#btnYes');
  cy.get('#guessText').should('have.text', 'Superman');
  cy.get('#undoAnswer').click();
  cy.get('#questionText').should('have.text', 'Voa?');
  answer('#btnNo');
  cy.get('#guessText').should('have.text', 'Batman');
  cy.contains('button', 'Acertou!').click();
  cy.get('#scoreWins').should('have.text', '1');
  cy.get('#scoreTotal').should('have.text', '1');
  cy.get('#historyList').should('contain.text', 'Batman').and('not.contain.text', 'Superman');
});

it('accepts unknown and maybe, and can undo both', () => {
  start();
  answer('#btnUnknown');
  cy.get('#questionText').should('not.have.text', 'É uma saga?');
  cy.get('#btnMaybe').should('be.enabled');
  answer('#btnMaybe');
  cy.get('#undoAnswer').should('be.enabled').click();
  cy.get('#btnYes').should('be.enabled');
  cy.get('#undoAnswer').click();
  cy.get('#questionText').should('have.text', 'É uma saga?');
});

it('learns a saga without recording a successful guess', () => {
  start();
  answer('#btnYes', 'É sobre Lanternas Verdes?');
  answer('#btnNo');
  cy.get('#guessText').should('contain.text', 'Não encontrei');
  cy.get('#registerResult').should('not.be.visible');
  cy.get('#scoreTotal').should('have.text', '0');
  cy.get('#learnCharacter').type('Saga espacial');
  cy.get('#learnQuestion').type('A saga ocorre no espaço?');
  cy.get('[name=learnAnswer][value=yes]').check();
  cy.contains('button', 'Ensinar saga').click();
  cy.get('#feedbackMsg').should('contain.text', 'Aprendi');
  cy.contains('button', 'Jogar Novamente').click();
  cy.get('#questionText').should('have.text', 'É uma saga?');
  answer('#btnYes', 'É sobre Lanternas Verdes?');
  answer('#btnNo', 'A saga ocorre no espaço?');
  answer('#btnYes');
  cy.get('#guessText').should('have.text', 'Saga espacial');
});

it('learns a character after a wrong guess', () => {
  start();
  answer('#btnNo', 'Voa?');
  answer('#btnNo');
  cy.get('#guessText').should('have.text', 'Batman');
  cy.contains('button', 'Errou!').click();
  cy.get('#learnCharacter').type('Robin');
  cy.get('#learnQuestion').type('É o Robin?');
  cy.get('[name=learnAnswer][value=yes]').check();
  cy.contains('button', 'Ensinar o Gênio').click();
  cy.get('#feedbackMsg').should('contain.text', 'Aprendi');
  cy.contains('button', 'Jogar Novamente').click();
  cy.get('#questionText').should('have.text', 'É uma saga?');
  answer('#btnNo', 'Voa?');
  answer('#btnNo', 'É o Robin?');
  answer('#btnYes');
  cy.get('#guessText').should('have.text', 'Robin');
});

it('shows balance and RPC error responses', () => {
  cy.intercept('POST', '/eth_balance', {balance: '12.5'}).as('balance');
  cy.get('#ethCard summary').click();
  cy.get('#ethAddress').type('0x' + '12'.repeat(20));
  cy.get('#ethCard button').click();
  cy.wait('@balance');
  cy.get('#ethResult').should('contain.text', '12.500000');
  cy.intercept('POST', '/eth_balance', {statusCode: 502, body: {error: 'RPC indisponível'}}).as('offline');
  cy.get('#ethCard button').click();
  cy.wait('@offline');
  cy.get('#ethResult').should('contain.text', 'RPC indisponível');
});

for (const rejected of [false, true]) {
  it(rejected ? 'handles wallet rejection' : 'registers using a simulated wallet', () => {
    const player = '0x' + '12'.repeat(20);
    const contract = '0x' + '34'.repeat(20);
    const hash = '0x' + 'ab'.repeat(32);
    let sent = false;
    cy.intercept('GET', '/scoreboard/config', {
      enabled: true, ready: true, chainId: '0x7a69', chainName: 'Anvil simulado',
      rpcUrl: 'http://127.0.0.1:1', address: contract,
    });
    cy.intercept('GET', '/scoreboard/scores/*', req => req.reply({
      games: sent ? 1 : 0, correctGuesses: sent ? 1 : 0, totalQuestions: sent ? 2 : 0,
    }));
    cy.intercept('POST', '/scoreboard/transaction', {to: contract, data: '0x1234'});
    cy.visit('/', {onBeforeLoad(win) {
      win.ethereum = {
        on() {},
        async request({method, params}) {
          if (method === 'eth_accounts' || method === 'eth_requestAccounts') return [player];
          if (method === 'eth_chainId') return '0x7a69';
          if (method === 'eth_getCode') return '0x6000';
          if (method === 'eth_sendTransaction') {
            expect(params[0].from).to.equal(player);
            expect(params[0].to).to.equal(contract);
            if (rejected) throw {code: 4001};
            sent = true;
            return hash;
          }
          if (method === 'eth_getTransactionReceipt') return {status: '0x1'};
          throw new Error('Unexpected wallet method: ' + method);
        },
      };
    }});
    start();
    answer('#btnNo', 'Voa?');
    answer('#btnYes');
    cy.get('#guessText').should('have.text', 'Superman');
    cy.contains('button', 'Acertou!').click();
    cy.get('#registerResult').should('be.enabled').click();
    cy.get('#chainStatus').should('contain.text', rejected ? 'Solicitação cancelada' : 'Resultado registrado');
    if (!rejected) {
      cy.get('#registerResult').should('be.disabled');
      cy.get('#onchainPanel').invoke('prop', 'open', true);
      cy.get('#chainGames').should('have.text', '1');
    }
  });
}
