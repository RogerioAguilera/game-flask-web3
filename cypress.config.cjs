const {defineConfig} = require('cypress');
module.exports = defineConfig({
  reporter: 'cypress-mochawesome-reporter',
  reporterOptions: {
    reportDir: 'cypress/reports',
    reportFilename: 'index',
    reportPageTitle: 'Game Flask — testes E2E (carteira simulada)',
    charts: true,
    embeddedScreenshots: true,
    inlineAssets: true,
    saveJson: true,
  },
  video: false,
  viewportWidth: 1280,
  viewportHeight: 900,
  e2e: {
    baseUrl: 'http://127.0.0.1:5055',
    supportFile: 'cypress/support/e2e.js',
    setupNodeEvents(on, config) {
      require('cypress-mochawesome-reporter/plugin')(on);
      return config;
    },
    specPattern: 'cypress/e2e/**/*.cy.js',
  },
});
