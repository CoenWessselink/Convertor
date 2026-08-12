import { createApp } from './app.js';
import { env } from './config/env.js';
import { repository } from './repositories/index.js';

const app = createApp();

repository.init()
  .then(() => {
    app.listen(env.port, () => {
      console.log(`Convertor API draait op http://localhost:${env.port} (${repository.mode})`);
    });
  })
  .catch((error) => {
    console.error('API start mislukt:', error);
    process.exit(1);
  });
