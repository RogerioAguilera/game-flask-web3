import 'cypress-mochawesome-reporter/register';

beforeEach(() => {
  cy.addTestContext('Flask real com dados temporários. Carteira e RPC simulados; nenhuma transação real é enviada.');
});
