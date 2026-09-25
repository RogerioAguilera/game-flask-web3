const {defineConfig} = require('cypress');
module.exports = defineConfig({
  video: false,
  viewportWidth: 1280,
  viewportHeight: 900,
  e2e: {
    baseUrl: 'http://127.0.0.1:5055',
    supportFile: false,
    specPattern: 'cypress/e2e/**/*.cy.js',
  },
});
