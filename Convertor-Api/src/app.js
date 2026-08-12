import express from 'express';
import cors from 'cors';
import authRoutes from './routes/auth-routes.js';
import jobRoutes from './routes/job-routes.js';
import { requestLogger } from './middleware/request-logger.js';
import { errorHandler } from './middleware/error-handler.js';
import { rateLimit } from './middleware/rate-limit.js';
import { repository } from './repositories/index.js';

export function createApp() {
  const app = express();
  app.use(cors());
  app.use(express.json({ limit: '10mb' }));
  app.use(requestLogger);
  app.use(rateLimit());

  app.get('/health', (req, res) => res.json({ ok: true, now: new Date().toISOString(), repository: repository.mode }));
  app.use('/auth', authRoutes);
  app.use('/jobs', jobRoutes);
  app.use(errorHandler);
  return app;
}
