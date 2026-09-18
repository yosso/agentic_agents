const { defineConfig } = require('@playwright/test');
module.exports = defineConfig({
  testDir: './browser-tests',
  workers: 1,
  use: { baseURL: 'http://127.0.0.1:31849', channel: 'chrome', headless: true },
  webServer: {
    command: 'node server.js',
    url: 'http://127.0.0.1:31849',
    env: { PORT: '31849' },
    reuseExistingServer: false,
  },
});
